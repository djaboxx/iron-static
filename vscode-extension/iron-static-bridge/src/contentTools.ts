/**
 * IRON STATIC Content Generation LM Tools
 *
 * Native TypeScript implementations — no Python script shelling.
 *
 * Tools:
 *   iron-static_generatePromoImage   — Imagen 4 still image generation
 *   iron-static_generatePromoVideo   — Veo 3 AI video generation (polls to completion)
 *   iron-static_renderWaveformVideo  — ffmpeg waveform visualizer (spawns ffmpeg binary directly)
 */

import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import * as cp from "child_process";
import { GoogleGenAI, type GenerateVideosConfig } from "@google/genai";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const WAVEFORM_COLOR = "0xb0e8ff";  // cold metallic blue-white
const BG_COLOR       = "0x0a0a0a";  // near-black
const ACCENT_COLOR   = "0x2a2a2a";  // dark grey letterbox bars

const FORMAT_SPECS: Record<string, { w: number; h: number; aspect: string }> = {
  landscape: { w: 1920, h: 1080, aspect: "16:9" },
  square:    { w: 1080, h: 1080, aspect: "1:1"  },
  portrait:  { w: 1080, h: 1920, aspect: "9:16" },
};

const VEO_NEGATIVE_PROMPT =
  "people, faces, hands, bright colors, cheerful, pastel, nature, animals, " +
  "cartoon, anime, illustrated, stock video, stage lighting, warm tones, " +
  "DJ equipment, guitar, generic music video cliches";

const VEO_BASE_STYLE =
  "dark industrial aesthetic, high contrast, no people, no faces, " +
  "machine textures, rust and corroded metal, electronic components in motion, " +
  "harsh cold lighting, black background with electric blue accent colors, " +
  "cinematic slow motion, photorealistic not illustrated";

const IMAGEN_BASE_STYLE =
  "IRON STATIC band aesthetic: dark industrial, corroded metal textures, " +
  "electric discharge, machine components, cold blue-white accent colors, " +
  "absolute black void background, ultra high contrast, photorealistic";

const IMAGEN_NEGATIVE_PROMPT =
  "people, faces, cheerful, pastel, warm tones, nature, animals, cartoon, " +
  "anime, illustrated, stock photo, generic, text, typography, letters, words";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getWorkspaceRoot(): string {
  const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (!root) { throw new Error("No workspace open — open the iron-static repo folder first."); }
  return root;
}

function getApiKey(): string {
  const key = process.env["GEMINI_API_KEY"] ?? process.env["GOOGLE_API_KEY"] ?? "";
  if (!key) { throw new Error("GEMINI_API_KEY or GOOGLE_API_KEY environment variable is not set."); }
  return key;
}

function readActiveSong(root: string): { title: string; slug: string; key?: string; scale?: string; bpm?: number; brainstorm_path?: string } | null {
  const db = JSON.parse(fs.readFileSync(path.join(root, "database", "songs.json"), "utf-8")) as { songs?: Array<Record<string, unknown>> };
  const songs = db.songs ?? [];
  return (songs.find((s) => s["status"] === "active") ?? null) as ReturnType<typeof readActiveSong>;
}

function readBrainstorm(root: string, brainstormPath: string | undefined): string {
  if (!brainstormPath) { return ""; }
  const full = path.isAbsolute(brainstormPath) ? brainstormPath : path.join(root, brainstormPath);
  if (!fs.existsSync(full)) { return ""; }
  return fs.readFileSync(full, "utf-8").slice(0, 2000);
}

function buildSongPrompt(song: ReturnType<typeof readActiveSong>, brainstorm: string, extraStyle: string): string {
  if (!song) { return [extraStyle, VEO_BASE_STYLE].filter(Boolean).join(" "); }
  const seedLines = brainstorm.split("\n").map((l) => l.trim()).filter((l) => l && !l.startsWith("#"));
  const seed = seedLines[0] ?? "";
  return [
    `Short abstract promo for '${song.title}' by IRON STATIC, an electronic metal band.`,
    seed || "Industrial electronic machine textures.",
    song.key ? `Musical energy: ${song.key} ${song.scale ?? ""} — heavy, mechanical, abrasive.` : "",
    extraStyle,
    VEO_BASE_STYLE,
  ].filter(Boolean).join(" ");
}

function nextOutputPath(root: string, slug: string, prefix: string, format: string, ext: string): string {
  const dir = path.join(root, "outputs", "social");
  fs.mkdirSync(dir, { recursive: true });
  let n = 1;
  while (true) {
    const candidate = path.join(dir, `${slug}_${prefix}_${format}_v${n}.${ext}`);
    if (!fs.existsSync(candidate)) { return candidate; }
    n++;
  }
}

function spawnSync(bin: string, args: string[], cwd: string): { code: number; stdout: string; stderr: string } {
  return new Promise<{ code: number; stdout: string; stderr: string }>((resolve) => {
    const proc = cp.spawn(bin, args, { cwd });
    let stdout = "", stderr = "";
    proc.stdout.on("data", (d: Buffer) => { stdout += d.toString(); });
    proc.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });
    proc.on("close", (code) => resolve({ code: code ?? 1, stdout, stderr }));
  }) as unknown as { code: number; stdout: string; stderr: string };
}

// ---------------------------------------------------------------------------
// Tool: generatePromoImage  (Imagen 4)
// ---------------------------------------------------------------------------

export interface GeneratePromoImageInput {
  /** Extra style / subject description to inject into the prompt */
  style?: string;
  /** Song slug — defaults to active song */
  song_slug?: string;
  /** Output format(s): landscape, square, portrait */
  formats?: string[];
  /** Brand image (not song-specific) */
  brand?: boolean;
  /** Number of images to generate (1–4) */
  count?: number;
}

export class GeneratePromoImageTool implements vscode.LanguageModelTool<GeneratePromoImageInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<GeneratePromoImageInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const { style = "", song_slug, formats = ["square"], brand = false, count = 1 } = options.input;
    const root = getWorkspaceRoot();

    let apiKey: string;
    try { apiKey = getApiKey(); } catch (e) {
      return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: (e as Error).message }))]);
    }

    const client = new GoogleGenAI({ apiKey });

    // Resolve song context
    const song = song_slug
      ? (() => { const db = JSON.parse(fs.readFileSync(path.join(root, "database", "songs.json"), "utf-8")) as { songs?: Array<Record<string, unknown>> }; return db.songs?.find((s) => s["slug"] === song_slug) ?? null; })()
      : readActiveSong(root);

    const slug = brand ? "brand" : (song_slug ?? song?.slug ?? "unknown");
    const brainstorm = brand ? "" : readBrainstorm(root, (song as { brainstorm_path?: string } | null)?.brainstorm_path);

    // Build prompt
    const promptParts = brand
      ? [style || "Extreme closeup of iron filaments magnetized into a standing wave, cobalt electric discharge crackling through corroded circuit traces", IMAGEN_BASE_STYLE]
      : [
          `Album art for '${(song as { title?: string } | null)?.title ?? slug}' by IRON STATIC.`,
          brainstorm.split("\n").find((l) => l.trim() && !l.startsWith("#"))?.trim() ?? "",
          style,
          IMAGEN_BASE_STYLE,
        ];
    const prompt = promptParts.filter(Boolean).join(" ");

    const outputPaths: string[] = [];
    const errors: string[] = [];

    for (const fmt of formats) {
      const aspectRatio = FORMAT_SPECS[fmt]?.aspect ?? "1:1";
      try {
        const response = await (client.models as unknown as {
          generateImages: (opts: {
            model: string;
            prompt: string;
            config: {
              numberOfImages: number;
              aspectRatio: string;
              negativePrompt: string;
              personGeneration: string;
            };
          }) => Promise<{ generatedImages?: Array<{ image?: { imageBytes?: string } }> }>;
        }).generateImages({
          model: "imagen-4.0-generate-001",
          prompt,
          config: {
            numberOfImages: Math.min(count, 4),
            aspectRatio,
            negativePrompt: IMAGEN_NEGATIVE_PROMPT,
            personGeneration: "dont_allow",
          },
        });

        const images = response.generatedImages ?? [];
        for (let i = 0; i < images.length; i++) {
          const imageBytes = images[i]?.image?.imageBytes;
          if (!imageBytes) { continue; }
          const outPath = nextOutputPath(root, slug, "cover", fmt, "png");
          fs.writeFileSync(outPath, Buffer.from(imageBytes, "base64"));
          outputPaths.push(outPath);
        }
      } catch (e) {
        errors.push(`${fmt}: ${(e as Error).message}`);
      }
    }

    return new vscode.LanguageModelToolResult([
      new vscode.LanguageModelTextPart(JSON.stringify({
        success: outputPaths.length > 0,
        saved: outputPaths,
        prompt,
        errors: errors.length ? errors : undefined,
      })),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Tool: generatePromoVideo  (Veo 3)
// ---------------------------------------------------------------------------

export interface GeneratePromoVideoInput {
  /** Extra style clause */
  style?: string;
  /** Full prompt override (skips auto-build) */
  prompt?: string;
  /** Song slug — defaults to active song */
  song_slug?: string;
  /** Output format: landscape | square | portrait */
  format?: string;
  /** Duration in seconds (5–8) */
  duration?: number;
  /** Number of videos (1–4) */
  count?: number;
  /** Path to input image for image-to-video (relative to repo root) */
  image_path?: string;
  /** Use 1080p (default 720p) */
  hd?: boolean;
  /** Let Veo generate audio (default false — we supply our own) */
  with_audio?: boolean;
}

export class GeneratePromoVideoTool implements vscode.LanguageModelTool<GeneratePromoVideoInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<GeneratePromoVideoInput>,
    token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const {
      style = "", prompt: promptOverride, song_slug, format = "landscape",
      duration = 8, count = 1, image_path, hd = false, with_audio = false,
    } = options.input;

    const root = getWorkspaceRoot();

    let apiKey: string;
    try { apiKey = getApiKey(); } catch (e) {
      return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: (e as Error).message }))]);
    }

    const client = new GoogleGenAI({ apiKey });

    const song = song_slug
      ? (() => { const db = JSON.parse(fs.readFileSync(path.join(root, "database", "songs.json"), "utf-8")) as { songs?: Array<Record<string, unknown>> }; return (db.songs?.find((s) => s["slug"] === song_slug) ?? null) as typeof readActiveSong extends (...args: unknown[]) => infer R ? R : never; })()
      : readActiveSong(root);

    const slug = song_slug ?? song?.slug ?? "unknown";
    const brainstorm = readBrainstorm(root, (song as { brainstorm_path?: string } | null)?.brainstorm_path);
    const prompt = promptOverride ?? buildSongPrompt(song, brainstorm, style);

    const fmtSpec = FORMAT_SPECS[format] ?? FORMAT_SPECS["landscape"];

    // Resolve optional input image
    let imageInput: { imageBytes: string; mimeType: string } | undefined;
    if (image_path) {
      const imgFull = path.isAbsolute(image_path) ? image_path : path.join(root, image_path);
      if (fs.existsSync(imgFull)) {
        imageInput = {
          imageBytes: fs.readFileSync(imgFull).toString("base64"),
          mimeType: imgFull.endsWith(".png") ? "image/png" : "image/jpeg",
        };
      }
    }

    const config: GenerateVideosConfig = {
      numberOfVideos: Math.min(count, 4) as 1 | 2 | 3 | 4,
      aspectRatio: fmtSpec.aspect as "16:9" | "9:16" | "1:1",
      durationSeconds: Math.min(Math.max(duration, 5), 8),
      personGeneration: "dont_allow" as const,
      negativePrompt: VEO_NEGATIVE_PROMPT,
    };

    // Try Veo 3, fall back to Veo 2
    const models = ["veo-3.0-generate-preview", "veo-2.0-generate-001"];
    let operation: Awaited<ReturnType<typeof client.models.generateVideos>> | null = null;
    let usedModel = "";

    for (const model of models) {
      if (token.isCancellationRequested) {
        return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: "Cancelled." }))]);
      }
      try {
        operation = await client.models.generateVideos({
          model,
          prompt,
          ...(imageInput ? { image: imageInput } : {}),
          config,
        });
        usedModel = model;
        break;
      } catch (e) {
        const msg = (e as Error).message ?? "";
        if (msg.includes("not found") || msg.includes("404") || msg.includes("INVALID_ARGUMENT")) {
          continue; // try fallback
        }
        return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: msg }))]);
      }
    }

    if (!operation) {
      return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: "No Veo model available." }))]);
    }

    // Poll until done (max 10 minutes)
    const deadline = Date.now() + 600_000;
    while (!operation.done) {
      if (token.isCancellationRequested) {
        return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: "Cancelled while polling." }))]);
      }
      if (Date.now() > deadline) {
        return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: "Timed out after 10 minutes waiting for Veo." }))]);
      }
      await new Promise((r) => setTimeout(r, 15_000));
      operation = await client.operations.getVideosOperation({ operation });
    }

    if (operation.error) {
      return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: String(operation.error) }))]);
    }

    const videos = operation.response?.generatedVideos ?? [];
    if (!videos.length) {
      return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: "Veo returned no videos." }))]);
    }

    const outputPaths: string[] = [];
    for (const gen of videos) {
      const videoBytes: string | undefined = (gen as unknown as { video?: { videoBytes?: string } }).video?.videoBytes;
      const videoUri: string | undefined = (gen as unknown as { video?: { uri?: string } }).video?.uri;

      const outPath = nextOutputPath(root, slug, "veo", format, "mp4");

      if (videoBytes) {
        fs.writeFileSync(outPath, Buffer.from(videoBytes, "base64"));
        outputPaths.push(outPath);
      } else if (videoUri) {
        // GCS URI — let the agent know to download it
        outputPaths.push(`gcs:${videoUri}`);
      }
    }

    return new vscode.LanguageModelToolResult([
      new vscode.LanguageModelTextPart(JSON.stringify({
        success: outputPaths.length > 0,
        model: usedModel,
        saved: outputPaths,
        prompt,
        format,
        duration: config.durationSeconds,
      })),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Tool: renderWaveformVideo  (ffmpeg — direct binary spawn, no Python)
// ---------------------------------------------------------------------------

export interface RenderWaveformVideoInput {
  /** Path to audio file relative to repo root, e.g. audio/generated/foo.mp3 */
  audio_path: string;
  /** Optional cover art image relative to repo root */
  cover_path?: string;
  /** Output format(s): landscape | square | portrait */
  formats?: string[];
  /** Duration cap in seconds (default: auto-detect, max 60) */
  duration?: number;
}

export class RenderWaveformVideoTool implements vscode.LanguageModelTool<RenderWaveformVideoInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<RenderWaveformVideoInput>,
    token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const { audio_path, cover_path, formats = ["landscape"], duration } = options.input;
    const root = getWorkspaceRoot();

    // Resolve paths
    const audioFull = path.isAbsolute(audio_path) ? audio_path : path.join(root, audio_path);
    if (!fs.existsSync(audioFull)) {
      return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: `Audio not found: ${audio_path}` }))]);
    }
    const coverFull = cover_path
      ? (path.isAbsolute(cover_path) ? cover_path : path.join(root, cover_path))
      : undefined;
    const hasCover = !!coverFull && fs.existsSync(coverFull);

    // Detect duration via ffprobe if not provided
    let dur = duration ?? await this.detectDuration(audioFull);
    if (!dur || dur > 60) { dur = Math.min(dur ?? 60, 60); }

    // Derive slug from audio filename for output naming
    const base = path.basename(audioFull, path.extname(audioFull));
    const slug = base.includes("_") ? base.split("_")[0] : base;

    const outDir = path.join(root, "outputs", "social");
    fs.mkdirSync(outDir, { recursive: true });

    const results: Record<string, string> = {};
    const errors: string[] = [];

    for (const fmt of formats) {
      if (token.isCancellationRequested) { break; }
      const spec = FORMAT_SPECS[fmt];
      if (!spec) { errors.push(`Unknown format: ${fmt}`); continue; }

      const outPath = path.join(outDir, `${slug}_visualizer_${fmt}.mp4`);
      const cmd = this.buildFfmpegArgs(audioFull, coverFull, hasCover, outPath, spec.w, spec.h, dur);

      const result = await new Promise<{ code: number; stderr: string }>((resolve) => {
        const proc = cp.spawn("ffmpeg", cmd, { cwd: root });
        let stderr = "";
        proc.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });
        token.onCancellationRequested(() => proc.kill("SIGTERM"));
        proc.on("close", (code) => resolve({ code: code ?? 1, stderr }));
      });

      if (result.code === 0) {
        results[fmt] = outPath;
      } else {
        errors.push(`${fmt}: ffmpeg exited ${result.code} — ${result.stderr.slice(-500)}`);
      }
    }

    return new vscode.LanguageModelToolResult([
      new vscode.LanguageModelTextPart(JSON.stringify({
        success: Object.keys(results).length > 0,
        rendered: results,
        duration: dur,
        errors: errors.length ? errors : undefined,
      })),
    ]);
  }

  private buildFfmpegArgs(
    audioPath: string, coverPath: string | undefined, hasCover: boolean,
    outPath: string, w: number, h: number, duration: number
  ): string[] {
    const args: string[] = ["-y"];
    if (hasCover && coverPath) {
      args.push("-loop", "1", "-i", coverPath);
      args.push("-i", audioPath);
    } else {
      args.push("-i", audioPath);
    }
    args.push("-t", String(duration));

    if (hasCover) {
      args.push("-filter_complex",
        `[0:v]scale=${w}:${h}:force_original_aspect_ratio=decrease,` +
        `pad=${w}:${h}:(ow-iw)/2:(oh-ih)/2:color=${ACCENT_COLOR}[bg];` +
        `[1:a]showwaves=s=${w}x${h}:mode=cline:rate=30:colors=${WAVEFORM_COLOR}:scale=sqrt[wave];` +
        `[bg][wave]blend=all_mode=screen[out]`,
        "-map", "[out]", "-map", "1:a",
      );
    } else {
      args.push("-filter_complex",
        `color=c=${BG_COLOR}:s=${w}x${h}:r=30[bg];` +
        `[0:a]showwaves=s=${w}x${h}:mode=cline:rate=30:colors=${WAVEFORM_COLOR}:scale=sqrt[wave];` +
        `[bg][wave]blend=all_mode=screen[out]`,
        "-map", "[out]", "-map", "0:a",
      );
    }

    args.push(
      "-c:v", "libx264", "-preset", "slow", "-crf", "18",
      "-pix_fmt", "yuv420p",
      "-c:a", "aac", "-b:a", "320k",
      "-movflags", "+faststart",
      outPath,
    );
    return args;
  }

  private detectDuration(audioPath: string): Promise<number | null> {
    return new Promise((resolve) => {
      const proc = cp.spawn("ffprobe", [
        "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", audioPath,
      ]);
      let out = "";
      proc.stdout.on("data", (d: Buffer) => { out += d.toString(); });
      proc.on("close", () => {
        const val = parseFloat(out.trim());
        resolve(isNaN(val) ? null : val);
      });
      proc.on("error", () => resolve(null));
    });
  }
}

// ---------------------------------------------------------------------------
// Tool: buildVideoPrompt  (Gemini Flash → rich Veo 3 prompt)
// ---------------------------------------------------------------------------

export interface BuildVideoPromptInput {
  /** Song slug — defaults to active song */
  song_slug?: string;
  /** Output format being targeted: landscape | square | portrait */
  format?: string;
  /** Focus within the brainstorm — which section to emphasize: "idea" | "sound" | "concept" | "arrangement" */
  focus?: "idea" | "sound" | "concept" | "arrangement";
  /** Additional director note or constraint to include */
  director_note?: string;
  /** How many prompt variants to generate (1–3, default 1) */
  variants?: number;
}

interface VisualStyle {
  description: string;
  palette: { primary_accent: { description: string }; background: { description: string }; secondary_accent: { description: string }; prohibition: string };
  motion: { camera_speed: string; primary_movements: string[]; pacing: string; prohibition: string };
  imagery: { vocabulary: Array<{ name: string; description: string; psychological_effect: string }>; prohibition: string };
  psychology: { primary_targets: string[]; the_distinction: string };
  veo_prompt_structure: { description: string; components: string[] };
  per_format_notes: Record<string, string>;
  negative_prompt: string;
}

export class BuildVideoPromptTool implements vscode.LanguageModelTool<BuildVideoPromptInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<BuildVideoPromptInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const { song_slug, format = "landscape", focus = "concept", director_note = "", variants = 1 } = options.input;
    const root = getWorkspaceRoot();

    let apiKey: string;
    try { apiKey = getApiKey(); } catch (e) {
      return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: (e as Error).message }))]);
    }
    const client = new GoogleGenAI({ apiKey });

    // --- Load brand visual style guide ---
    const styleFile = path.join(root, "database", "visual-style.json");
    if (!fs.existsSync(styleFile)) {
      return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: "database/visual-style.json not found. The brand visual identity must be defined before generating prompts." }))]);
    }
    const style: VisualStyle = JSON.parse(fs.readFileSync(styleFile, "utf-8"));

    // --- Load song + brainstorm ---
    const song = song_slug
      ? (() => { const db = JSON.parse(fs.readFileSync(path.join(root, "database", "songs.json"), "utf-8")) as { songs?: Array<Record<string, unknown>> }; return db.songs?.find((s) => s["slug"] === song_slug) ?? null; })()
      : readActiveSong(root);

    const slug = song_slug ?? (song as { slug?: string } | null)?.slug ?? "brand";
    const brainstormRaw = readBrainstorm(root, (song as { brainstorm_path?: string } | null)?.brainstorm_path);

    // Extract the most visually evocative brainstorm sections
    const brainstormSections = this.extractBrainstormSections(brainstormRaw, focus);

    // --- Format-specific note ---
    const formatNote = style.per_format_notes[`${format}_${format === "landscape" ? "16_9" : format === "square" ? "1_1" : "9_16"}`] ?? "";

    // --- Build system prompt for Gemini ---
    const systemPrompt = this.buildSystemPrompt(style, brainstormSections, song, format, formatNote, director_note, variants);

    // --- Call Gemini Flash ---
    let rawText = "";
    try {
      const response = await client.models.generateContent({
        model: "gemini-2.0-flash",
        contents: systemPrompt,
        config: { temperature: 0.9, maxOutputTokens: 1500 },
      });
      rawText = (response as unknown as { text?: string }).text ?? "";
    } catch (e) {
      return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: `Gemini error: ${(e as Error).message}` }))]);
    }

    // Parse variants if multiple were requested
    const parsedVariants = this.parseVariants(rawText, variants);

    return new vscode.LanguageModelToolResult([
      new vscode.LanguageModelTextPart(JSON.stringify({
        success: true,
        slug,
        format,
        focus,
        variants: parsedVariants,
        negative_prompt: style.negative_prompt,
        note: "Pass variants[0].prompt (or your chosen variant) to iron-static_generatePromoVideo as the 'prompt' field.",
      })),
    ]);
  }

  private extractBrainstormSections(raw: string, focus: string): string {
    if (!raw) { return ""; }
    const sectionMap: Record<string, string[]> = {
      idea: ["## 1.", "## Song Idea"],
      sound: ["## 3.", "## Sound Design"],
      concept: ["## 5.", "## Conceptual Direction"],
      arrangement: ["## 2.", "## Arrangement"],
    };
    const headers = sectionMap[focus] ?? sectionMap["concept"];

    const lines = raw.split("\n");
    let capturing = false;
    const collected: string[] = [];

    for (const line of lines) {
      const isTarget = headers.some((h) => line.startsWith(h));
      const isNewSection = line.startsWith("## ") && !isTarget;

      if (isTarget) { capturing = true; continue; }
      if (isNewSection && capturing) { break; }
      if (capturing) { collected.push(line); }
    }

    // If nothing found, return first 600 chars
    return collected.length ? collected.join("\n").slice(0, 800) : raw.slice(0, 600);
  }

  private buildSystemPrompt(
    style: VisualStyle, brainstorm: string, song: ReturnType<typeof readActiveSong>,
    format: string, formatNote: string, directorNote: string, variants: number
  ): string {
    const songLine = song
      ? `Song: "${(song as { title?: string }).title}" by IRON STATIC — ${(song as { key?: string }).key ?? ""} ${(song as { scale?: string }).scale ?? ""} @ ${(song as { bpm?: number }).bpm ?? ""}BPM`
      : "Song: IRON STATIC brand video — no specific track";

    const imageryList = style.imagery.vocabulary
      .map((v, i) => `  ${i + 1}. ${v.name}: ${v.description} (effect: ${v.psychological_effect})`)
      .join("\n");

    const motionList = style.motion.primary_movements
      .map((m, i) => `  ${i + 1}. ${m}`)
      .join("\n");

    const variantInstruction = variants > 1
      ? `Generate ${variants} distinct prompt variants. Label each one:\n### VARIANT 1\n[prompt]\n### VARIANT 2\n[prompt]\netc.`
      : "Generate one prompt.";

    return `You are a creative director for IRON STATIC, a dark electronic-metal band. Your task is to write a precise, cinematic prompt for Google Veo 3 AI video generation.

=== BRAND VISUAL IDENTITY ===
${style.description}

COLOR LANGUAGE:
- Background: ${style.palette.background.description}
- Primary accent: ${style.palette.primary_accent.description}
- Danger signal: ${style.palette.secondary_accent.description}
- NEVER: ${style.palette.prohibition}

MOTION LANGUAGE:
${style.motion.camera_speed}
Available camera movements:
${motionList}
NEVER: ${style.motion.prohibition}

VISUAL VOCABULARY (these are the motifs we return to):
${imageryList}
NEVER SHOW: ${style.imagery.prohibition}

PSYCHOLOGICAL TARGETS:
${style.psychology.primary_targets.map((t) => `- ${t}`).join("\n")}
The distinction: ${style.psychology.the_distinction}

=== SONG / CONTEXT ===
${songLine}
Target format: ${format} — ${formatNote}
${directorNote ? `Director note: ${directorNote}` : ""}

Brainstorm content (the emotional and sonic idea this video must serve):
---
${brainstorm || "No brainstorm available — generate from brand identity only."}
---

=== PROMPT STRUCTURE ===
${style.veo_prompt_structure.description}
Write in this order:
${style.veo_prompt_structure.components.map((c, i) => `${i + 1}. ${c}`).join("\n")}

=== YOUR TASK ===
Write a Veo 3 video prompt that:
1. Captures the EMOTIONAL CORE of the brainstorm content — not literally illustrates it, but makes the viewer feel what the music is
2. Uses SPECIFIC, CONCRETE visual descriptions — not mood adjectives alone
3. Draws from the visual vocabulary above — at least one of the 7 motifs should appear
4. Obeys the format-specific guidance for ${format}
5. Is 150-350 words — dense and specific, not padded
6. Ends with: "Photorealistic. No people. No faces. Cinematic slow motion. 4K. Ultra high contrast."

${variantInstruction}

Write only the prompt text. No explanation, no preamble.`;
  }

  private parseVariants(text: string, count: number): Array<{ label: string; prompt: string }> {
    if (count === 1) {
      return [{ label: "v1", prompt: text.trim() }];
    }
    const parts = text.split(/###\s*VARIANT\s*\d+/i).map((p) => p.trim()).filter(Boolean);
    if (parts.length >= count) {
      return parts.slice(0, count).map((p, i) => ({ label: `v${i + 1}`, prompt: p }));
    }
    // Fallback: treat whole text as one variant
    return [{ label: "v1", prompt: text.trim() }];
  }
}

// ---------------------------------------------------------------------------
// Tool: generateStoryboardVideo
//   Gemini → storyboard JSON
//   Imagen 4 → keyframe image per scene
//   Veo 2 image-to-video → 8s clip per scene
//   ffmpeg concat → single stitched MP4
// ---------------------------------------------------------------------------

export interface GenerateStoryboardVideoInput {
  /** Song slug — defaults to active song */
  song_slug?: string;
  /** Number of scenes to generate (2–5, default 3) */
  scenes?: number;
  /** Output format: landscape | square | portrait */
  format?: string;
  /** Extra direction for Gemini storyboard (e.g. "focus on the machine waking up") */
  director_note?: string;
  /** Seed image path (relative to repo root) — used as visual anchor for scene 1 */
  seed_image?: string;
}

interface StoryboardScene {
  id: number;
  description: string;
  image_prompt: string;
  animation_prompt: string;
}

interface Storyboard {
  title: string;
  arc: string;
  scenes: StoryboardScene[];
}

export class GenerateStoryboardVideoTool implements vscode.LanguageModelTool<GenerateStoryboardVideoInput> {

  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<GenerateStoryboardVideoInput>,
    token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const { song_slug, scenes: sceneCount = 3, format = "landscape", director_note = "", seed_image } = options.input;
    const numScenes = Math.min(Math.max(sceneCount, 2), 5);

    const root = getWorkspaceRoot();

    let apiKey: string;
    try { apiKey = getApiKey(); } catch (e) {
      return err((e as Error).message);
    }

    const client = new GoogleGenAI({ apiKey });

    const song = song_slug
      ? (() => { const db = JSON.parse(fs.readFileSync(path.join(root, "database", "songs.json"), "utf-8")) as { songs?: Array<Record<string, unknown>> }; return db.songs?.find((s) => s["slug"] === song_slug) ?? null; })()
      : readActiveSong(root);
    const slug = song_slug ?? (song as { slug?: string } | null)?.slug ?? "unknown";
    const brainstorm = readBrainstorm(root, (song as { brainstorm_path?: string } | null)?.brainstorm_path);

    const styleFile = path.join(root, "database", "visual-style.json");
    const style = fs.existsSync(styleFile) ? JSON.parse(fs.readFileSync(styleFile, "utf-8")) as VisualStyle : null;

    const outDir = path.join(root, "outputs", "social");
    fs.mkdirSync(outDir, { recursive: true });

    // ── Step 1: Generate storyboard via Gemini ──────────────────────────────
    let storyboard: Storyboard;
    try {
      storyboard = await this.generateStoryboard(client, song, slug, brainstorm, style, numScenes, format, director_note, seed_image ? path.basename(seed_image) : undefined);
    } catch (e) {
      return err(`Storyboard generation failed: ${(e as Error).message}`);
    }

    const fmtSpec = FORMAT_SPECS[format] ?? FORMAT_SPECS["landscape"];
    const scenePaths: Array<{ scene: number; description: string; image?: string; video?: string; error?: string }> = [];

    // ── Steps 2+3: Imagen keyframe → Veo animation per scene ────────────────
    for (const scene of storyboard.scenes) {
      if (token.isCancellationRequested) { break; }

      const sceneResult: { scene: number; description: string; image?: string; video?: string; error?: string } = {
        scene: scene.id,
        description: scene.description,
      };

      // Step 2a: Use seed image for scene 1 if provided, else generate via Imagen
      let imagePath: string | undefined;
      if (scene.id === 1 && seed_image) {
        const full = path.isAbsolute(seed_image) ? seed_image : path.join(root, seed_image);
        if (fs.existsSync(full)) { imagePath = full; }
      }

      if (!imagePath) {
        try {
          imagePath = await this.generateKeyframe(client, scene, slug, outDir, fmtSpec.aspect);
          sceneResult.image = path.relative(root, imagePath);
        } catch (e) {
          sceneResult.error = `Imagen failed: ${(e as Error).message}`;
          scenePaths.push(sceneResult);
          continue;
        }
      } else {
        sceneResult.image = path.relative(root, imagePath);
      }

      if (token.isCancellationRequested) { break; }

      // Step 2b: Animate keyframe via Veo 2
      try {
        const videoPath = await this.animateScene(client, scene, imagePath, slug, outDir, fmtSpec, token);
        sceneResult.video = path.relative(root, videoPath);
      } catch (e) {
        sceneResult.error = `Veo failed: ${(e as Error).message}`;
        scenePaths.push(sceneResult);
        continue;
      }

      scenePaths.push(sceneResult);
    }

    // ── Step 4: ffmpeg concat all clips ─────────────────────────────────────
    const clipPaths = scenePaths
      .filter((s) => s.video)
      .map((s) => path.join(root, s.video!));

    let finalPath: string | undefined;
    let concatError: string | undefined;

    if (clipPaths.length >= 2) {
      try {
        finalPath = await this.concatClips(clipPaths, slug, format, outDir, root);
      } catch (e) {
        concatError = `ffmpeg concat failed: ${(e as Error).message}`;
      }
    } else if (clipPaths.length === 1) {
      // Single clip — just use it as-is
      finalPath = clipPaths[0];
    }

    return new vscode.LanguageModelToolResult([
      new vscode.LanguageModelTextPart(JSON.stringify({
        success: !!finalPath,
        final_video: finalPath ? path.relative(root, finalPath) : undefined,
        storyboard: {
          title: storyboard.title,
          arc: storyboard.arc,
          scenes: scenePaths,
        },
        total_duration_seconds: clipPaths.length * 8,
        errors: [concatError, ...scenePaths.map((s) => s.error)].filter(Boolean),
      }, null, 2)),
    ]);
  }

  // --------------------------------------------------------------------------

  private async generateStoryboard(
    client: GoogleGenAI,
    song: ReturnType<typeof readActiveSong>,
    slug: string,
    brainstorm: string,
    style: VisualStyle | null,
    numScenes: number,
    format: string,
    directorNote: string,
    seedImageName?: string,
  ): Promise<Storyboard> {
    const songLine = song
      ? `"${(song as { title?: string }).title}" by IRON STATIC — ${(song as { key?: string }).key ?? ""} ${(song as { scale?: string }).scale ?? ""} @ ${(song as { bpm?: number }).bpm ?? ""}BPM`
      : `${slug} — IRON STATIC brand video`;

    const imageryVocab = style?.imagery.vocabulary
      .map((v) => `${v.name}: ${v.description}`)
      .join("; ") ?? "corroded metal, circuit traces, iron filings, electric discharge";

    const colorLang = style
      ? `Background: ${style.palette.background.description}. Primary: ${style.palette.primary_accent.description}. Danger: ${style.palette.secondary_accent.description}.`
      : "Void black background. Cold cobalt-white accents. Rust-orange as danger/heat.";

    const prompt = `You are a creative director for IRON STATIC, a dark electronic-metal band. Generate a ${numScenes}-scene video storyboard as valid JSON.

SONG: ${songLine}
FORMAT: ${format}
${directorNote ? `DIRECTOR NOTE: ${directorNote}` : ""}
${seedImageName ? `SCENE 1 ANCHOR: The first scene will be animated from an existing image "${seedImageName}" — its image_prompt should describe this image accurately so Imagen can reproduce it if needed.` : ""}

VISUAL LANGUAGE:
Colors: ${colorLang}
Imagery vocabulary: ${imageryVocab}
Motion: Imperceptibly slow camera. No cuts within clips. Photorealistic.
NEVER: people, faces, hands, warm colors, cartoon, anime.

BRAINSTORM CONTEXT:
${brainstorm.slice(0, 1200) || "Industrial electronic music — heavy machine energy, cold precision, controlled chaos."}

STORYBOARD RULES:
1. Scenes should flow together — shared visual thread but each reveals something new
2. Arc: build tension → peak intensity → release or unresolved question
3. Each scene = a distinct LOCATION or PHASE within the same visual world
4. image_prompt: what Imagen 4 should render (150-200 words, photorealistic, still frame)
5. animation_prompt: what Veo 2 should animate (60-80 words MAX — shorter is better for Veo 2)
6. animation_prompt must describe MOTION ONLY of elements already in the image — never introduce new subjects
7. Every animation_prompt ends with: "Camera holds still. No cuts. Extreme slow motion. Photorealistic."

Respond with ONLY valid JSON matching this exact schema:
{
  "title": "short evocative title",
  "arc": "one sentence describing the emotional arc across all scenes",
  "scenes": [
    {
      "id": 1,
      "description": "25 words describing the emotional/narrative purpose of this scene",
      "image_prompt": "...",
      "animation_prompt": "..."
    }
  ]
}`;

    const response = await client.models.generateContent({
      model: "gemini-2.0-flash",
      contents: prompt,
      config: { temperature: 0.85, maxOutputTokens: 3000 },
    });

    const raw = ((response as unknown as { text?: string }).text ?? "").trim();

    // Strip markdown code fences if present
    const json = raw.replace(/^```(?:json)?\n?/, "").replace(/\n?```$/, "").trim();
    return JSON.parse(json) as Storyboard;
  }

  private async generateKeyframe(
    client: GoogleGenAI,
    scene: StoryboardScene,
    slug: string,
    outDir: string,
    aspectRatio: string,
  ): Promise<string> {
    const response = await (client.models as unknown as {
      generateImages: (opts: {
        model: string; prompt: string;
        config: { numberOfImages: number; aspectRatio: string; negativePrompt: string; personGeneration: string };
      }) => Promise<{ generatedImages?: Array<{ image?: { imageBytes?: string } }> }>;
    }).generateImages({
      model: "imagen-4.0-generate-001",
      prompt: scene.image_prompt,
      config: { numberOfImages: 1, aspectRatio, negativePrompt: IMAGEN_NEGATIVE_PROMPT, personGeneration: "dont_allow" },
    });

    const imageBytes = response.generatedImages?.[0]?.image?.imageBytes;
    if (!imageBytes) { throw new Error("Imagen returned no image bytes"); }

    const outPath = path.join(outDir, `${slug}_storyboard_scene${scene.id}.png`);
    fs.writeFileSync(outPath, Buffer.from(imageBytes, "base64"));
    return outPath;
  }

  private async animateScene(
    client: GoogleGenAI,
    scene: StoryboardScene,
    imagePath: string,
    slug: string,
    outDir: string,
    fmtSpec: { w: number; h: number; aspect: string },
    token: vscode.CancellationToken,
  ): Promise<string> {
    const imageBytes = fs.readFileSync(imagePath).toString("base64");
    const mime = imagePath.endsWith(".png") ? "image/png" : "image/jpeg";

    const config: GenerateVideosConfig = {
      numberOfVideos: 1,
      aspectRatio: fmtSpec.aspect as "16:9" | "9:16" | "1:1",
      durationSeconds: 8,
      personGeneration: "dont_allow",
      negativePrompt: VEO_NEGATIVE_PROMPT,
    };

    // Try Veo 3, fall back to Veo 2
    let operation: Awaited<ReturnType<typeof client.models.generateVideos>> | null = null;
    for (const model of ["veo-3.0-generate-preview", "veo-2.0-generate-001"]) {
      try {
        operation = await client.models.generateVideos({
          model,
          prompt: scene.animation_prompt,
          image: { imageBytes, mimeType: mime } as unknown as Parameters<typeof client.models.generateVideos>[0]["image"],
          config,
        });
        break;
      } catch (e) {
        const msg = (e as Error).message ?? "";
        if (msg.includes("not found") || msg.includes("404") || msg.includes("INVALID_ARGUMENT")) { continue; }
        throw e;
      }
    }
    if (!operation) { throw new Error("No Veo model available"); }

    // Poll until done (max 8 min per clip)
    const deadline = Date.now() + 480_000;
    while (!operation.done) {
      if (token.isCancellationRequested) { throw new Error("Cancelled"); }
      if (Date.now() > deadline) { throw new Error("Timed out waiting for Veo"); }
      await new Promise((r) => setTimeout(r, 15_000));
      operation = await client.operations.getVideosOperation({ operation });
    }
    if (operation.error) { throw new Error(String(operation.error)); }

    const videos = operation.response?.generatedVideos ?? [];
    if (!videos.length) { throw new Error("Veo returned no videos"); }

    const videoBytes: string | undefined = (videos[0] as unknown as { video?: { videoBytes?: string } }).video?.videoBytes;
    const videoUri: string | undefined = (videos[0] as unknown as { video?: { uri?: string } }).video?.uri;

    const outPath = path.join(outDir, `${slug}_storyboard_scene${scene.id}.mp4`);

    if (videoBytes) {
      fs.writeFileSync(outPath, Buffer.from(videoBytes, "base64"));
    } else if (videoUri) {
      // Download from URI (requires API key)
      const sep = videoUri.includes("?") ? "&" : "?";
      const downloadUrl = `${videoUri}${sep}key=${process.env["GEMINI_API_KEY"] ?? process.env["GOOGLE_API_KEY"] ?? ""}`;
      const https = await import("https");
      await new Promise<void>((resolve, reject) => {
        const file = fs.createWriteStream(outPath);
        https.get(downloadUrl, (res) => {
          res.pipe(file);
          file.on("finish", () => { file.close(); resolve(); });
        }).on("error", (e) => { fs.unlink(outPath, () => {}); reject(e); });
      });
    } else {
      throw new Error("Veo response had no video bytes or URI");
    }

    return outPath;
  }

  private async concatClips(
    clipPaths: string[],
    slug: string,
    format: string,
    outDir: string,
    root: string,
  ): Promise<string> {
    // Write ffmpeg concat list file
    const listPath = path.join(outDir, `${slug}_concat_list.txt`);
    fs.writeFileSync(listPath, clipPaths.map((p) => `file '${p}'`).join("\n"));

    const outPath = nextOutputPath(root, slug, "storyboard", format, "mp4");

    await new Promise<void>((resolve, reject) => {
      const proc = cp.spawn("ffmpeg", [
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", listPath,
        "-c", "copy",
        outPath,
      ], { cwd: root });
      let stderr = "";
      proc.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });
      proc.on("close", (code) => {
        fs.unlink(listPath, () => {});
        if (code === 0) { resolve(); } else { reject(new Error(`ffmpeg concat exited ${code}: ${stderr.slice(-300)}`)); }
      });
    });

    return outPath;
  }
}

function err(message: string): vscode.LanguageModelToolResult {
  return new vscode.LanguageModelToolResult([
    new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: message })),
  ]);
}
