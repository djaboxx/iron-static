![IRON STATIC](brand_repo.png)

# IRON STATIC Bridge

> *The machine half of the band, running inside VS Code.*

**IRON STATIC Bridge** is the VS Code extension for [IRON STATIC](https://github.com/djaboxx/iron-static) — an electronic metal project built as a human-machine creative partnership. The extension connects the live studio session to the rest of the AI toolchain: Arc (Copilot), Gemini, and VELA.

---

## What it does

### Bridge Server
An HTTP server (port 9880) that lets IRON STATIC Python scripts push events into VS Code in real time — notifications, status updates, progress bars, file opens, and structured events the LM tools can read.

```
GET  /health     → 200 { ok: true }
POST /notify     → VS Code notification (info / warn / error)
POST /status     → status bar update
POST /progress   → progress notification
POST /open       → open a file in the editor
POST /event      → push a structured event into the LM tool queue
```

### Audio Recorder
A one-click recorder panel with device selection, level meter, and WAV encoding — built directly into VS Code.

**Command**: `IRON STATIC: Open Audio Recorder`

- Enumerates all system audio inputs
- Mono or stereo, 44.1 / 48 kHz
- Take label auto-prefixes the active song slug
- After saving: tag as VELA training material or queue for GCS upload

### Homework Scheduler
Tracks the prerequisite tasks blocking IRON STATIC pipelines — platform accounts, GitHub Secrets, infrastructure setup — and surfaces them in the status bar and via Copilot Chat.

**Commands**: `IRON STATIC: Show Homework`, `IRON STATIC: Mark Homework Item Done`

### Chat Agents
All IRON STATIC agent personas are available as VS Code Copilot Chat participants:

| Agent | `@mention` | Role |
|---|---|---|
| The Arranger | `@the-arranger` | Song structure, energy arcs |
| The Sound Designer | `@the-sound-designer` | Presets, synthesis, hardware push |
| The Theorist | `@the-theorist` | Scales, harmony, rhythm |
| The Critic | `@the-critic` | Evaluation and challenge |
| The Live Engineer | `@the-live-engineer` | Ableton session architecture |
| The Alchemist | `@the-alchemist` | Gemini audio generation |
| The Mix Engineer | `@the-mix-engineer` | Mix balance and effects chains |

### LM Tools (Agent Mode)
When GitHub Copilot is in agent mode, these tools are automatically available:

| Tool | What it does |
|---|---|
| `iron-static_getLiveState` | Read current Ableton session state |
| `iron-static_getEvents` | Drain the event queue from Python scripts |
| `iron-static_getActiveSong` | Get active song key, scale, BPM |
| `iron-static_getHomework` | List open prerequisite tasks |

---

## Setup

1. Clone the [IRON STATIC repo](https://github.com/djaboxx/iron-static)
2. Open the workspace in VS Code — the extension activates on startup
3. The bridge server starts automatically on port 9880
4. Status bar shows `$(radio-tower) IS :9880` when running

**To run Python scripts against the bridge:**
```bash
cd /path/to/iron-static
python scripts/bridge_client.py --notify "Session started"
```

---

## Configuration

| Setting | Default | Description |
|---|---|---|
| `ironStatic.bridge.port` | `9880` | HTTP bridge server port |
| `ironStatic.recorder.outputDirectory` | `audio/recordings/raw` | Where WAV files are saved |
| `ironStatic.homework.showOnStartup` | `true` | Daily startup reminder for open homework |
| `ironStatic.homework.reminderIntervalHours` | `0` | Periodic reminder interval (0 = disabled) |

---

## How to open the UI

**Recorder panel:**
1. Open the Command Palette (`Cmd+Shift+P`)
2. Type `IRON STATIC: Open Audio Recorder`
3. The panel opens beside your current editor

**Homework QuickPick:**
1. Command Palette → `IRON STATIC: Show Homework`
2. Or click the homework status bar item (bottom-right, shows open item count)

**Chat agents:**
1. Open Copilot Chat (`Cmd+Shift+I` or the chat icon in the sidebar)
2. Type `@the-sound-designer` (or any agent name) to activate that persona

**Agent mode LM tools:**
- Switch Copilot Chat to agent mode
- Tools are automatically surfaced — no explicit invocation needed

---

## Development

```bash
cd vscode-extension/iron-static-bridge
npm install
node esbuild.mjs          # build
# Press F5 in VS Code to launch Extension Development Host
```

The Extension Development Host opens a second VS Code window with the extension loaded. All changes require a rebuild + reload (`Cmd+Shift+P` → `Developer: Reload Window` in the host).
