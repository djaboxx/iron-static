/**
 * ragEngine.ts — Self-contained local RAG engine for IRON STATIC.
 *
 * Runs entirely inside the VS Code extension — no Python process, no
 * external server. Uses:
 *   - Ollama /api/embed  for embeddings (same Ollama daemon as Gemma)
 *   - JSON file on disk  for persistent vector index
 *   - Brute-force cosine similarity  for retrieval
 *
 * For the size of this repo's corpus (~2–5k chunks) brute-force is
 * fast enough (<5ms per query) and avoids any native binary deps.
 *
 * Index is stored at outputs/rag/index.json relative to the workspace root.
 *
 * Public API:
 *   const engine = new RagEngine(workspaceRoot);
 *   await engine.index({ force: false });     // build / update index
 *   const results = await engine.query(text, { nResults: 5 });
 *   engine.health()                           // { docs, model, indexPath }
 */

import * as fs from "fs";
import * as http from "http";
import * as path from "path";
import * as crypto from "crypto";

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const EMBED_MODEL = "nomic-embed-text";
const CHUNK_SIZE = 800;       // characters
const CHUNK_OVERLAP = 150;    // character overlap
const EMBED_BATCH = 24;       // items per Ollama embed call
const OLLAMA_BASE = "http://127.0.0.1:11434";
const EMBED_TIMEOUT_MS = 60_000;

// Globs (relative to workspace root) and their document types
const INDEX_GLOBS: Array<[string, string]> = [
  ["docs/**/*.md", "doc"],
  ["knowledge/**/*.md", "knowledge"],
  ["database/*.json", "database"],
  ["instruments/*/manuals/**/*.md", "instrument-manual"],
  [".github/agents/*.agent.md", "agent"],
  [".github/skills/*/SKILL.md", "skill"],
  [".github/copilot-instructions.md", "doc"],
  [".github/instructions/*.md", "doc"],
];

// JSON files where top-level items should each become a separate chunk
const ITEMIZED_JSON = new Set([
  "database/songs.json",
  "database/ableton_devices.json",
  "database/device_library.json",
  "database/instruments.json",
]);

// ---------------------------------------------------------------------------
// Persistence types
// ---------------------------------------------------------------------------

interface IndexEntry {
  id: string;
  /** Original text chunk */
  text: string;
  /** Embedding vector */
  vector: number[];
  /** Metadata */
  source: string;
  type: string;
  title: string;
  chunk: number;
  contentHash: string;
}

interface IndexFile {
  version: 1;
  model: string;
  entries: IndexEntry[];
  /** source → contentHash for change detection */
  hashes: Record<string, string>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function chunkText(text: string): string[] {
  text = text.trim();
  if (!text) return [];
  if (text.length <= CHUNK_SIZE) return [text];
  const chunks: string[] = [];
  let start = 0;
  while (start < text.length) {
    const chunk = text.slice(start, start + CHUNK_SIZE).trim();
    if (chunk) chunks.push(chunk);
    if (start + CHUNK_SIZE >= text.length) break;
    start += CHUNK_SIZE - CHUNK_OVERLAP;
  }
  return chunks;
}

function fileHash(content: string): string {
  return crypto.createHash("sha256").update(content).digest("hex").slice(0, 16);
}

function extractTitle(content: string, filePath: string): string {
  const m = content.match(/^#\s+(.+)/m);
  return m ? m[1].trim() : path.basename(filePath, path.extname(filePath));
}

function cosine(a: number[], b: number[]): number {
  let dot = 0, normA = 0, normB = 0;
  for (let i = 0; i < a.length; i++) {
    dot += a[i] * b[i];
    normA += a[i] * a[i];
    normB += b[i] * b[i];
  }
  const denom = Math.sqrt(normA) * Math.sqrt(normB);
  return denom === 0 ? 0 : dot / denom;
}

/** Walk a glob-like pattern (supports ** and *) against workspace files. */
function walkGlob(root: string, pattern: string): string[] {
  const results: string[] = [];
  const parts = pattern.split("/");

  function matchPart(segment: string, name: string): boolean {
    if (segment === "**") return true;
    const re = new RegExp(
      "^" + segment.replace(/\./g, "\\.").replace(/\*/g, "[^/]*") + "$"
    );
    return re.test(name);
  }

  function walk(dir: string, patternParts: string[]): void {
    if (!patternParts.length) return;
    const [head, ...tail] = patternParts;

    let entries: fs.Dirent[];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }

    for (const entry of entries) {
      if (head === "**") {
        // Match current dir content with the rest of pattern
        if (tail.length) {
          walk(dir, tail);           // skip the **
          if (entry.isDirectory()) {
            walk(path.join(dir, entry.name), patternParts); // recurse with ** still active
          }
        }
      } else if (tail.length === 0) {
        // Last segment — must be a file match
        if (entry.isFile() && matchPart(head, entry.name)) {
          results.push(path.join(dir, entry.name));
        }
      } else {
        // Middle segment — must be a directory match
        if (entry.isDirectory() && matchPart(head, entry.name)) {
          walk(path.join(dir, entry.name), tail);
        }
      }
    }
  }

  walk(root, parts);
  return results;
}

// ---------------------------------------------------------------------------
// Ollama embed via raw HTTP (no npm deps)
// ---------------------------------------------------------------------------

function ollamaEmbed(texts: string[], model: string): Promise<number[][]> {
  const payload = JSON.stringify({ model, input: texts });
  return new Promise((resolve, reject) => {
    const urlObj = new URL(`${OLLAMA_BASE}/api/embed`);
    const opts: http.RequestOptions = {
      hostname: urlObj.hostname,
      port: urlObj.port,
      path: urlObj.pathname,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(payload),
      },
      timeout: EMBED_TIMEOUT_MS,
    };
    const req = http.request(opts, (res) => {
      let body = "";
      res.on("data", (c: Buffer) => { body += c.toString(); });
      res.on("end", () => {
        try {
          const parsed = JSON.parse(body) as { embeddings?: number[][]; error?: string };
          if (parsed.error) { reject(new Error(`Ollama embed error: ${parsed.error}`)); return; }
          resolve(parsed.embeddings ?? []);
        } catch (e) {
          reject(e);
        }
      });
    });
    req.on("error", reject);
    req.on("timeout", () => { req.destroy(); reject(new Error("Ollama embed timed out")); });
    req.write(payload);
    req.end();
  });
}

// ---------------------------------------------------------------------------
// RagEngine
// ---------------------------------------------------------------------------

export interface RagResult {
  text: string;
  source: string;
  type: string;
  title: string;
  score: number;
}

export interface IndexOptions {
  /** Re-index all files even if content hash is unchanged */
  force?: boolean;
  /** Override embedding model */
  model?: string;
  /** Progress callback */
  onProgress?: (msg: string) => void;
}

export interface RagQueryOptions {
  nResults?: number;
  filterType?: string;
}

export interface RagEngineHealth {
  indexed: boolean;
  docs: number;
  model: string;
  indexPath: string;
  ollamaReachable: boolean;
}

export class RagEngine {
  private readonly workspaceRoot: string;
  private readonly indexPath: string;
  private _index: IndexFile | null = null;
  private _indexing = false;

  constructor(workspaceRoot: string) {
    this.workspaceRoot = workspaceRoot;
    this.indexPath = path.join(workspaceRoot, "outputs", "rag", "index.json");
  }

  // ------------------------------------------------------------------
  // Load / save
  // ------------------------------------------------------------------

  private loadIndex(): IndexFile {
    if (this._index) return this._index;
    if (fs.existsSync(this.indexPath)) {
      try {
        const raw = fs.readFileSync(this.indexPath, "utf-8");
        this._index = JSON.parse(raw) as IndexFile;
        return this._index;
      } catch {
        // Corrupt — rebuild
      }
    }
    this._index = { version: 1, model: EMBED_MODEL, entries: [], hashes: {} };
    return this._index;
  }

  private saveIndex(idx: IndexFile): void {
    const dir = path.dirname(this.indexPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    fs.writeFileSync(this.indexPath, JSON.stringify(idx), "utf-8");
    this._index = idx;
  }

  // ------------------------------------------------------------------
  // Health
  // ------------------------------------------------------------------

  async health(): Promise<RagEngineHealth> {
    const idx = this.loadIndex();
    let ollamaReachable = false;
    try {
      await ollamaEmbed(["ping"], idx.model || EMBED_MODEL);
      ollamaReachable = true;
    } catch {
      // not reachable
    }
    return {
      indexed: idx.entries.length > 0,
      docs: idx.entries.length,
      model: idx.model || EMBED_MODEL,
      indexPath: this.indexPath,
      ollamaReachable,
    };
  }

  // ------------------------------------------------------------------
  // Query
  // ------------------------------------------------------------------

  async query(queryText: string, opts: RagQueryOptions = {}): Promise<RagResult[]> {
    const { nResults = 5, filterType } = opts;
    const idx = this.loadIndex();
    if (!idx.entries.length) return [];

    let candidates = idx.entries;
    if (filterType) {
      candidates = candidates.filter((e) => e.type === filterType);
      if (!candidates.length) return [];
    }

    const model = idx.model || EMBED_MODEL;
    let queryVec: number[];
    try {
      const vecs = await ollamaEmbed([queryText], model);
      queryVec = vecs[0];
    } catch {
      return [];
    }
    if (!queryVec?.length) return [];

    const scored = candidates.map((e) => ({
      entry: e,
      score: cosine(queryVec, e.vector),
    }));
    scored.sort((a, b) => b.score - a.score);

    return scored.slice(0, nResults).map(({ entry, score }) => ({
      text: entry.text,
      source: entry.source,
      type: entry.type,
      title: entry.title,
      score: Math.round(score * 10000) / 10000,
    }));
  }

  // ------------------------------------------------------------------
  // Index
  // ------------------------------------------------------------------

  get isIndexing(): boolean {
    return this._indexing;
  }

  /** Build or update the index. Runs in-process (call from a background task). */
  async index(opts: IndexOptions = {}): Promise<{ added: number; skipped: number; errors: number }> {
    if (this._indexing) {
      return { added: 0, skipped: 0, errors: 0 };
    }
    this._indexing = true;
    let added = 0, skipped = 0, errors = 0;

    try {
      const model = opts.model ?? EMBED_MODEL;
      const idx = opts.force
        ? { version: 1 as const, model, entries: [], hashes: {} }
        : this.loadIndex();
      idx.model = model;

      const log = opts.onProgress ?? (() => undefined);

      // Collect all file paths
      const files: Array<{ absPath: string; relPath: string; docType: string }> = [];
      for (const [glob, docType] of INDEX_GLOBS) {
        const matches = walkGlob(this.workspaceRoot, glob);
        for (const absPath of matches) {
          const relPath = path.relative(this.workspaceRoot, absPath);
          files.push({ absPath, relPath, docType });
        }
      }

      log(`Indexing ${files.length} files...`);

      for (const { absPath, relPath, docType } of files) {
        let content: string;
        try {
          content = fs.readFileSync(absPath, "utf-8");
        } catch (e) {
          log(`  ERROR reading ${relPath}: ${(e as Error).message}`);
          errors++;
          continue;
        }
        if (!content.trim()) continue;

        const h = fileHash(content);
        if (!opts.force && idx.hashes[relPath] === h) {
          skipped++;
          continue;
        }

        // Remove old entries for this source
        idx.entries = idx.entries.filter((e) => e.source !== relPath);

        let chunks: string[];
        if (absPath.endsWith(".json")) {
          const isItemized = ITEMIZED_JSON.has(relPath.replace(/\\/g, "/"));
          if (isItemized) {
            try {
              const data = JSON.parse(content);
              const items: unknown[] = Array.isArray(data) ? data : Object.values(data);
              chunks = items.map((item) => JSON.stringify(item, null, 2));
            } catch {
              chunks = chunkText(JSON.stringify(JSON.parse(content), null, 2));
            }
          } else {
            try {
              chunks = chunkText(JSON.stringify(JSON.parse(content), null, 2));
            } catch {
              chunks = chunkText(content);
            }
          }
        } else {
          chunks = chunkText(content);
        }

        const title = absPath.endsWith(".json")
          ? relPath
          : extractTitle(content, relPath);

        // Embed in batches
        for (let bStart = 0; bStart < chunks.length; bStart += EMBED_BATCH) {
          const batch = chunks.slice(bStart, bStart + EMBED_BATCH);
          let vectors: number[][];
          try {
            vectors = await ollamaEmbed(batch, model);
          } catch (e) {
            log(`  ERROR embedding ${relPath}: ${(e as Error).message}`);
            errors++;
            break;
          }
          for (let i = 0; i < batch.length; i++) {
            const chunkIndex = bStart + i;
            idx.entries.push({
              id: `${relPath}::c${chunkIndex}`,
              text: batch[i],
              vector: vectors[i],
              source: relPath,
              type: docType,
              title,
              chunk: chunkIndex,
              contentHash: h,
            });
            added++;
          }
        }

        idx.hashes[relPath] = h;
        this.saveIndex(idx);  // save after each file so progress survives restarts
        log(`  ✓ ${relPath} (${chunks.length} chunks)`);
      }

      log(`\nDone. Added ${added} chunks, skipped ${skipped} files, errors: ${errors}. Total: ${idx.entries.length}`);
    } finally {
      this._indexing = false;
    }

    return { added, skipped, errors };
  }
}

// ---------------------------------------------------------------------------
// Singleton management (one engine per workspace root)
// ---------------------------------------------------------------------------

const engines = new Map<string, RagEngine>();

export function getRagEngine(workspaceRoot: string): RagEngine {
  let engine = engines.get(workspaceRoot);
  if (!engine) {
    engine = new RagEngine(workspaceRoot);
    engines.set(workspaceRoot, engine);
  }
  return engine;
}

// ---------------------------------------------------------------------------
// formatRagContext helper (re-exported for chat participants)
// ---------------------------------------------------------------------------

export function formatRagContext(
  results: RagResult[],
  header = "## Retrieved Knowledge Context"
): string {
  if (!results.length) return "";
  const blocks = results.map((r, i) => {
    const sourceTag = r.source ? ` _[${r.source}]_` : "";
    return `### [${i + 1}] ${r.title}${sourceTag}\n\n${r.text}`;
  });
  return [header, "", ...blocks].join("\n\n");
}
