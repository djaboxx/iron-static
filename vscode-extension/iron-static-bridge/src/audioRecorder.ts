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
    this._disposables.forEach((d) => d.dispose());
    this._disposables = [];
    this._disposeCallback?.();
  }

  // -------------------------------------------------------------------------
  // Message handler
  // -------------------------------------------------------------------------

  private async _handleMessage(msg: WebviewMessage): Promise<void> {
    switch (msg.type) {
      case "save":
        await this._saveRecording(msg);
        break;
      case "error":
        vscode.window.showErrorMessage(`Recorder: ${msg.text}`);
        break;
      case "log":
        console.log("[IRON STATIC Recorder]", msg.text);
        break;
    }
  }

  private async _saveRecording(msg: SaveMessage): Promise<void> {
    const config = vscode.workspace.getConfiguration("ironStatic.recorder");
    const outputDir = path.join(
      this._workspaceRoot,
      config.get<string>("outputDirectory") ?? "audio/recordings/raw"
    );

    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    const slug = this._activeSongSlug();
    const timestamp = new Date()
      .toISOString()
      .replace(/[:.]/g, "-")
      .slice(0, 19);
    const label = msg.label
      ? msg.label.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "")
      : "take";
    const filename = slug
      ? `${slug}_${label}_${timestamp}.wav`
      : `${label}_${timestamp}.wav`;
    const filePath = path.join(outputDir, filename);

    const wavBuffer = Buffer.from(msg.wav, "base64");
    fs.writeFileSync(filePath, wavBuffer);

    this._panel.webview.postMessage({ type: "saved", path: filePath, filename });

    const action = await vscode.window.showInformationMessage(
      `Saved: ${filename}`,
      "Tag as VELA training",
      "Queue for GCS upload",
      "Reveal in Finder"
    );

    if (action === "Tag as VELA training") {
      await this._tagAsTraining(filePath, filename, msg);
    } else if (action === "Queue for GCS upload") {
      await this._addToGcsManifest(filePath, filename, slug);
    } else if (action === "Reveal in Finder") {
      vscode.commands.executeCommand("revealFileInOS", vscode.Uri.file(filePath));
    }
  }

  // -------------------------------------------------------------------------
  // Training tag
  // -------------------------------------------------------------------------

  private async _tagAsTraining(
    filePath: string,
    filename: string,
    msg: SaveMessage
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
      duration_seconds: msg.durationSeconds ?? null,
      sample_rate: msg.sampleRate,
      channels: msg.channels,
      label: msg.label ?? "",
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
<div id="status">Select a device and press Record.</div>

<div class="row">
  <button id="btnRecord">&#9679; Record</button>
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
let audioCtx, stream, analyser, scriptProcessor;
let recLeft = [], recRight = [];
let recording = false, startTime = 0, timerIv = null;

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
let meterRunning = false;

async function enumerate() {
  try {
    const tmp = await navigator.mediaDevices.getUserMedia({ audio: true });
    tmp.getTracks().forEach(t => t.stop());
    const devs = await navigator.mediaDevices.enumerateDevices();
    const inputs = devs.filter(d => d.kind === 'audioinput');
    deviceSelect.innerHTML = '';
    inputs.forEach((d, i) => {
      const o = document.createElement('option');
      o.value = d.deviceId;
      o.textContent = d.label || 'Input ' + (i + 1);
      deviceSelect.appendChild(o);
    });
    setStatus(inputs.length + ' device(s) found. Ready.');
  } catch(e) {
    setStatus('Permission denied: ' + e.message);
  }
}
enumerate();

function drawMeter() {
  if (!analyser || !meterRunning) return;
  const W = canvas.offsetWidth || 480, H = 60;
  canvas.width = W; canvas.height = H;
  const data = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteFrequencyData(data);
  ctx2d.fillStyle = '#0d0d0d';
  ctx2d.fillRect(0, 0, W, H);
  const bw = (W / data.length) * 2.5;
  let x = 0;
  for (let i = 0; i < data.length; i++) {
    const h = (data[i] / 255) * H;
    ctx2d.fillStyle = 'rgb(' + Math.round(data[i]*0.8) + ',50,30)';
    ctx2d.fillRect(x, H - h, bw, h);
    x += bw + 1;
  }
  requestAnimationFrame(drawMeter);
}

btnRecord.addEventListener('click', async () => {
  const ch = parseInt(channelSelect.value, 10);
  const sr = parseInt(srSelect.value, 10);
  const did = deviceSelect.value;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        deviceId: did ? { exact: did } : undefined,
        channelCount: { ideal: ch },
        sampleRate: { ideal: sr },
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
      }
    });
  } catch(e) { setStatus('Cannot open device: ' + e.message); return; }

  const actualSR = stream.getAudioTracks()[0].getSettings().sampleRate || sr;
  audioCtx = new AudioContext({ sampleRate: actualSR });
  const src = audioCtx.createMediaStreamSource(stream);
  analyser = audioCtx.createAnalyser();
  analyser.fftSize = 256;
  src.connect(analyser);

  scriptProcessor = audioCtx.createScriptProcessor(4096, ch, ch);
  src.connect(scriptProcessor);
  scriptProcessor.connect(audioCtx.destination);
  recLeft = []; recRight = [];
  scriptProcessor.onaudioprocess = e => {
    if (!recording) return;
    recLeft.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    if (ch > 1) recRight.push(new Float32Array(e.inputBuffer.getChannelData(1)));
  };

  recording = true; startTime = Date.now();
  timerIv = setInterval(() => {
    const s = (Date.now() - startTime) / 1000;
    timerEl.textContent = pad(Math.floor(s/60)) + ':' + (s%60).toFixed(1).padStart(4,'0');
  }, 100);
  meterRunning = true; requestAnimationFrame(drawMeter);
  setStatus('Recording\u2026');
  btnRecord.disabled = true; btnStop.disabled = false;
  [deviceSelect, channelSelect, srSelect].forEach(e => e.disabled = true);
});

btnStop.addEventListener('click', () => {
  recording = false; meterRunning = false;
  clearInterval(timerIv); btnStop.disabled = true;
  stream.getTracks().forEach(t => t.stop());
  scriptProcessor.disconnect(); analyser.disconnect();
  setStatus('Encoding WAV\u2026');

  const ch = parseInt(channelSelect.value, 10);
  const sr = audioCtx.sampleRate;
  const label = labelInput.value.trim() || 'take';
  const dur = (Date.now() - startTime) / 1000;
  const L = flatten(recLeft);
  const R = ch > 1 ? flatten(recRight) : L;
  const wav = encodeWav(L, R, ch, sr);
  setStatus('Saving\u2026');
  vscode.postMessage({ type: 'save', wav, label, sampleRate: sr, channels: ch, durationSeconds: dur });
  audioCtx.close(); audioCtx = null; analyser = null;
  btnRecord.disabled = false;
  [deviceSelect, channelSelect, srSelect].forEach(e => e.disabled = false);
});

function flatten(chunks) {
  const n = chunks.reduce((a,c) => a+c.length, 0);
  const out = new Float32Array(n); let off = 0;
  for (const c of chunks) { out.set(c, off); off += c.length; }
  return out;
}

function encodeWav(L, R, ch, sr) {
  const n = L.length, bps = 2, ba = ch*bps;
  const buf = new ArrayBuffer(44 + n*ch*bps);
  const v = new DataView(buf);
  const ws = (o,s) => { for(let i=0;i<s.length;i++) v.setUint8(o+i,s.charCodeAt(i)); };
  const wi = (o,x,l) => { for(let i=0;i<l;i++) v.setUint8(o+i,(x>>(i*8))&0xff); };
  ws(0,'RIFF'); wi(4,36+n*ch*bps,4); ws(8,'WAVE'); ws(12,'fmt ');
  wi(16,16,4); wi(20,1,2); wi(22,ch,2); wi(24,sr,4);
  wi(28,sr*ba,4); wi(32,ba,2); wi(34,16,2); ws(36,'data'); wi(40,n*ch*bps,4);
  let off = 44;
  for(let i=0;i<n;i++){
    const l=Math.max(-1,Math.min(1,L[i]));
    v.setInt16(off,l<0?l*0x8000:l*0x7fff,true); off+=2;
    if(ch>1){const r=Math.max(-1,Math.min(1,R[i]));v.setInt16(off,r<0?r*0x8000:r*0x7fff,true);off+=2;}
  }
  const bytes = new Uint8Array(buf); let bin='';
  for(let i=0;i<bytes.length;i++) bin+=String.fromCharCode(bytes[i]);
  return btoa(bin);
}

function setStatus(s) { statusEl.textContent = s; }
function pad(n) { return n.toString().padStart(2,'0'); }

window.addEventListener('message', e => {
  const m = e.data;
  if (m.type === 'saved') {
    setStatus('Saved: ' + m.filename);
    const d = document.createElement('div');
    d.className = 'save-item';
    d.textContent = m.filename;
    const ts = document.createElement('span');
    ts.textContent = new Date().toLocaleTimeString();
    d.appendChild(ts);
    savedListEl.prepend(d);
  }
});
</script>
</body>
</html>`;
  }
}

// ── Types ──────────────────────────────────────────────────────────────────

type WebviewMessage =
  | SaveMessage
  | { type: "error"; text: string }
  | { type: "log"; text: string };

interface SaveMessage {
  type: "save";
  wav: string;
  label: string;
  sampleRate: number;
  channels: number;
  durationSeconds: number;
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
