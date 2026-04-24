# IRON STATIC — Day One Guide

Everything you need to use this system on the first day. No fluff.

---

## Table of Contents

1. [How the System Is Structured](#1-how-the-system-is-structured)
2. [Agent Personas](#2-agent-personas)
3. [Skills](#3-skills)
4. [Scripts Reference](#4-scripts-reference)
5. [M4L Devices](#5-m4l-devices)
6. [Remote Script Bridge](#6-remote-script-bridge)
7. [Key Files and Databases](#7-key-files-and-databases)
8. [Day 1 Workflows](#8-day-1-workflows)

---

## 1. How the System Is Structured

Three layers, each dependent on the one below it:

```
┌─────────────────────────────────────────────────────────┐
│  AGENT PERSONAS  (VS Code Chat — creative intelligence) │
│  The Arranger · Sound Designer · Theorist · Critic      │
│  Live Engineer · Producer                               │
└──────────────────────┬──────────────────────────────────┘
                       │ call
┌──────────────────────▼──────────────────────────────────┐
│  SCRIPTS  (Python CLI — execution layer)                │
│  manage_songs · generate_als · ableton_push             │
│  midi_craft · pattern_learn · sysex_capture · ...       │
└──────────────────────┬──────────────────────────────────┘
                       │ writes/reads
┌──────────────────────▼──────────────────────────────────┐
│  DATABASE / FILES  (source of truth)                    │
│  database/songs.json · instruments/ · midi/ · ableton/  │
└─────────────────────────────────────────────────────────┘
```

**The rule**: Agents make all creative decisions. Scripts execute those decisions. Scripts are pure executors — they have no aesthetic opinions.

**The venv**: Always use `/Users/darnold/venv/bin/python3` (Python 3.12, Rosetta). Not the system Python.

---

## 2. Agent Personas

Switch agents in VS Code Chat via the agent dropdown (top of chat panel). Each agent has a different focus, tool set, and set of automatic handoffs.

### The Live Engineer ⚡
**Your current mode.** In-the-box session architecture, M4L devices, Ableton routing, device chain design, internal instrument selection, ALS generation.

- Reads `outputs/live_state.json` before any session suggestion
- Runs `generate_als.py` to inject instruments into sessions
- Makes all creative decisions for offline sessions (not just matching hardware to software)
- Hands off to: Sound Designer (patch params), Arranger (scene flow), Critic (evaluation)

**When to use**: Setting up or modifying an Ableton session, building in-box alternatives, diagnosing M4L device issues.

---

### The Sound Designer 🎛
Presets, synthesis, hardware push, MIDI generation. Full terminal and file access.

- Designs patches using the MIDI param maps in `database/midi_params/`
- Pushes presets via NRPN with `push_preset.py`
- Captures SysEx dumps from Rev2/Take5 via `sysex_capture.py`
- Writes preset JSON files to `instruments/[slug]/presets/`
- Hands off to: Critic, Arranger, Theorist, Live Engineer

**When to use**: Designing or documenting a patch, generating MIDI patterns, pushing a preset to hardware.

**MIDI generation order**: For MIDI patterns, the correct flow is **Theorist first → Sound Designer**. The Sound Designer reads `knowledge/music-theory/pulse/YYYY-MM-DD.md` (the Theorist's chord vocabulary, voicings, and rhythmic analysis) before writing any notes. If that file doesn't exist, hand off to the Theorist first. The "Check the harmony" handoff on the Sound Designer goes the other direction — it's a post-hoc check after patches are designed, not a pre-MIDI consultation.

---

### The Arranger 📐
Song structure, sections, energy arcs, transitions. Read-only.

- Reads `database/songs.json` and `knowledge/brainstorms/` before proposing anything
- Proposes 80-bar (or N-bar) arrangements with energy levels per section
- Does not touch presets, MIDI, or scripts
- Hands off to: Sound Designer, Theorist, Critic, Live Engineer

**When to use**: Planning a new song, extending or revising a song structure, mapping sections to scenes.

---

### The Theorist 🎵
Scales, modes, chord vocabulary, rhythm, voice leading — always mapped to hardware.

- Answers "what notes are in A Phrygian Dominant?" with "here's how to set that on the Subharmonicon"
- Writes discovered theory to `knowledge/music-theory/`
- Does not generate MIDI — describes what should be played
- Hands off to: Arranger, Sound Designer, Critic

**When to use**: Harmony questions, scale/mode reference, chord voicing, rhythm pattern design.

---

### The Critic 🔍
Evaluation only. Read-only. No approval without reason.

- Measures everything against the manifesto: heavy, weird, electronic, intentional
- References the brainstorm to check if decisions actually serve the song
- Will call out a wrong choice directly without softening it
- Hands off to: Sound Designer (fix it), Arranger (restructure), Theorist (rethink harmony)

**When to use**: Evaluating an arrangement, a patch, a set of instrument choices, a mix decision. Never skip this step.

---

### The Producer 🎬
Meta-coordinator. Dispatches the other agents in sequence for full workflows.

- Always reads `database/songs.json` → finds `brainstorm_path` → reads that file first
- Available workflows: `theory-to-hardware`, `patch-and-critique`, `song-review`
- Runs agents sequentially, passes context between them, surfaces blockers
- Never skips The Critic

**When to use**: Starting a full song development cycle from scratch, running a complete patch-build-critique loop, doing a structured weekly song review.

---

## 3. Skills

Skills are focused instruction sets loaded by agents before executing specific tasks. **You never call skills directly** — agents load them automatically when needed. But you should know what triggers them so you understand what's happening.

Each skill lives in `.github/skills/[name]/SKILL.md`.

| Skill | Trigger | What It Does |
|---|---|---|
| `ableton-launch` | Any Ableton push work | Checks if Live is running, opens it if not |
| `ableton-push` | Pushing MIDI, setting up rigs, controlling playback | Full bridge command reference |
| `analyze-audio` | Given an audio file to analyze | librosa BPM/key detection, spectral analysis |
| `audio-to-midi` | Converting audio to MIDI | Demucs stem separation + Basic Pitch transcription |
| `analyze-ableton-logs` | Diagnosing Remote Script errors | Reads Live log files, finds crash causes |
| `create-preset` | Creating or documenting a patch | Preset format, NRPN documentation, panel-state notation |
| `extract-midi-clips` | Extracting clips from an .als file | Runs `extract_midi_clips.py`, outputs .mid files |
| `gcs-audio` | Uploading/downloading audio to/from GCS | Audio never goes into git directly — GCS only |
| `gemini-listen` | Qualitative audio analysis ("is this heavy enough?") | Sends audio to Gemini API, aesthetic evaluation |
| `instrument-onboard` | Adding a new instrument | Folder structure, manual index, param map, SysEx wiring |
| `m4l-build` | Building or modifying a Max for Live device | .maxpat authoring, JS/LiveAPI patterns, amxd packaging |
| `manual-lookup` | Questions from instrument manuals | Searches indexed manual text, returns spec/procedure |
| `midi-craft` | Writing or generating MIDI sequences | Scale-correct note generation, .mid file output |
| `music-theory` | Harmony/scale/rhythm questions | Theory in the context of the IRON STATIC rig |
| `parse-als` | Parsing an .als project file | Extracts track list, clips, tempo, device inventory |
| `sysex-capture` | Receiving a SysEx dump from hardware | Parses dump, writes JSON preset catalog |

---

## 4. Scripts Reference

All scripts in `scripts/`. Always run with `/Users/darnold/venv/bin/python3` unless otherwise noted.

### Song Lifecycle

**`manage_songs.py`** — The source of truth for all song context.

```bash
# Add a new song
python scripts/manage_songs.py add \
  --slug my-song --title "My Song" --key E --scale phrygian --bpm 138

# Set a song as active (clears previous active)
python scripts/manage_songs.py activate --slug my-song

# List all songs and their status
python scripts/manage_songs.py list

# Print just the active slug (for scripting)
python scripts/manage_songs.py active

# Mark as released
python scripts/manage_songs.py release --slug my-song

# Archive
python scripts/manage_songs.py archive --slug my-song --reason "shelved"
```

Status lifecycle: `in-progress` → `active` → `released` → `archived`
**Exactly one song should be `active` at a time.** Copilot reads it for all context-aware generation.

---

### Session Generation

**`generate_als.py`** — Pure executor. Injects instrument devices into a base ALS file. The Live Engineer provides the config; this script executes it.

```bash
# See what tracks exist in a base session (use these names in your config)
python scripts/generate_als.py --list --base ableton/sessions/rust-protocol_v1.als

# See all available Internal.als devices
python scripts/generate_als.py --list-devices

# Dry run — shows plan, writes nothing
python scripts/generate_als.py \
  --base ableton/sessions/rust-protocol_v1.als \
  --config ableton/m4l/configs/rust-protocol-internal.json \
  --dry-run -v

# Generate the session
python scripts/generate_als.py \
  --base ableton/sessions/rust-protocol_v1.als \
  --config ableton/m4l/configs/rust-protocol-internal.json \
  --out ableton/sessions/rust-protocol_v1-internal.als

# Open in Live
open 'ableton/sessions/rust-protocol_v1-internal.als'
```

**Config file format** (`ableton/m4l/configs/[slug]-internal.json`):
```json
{
  "tracks": {
    "TrackName": "19-Operator",   // inject device from Internal.als
    "OtherTrack": "pigments",     // inject Arturia Pigments VST3
    "HardwareTrack": null         // clear devices (hardware present, no injection)
  }
}
```
Track names must exactly match `--list` output. Device names must exactly match `--list-devices` output.

---

### Ableton Live Bridge

**`ableton_push.py`** — Talks to the IronStatic Remote Script over TCP port 9877. Requires Live to be running with IronStatic selected as a control surface.

```bash
# Check connection + see current session state
python scripts/ableton_push.py status

# Build session from HCL template
python scripts/ableton_push.py setup-rig \
  --template ableton/templates/iron-static-default.hcl

# Push a MIDI file into a clip slot
python scripts/ableton_push.py push-midi \
  --file midi/sequences/riff_v1.mid --track Rev2-A --clip 0

# Fire a clip
python scripts/ableton_push.py fire --track Digitakt --clip 0

# Stop all clips
python scripts/ableton_push.py stop

# Set tempo
python scripts/ableton_push.py set-tempo --bpm 95
```

**Prerequisite**: Remote Script must be installed (see `deploy_remote_script.py`).

---

### Remote Script Deployment

**`deploy_remote_script.py`** — Installs/updates the IronStatic Remote Script into Live's app bundle. Run this after any changes to `ableton/remote_script/IronStatic/__init__.py`.

```bash
# Deploy to app bundle (required for Live 12.2+)
python scripts/deploy_remote_script.py

# Deploy to both app bundle and user scripts dir
python scripts/deploy_remote_script.py --app-bundle --user-scripts
```

After deploying: deselect then reselect "IronStatic" in Ableton → Settings → Link/Tempo/MIDI → Control Surface to reload without restarting Live. For first install, restart Live fully.

---

### Session Initialization

**`session_init.py`** — Monday morning startup script. Scans connected MIDI devices, reports rig status, wires up Ableton.

```bash
# Scan which hardware instruments are connected
python scripts/session_init.py scan

# Scan + setup Ableton (calls ableton_push.py setup-rig)
python scripts/session_init.py setup

# Setup for a specific song
python scripts/session_init.py setup --song rust-protocol

# Add a single instrument track to the current Ableton session
python scripts/session_init.py add-instrument --slug take5

# Print full MIDI channel map
python scripts/session_init.py midi-map
```

---

### MIDI Generation

**`midi_craft.py`** — Generates MIDI files from a concept description, key, and BPM.

```bash
# Generate a pattern from a concept
python scripts/midi_craft.py --concept "heavy 7/8 kick groove" --bpm 95 --key A

# Euclidean pattern for a specific instrument
python scripts/midi_craft.py --pattern "euclidean kick" --steps 16 --instrument digitakt

# Scale-correct melodic sequence
python scripts/midi_craft.py --concept "Phrygian bass line" --bpm 95 --key A --instrument minibrute2s
```

Output goes to `midi/patterns/` or `midi/sequences/` depending on context.

---

### Pattern Learning and Mutation

**`pattern_learn.py`** — Pulls clip notes from a running Live session, analyzes them, and generates statistically-inspired variations.

```bash
# Learn all clips currently in Live
python scripts/pattern_learn.py learn --all

# Learn a specific clip (by track/slot index)
python scripts/pattern_learn.py learn --track 0 --slot 0

# List learned profiles
python scripts/pattern_learn.py list

# Inspect a profile
python scripts/pattern_learn.py show \
  --profile midi/patterns/learned/rust-protocol_0_0.json

# Generate a new pattern from a learned profile
python scripts/pattern_learn.py generate \
  --profile midi/patterns/learned/rust-protocol_0_0.json

# Generate and immediately push to Live
python scripts/pattern_learn.py generate \
  --profile midi/patterns/learned/rust-protocol_0_0.json --push
```

Learned profiles: `midi/patterns/learned/`
Generated patterns: `midi/patterns/generated/`

**`run_pattern_mutator.py`** — Algorithmic mutations (inversion, retrograde, displacement, Euclidean reshaping) on existing patterns. Writes mutated .mid files and a session log.

```bash
python scripts/run_pattern_mutator.py                        # all patterns in midi/patterns/
python scripts/run_pattern_mutator.py --pattern kick_v1.mid  # specific file
python scripts/run_pattern_mutator.py --no-llm               # skip Gemini annotation
python scripts/run_pattern_mutator.py --force                # overwrite today's log
```

---

### Audio Analysis

**`analyze_audio.py`** — BPM detection, key estimation, spectral analysis (librosa).

```bash
python scripts/analyze_audio.py audio/recordings/raw/take1.wav
python scripts/analyze_audio.py audio/recordings/raw/take1.wav --focus bpm
python scripts/analyze_audio.py audio/recordings/raw/take1.wav --output outputs/analysis.json
```

**`gemini_listen.py`** — Qualitative audio analysis via Gemini API. Answers "does this feel right?"

```bash
python scripts/gemini_listen.py --file audio/recordings/raw/take1.wav
python scripts/gemini_listen.py --file ref.mp3 --question "Is this heavy enough?"
python scripts/gemini_listen.py --file loop.wav --output json
```

**`run_audio_intake.py`** — Batch processor. Scans `audio/recordings/raw/` for new files, runs BPM+key detection, calls Gemini for rig-specific suggestions, writes to manifest.

```bash
python scripts/run_audio_intake.py
python scripts/run_audio_intake.py --no-llm         # skip Gemini, analysis only
python scripts/run_audio_intake.py --scan-stems     # also scan audio/recordings/stems/
```

---

### Audio to MIDI

**`audio_to_midi.py`** — Converts audio to MIDI via Basic Pitch. Optionally separates stems with Demucs first.

```bash
# Single file
python scripts/audio_to_midi.py audio/recordings/raw/bass_riff.aif

# Full mix with stem separation
python scripts/audio_to_midi.py audio/recordings/raw/full_mix.wav --stems

# Specific stem type
python scripts/audio_to_midi.py audio/recordings/raw/full_mix.wav --stems --stem-type bass

# Specify output directory
python scripts/audio_to_midi.py path/to/file.wav --output midi/sequences/
```

---

### ALS / Session Parsing

**`parse_als.py`** — Quick parse of an .als file to JSON summary.

```bash
python scripts/parse_als.py ableton/sessions/rust-protocol_v1.als
python scripts/parse_als.py ableton/sessions/rust-protocol_v1.als outputs/rust-protocol_summary.json
```

**`extract_midi_clips.py`** — Extracts MIDI notes from all clips in an .als file, writes one .mid per clip.

```bash
python scripts/extract_midi_clips.py ableton/sessions/rust-protocol_v1.als midi/sequences/
python scripts/extract_midi_clips.py path/to/Project.als /path/to/outdir --ticks 480
```

---

### SysEx / Preset Management

**`sysex_capture.py`** — Capture and catalog SysEx dumps from the Rev2 or Take5.

```bash
# List available MIDI ports
python scripts/sysex_capture.py list-ports

# Open a port and capture incoming SysEx (sends to hardware: initiate dump from instrument panel)
python scripts/sysex_capture.py capture --port "Rev2" --instrument rev2
python scripts/sysex_capture.py capture --port "Take 5" --instrument take5 --timeout 60

# Parse a raw dump file into preset JSON
python scripts/sysex_capture.py parse \
  --file instruments/sequential-rev2/presets/raw/dump_20260424.syx --instrument rev2

# Re-catalog all dumps for an instrument
python scripts/sysex_capture.py catalog --instrument rev2
```

Raw dumps: `instruments/[slug]/presets/raw/`
Parsed presets: `instruments/[slug]/presets/`

**`push_preset.py`** — Push a preset JSON to hardware via NRPN.

```bash
python scripts/push_preset.py \
  --preset instruments/sequential-take5/presets/take5_oxidized-floor-bass_A-phrygian.json

# Dry run (print what would be sent, don't send)
python scripts/push_preset.py --preset path/to/preset.json --dry-run

# Override port and channel
python scripts/push_preset.py --preset path/to/preset.json --port "Take5" --channel 4
```

---

### LLM-Assisted Weekly Generators

All of these call Gemini (requires `GEMINI_API_KEY` env var). All support `--no-llm` to generate stubs without an API call.

**`run_brainstorm.py`** — Weekly creative brainstorm based on active song context.
```bash
python scripts/run_brainstorm.py
python scripts/run_brainstorm.py --no-llm
python scripts/run_brainstorm.py --date 2026-05-01   # override output date
```
Output: `knowledge/brainstorms/YYYY-MM-DD.md`

**`run_theory_pulse.py`** — Weekly theory document for the active song's key/scale/BPM.
```bash
python scripts/run_theory_pulse.py
python scripts/run_theory_pulse.py --no-llm
```
Output: `knowledge/music-theory/pulse/YYYY-MM-DD.md`

**`run_preset_ideas.py`** — Sound design blueprints for each instrument in the rig.
```bash
python scripts/run_preset_ideas.py
python scripts/run_preset_ideas.py --instrument rev2   # single instrument
python scripts/run_preset_ideas.py --no-llm
python scripts/run_preset_ideas.py --force             # overwrite if exists
```
Output: `knowledge/sound-design/YYYY-MM-DD.md`

**`run_reference_digest.py`** — 5 reference tracks with production analysis and rig parallels.
```bash
python scripts/run_reference_digest.py
python scripts/run_reference_digest.py --no-llm
```
Output: `knowledge/references/YYYY-MM-DD.md`

**`run_session_summarizer.py`** — Narrative summary of the current Ableton session state.
```bash
python scripts/run_session_summarizer.py
python scripts/run_session_summarizer.py --no-llm
python scripts/run_session_summarizer.py --force
```
Reads from: `outputs/live_state.json` (requires session-reporter.amxd dump first)
Output: `knowledge/sessions/YYYY-MM-DD.md`

---

### Utilities and Infrastructure

**`scan_plugins.py`** — Scans installed VST2/VST3/CLAP/AU plugins on macOS.
```bash
python scripts/scan_plugins.py                            # writes database/plugins.json
python scripts/scan_plugins.py --format table             # human-readable
python scripts/scan_plugins.py --filter instruments       # instruments only
python scripts/scan_plugins.py --filter effects           # effects only
```

**`index_manuals.py`** — Extracts and indexes text from instrument PDF manuals for `manual-lookup` skill.
```bash
python scripts/index_manuals.py                   # all instruments
python scripts/index_manuals.py --instrument rev2 # one instrument
python scripts/index_manuals.py --force           # always re-index
python scripts/index_manuals.py --list            # list index status
```

**`gcs_sync.py`** — Upload/download audio files to GCS. Audio never goes into git directly.
```bash
python scripts/gcs_sync.py push audio/recordings/raw/take1.wav
python scripts/gcs_sync.py push audio/recordings/raw/          # whole directory
python scripts/gcs_sync.py pull audio/recordings/raw/take1.wav
python scripts/gcs_sync.py ls
python scripts/gcs_sync.py status
python scripts/gcs_sync.py index                              # rebuild manifest from GCS
```

**`run_repo_health.py`** — Audits repo structure for missing docs, uncatalogued instruments, etc.
```bash
python scripts/run_repo_health.py
python scripts/run_repo_health.py --no-llm
```
Output: `outputs/repo_health.json` and `outputs/repo_health_issues.md`

**`maxpat_to_amxd.py`** — Convert a .maxpat file to deployable .amxd format.
```bash
python scripts/maxpat_to_amxd.py ableton/m4l/my-device.maxpat
python scripts/maxpat_to_amxd.py --all   # build all .maxpat files in ableton/m4l/
```

---

## 5. M4L Devices

All live in `ableton/m4l/`. Drop these on tracks in Ableton.

### `session-reporter.amxd`
**Drop on Master track.**
Dumps current session state to `outputs/live_state.json` on demand. Click the Dump button.
This file is the Live Engineer's eyes — read it before making any session suggestions.

### `iron-static-bridge.amxd`
**Drop on Master track.**
OSC UDP bridge (port 7400 receive, 7401 send). Keeps Python ↔ Live comms alive.
Required for `bridge_client.py`, `pattern_learn.py --push`, and any real-time remote control.

### `pattern-injector.amxd`
**Drop on a MIDI track.**
Writes notes from a generated pattern JSON directly into a Live clip.
Used by `pattern_learn.py --push` and the ableton-push skill.

---

## 6. Remote Script Bridge

The IronStatic Remote Script is a Python TCP server running inside Live on port 9877. It is **not** an M4L device — it's installed in the app bundle.

### Check if it's alive
```bash
echo '{"command": "ping"}' | nc -q1 127.0.0.1 9877
```

### Direct JSON commands
```bash
# Get current session info
echo '{"command": "get_session_info"}' | nc -q1 127.0.0.1 9877

# Set tempo
echo '{"command": "set_tempo", "bpm": 95}' | nc -q1 127.0.0.1 9877

# Fire a scene
echo '{"command": "fire_scene", "index": 0}' | nc -q1 127.0.0.1 9877
```

### If the bridge isn't responding
1. Check Ableton is running: `pgrep -x "Live"`
2. Confirm IronStatic is selected in Settings → Link/Tempo/MIDI → Control Surface
3. Deselect and reselect IronStatic to force reload
4. If still broken: `python scripts/deploy_remote_script.py` then restart Live

---

## 7. Key Files and Databases

### State files (read first, always)

| File | What it contains | How to update |
|---|---|---|
| `database/songs.json` | All songs, active song flag, key/scale/BPM/ALS path, brainstorm path | `manage_songs.py` |
| `outputs/live_state.json` | Current Ableton session state (tracks, clips, tempo, devices) | Trigger `session-reporter.amxd` Dump button |
| `database/instruments.json` | Registered instruments, MIDI channels, has_memory flag | Manual edit or `instrument-onboard` skill |
| `database/plugins.json` | Installed VST/AU plugins on this machine | `scan_plugins.py` |
| `database/ableton_devices.json` | Full index of built-in Ableton instruments and FX | Updated by Live Engineer when new devices are catalogued |

### Instrument data

| Path | What it contains |
|---|---|
| `instruments/[slug]/presets/` | Preset JSON files and panel-state .md files |
| `instruments/[slug]/presets/raw/` | Raw .syx SysEx dumps |
| `instruments/[slug]/manuals/` | PDF manuals + indexed .txt and .index.json files |
| `database/midi_params/[slug].json` | Full MIDI/NRPN parameter map for MIDI-dumpable instruments |

### Session files

| Path | What it contains |
|---|---|
| `ableton/sessions/[slug]_v[N].als` | Working session |
| `ableton/sessions/[slug]_v[N]-internal.als` | Offline/internal instrument version |
| `ableton/sessions/Internal Project/Internal.als` | Reference session with all built-in devices — source of truth for `generate_als.py` |
| `ableton/templates/[slug].hcl` | HCL session templates for `ableton_push.py setup-rig` |
| `ableton/m4l/configs/[slug]-internal.json` | Config for `generate_als.py` — maps track names to devices |

### Knowledge files (living documents)

| Path | What it contains |
|---|---|
| `knowledge/brainstorms/YYYY-MM-DD.md` | Weekly creative brainstorm output (active song-specific) |
| `knowledge/music-theory/pulse/YYYY-MM-DD.md` | Weekly theory pulse for active key/scale |
| `knowledge/sound-design/YYYY-MM-DD.md` | Weekly preset ideas per instrument |
| `knowledge/references/YYYY-MM-DD.md` | Weekly reference track digest |
| `knowledge/sessions/YYYY-MM-DD.md` | Session summary from Ableton state |
| `knowledge/band-lore/manifesto.md` | The aesthetic standard. The Critic uses this. |
| `knowledge/patterns/YYYY-MM-DD.md` | Pattern mutator session log |

---

## 8. Day 1 Workflows

### Starting a new session from scratch

```bash
# 1. Check what song is active
python scripts/manage_songs.py list

# 2. If no active song, add and activate one
python scripts/manage_songs.py add --slug my-song --title "My Song" --key A --scale phrygian --bpm 95
python scripts/manage_songs.py activate --slug my-song

# 3. Scan connected hardware
python scripts/session_init.py scan

# 4. Generate a weekly brainstorm for the new song (requires GEMINI_API_KEY)
python scripts/run_brainstorm.py

# 5. In VS Code Chat, switch to "The Live Engineer" agent and ask:
#    "Generate an internal session for [song-slug] based on the brainstorm"
```

---

### Hardware is offline — build an in-box session

```bash
# 1. Check track names in your base session
python scripts/generate_als.py --list --base ableton/sessions/rust-protocol_v1.als

# 2. Check available internal devices
python scripts/generate_als.py --list-devices

# 3. Ask The Live Engineer agent to create the config
#    (it reads the brainstorm and makes creative decisions)

# 4. Run dry-run to verify
python scripts/generate_als.py \
  --base ableton/sessions/rust-protocol_v1.als \
  --config ableton/m4l/configs/rust-protocol-internal.json \
  --dry-run -v

# 5. Generate
python scripts/generate_als.py \
  --base ableton/sessions/rust-protocol_v1.als \
  --config ableton/m4l/configs/rust-protocol-internal.json \
  --out ableton/sessions/rust-protocol_v1-internal.als

# 6. Open
open 'ableton/sessions/rust-protocol_v1-internal.als'

# 7. Switch to "The Critic" agent and ask it to evaluate the choices
```

---

### Push a MIDI file to a Live clip

```bash
# 1. Confirm Live is running with IronStatic selected
python scripts/ableton_push.py status

# 2. Push the file
python scripts/ableton_push.py push-midi \
  --file midi/sequences/riff_v1.mid --track "Rev2-A" --clip 0

# 3. Fire the clip to hear it
python scripts/ableton_push.py fire --track "Rev2-A" --clip 0
```

---

### Capture a SysEx dump from the Rev2

```bash
# 1. List MIDI ports to confirm the Rev2 is visible
python scripts/sysex_capture.py list-ports

# 2. Start listening (this script opens the port and waits)
python scripts/sysex_capture.py capture --port "Rev2" --instrument rev2

# 3. On the Rev2: hold SHIFT + press WRITE to initiate a global dump
#    (The script captures and saves to instruments/sequential-rev2/presets/raw/)

# 4. Parse the dump
python scripts/sysex_capture.py catalog --instrument rev2
```

---

### Learn a clip from Live and generate a variation

```bash
# 1. Confirm Live is running and iron-static-bridge.amxd is loaded on Master
python scripts/ableton_push.py status

# 2. Learn a specific clip
python scripts/pattern_learn.py learn --track 0 --slot 0

# 3. Generate a variation
python scripts/pattern_learn.py generate \
  --profile midi/patterns/learned/rust-protocol_0_0.json

# 4. Push the variation directly back to Live
python scripts/pattern_learn.py generate \
  --profile midi/patterns/learned/rust-protocol_0_0.json --push
```

---

### Dump and summarize the current Live session

```bash
# 1. In Ableton, click the Dump button on session-reporter.amxd
#    (this writes outputs/live_state.json)

# 2. Generate a narrative summary
python scripts/run_session_summarizer.py

# 3. Read the result
cat knowledge/sessions/$(date +%Y-%m-%d).md
```

---

### Run the full weekly creative cycle

Run these once per week (Monday). All require `GEMINI_API_KEY`.

```bash
# 1. Reference digest — 5 reference tracks with production analysis (feeds into brainstorm)
python scripts/run_reference_digest.py

# 2. Brainstorm — creative direction for the active song (reads the reference digest above)
python scripts/run_brainstorm.py

# 3. Theory pulse — scale map, chord vocabulary, hardware-actionable theory
python scripts/run_theory_pulse.py

# 4. Preset ideas — sound design blueprints per instrument
python scripts/run_preset_ideas.py

# 5. Repo health check — catch missing docs, uncatalogued instruments
python scripts/run_repo_health.py

# 6. Open this week's brainstorm and read it before starting any session work
cat knowledge/brainstorms/$(date +%Y-%m-%d).md
```

---

### Add a new instrument to the repo

```bash
# In VS Code Chat, switch to "The Sound Designer" agent and say:
# "Onboard a new instrument: [name]"
# The instrument-onboard skill handles folder structure, manual index, param map, SysEx wiring
```

Manual steps if doing it yourself:
```bash
mkdir -p instruments/[slug]/manuals instruments/[slug]/presets/raw
# Add PDF manual to instruments/[slug]/manuals/
python scripts/index_manuals.py --instrument [slug]
# Add entry to database/instruments.json
# Add entry to database/midi_params/[slug].json (if MIDI dumpable)
```

---

### Deploy an updated Remote Script

```bash
# 1. Edit ableton/remote_script/IronStatic/__init__.py

# 2. Deploy (compiles .pyc, copies to app bundle)
python scripts/deploy_remote_script.py

# 3. In Ableton Settings → Link/Tempo/MIDI → Control Surface:
#    Deselect IronStatic, wait 2 seconds, reselect IronStatic

# 4. Confirm it loaded:
python scripts/ableton_push.py status
```

---

## MIDI Channel Quick Reference

| Channel | Instrument |
|---|---|
| 1 | Digitakt (auto-channel) |
| 2 | Rev2 Layer A |
| 3 | Rev2 Layer B |
| 4 | Take 5 |
| 5 | Subharmonicon |
| 6 | DFAM |
| 7 | Minibrute 2S |
| 8 | Arturia Pigments |
| 16 | Global clock / transport |

## Instrument Slugs Quick Reference

| Slug | Instrument |
|---|---|
| `digitakt` | Elektron Digitakt MK1 |
| `rev2` | Sequential Rev2 |
| `take5` | Sequential Take 5 |
| `subharmonicon` | Moog Subharmonicon |
| `dfam` | Moog DFAM |
| `minibrute2s` | Arturia Minibrute 2S |
| `pigments` | Arturia Pigments |
