/**
 * IRON STATIC Language Model Tools
 *
 * Registers vscode.lm tools that agent mode can invoke automatically based on
 * user intent — no @mention required. Tools are called by the LLM when it
 * determines they are relevant to the current prompt.
 *
 * Tools registered here:
 *   iron-static_getActiveSong          — active song context from songs.json
 *   iron-static_getLiveState           — Ableton session state from live_state.json
 *   iron-static_getVelaConfig          — VELA voice config from voices.json
 *   iron-static_checkAceStepHealth     — ACE-Step server health (HTTP)
 *   iron-static_getAceStepStats        — ACE-Step server stats (HTTP)
 *   iron-static_submitAceStepJob       — Submit generation job to ACE-Step
 *   iron-static_pollAceStepJob         — Poll job status / get audio URL
 *   iron-static_runIronStaticScript    — Run allowlisted Python scripts
 *   iron-static_startAceStepServer     — Start ACE-Step server if not running
 *   iron-static_generateForSong        — One-shot: song context → prompt → ACE-Step job
 *   iron-static_abletonGetSessionInfo  — Fresh Ableton session info via TCP bridge (port 9877)
 *   iron-static_abletonTransport       — Play/stop/set tempo in Ableton via TCP bridge
 *   iron-static_abletonClip            — Create, write, fire, stop, clear, or read clips
 *   iron-static_abletonDeviceParam     — Get or set a device parameter value
 *   iron-static_abletonFireScene       — Fire a scene in Ableton
 *   iron-static_triggerWorkflow        — gh workflow run (allowlisted workflows)
 *   iron-static_getWorkflowStatus      — gh run list for a named workflow
 *   iron-static_listWorkflows          — enumerate .github/workflows/*.yml
 *   iron-static_listSkills             — enumerate .github/skills/<name>/SKILL.md
 *   iron-static_invokeSkill            — read a named skill's SKILL.md in full
 */

import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import * as http from "http";
import * as net from "net";
import * as cp from "child_process";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ACESTEP_BASE = "http://127.0.0.1:8001";

const SCRIPT_ALLOWLIST: ReadonlySet<string> = new Set([
  "gemini_forge.py",
  "vela_vocalist.py",
  "midi_craft.py",
  "manage_songs.py",
  "analyze_audio.py",
  "gcs_sync.py",
  "build_session.py",
]);

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getWorkspaceRoot(): string {
  const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (!root) {
    throw new Error("No workspace open — open the iron-static repo folder first.");
  }
  return root;
}

function readJsonFile(fullPath: string): unknown {
  const raw = fs.readFileSync(fullPath, "utf-8");
  return JSON.parse(raw);
}

function httpGet(url: string): Promise<string> {
  return new Promise((resolve, reject) => {
    const req = http.get(url, { timeout: 10000 }, (res) => {
      let body = "";
      res.on("data", (chunk: Buffer) => { body += chunk.toString(); });
      res.on("end", () => resolve(body));
    });
    req.on("error", reject);
    req.on("timeout", () => { req.destroy(); reject(new Error("Request timed out")); });
  });
}

function httpPost(url: string, payload: unknown): Promise<string> {
  return new Promise((resolve, reject) => {
    const data = JSON.stringify(payload);
    const urlObj = new URL(url);
    const options: http.RequestOptions = {
      hostname: urlObj.hostname,
      port: urlObj.port,
      path: urlObj.pathname,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(data),
      },
      timeout: 30000,
    };
    const req = http.request(options, (res) => {
      let body = "";
      res.on("data", (chunk: Buffer) => { body += chunk.toString(); });
      res.on("end", () => resolve(body));
    });
    req.on("error", reject);
    req.on("timeout", () => { req.destroy(); reject(new Error("Request timed out")); });
    req.write(data);
    req.end();
  });
}

// ---------------------------------------------------------------------------
// Tool: getActiveSong
// ---------------------------------------------------------------------------

interface GetActiveSongInput {
  // No input required
}

class GetActiveSongTool implements vscode.LanguageModelTool<GetActiveSongInput> {
  async invoke(
    _options: vscode.LanguageModelToolInvocationOptions<GetActiveSongInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const root = getWorkspaceRoot();
    const db = readJsonFile(path.join(root, "database", "songs.json")) as {
      songs?: Array<{
        status: string;
        title: string;
        slug: string;
        key?: string;
        scale?: string;
        bpm?: number;
        time_signature?: string;
        als_path?: string;
        brainstorm_path?: string;
      }>;
    };
    const songs = db?.songs ?? (Array.isArray(db) ? db as typeof db.songs : []);
    const active = (songs ?? []).find((s) => s.status === "active");
    if (!active) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({ active: null, message: "No active song in database/songs.json." })),
      ]);
    }
    return new vscode.LanguageModelToolResult([
      new vscode.LanguageModelTextPart(JSON.stringify({
        title: active.title,
        slug: active.slug,
        key: active.key ?? null,
        scale: active.scale ?? null,
        bpm: active.bpm ?? null,
        time_signature: active.time_signature ?? null,
        als_path: active.als_path ?? null,
        brainstorm_path: active.brainstorm_path ?? null,
      })),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Tool: getLiveState
// ---------------------------------------------------------------------------

interface GetLiveStateInput {
  // No input required
}

class GetLiveStateTool implements vscode.LanguageModelTool<GetLiveStateInput> {
  async invoke(
    _options: vscode.LanguageModelToolInvocationOptions<GetLiveStateInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const root = getWorkspaceRoot();
    const liveStatePath = path.join(root, "outputs", "live_state.json");
    if (!fs.existsSync(liveStatePath)) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({
          available: false,
          message: "outputs/live_state.json not found. Trigger session-reporter.amxd in Ableton to dump it.",
        })),
      ]);
    }
    const state = readJsonFile(liveStatePath);
    return new vscode.LanguageModelToolResult([
      new vscode.LanguageModelTextPart(JSON.stringify({ available: true, state })),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Tool: getVelaConfig
// ---------------------------------------------------------------------------

interface GetVelaConfigInput {
  // No input required
}

class GetVelaConfigTool implements vscode.LanguageModelTool<GetVelaConfigInput> {
  async invoke(
    _options: vscode.LanguageModelToolInvocationOptions<GetVelaConfigInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const root = getWorkspaceRoot();
    const db = readJsonFile(path.join(root, "database", "voices.json")) as {
      voices?: {
        vela?: {
          engine: string;
          modality: string;
          model?: string;
          lora_path?: string | null;
          lora_name?: string | null;
          character_tags?: string;
          description?: string;
          note?: string;
        };
      };
    };
    const vela = db?.voices?.vela;
    if (!vela) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({ error: "VELA config not found in database/voices.json" })),
      ]);
    }
    return new vscode.LanguageModelToolResult([
      new vscode.LanguageModelTextPart(JSON.stringify({
        engine: vela.engine,
        modality: vela.modality,
        model: vela.model ?? null,
        lora_path: vela.lora_path ?? null,
        lora_name: vela.lora_name ?? null,
        lora_trained: !!vela.lora_path,
        character_tags: vela.character_tags ?? null,
        description: vela.description ?? null,
        note: vela.note ?? null,
      })),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Tool: checkAceStepHealth
// ---------------------------------------------------------------------------

interface CheckAceStepHealthInput {
  // No input required
}

class CheckAceStepHealthTool implements vscode.LanguageModelTool<CheckAceStepHealthInput> {
  async invoke(
    _options: vscode.LanguageModelToolInvocationOptions<CheckAceStepHealthInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    try {
      const body = await httpGet(`${ACESTEP_BASE}/health`);
      const parsed = JSON.parse(body) as Record<string, unknown>;
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({ running: true, response: parsed })),
      ]);
    } catch (err) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({
          running: false,
          message: "ACE-Step server is not reachable at 127.0.0.1:8001.",
          how_to_start: "unset VIRTUAL_ENV && cd ~/tools/ACE-Step-1.5 && nohup bash start_api_server_macos.sh > /tmp/acestep-api.log 2>&1 &",
          error: (err as Error).message,
        })),
      ]);
    }
  }
}

// ---------------------------------------------------------------------------
// Tool: getAceStepStats
// ---------------------------------------------------------------------------

interface GetAceStepStatsInput {
  // No input required
}

class GetAceStepStatsTool implements vscode.LanguageModelTool<GetAceStepStatsInput> {
  async invoke(
    _options: vscode.LanguageModelToolInvocationOptions<GetAceStepStatsInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    try {
      const body = await httpGet(`${ACESTEP_BASE}/v1/stats`);
      const parsed = JSON.parse(body) as { data?: Record<string, unknown> };
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({ available: true, stats: parsed?.data ?? parsed })),
      ]);
    } catch (err) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({
          available: false,
          error: (err as Error).message,
        })),
      ]);
    }
  }
}

// ---------------------------------------------------------------------------
// Tool: submitAceStepJob
// ---------------------------------------------------------------------------

interface SubmitAceStepJobInput {
  prompt: string;
  lyrics?: string;
  task_type?: string;
  duration_seconds?: number;
  batch_size?: number;
  thinking?: boolean;
  lora_name?: string;
  model?: string;
}

class SubmitAceStepJobTool implements vscode.LanguageModelTool<SubmitAceStepJobInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<SubmitAceStepJobInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const input = options.input;
    const payload: Record<string, unknown> = {
      prompt: input.prompt,
      lyrics: input.lyrics ?? "[inst]",
      task_type: input.task_type ?? "text2music",
      duration_seconds: input.duration_seconds ?? 30,
      batch_size: input.batch_size ?? 1,
      thinking: input.thinking ?? true,
    };
    if (input.lora_name) {
      payload["lora_name"] = input.lora_name;
    }
    if (input.model) {
      payload["model"] = input.model;
    }
    try {
      const body = await httpPost(`${ACESTEP_BASE}/release_task`, payload);
      const parsed = JSON.parse(body) as { task_id?: string; data?: { task_id?: string } };
      const taskId = parsed?.task_id ?? parsed?.data?.task_id;
      if (!taskId) {
        return new vscode.LanguageModelToolResult([
          new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: "No task_id in response", raw: body })),
        ]);
      }
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({
          success: true,
          task_id: taskId,
          message: `Job submitted. Poll with iron-static_pollAceStepJob using task_id: ${taskId}`,
        })),
      ]);
    } catch (err) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({
          success: false,
          error: (err as Error).message,
          hint: "Make sure ACE-Step server is running — use iron-static_checkAceStepHealth first.",
        })),
      ]);
    }
  }
}

// ---------------------------------------------------------------------------
// Tool: pollAceStepJob
// ---------------------------------------------------------------------------

interface PollAceStepJobInput {
  task_id: string;
}

class PollAceStepJobTool implements vscode.LanguageModelTool<PollAceStepJobInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<PollAceStepJobInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const { task_id } = options.input;
    try {
      const body = await httpPost(`${ACESTEP_BASE}/query_result`, { task_id_list: [task_id] });
      const parsed = JSON.parse(body) as Array<{
        task_id: string;
        status: string;
        audio_url?: string;
        error?: string;
      }>;
      const items = Array.isArray(parsed) ? parsed : (parsed as { data?: typeof parsed })?.data ?? [];
      const item = items.find((i) => i.task_id === task_id);
      if (!item) {
        return new vscode.LanguageModelToolResult([
          new vscode.LanguageModelTextPart(JSON.stringify({ found: false, task_id, raw: body })),
        ]);
      }
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({
          task_id: item.task_id,
          status: item.status,
          audio_url: item.audio_url ?? null,
          error: item.error ?? null,
          done: item.status === "succeeded" || item.status === "failed",
          download_hint: item.audio_url
            ? `Audio available. Local path may be embedded in audio_url. If path starts with /tmp/, use shutil.copy2. Otherwise: curl "${ACESTEP_BASE}${item.audio_url}" -o output.wav`
            : null,
        })),
      ]);
    } catch (err) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({
          error: (err as Error).message,
          task_id,
        })),
      ]);
    }
  }
}

// ---------------------------------------------------------------------------
// Tool: runIronStaticScript
// ---------------------------------------------------------------------------

interface RunIronStaticScriptInput {
  script: string;
  args?: string[];
}

class RunIronStaticScriptTool implements vscode.LanguageModelTool<RunIronStaticScriptInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<RunIronStaticScriptInput>,
    token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const { script, args = [] } = options.input;

    if (!SCRIPT_ALLOWLIST.has(script)) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({
          success: false,
          error: `Script '${script}' is not on the allowlist.`,
          allowlist: Array.from(SCRIPT_ALLOWLIST),
        })),
      ]);
    }

    // Validate args — no shell injection vectors
    const safeArgPattern = /^[a-zA-Z0-9_\-./: ]+$/;
    for (const arg of args) {
      if (!safeArgPattern.test(arg)) {
        return new vscode.LanguageModelToolResult([
          new vscode.LanguageModelTextPart(JSON.stringify({
            success: false,
            error: `Argument rejected (unsafe characters): ${arg}`,
          })),
        ]);
      }
    }

    const root = getWorkspaceRoot();
    const venvPython = path.join(root, "..", "..", "venv", "bin", "python3");
    const python = fs.existsSync(venvPython) ? venvPython : "python3";
    const scriptPath = path.join(root, "scripts", script);

    return new Promise((resolve) => {
      const proc = cp.spawn(python, [scriptPath, ...args], {
        cwd: root,
        env: { ...process.env },
        timeout: 300000, // 5 minutes max
      });

      let stdout = "";
      let stderr = "";

      proc.stdout.on("data", (d: Buffer) => { stdout += d.toString(); });
      proc.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });

      token.onCancellationRequested(() => {
        proc.kill("SIGTERM");
      });

      proc.on("close", (code) => {
        resolve(new vscode.LanguageModelToolResult([
          new vscode.LanguageModelTextPart(JSON.stringify({
            success: code === 0,
            exit_code: code,
            script,
            args,
            stdout: stdout.slice(-8000), // cap at 8KB to avoid context overflow
            stderr: stderr.slice(-2000),
          })),
        ]));
      });

      proc.on("error", (err) => {
        resolve(new vscode.LanguageModelToolResult([
          new vscode.LanguageModelTextPart(JSON.stringify({
            success: false,
            error: err.message,
            script,
          })),
        ]));
      });
    });
  }
}

// ---------------------------------------------------------------------------
// TCP Bridge helper (mirrors bridge_client.py protocol — port 9877)
// ---------------------------------------------------------------------------

function abletonBridgeCall(cmdType: string, params: Record<string, unknown> = {}): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const payload = JSON.stringify({ type: cmdType, params });
    const sock = new net.Socket();
    let buf = "";

    sock.setTimeout(10000);
    sock.connect(9877, "127.0.0.1", () => {
      sock.write(payload);
      sock.end(); // signal EOF so remote knows we're done sending
    });
    sock.on("data", (d: Buffer) => { buf += d.toString(); });
    sock.on("end", () => {
      try { resolve(JSON.parse(buf)); }
      catch (e) { reject(new Error(`Bad JSON from bridge: ${buf.slice(0, 200)}`)); }
    });
    sock.on("timeout", () => { sock.destroy(); reject(new Error("Ableton bridge timeout")); });
    sock.on("error", (e: Error) => reject(e));
  });
}

function abletonNotAvailable(cmdType: string, err: unknown): vscode.LanguageModelToolResult {
  return new vscode.LanguageModelToolResult([
    new vscode.LanguageModelTextPart(JSON.stringify({
      available: false,
      command: cmdType,
      error: (err as Error).message,
      hint: "IronStatic Remote Script not responding on port 9877. In Ableton → Settings → Link/Tempo/MIDI → Control Surface, ensure 'IronStatic' is selected. If just installed, restart Live once.",
    })),
  ]);
}

// ---------------------------------------------------------------------------
// Tool: startAceStepServer
// ---------------------------------------------------------------------------

interface StartAceStepServerInput {
  // No input required
}

class StartAceStepServerTool implements vscode.LanguageModelTool<StartAceStepServerInput> {
  async invoke(
    _options: vscode.LanguageModelToolInvocationOptions<StartAceStepServerInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    // First check if already running
    try {
      await httpGet(`${ACESTEP_BASE}/health`);
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({ started: false, already_running: true })),
      ]);
    } catch {
      // Not running — try to start it
    }

    const serverDir = path.join(process.env.HOME ?? "/Users/darnold", "tools", "ACE-Step-1.5");
    const startScript = path.join(serverDir, "start_api_server_macos.sh");

    if (!fs.existsSync(startScript)) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({
          started: false,
          error: `Start script not found at ${startScript}`,
          manual_command: `unset VIRTUAL_ENV && cd ~/tools/ACE-Step-1.5 && nohup bash start_api_server_macos.sh > /tmp/acestep-api.log 2>&1 &`,
        })),
      ]);
    }

    // Spawn detached so it outlives the extension host
    const child = cp.spawn("bash", [startScript], {
      cwd: serverDir,
      detached: true,
      stdio: "ignore",
      env: { ...process.env, VIRTUAL_ENV: "" },
    });
    child.unref();

    // Give it up to 30 seconds to become healthy
    for (let i = 0; i < 30; i++) {
      await new Promise((r) => setTimeout(r, 1000));
      try {
        const body = await httpGet(`${ACESTEP_BASE}/health`);
        const parsed = JSON.parse(body) as Record<string, unknown>;
        return new vscode.LanguageModelToolResult([
          new vscode.LanguageModelTextPart(JSON.stringify({
            started: true,
            startup_seconds: i + 1,
            health: parsed,
            log: "/tmp/acestep-api.log",
          })),
        ]);
      } catch {
        // still starting
      }
    }

    return new vscode.LanguageModelToolResult([
      new vscode.LanguageModelTextPart(JSON.stringify({
        started: false,
        error: "Server process launched but did not become healthy within 30 seconds.",
        log: "/tmp/acestep-api.log",
        pid: child.pid ?? null,
      })),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Tool: generateForSong  (one-shot song-aware generation)
// ---------------------------------------------------------------------------

interface GenerateForSongInput {
  description: string;
  role: string;
  lyrics?: string;
  duration_seconds?: number;
  batch_size?: number;
  use_vela_voice?: boolean;
}

// IRON STATIC aesthetic style modifier — appended to every prompt
const IS_STYLE_BASE = "industrial metal, electronic, heavy, machine-driven, distorted, dark";

class GenerateForSongTool implements vscode.LanguageModelTool<GenerateForSongInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<GenerateForSongInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const { description, role, lyrics, duration_seconds = 30, batch_size = 1, use_vela_voice = false } = options.input;

    // 1. Read active song
    let songCtx: { title: string; slug: string; key?: string; scale?: string; bpm?: number } | null = null;
    try {
      const root = getWorkspaceRoot();
      const db = readJsonFile(path.join(root, "database", "songs.json")) as {
        songs?: Array<{ status: string; title: string; slug: string; key?: string; scale?: string; bpm?: number }>;
      };
      const songs = db?.songs ?? (Array.isArray(db) ? (db as typeof db.songs) : []);
      songCtx = (songs ?? []).find((s) => s.status === "active") ?? null;
    } catch (e) {
      // proceed without song context
    }

    // 2. Read VELA config if requested
    let loraName: string | undefined;
    if (use_vela_voice) {
      try {
        const root = getWorkspaceRoot();
        const db = readJsonFile(path.join(root, "database", "voices.json")) as {
          voices?: { vela?: { lora_name?: string } };
        };
        loraName = db?.voices?.vela?.lora_name ?? undefined;
      } catch {
        // no LoRA available
      }
    }

    // 3. Build style prompt
    const keyScale = songCtx
      ? `${songCtx.bpm ? `${songCtx.bpm}bpm, ` : ""}${songCtx.key ? `${songCtx.key} ` : ""}${songCtx.scale ?? ""}`.trim()
      : "";
    const promptParts = [
      IS_STYLE_BASE,
      role,
      description,
      keyScale,
    ].filter(Boolean);
    const prompt = promptParts.join(", ");

    // 4. Build suggested output path
    const slug = songCtx?.slug ?? "unknown-song";
    const roleSlug = role.toLowerCase().replace(/\s+/g, "-");
    const timestamp = new Date().toISOString().slice(0, 19).replace(/[T:]/g, "-");
    let root: string;
    try { root = getWorkspaceRoot(); } catch { root = "."; }
    const outputDir = path.join(root, "audio", "generated");
    const outputPath = path.join(outputDir, `${slug}_${roleSlug}_${timestamp}.wav`);

    // 5. Submit to ACE-Step
    const payload: Record<string, unknown> = {
      prompt,
      lyrics: lyrics ?? "[inst]",
      task_type: "text2music",
      duration_seconds,
      batch_size,
      thinking: true,
    };
    if (loraName) {
      payload["lora_name"] = loraName;
    }

    try {
      const body = await httpPost(`${ACESTEP_BASE}/release_task`, payload);
      const parsed = JSON.parse(body) as { task_id?: string; data?: { task_id?: string } };
      const taskId = parsed?.task_id ?? parsed?.data?.task_id;
      if (!taskId) {
        return new vscode.LanguageModelToolResult([
          new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: "No task_id", raw: body })),
        ]);
      }
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({
          success: true,
          task_id: taskId,
          prompt_used: prompt,
          song: songCtx ? { title: songCtx.title, slug: songCtx.slug } : null,
          output_path: outputPath,
          note: `Poll with iron-static_pollAceStepJob(task_id="${taskId}"). When done, move audio_url file to ${outputPath}`,
        })),
      ]);
    } catch (err) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({
          success: false,
          error: (err as Error).message,
          prompt_built: prompt,
          hint: "Start ACE-Step server first with iron-static_startAceStepServer.",
        })),
      ]);
    }
  }
}

// ---------------------------------------------------------------------------
// Tool: abletonGetSessionInfo
// ---------------------------------------------------------------------------

interface AbletonGetSessionInfoInput {
  // No input required
}

class AbletonGetSessionInfoTool implements vscode.LanguageModelTool<AbletonGetSessionInfoInput> {
  async invoke(
    _options: vscode.LanguageModelToolInvocationOptions<AbletonGetSessionInfoInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    try {
      const result = await abletonBridgeCall("get_session_info");
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({ available: true, session: result })),
      ]);
    } catch (err) {
      return abletonNotAvailable("get_session_info", err);
    }
  }
}

// ---------------------------------------------------------------------------
// Tool: abletonTransport
// ---------------------------------------------------------------------------

interface AbletonTransportInput {
  action: "play" | "stop" | "set_tempo";
  tempo?: number;
}

class AbletonTransportTool implements vscode.LanguageModelTool<AbletonTransportInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<AbletonTransportInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const { action, tempo } = options.input;
    try {
      let result: unknown;
      if (action === "play") {
        result = await abletonBridgeCall("start_playback");
      } else if (action === "stop") {
        result = await abletonBridgeCall("stop_playback");
      } else if (action === "set_tempo") {
        if (tempo === undefined || tempo <= 0) {
          return new vscode.LanguageModelToolResult([
            new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: "tempo must be a positive number when action is set_tempo" })),
          ]);
        }
        result = await abletonBridgeCall("set_tempo", { tempo });
      } else {
        return new vscode.LanguageModelToolResult([
          new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: `Unknown action: ${action}` })),
        ]);
      }
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({ success: true, action, result })),
      ]);
    } catch (err) {
      return abletonNotAvailable(`transport:${action}`, err);
    }
  }
}

// ---------------------------------------------------------------------------
// Tool: abletonClip
// ---------------------------------------------------------------------------

interface AbletonClipInput {
  action: "create" | "write" | "fire" | "stop" | "clear" | "get_notes" | "get_info" | "set_name" | "find_by_name";
  track_index?: number;
  clip_index?: number;
  length_beats?: number;
  notes?: Array<{ pitch: number; start_time: number; duration: number; velocity: number; mute: boolean }>;
  name?: string;
  track_name?: string;
}

class AbletonClipTool implements vscode.LanguageModelTool<AbletonClipInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<AbletonClipInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const { action, track_index, clip_index, length_beats, notes, name, track_name } = options.input;

    const needsTrackClip = ["create", "write", "fire", "stop", "clear", "get_notes", "get_info", "set_name"];
    if (needsTrackClip.includes(action) && (track_index === undefined || clip_index === undefined)) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: "track_index and clip_index are required for this action" })),
      ]);
    }

    try {
      let result: unknown;
      switch (action) {
        case "create":
          result = await abletonBridgeCall("create_clip", { track_index, clip_index, length: length_beats ?? 8.0 });
          break;
        case "write":
          if (!notes?.length) {
            return new vscode.LanguageModelToolResult([
              new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: "notes array is required for write action" })),
            ]);
          }
          await abletonBridgeCall("clear_clip", { track_index, clip_index });
          result = await abletonBridgeCall("add_notes_to_clip", { track_index, clip_index, notes });
          break;
        case "fire":
          result = await abletonBridgeCall("fire_clip", { track_index, clip_index });
          break;
        case "stop":
          result = await abletonBridgeCall("stop_clip", { track_index, clip_index });
          break;
        case "clear":
          result = await abletonBridgeCall("clear_clip", { track_index, clip_index });
          break;
        case "get_notes":
          result = await abletonBridgeCall("get_clip_notes", { track_index, clip_index });
          break;
        case "get_info":
          result = await abletonBridgeCall("get_clip_info", { track_index, clip_index });
          break;
        case "set_name":
          if (!name) {
            return new vscode.LanguageModelToolResult([
              new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: "name is required for set_name action" })),
            ]);
          }
          result = await abletonBridgeCall("set_clip_name", { track_index, clip_index, name });
          break;
        case "find_by_name":
          if (!name) {
            return new vscode.LanguageModelToolResult([
              new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: "name is required for find_by_name action" })),
            ]);
          }
          result = await abletonBridgeCall("find_clip_by_name", { name, track_name });
          break;
        default:
          return new vscode.LanguageModelToolResult([
            new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: `Unknown action: ${action}` })),
          ]);
      }
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({ success: true, action, result })),
      ]);
    } catch (err) {
      return abletonNotAvailable(`clip:${action}`, err);
    }
  }
}

// ---------------------------------------------------------------------------
// Tool: abletonDeviceParam
// ---------------------------------------------------------------------------

interface AbletonDeviceParamInput {
  action: "get" | "set";
  track_index: number;
  device_index: number;
  chain_index?: number;
  chain_device_index?: number;
  param_name?: string;
  param_index?: number;
  value?: number;
}

class AbletonDeviceParamTool implements vscode.LanguageModelTool<AbletonDeviceParamInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<AbletonDeviceParamInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const { action, track_index, device_index, chain_index, chain_device_index, param_name, param_index, value } = options.input;

    try {
      let result: unknown;
      if (action === "get") {
        result = await abletonBridgeCall("get_device_params", {
          track_index,
          device_index,
          chain_index,
          chain_device_index,
        });
      } else if (action === "set") {
        if (value === undefined) {
          return new vscode.LanguageModelToolResult([
            new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: "value is required for set action" })),
          ]);
        }
        result = await abletonBridgeCall("set_device_param", {
          track_index,
          device_index,
          chain_index,
          chain_device_index,
          param_name,
          param_index,
          value,
        });
      } else {
        return new vscode.LanguageModelToolResult([
          new vscode.LanguageModelTextPart(JSON.stringify({ success: false, error: `Unknown action: ${action}` })),
        ]);
      }
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({ success: true, action, result })),
      ]);
    } catch (err) {
      return abletonNotAvailable(`device_param:${action}`, err);
    }
  }
}

// ---------------------------------------------------------------------------
// Tool: abletonFireScene
// ---------------------------------------------------------------------------

interface AbletonFireSceneInput {
  scene_index: number;
}

class AbletonFireSceneTool implements vscode.LanguageModelTool<AbletonFireSceneInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<AbletonFireSceneInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    try {
      const result = await abletonBridgeCall("fire_scene", { scene_index: options.input.scene_index });
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({ success: true, scene_index: options.input.scene_index, result })),
      ]);
    } catch (err) {
      return abletonNotAvailable("fire_scene", err);
    }
  }
}

// ---------------------------------------------------------------------------
// Tool: triggerWorkflow — gh workflow run
// ---------------------------------------------------------------------------

const WORKFLOW_ALLOWLIST: ReadonlySet<string> = new Set([
  "weekly-brainstorm.yml",
  "forge-audio.yml",
  "gcs-sync.yml",
  "session-summarizer.yml",
  "repo-health.yml",
  "audio-intake.yml",
  "feed-digest.yml",
  "pattern-mutator.yml",
  "preset-ideas.yml",
  "reference-digest.yml",
  "theory-pulse.yml",
  "publish-release.yml",
  "social-post.yml",
  "dispatch-workers.yml",
]);

interface TriggerWorkflowInput {
  workflow: string;
  fields?: Record<string, string>;
}

class TriggerWorkflowTool implements vscode.LanguageModelTool<TriggerWorkflowInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<TriggerWorkflowInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const { workflow, fields = {} } = options.input;

    if (!WORKFLOW_ALLOWLIST.has(workflow)) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({
          error: `Workflow '${workflow}' is not in the allowlist.`,
          allowed: Array.from(WORKFLOW_ALLOWLIST),
        })),
      ]);
    }

    const fieldArgs: string[] = [];
    for (const [k, v] of Object.entries(fields)) {
      fieldArgs.push("--field", `${k}=${v}`);
    }

    return new Promise((resolve) => {
      cp.execFile("gh", ["workflow", "run", workflow, ...fieldArgs], { cwd: getWorkspaceRoot() }, (err, stdout, stderr) => {
        resolve(new vscode.LanguageModelToolResult([
          new vscode.LanguageModelTextPart(JSON.stringify({
            success: !err,
            workflow,
            fields,
            stdout: stdout.trim(),
            stderr: stderr.trim(),
            error: err?.message,
          })),
        ]));
      });
    });
  }
}

// ---------------------------------------------------------------------------
// Tool: getWorkflowStatus — gh run list
// ---------------------------------------------------------------------------

interface GetWorkflowStatusInput {
  workflow: string;
  limit?: number;
}

class GetWorkflowStatusTool implements vscode.LanguageModelTool<GetWorkflowStatusInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<GetWorkflowStatusInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const { workflow, limit = 3 } = options.input;
    const args = ["run", "list", `--workflow=${workflow}`, `--limit=${limit}`, "--json", "status,conclusion,createdAt,displayTitle,databaseId"];
    return new Promise((resolve) => {
      cp.execFile("gh", args, { cwd: getWorkspaceRoot() }, (err, stdout, stderr) => {
        let runs: unknown = [];
        try { runs = JSON.parse(stdout); } catch { /* empty */ }
        resolve(new vscode.LanguageModelToolResult([
          new vscode.LanguageModelTextPart(JSON.stringify({ workflow, runs, error: err?.message, stderr: stderr.trim() })),
        ]));
      });
    });
  }
}

// ---------------------------------------------------------------------------
// Tool: listWorkflows — enumerate .github/workflows/*.yml
// ---------------------------------------------------------------------------

class ListWorkflowsTool implements vscode.LanguageModelTool<Record<string, never>> {
  async invoke(
    _options: vscode.LanguageModelToolInvocationOptions<Record<string, never>>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const wfDir = path.join(getWorkspaceRoot(), ".github", "workflows");
    const results: Array<{ file: string; name: string; inAllowlist: boolean }> = [];
    try {
      const files = fs.readdirSync(wfDir).filter((f) => f.endsWith(".yml") || f.endsWith(".yaml"));
      for (const file of files) {
        const content = fs.readFileSync(path.join(wfDir, file), "utf8");
        const nameLine = content.split("\n").find((l) => l.startsWith("name:"));
        const name = nameLine ? nameLine.replace(/^name:\s*/, "").trim() : file;
        results.push({ file, name, inAllowlist: WORKFLOW_ALLOWLIST.has(file) });
      }
    } catch (err) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({ error: (err as Error).message })),
      ]);
    }
    return new vscode.LanguageModelToolResult([
      new vscode.LanguageModelTextPart(JSON.stringify({ workflows: results, total: results.length })),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Tool: listSkills — enumerate .github/skills/*/SKILL.md
// ---------------------------------------------------------------------------

class ListSkillsTool implements vscode.LanguageModelTool<Record<string, never>> {
  async invoke(
    _options: vscode.LanguageModelToolInvocationOptions<Record<string, never>>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const skillsDir = path.join(getWorkspaceRoot(), ".github", "skills");
    const results: Array<{ skill: string; description: string }> = [];
    try {
      const dirs = fs.readdirSync(skillsDir, { withFileTypes: true })
        .filter((d) => d.isDirectory())
        .map((d) => d.name);
      for (const dir of dirs) {
        const skillFile = path.join(skillsDir, dir, "SKILL.md");
        if (fs.existsSync(skillFile)) {
          const content = fs.readFileSync(skillFile, "utf8");
          const firstMeaningfulLine = content.split("\n")
            .map((l) => l.trim())
            .find((l) => l && !l.startsWith("#") && !l.startsWith("---")) ?? "";
          results.push({ skill: dir, description: firstMeaningfulLine.slice(0, 120) });
        }
      }
    } catch (err) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({ error: (err as Error).message })),
      ]);
    }
    return new vscode.LanguageModelToolResult([
      new vscode.LanguageModelTextPart(JSON.stringify({ skills: results, total: results.length })),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Tool: invokeSkill — read a named skill's SKILL.md in full
// ---------------------------------------------------------------------------

interface InvokeSkillInput {
  skill: string;
}

class InvokeSkillTool implements vscode.LanguageModelTool<InvokeSkillInput> {
  async invoke(
    options: vscode.LanguageModelToolInvocationOptions<InvokeSkillInput>,
    _token: vscode.CancellationToken
  ): Promise<vscode.LanguageModelToolResult> {
    const skillFile = path.join(getWorkspaceRoot(), ".github", "skills", options.input.skill, "SKILL.md");
    if (!fs.existsSync(skillFile)) {
      return new vscode.LanguageModelToolResult([
        new vscode.LanguageModelTextPart(JSON.stringify({
          error: `Skill '${options.input.skill}' not found.`,
          hint: "Use iron-static_listSkills to see available skills.",
        })),
      ]);
    }
    const content = fs.readFileSync(skillFile, "utf8");
    return new vscode.LanguageModelToolResult([
      new vscode.LanguageModelTextPart(JSON.stringify({ skill: options.input.skill, content })),
    ]);
  }
}

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

export function registerLmTools(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    // Context readers
    vscode.lm.registerTool("iron-static_getActiveSong", new GetActiveSongTool()),
    vscode.lm.registerTool("iron-static_getLiveState", new GetLiveStateTool()),
    vscode.lm.registerTool("iron-static_getVelaConfig", new GetVelaConfigTool()),
    // ACE-Step — health, stats, lifecycle
    vscode.lm.registerTool("iron-static_checkAceStepHealth", new CheckAceStepHealthTool()),
    vscode.lm.registerTool("iron-static_getAceStepStats", new GetAceStepStatsTool()),
    vscode.lm.registerTool("iron-static_startAceStepServer", new StartAceStepServerTool()),
    // ACE-Step — generation
    vscode.lm.registerTool("iron-static_generateForSong", new GenerateForSongTool()),
    vscode.lm.registerTool("iron-static_submitAceStepJob", new SubmitAceStepJobTool()),
    vscode.lm.registerTool("iron-static_pollAceStepJob", new PollAceStepJobTool()),
    // Ableton — live TCP bridge (port 9877)
    vscode.lm.registerTool("iron-static_abletonGetSessionInfo", new AbletonGetSessionInfoTool()),
    vscode.lm.registerTool("iron-static_abletonTransport", new AbletonTransportTool()),
    vscode.lm.registerTool("iron-static_abletonClip", new AbletonClipTool()),
    vscode.lm.registerTool("iron-static_abletonDeviceParam", new AbletonDeviceParamTool()),
    vscode.lm.registerTool("iron-static_abletonFireScene", new AbletonFireSceneTool()),
    // Scripting
    vscode.lm.registerTool("iron-static_runIronStaticScript", new RunIronStaticScriptTool()),
    // GitHub Actions + workflow orchestration
    vscode.lm.registerTool("iron-static_triggerWorkflow", new TriggerWorkflowTool()),
    vscode.lm.registerTool("iron-static_getWorkflowStatus", new GetWorkflowStatusTool()),
    vscode.lm.registerTool("iron-static_listWorkflows", new ListWorkflowsTool()),
    // Skills introspection
    vscode.lm.registerTool("iron-static_listSkills", new ListSkillsTool()),
    vscode.lm.registerTool("iron-static_invokeSkill", new InvokeSkillTool()),
  );
}
