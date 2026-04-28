/**
 * ragClient.ts — Thin facade over RagEngine for backward-compatible imports.
 *
 * The RAG engine runs entirely inside the VS Code extension runtime —
 * no Python server, no external process. Everything is Node.js:
 *   - Embeddings via Ollama HTTP API (same daemon used for Gemma)
 *   - Vector index persisted as outputs/rag/index.json
 *   - Cosine similarity search in-process
 *
 * The Python scripts/rag_index.py and scripts/rag_server.py still exist
 * as standalone CLI tools, but the extension no longer depends on them.
 *
 * Requires Ollama to be running with nomic-embed-text pulled:
 *   ollama pull nomic-embed-text
 */

import { getRagEngine, formatRagContext, RagResult, RagQueryOptions } from "./ragEngine";
import * as vscode from "vscode";

export type { RagResult, RagQueryOptions };
export { formatRagContext };

export interface RagHealth {
  running: boolean;
  docs: number;
  model: string;
}

function getRoot(): string | undefined {
  return vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
}

/**
 * Query the in-process RAG engine for relevant knowledge chunks.
 * Returns an empty array (never throws) if Ollama is unreachable or the
 * index has not been built yet.
 */
export async function queryRag(
  query: string,
  opts: RagQueryOptions = {}
): Promise<RagResult[]> {
  const root = getRoot();
  if (!root) return [];
  try {
    return await getRagEngine(root).query(query, opts);
  } catch {
    return [];
  }
}

/**
 * Check the in-process RAG engine health.
 */
export async function checkRagHealth(): Promise<RagHealth> {
  const root = getRoot();
  if (!root) return { running: false, docs: 0, model: "unknown" };
  try {
    const h = await getRagEngine(root).health();
    return { running: h.indexed, docs: h.docs, model: h.model };
  } catch {
    return { running: false, docs: 0, model: "unknown" };
  }
}

/**
 * Trigger a background re-index.
 * Runs inside Node.js — no Python server needed.
 */
export async function triggerRagReload(): Promise<void> {
  const root = getRoot();
  if (!root) return;
  const engine = getRagEngine(root);
  if (engine.isIndexing) return;
  // Fire-and-forget — the caller doesn't need to wait
  engine.index({ onProgress: (msg) => console.log("[RAG]", msg) }).catch((e) =>
    console.error("[RAG] index error:", e)
  );
}


