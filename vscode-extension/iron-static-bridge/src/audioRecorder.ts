/**
 * audioRecorder.ts — IRON STATIC in-extension audio capture
 *
 * Opens a Webview panel that enumerates audio input devices via the Web Audio
 * API, records from the selected device, encodes to PCM WAV client-side, and
 * saves the result to audio/recordings/raw/ with proper naming conventions.
 *
 * After saving the user is offered the option to tag the file as VELA training
 * material (writes an entry to database/voices_training.json) or to queue it
 * for GCS upload (appends to database/gcs_manifest.json).
 *
 * Commands registered:
 *   ironStatic.openRecorder   — open the recorder panel
 */

import * as fs from "fs";
import * as path from "path";
import * as vscode from "vscode";
import { execFile, spawn, ChildProcess } from "child_process";
import { runVelaPipeline, seedBrainstormFromTranscription } from "./velaPipeline";

// ---------------------------------------------------------------------------
// Registration entry point
// ---------------------------------------------------------------------------

export function registerAudioRecorder(
  context: vscode.ExtensionContext,
  workspaceRoot: string
): void {
  let panel: AudioRecorderPanel | undefined;

  const openRecorder = vscode.commands.registerCommand(
    "ironStatic.openRecorder",
    () => {
      if (panel) {
        panel.reveal();
        return;
      }
      panel = new AudioRecorderPanel(context, workspaceRoot);
      panel.onDispose(() => {
        panel = undefined;
      });
    }
  );

  context.subscriptions.push(openRecorder);
}

// ---------------------------------------------------------------------------
// Panel class
// ---------------------------------------------------------------------------

class AudioRecorderPanel {
  private readonly _panel: vscode.WebviewPanel;
  private readonly _workspaceRoot: string;
  private _disposables: vscode.Disposable[] = [];
  private _disposeCallback?: () => void;
  // Host-side recording state
  private _ffmpegProc?: ChildProcess;
  private _recordingPath?: string;
  private _recordingStart?: number;
  private _recordingChannels = 2;
  private _recordingSampleRate = 48000;

  constructor(context: vscode.ExtensionContext, workspaceRoot: string) {
    this._workspaceRoot = workspaceRoot;

    this._panel = vscode.window.createWebviewPanel(
      "ironStaticRecorder",
      "IRON STATIC — Recorder",
      vscode.ViewColumn.Beside,
      {
        enableScripts: true,
        retainContextWhenHidden: true,
        localResourceRoots: [],
      }
    );

    this._panel.webview.html = this._buildHtml();

    this._panel.webview.onDidReceiveMessage(
      (msg) => this._handleMessage(msg),
      undefined,
      this._disposables
    );

    this._panel.onDidDispose(
      () => this._dispose(),
      undefined,
      this._disposables
    );
  }

  reveal(): void {
    this._panel.reveal();
  }

  onDispose(cb: () => void): void {
    this._disposeCallback = cb;
  }

  private _dispose(): void {
    if (this._ffmpegProc) {
      try { this._ffmpegProc.kill("SIGTERM"); } catch { /* ignore */ }
      this._ffmpegProc = undefined;
    }
    this._disposables.forEach((d) => d.dispose());
    this._disposables = [];
    this._disposeCallback?.();
  }

  // -------------------------------------------------------------------------
  // Message handler
  // -------------------------------------------------------------------------

  private async _handleMessage(msg: WebviewMessage): Promise<void> {
    switch (msg.type) {
      case "getDevices":
        this._enumerateDevices();
        break;
      case "startRecord":
        this._startRecording(msg);
        break;
      case "stopRecord":
        this._stopRecording();
        break;
      case "error":
        vscode.window.showErrorMessage(`Recorder: ${msg.text}`);
        break;
      case "log":
        console.log("[IRON STATIC Recorder]", msg.text);
        break;
    }
  }

  private async _saveRecordingFromPath(
    filePath: string,
    durationSeconds: number | null
  ): Promise<void> {
    // Brief wait for ffmpeg to finish flushing
    await new Promise<void>((r) => setTimeout(r, 500));

    if (!fs.existsSync(filePath)) {
      vscode.window.showErrorMessage(
        `Recorder: output file not found: ${filePath}`
      );
      return;
    }

    const filename = path.basename(filePath);
    this._panel.webview.postMessage({ type: "saved", path: filePath, filename });

    const picks: vscode.QuickPickItem[] = [
      {
        label: "$(beaker) Run Full Pipeline",
        description: "Analyze → Transcribe → Forge spec → Images → Video",
      },
      {
        label: "$(music) Run Full Pipeline + Music Bed",
        description: "Same as above, + ACE-Step instrumental → mix → video with audio",
      },
      {
        label: "$(milestone) Seed Brainstorm from Recording",
        description: "Analyze → Transcribe → run_brainstorm.py --seed (Gemini generates brainstorm)",
      },
      {
        label: "$(tag) Tag as VELA training",
        description: "Add to database/voices_training.json",
      },
      {
        label: "$(cloud-upload) Queue for GCS upload",
        description: "Mark pending in database/gcs_manifest.json",
      },
      {
        label: "$(folder-opened) Reveal in Finder",
      },
    ];

    const pick = await vscode.window.showQuickPick(picks, {
      title: `Saved: ${filename}`,
      placeHolder: "Choose what to do with this recording…",
    });

    if (!pick) { return; }

    if (pick.label.includes("Music Bed")) {
      await runVelaPipeline(filePath, this._workspaceRoot, { withMusicBed: true });
    } else if (pick.label.includes("Seed Brainstorm")) {
      await this._seedBrainstorm(filePath);
    } else if (pick.label.includes("Full Pipeline")) {
      await runVelaPipeline(filePath, this._workspaceRoot);
    } else if (pick.label.includes("VELA training")) {
      await this._tagAsTraining(filePath, filename, durationSeconds);
    } else if (pick.label.includes("GCS")) {
      await this._addToGcsManifest(filePath, filename, this._activeSongSlug());
    } else if (pick.label.includes("Finder")) {
      vscode.commands.executeCommand("revealFileInOS", vscode.Uri.file(filePath));
    }
  }

  // -------------------------------------------------------------------------
  // Training tag
  // -------------------------------------------------------------------------

  // -------------------------------------------------------------------------
  // Seed brainstorm from recording (analyze → transcribe → brainstorm --seed)
  // -------------------------------------------------------------------------

  private async _seedBrainstorm(filePath: string): Promise<void> {
    // Step 1: transcribe via gemini_listen.py
    const python = await (async () => {
      for (const candidate of [
        `${this._workspaceRoot}/.venv/bin/python3`,
        "/Users/darnold/venv/bin/python3",
        "python3",
        "python",
      ]) {
        try {
          if (fs.existsSync(candidate)) { return candidate; }
        } catch { /* skip */ }
      }
      return "python3";
    })();

    const listenScript = path.join(this._workspaceRoot, "scripts", "gemini_listen.py");
    const brainstormScript = path.join(this._workspaceRoot, "scripts", "run_brainstorm.py");

    if (!fs.existsSync(listenScript) || !fs.existsSync(brainstormScript)) {
      vscode.window.showErrorMessage("Required scripts not found (gemini_listen.py, run_brainstorm.py)");
      return;
    }

    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: "IRON STATIC — Seeding brainstorm…",
        cancellable: false,
      },
      async (progress) => {
        // Step 1: Transcribe (best-effort — empty result is fine, audio seed covers it)
        progress.report({ message: "Transcribing recording via Gemini…" });
        const transcription = await new Promise<string>((resolve) => {
          let out = "";
          const proc = spawn(python, [
            listenScript,
            "--file", filePath,
            "--question", "Transcribe all spoken words exactly as heard. Return only the transcription text, no commentary.",
            "--output", "json",
            "--no-song-context",
          ], { cwd: this._workspaceRoot });
          proc.stdout.on("data", (d: Buffer) => { out += d.toString(); });
          proc.stderr.on("data", () => {});
          proc.on("close", (code) => {
            if (code !== 0 || !out.trim()) { resolve(""); return; }
            try { resolve(JSON.parse(out).analysis ?? ""); }
            catch { resolve(out.trim()); }
          });
        });

        // Step 2: Seed brainstorm — always send --seed-audio; add --seed text when available
        const seedMsg = transcription.trim()
          ? "Transcribed. Seeding brainstorm with audio + text…"
          : "No speech detected — seeding brainstorm from audio…";
        progress.report({ message: seedMsg });

        const brainstormArgs = [
          brainstormScript,
          "--seed-audio", filePath,
          "--force",
          ...(transcription.trim() ? ["--seed", transcription] : []),
        ];

        const result = await new Promise<{ code: number; stderr: string }>((resolve) => {
          let stderr = "";
          const proc = spawn(python, brainstormArgs, { cwd: this._workspaceRoot });
          proc.stdout.on("data", () => {});
          proc.stderr.on("data", (d: Buffer) => { stderr += d.toString(); });
          proc.on("close", (code) => resolve({ code: code ?? 1, stderr }));
        });

        if (result.code === 0) {
          const match = result.stderr.match(/Wrote (.+brainstorms\/.+\.md)/);
          const brainstormPath = match ? path.join(this._workspaceRoot, match[1]) : undefined;
          const msg = brainstormPath
            ? `Brainstorm seeded → ${path.basename(brainstormPath)}`
            : "Brainstorm seeded.";
          vscode.window.showInformationMessage(msg, "Open File").then((action) => {
            if (action === "Open File" && brainstormPath && fs.existsSync(brainstormPath)) {
              vscode.workspace.openTextDocument(brainstormPath).then((doc) =>
                vscode.window.showTextDocument(doc, { preview: false })
              );
            }
          });
        } else {
          vscode.window.showErrorMessage(
            `Brainstorm seed failed (exit ${result.code}): ${result.stderr.slice(-300)}`
          );
        }
      }
    );
  }

  private async _tagAsTraining(
    filePath: string,
    filename: string,
    durationSeconds: number | null
  ): Promise<void> {
    const dbPath = path.join(this._workspaceRoot, "database", "voices_training.json");
    let db: TrainingDatabase = { version: 1, items: [] };
    if (fs.existsSync(dbPath)) {
      try { db = JSON.parse(fs.readFileSync(dbPath, "utf-8")); } catch { /* start fresh */ }
    }
    db.items.push({
      id: filename.replace(".wav", ""),
      filename,
      path: path.relative(this._workspaceRoot, filePath),
      added_at: new Date().toISOString(),
      duration_seconds: durationSeconds,
      sample_rate: this._recordingSampleRate,
      channels: this._recordingChannels,
      label: filename.replace(/\.wav$/, "").split("_").slice(1, -1).join("_") || "",
      voice: "vela",
      ready_for_training: false,
      notes: "",
    });
    fs.writeFileSync(dbPath, JSON.stringify(db, null, 2) + "\n");
    vscode.window.showInformationMessage(
      `Tagged ${filename} as VELA training material in database/voices_training.json`
    );
  }

  // -------------------------------------------------------------------------
  // GCS manifest
  // -------------------------------------------------------------------------

  private async _addToGcsManifest(
    filePath: string,
    filename: string,
    slug: string | null
  ): Promise<void> {
    const manifestPath = path.join(this._workspaceRoot, "database", "gcs_manifest.json");
    let manifest: GcsManifest = { bucket: "iron-static-files", files: {} };
    if (fs.existsSync(manifestPath)) {
      try { manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8")); } catch { /* start fresh */ }
    }
    const gcsKey = `audio/recordings/raw/${filename}`;
    const stat = fs.statSync(filePath);
    manifest.files[gcsKey] = {
      size_bytes: stat.size,
      sha256: null,
      content_type: "audio/wav",
      uploaded_at: null,
      pending_upload: true,
      local_path: path.relative(this._workspaceRoot, filePath),
      tags: slug ? [slug] : [],
    };
    manifest.last_updated = new Date().toISOString();
    fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2) + "\n");
    vscode.window.showInformationMessage(
      `${filename} queued for GCS. Run: python scripts/gcs_sync.py --upload`
    );
  }

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------

  private _activeSongSlug(): string | null {
    try {
      const songs = JSON.parse(
        fs.readFileSync(path.join(this._workspaceRoot, "database", "songs.json"), "utf-8")
      );
      for (const s of songs.songs ?? []) {
        if (s.status === "active") return s.slug as string;
      }
    } catch { /* non-fatal */ }
    return null;
  }

  // -------------------------------------------------------------------------
  // Host-side recording (ffmpeg)
  // -------------------------------------------------------------------------

  private _findFfmpeg(): string | undefined {
    for (const p of [
      "/usr/local/bin/ffmpeg",
      "/opt/homebrew/bin/ffmpeg",
      "/usr/bin/ffmpeg",
    ]) {
      if (fs.existsSync(p)) { return p; }
    }
    return undefined;
  }

  private _enumerateDevices(): void {
    const ffmpeg = this._findFfmpeg();
    if (!ffmpeg) {
      this._panel.webview.postMessage({
        type: "devicesError",
        message: "ffmpeg not found. Install it: brew install ffmpeg",
      });
      return;
    }
    execFile(
      ffmpeg,
      ["-f", "avfoundation", "-list_devices", "true", "-i", ""],
      { timeout: 5000 },
      (_err, _stdout, stderr) => {
        // ffmpeg always exits non-zero when listing devices — output is in stderr
        const devices = this._parseAvfDevices(stderr || "");
        if (devices.length > 0) {
          this._panel.webview.postMessage({ type: "devices", devices });
        } else {
          this._panel.webview.postMessage({
            type: "devicesError",
            message: "No audio input devices found.",
          });
        }
      }
    );
  }

  private _parseAvfDevices(
    output: string
  ): Array<{ index: string; label: string }> {
    const devices: Array<{ index: string; label: string }> = [];
    let inAudioSection = false;
    for (const line of output.split("\n")) {
      if (line.includes("AVFoundation audio devices")) {
        inAudioSection = true;
        continue;
      }
      if (inAudioSection && line.includes("AVFoundation video devices")) {
        break;
      }
      if (inAudioSection) {
        const match = line.match(/\[(\d+)\]\s+(.+)/);
        if (match) {
          devices.push({ index: match[1], label: match[2].trim() });
        }
      }
    }
    return devices;
  }

  private _startRecording(msg: StartRecordMessage): void {
    const ffmpeg = this._findFfmpeg();
    if (!ffmpeg) {
      this._panel.webview.postMessage({ type: "recordError", message: "ffmpeg not found." });
      return;
    }

    const config = vscode.workspace.getConfiguration("ironStatic.recorder");
    const outputDir = path.join(
      this._workspaceRoot,
      config.get<string>("outputDirectory") ?? "audio/recordings/raw"
    );
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    const label = msg.label
      ? msg.label.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "")
      : "take";
    const filename = `${label}_${timestamp}.wav`;
    this._recordingPath = path.join(outputDir, filename);
    this._recordingChannels = msg.channels;
    this._recordingSampleRate = msg.sampleRate;
    this._recordingStart = Date.now();

    this._ffmpegProc = spawn(ffmpeg, [
      "-f", "avfoundation",
      "-i", `:${msg.deviceIndex}`,
      "-ac", String(msg.channels),
      "-ar", String(msg.sampleRate),
      "-c:a", "pcm_s16le",
      "-y", this._recordingPath,
    ], { stdio: ["pipe", "pipe", "pipe"] });

    this._ffmpegProc.stderr?.on("data", (data: Buffer) => {
      console.log("[IRON STATIC Recorder ffmpeg]", data.toString().trim());
    });

    this._ffmpegProc.on("error", (err: Error) => {
      this._panel.webview.postMessage({ type: "recordError", message: err.message });
      this._ffmpegProc = undefined;
      this._recordingPath = undefined;
    });

    this._panel.webview.postMessage({ type: "recordingStarted", filename });
  }

  private _stopRecording(): void {
    if (!this._ffmpegProc || !this._recordingPath) { return; }

    const filePath = this._recordingPath;
    const durationSeconds = this._recordingStart
      ? (Date.now() - this._recordingStart) / 1000
      : null;
    this._recordingPath = undefined;
    this._recordingStart = undefined;
    const proc = this._ffmpegProc;
    this._ffmpegProc = undefined;

    proc.on("close", () => this._saveRecordingFromPath(filePath, durationSeconds));

    // Send 'q' for graceful stop — ffmpeg writes proper WAV headers on clean exit
    try {
      proc.stdin?.write("q");
      proc.stdin?.end();
    } catch {
      // stdin already closed
    }
    // Fallback SIGTERM after 4s
    setTimeout(() => { try { proc.kill("SIGTERM"); } catch { /* already gone */ } }, 4000);
  }

  // -------------------------------------------------------------------------
  // Webview HTML
  // -------------------------------------------------------------------------

  private _buildHtml(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>IRON STATIC Recorder</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: var(--vscode-font-family);
    font-size: var(--vscode-font-size);
    color: var(--vscode-foreground);
    background: var(--vscode-editor-background);
    padding: 20px;
    max-width: 540px;
  }
  h2 { font-size: 1.1em; letter-spacing: 0.08em; margin-bottom: 16px;
       text-transform: uppercase; color: var(--vscode-textLink-foreground); }
  label { display: block; font-size: 0.85em; margin-bottom: 4px;
          color: var(--vscode-descriptionForeground); }
  select, input[type="text"] {
    width: 100%;
    background: var(--vscode-input-background);
    color: var(--vscode-input-foreground);
    border: 1px solid var(--vscode-input-border, #555);
    padding: 5px 8px; border-radius: 2px;
    font-size: 0.9em; margin-bottom: 14px;
  }
  .row { display: flex; gap: 10px; margin-bottom: 14px; }
  .row > * { flex: 1; }
  button {
    background: var(--vscode-button-background);
    color: var(--vscode-button-foreground);
    border: none; padding: 7px 16px; border-radius: 2px;
    cursor: pointer; font-size: 0.9em; letter-spacing: 0.04em; width: 100%;
  }
  button:hover { background: var(--vscode-button-hoverBackground); }
  button:disabled { opacity: 0.4; cursor: default; }
  button.stop { background: #c53030; color: #fff; }
  canvas { width: 100%; height: 60px; background: #0d0d0d; border-radius: 2px;
           margin-bottom: 14px; display: block; }
  #status { font-size: 0.82em; color: var(--vscode-descriptionForeground);
            min-height: 1.4em; margin-bottom: 8px; }
  #timer { font-size: 1.6em; font-variant-numeric: tabular-nums;
           letter-spacing: 0.05em; margin-bottom: 14px; }
  .saves h3 { font-size: 0.78em; text-transform: uppercase; letter-spacing: 0.07em;
              margin: 18px 0 8px; color: var(--vscode-descriptionForeground); }
  .save-item { font-size: 0.8em; padding: 4px 0;
               border-bottom: 1px solid var(--vscode-widget-border, #333); }
  .save-item span { float: right; color: var(--vscode-descriptionForeground); }
  .note { font-size: 0.78em; color: var(--vscode-descriptionForeground);
          margin-top: 6px; line-height: 1.4; }
</style>
</head>
<body>
<h2>&#9679; IRON STATIC &mdash; Recorder</h2>

<label for="deviceSelect">Audio input device</label>
<select id="deviceSelect"><option value="">Loading devices&hellip;</option></select>

<div class="row">
  <div>
    <label for="channelSelect">Channels</label>
    <select id="channelSelect">
      <option value="1">Mono (1ch)</option>
      <option value="2" selected>Stereo (2ch)</option>
    </select>
  </div>
  <div>
    <label for="srSelect">Sample rate</label>
    <select id="srSelect">
      <option value="44100">44.1 kHz</option>
      <option value="48000" selected>48 kHz</option>
    </select>
  </div>
</div>

<label for="labelInput">Take label</label>
<input type="text" id="labelInput" placeholder="e.g. vela-verse1, guitar-riff, take">

<canvas id="meter"></canvas>
<div id="timer">00:00.0</div>
<div id="status">Loading audio devices&hellip;</div>

<div class="row">
  <button id="btnRecord" disabled>&#9679; Record</button>
  <button id="btnStop" class="stop" disabled>&#9632; Stop &amp; Save</button>
</div>

<p class="note">
  Device selection is system-level. To record a specific channel from a
  multi-channel interface, route that source to a stereo pair in your audio
  interface software first, then select it here.
</p>

<div class="saves">
  <h3>Session recordings</h3>
  <div id="savedList"></div>
</div>

<script>
const vscode = acquireVsCodeApi();
const deviceSelect = document.getElementById('deviceSelect');
const channelSelect = document.getElementById('channelSelect');
const srSelect = document.getElementById('srSelect');
const labelInput = document.getElementById('labelInput');
const btnRecord = document.getElementById('btnRecord');
const btnStop = document.getElementById('btnStop');
const statusEl = document.getElementById('status');
const timerEl = document.getElementById('timer');
const canvas = document.getElementById('meter');
const ctx2d = canvas.getContext('2d');
const savedListEl = document.getElementById('savedList');
let recording = false, startTime = 0, timerIv = null, meterIv = null;

// Ask extension host for device list
vscode.postMessage({ type: 'getDevices' });

function drawIdleMeter() {
  const W = canvas.offsetWidth || 480, H = 60;
  canvas.width = W; canvas.height = H;
  ctx2d.fillStyle = '#0d0d0d';
  ctx2d.fillRect(0, 0, W, H);
}

function animateMeter() {
  const W = canvas.offsetWidth || 480, H = 60;
  canvas.width = W; canvas.height = H;
  ctx2d.fillStyle = '#0d0d0d';
  ctx2d.fillRect(0, 0, W, H);
  const t = Date.now() / 200;
  const bars = 32, bw = Math.floor(W / bars) - 1;
  for (let i = 0; i < bars; i++) {
    const h = Math.abs(Math.sin(t + i * 0.4) * Math.cos(t * 0.7 + i * 0.2)) * H * 0.85 + 2;
    ctx2d.fillStyle = 'rgb(' + Math.round(h / H * 200) + ',50,30)';
    ctx2d.fillRect(i * (bw + 1), H - h, bw, h);
  }
}

drawIdleMeter();

btnRecord.addEventListener('click', function() {
  const deviceIndex = deviceSelect.value;
  const ch = parseInt(channelSelect.value, 10);
  const sr = parseInt(srSelect.value, 10);
  const label = labelInput.value.trim() || 'take';
  vscode.postMessage({ type: 'startRecord', deviceIndex, channels: ch, sampleRate: sr, label });
  setStatus('Starting recorder\u2026');
  btnRecord.disabled = true;
  [deviceSelect, channelSelect, srSelect].forEach(function(e) { e.disabled = true; });
});

btnStop.addEventListener('click', function() {
  vscode.postMessage({ type: 'stopRecord' });
  btnStop.disabled = true;
  setStatus('Stopping\u2026');
  recording = false;
  if (timerIv) { clearInterval(timerIv); timerIv = null; }
  if (meterIv) { clearInterval(meterIv); meterIv = null; }
  drawIdleMeter();
});

function setStatus(s) { statusEl.textContent = s; }
function pad(n) { return n.toString().padStart(2, '0'); }

window.addEventListener('message', function(e) {
  const m = e.data;
  switch (m.type) {
    case 'devices':
      deviceSelect.innerHTML = '';
      if (!m.devices || m.devices.length === 0) {
        deviceSelect.innerHTML = '<option value="">No devices found</option>';
        setStatus('No audio inputs found. Is ffmpeg installed? Run: brew install ffmpeg');
        return;
      }
      m.devices.forEach(function(d) {
        const o = document.createElement('option');
        o.value = d.index;
        o.textContent = d.label;
        deviceSelect.appendChild(o);
      });
      btnRecord.disabled = false;
      setStatus(m.devices.length + ' device(s) found. Ready.');
      break;
    case 'devicesError':
      deviceSelect.innerHTML = '<option value="">Error</option>';
      setStatus(m.message);
      break;
    case 'recordingStarted':
      recording = true;
      startTime = Date.now();
      timerIv = setInterval(function() {
        const s = (Date.now() - startTime) / 1000;
        timerEl.textContent = pad(Math.floor(s / 60)) + ':' + (s % 60).toFixed(1).padStart(4, '0');
      }, 100);
      meterIv = setInterval(animateMeter, 50);
      btnStop.disabled = false;
      setStatus('Recording\u2026');
      break;
    case 'saved':
      setStatus('Saved: ' + m.filename);
      const d = document.createElement('div');
      d.className = 'save-item';
      d.textContent = m.filename;
      const ts = document.createElement('span');
      ts.textContent = new Date().toLocaleTimeString();
      d.appendChild(ts);
      savedListEl.prepend(d);
      btnRecord.disabled = false;
      [deviceSelect, channelSelect, srSelect].forEach(function(el) { el.disabled = false; });
      timerEl.textContent = '00:00.0';
      drawIdleMeter();
      break;
    case 'recordError':
      setStatus('Error: ' + m.message);
      btnRecord.disabled = false;
      btnStop.disabled = true;
      [deviceSelect, channelSelect, srSelect].forEach(function(el) { el.disabled = false; });
      break;
  }
});
</script>

</body>
</html>`;
  }
}

// ── Types ──────────────────────────────────────────────────────────────────

type WebviewMessage =
  | StartRecordMessage
  | { type: "stopRecord" }
  | { type: "getDevices" }
  | { type: "error"; text: string }
  | { type: "log"; text: string };

interface StartRecordMessage {
  type: "startRecord";
  deviceIndex: string;
  channels: number;
  sampleRate: number;
  label: string;
}

interface TrainingItem {
  id: string; filename: string; path: string; added_at: string;
  duration_seconds: number | null; sample_rate: number; channels: number;
  label: string; voice: string; ready_for_training: boolean; notes: string;
}
interface TrainingDatabase { version: number; items: TrainingItem[]; }

interface GcsManifest {
  bucket: string; last_updated?: string;
  files: Record<string, {
    size_bytes: number; sha256: string | null; content_type: string;
    uploaded_at: string | null; pending_upload?: boolean;
    local_path?: string; tags: string[];
  }>;
}
