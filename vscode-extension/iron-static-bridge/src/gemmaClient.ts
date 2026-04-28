/**
 * gemmaClient.ts — Local Gemma inference client via Ollama.
 *
 * Calls the Ollama OpenAI-compatible API at http://localhost:11434 to run
 * Gemma 3 (or any other locally-pulled model) for generation tasks that
 * benefit from deep training on music/synthesis knowledge.
 *
 * Ollama must be running with the target model pulled:
 *   brew install ollama         # if not installed
 *   ollama serve                # start the daemon
 *   ollama pull gemma3:27b      # pull the model (one-time, ~16GB)
 *
 * This client calls Ollama's /api/chat endpoint directly using Node stdlib
 * HTTP — no npm packages required.
 */

import * as http from "http";

const OLLAMA_BASE = "http://127.0.0.1:11434";
const DEFAULT_MODEL = "gemma3:27b";
const CHAT_TIMEOUT_MS = 120_000;   // 2 min — local inference can be slow
const HEALTH_TIMEOUT_MS = 3_000;

export interface OllamaChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export interface OllamaChatOptions {
  model?: string;
  temperature?: number;
  /** Max tokens to generate */
  numPredict?: number;
  timeoutMs?: number;
}

export interface OllamaHealth {
  running: boolean;
  models: string[];
}

// ---------------------------------------------------------------------------
// HTTP helpers
// ---------------------------------------------------------------------------

function postJsonStreamed(
  url: string,
  payload: unknown,
  timeoutMs: number
): Promise<string> {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(payload);
    const urlObj = new URL(url);
    const opts: http.RequestOptions = {
      hostname: urlObj.hostname,
      port: urlObj.port,
      path: urlObj.pathname,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(data),
      },
      timeout: timeoutMs,
    };
    const req = http.request(opts, (res) => {
      let raw = "";
      res.on("data", (chunk: Buffer) => { raw += chunk.toString(); });
      res.on("end", () => resolve(raw));
    });
    req.on("error", reject);
    req.on("timeout", () => {
      req.destroy();
      reject(new Error(`Ollama request timed out after ${timeoutMs}ms`));
    });
    req.write(data);
    req.end();
  });
}

function getJson(url: string, timeoutMs: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const req = http.get(url, { timeout: timeoutMs }, (res) => {
      let body = "";
      res.on("data", (chunk: Buffer) => { body += chunk.toString(); });
      res.on("end", () => resolve(body));
    });
    req.on("error", reject);
    req.on("timeout", () => { req.destroy(); reject(new Error("Ollama health check timed out")); });
  });
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

/**
 * Send a chat request to a locally-running Ollama model.
 *
 * Uses /api/chat with stream:false — returns the full response text.
 */
export async function ollamaChat(
  messages: OllamaChatMessage[],
  opts: OllamaChatOptions = {}
): Promise<string> {
  const {
    model = DEFAULT_MODEL,
    temperature = 0.7,
    numPredict,
    timeoutMs = CHAT_TIMEOUT_MS,
  } = opts;

  const options: Record<string, unknown> = { temperature };
  if (numPredict !== undefined) {
    options["num_predict"] = numPredict;
  }

  const payload: Record<string, unknown> = {
    model,
    messages,
    stream: false,
    options,
  };

  const raw = await postJsonStreamed(`${OLLAMA_BASE}/api/chat`, payload, timeoutMs);

  // Ollama /api/chat (non-streaming) returns one JSON object
  const parsed = JSON.parse(raw) as {
    message?: { content?: string };
    error?: string;
  };

  if (parsed.error) {
    throw new Error(`Ollama error: ${parsed.error}`);
  }
  return parsed.message?.content ?? "";
}

/**
 * Check if Ollama is running and return the list of pulled models.
 */
export async function checkOllamaHealth(): Promise<OllamaHealth> {
  try {
    const raw = await getJson(`${OLLAMA_BASE}/api/tags`, HEALTH_TIMEOUT_MS);
    const parsed = JSON.parse(raw) as { models?: Array<{ name: string }> };
    return {
      running: true,
      models: (parsed.models ?? []).map((m) => m.name),
    };
  } catch {
    return { running: false, models: [] };
  }
}

export { DEFAULT_MODEL };
