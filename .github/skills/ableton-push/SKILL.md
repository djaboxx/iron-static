---
name: ableton-push
description: Set up Ableton sessions from HCL templates, push MIDI files into clips, and control playback — all via the IronStatic Remote Script bridge.
argument-hint: "[command: setup-rig|push-midi|fire|stop|set-tempo|status] [options]"
user-invocable: true
disable-model-invocation: false
---

# Skill: ableton-push

## What This Skill Does

Bridges the Iron Static repo directly to a live Ableton session via TCP socket.
Uses `scripts/ableton_push.py` to:
1. Build a full session layout from an HCL template (`setup-rig`)
2. Push `.mid` files from `midi/sequences/` directly into Ableton clip slots (`push-midi`)
3. Control playback — fire clips, stop clips, set tempo
4. Inspect the current session state (`status`)

## Prerequisites

1. **Install the Remote Script** — run the deploy script (handles pyc compilation):
   ```bash
   python scripts/deploy_remote_script.py
   ```
   This installs into the app bundle (`Contents/App-Resources/MIDI Remote Scripts/IronStatic/`).
   **Important**: Live 12 on macOS requires `__init__.pyc` in the script folder root, NOT just `__pycache__/`.
   User Remote Scripts directories are NOT scanned by Live 12.2+ — use the app bundle.

2. In Ableton → Settings → Link/Tempo/MIDI → Control Surface → select **IronStatic**, Input: None, Output: None
3. Ableton must be open with the script loaded (check log: "listening on port 9877") before any commands will work
4. If redeploying after changes: deselect + reselect IronStatic in preferences to reload without restarting Ableton

## When to Use

- When setting up a new Ableton session for an Iron Static session/rehearsal
- After `midi-craft` or `audio-to-midi` generates a `.mid` file and you want it live in Ableton immediately
- When iterating on a sequence — push → fire → listen → revise
- When you want to define a new session layout as an HCL file and apply it

## Usage

### Check connection / session state
```bash
python scripts/ableton_push.py status
```

### Build rig from HCL template
```bash
python scripts/ableton_push.py setup-rig --template ableton/templates/iron-static-default.hcl
```

### Push a MIDI file into a clip
```bash
# By track name (preferred)
python scripts/ableton_push.py push-midi --file midi/sequences/my_bass_v1.mid --track Minibrute2S --clip 0

# By track index
python scripts/ableton_push.py push-midi --file midi/sequences/my_pad_v1.mid --track 1 --clip 0
```

### Fire / stop a clip
```bash
python scripts/ableton_push.py fire --track Digitakt --clip 0
python scripts/ableton_push.py stop --track Digitakt --clip 0
```

### Set tempo
```bash
python scripts/ableton_push.py set-tempo --bpm 140
```

## HCL Template Format

Session templates live in `ableton/templates/`. Create new ones to define different rig configurations.

```hcl
session {
  name           = "My Session"
  tempo          = 140
  time_signature = [4, 4]
}

track "Rev2-A" {
  midi_channel = 2
  color        = 0x0044FF

  clip "pad-main" {
    index  = 0
    length = 8.0
  }
}
```

See [iron-static-default.hcl](../../ableton/templates/iron-static-default.hcl) for the full rig template.

## Full Pipeline Example

```bash
# 1. Analyze a recording
python scripts/analyze_audio.py audio/recordings/raw/take1.aif
# → Key: G minor, BPM: 92

# 2. Transcribe to MIDI
python scripts/audio_to_midi.py audio/recordings/raw/take1.aif
# → midi/sequences/take1_unknown_v1.mid

# 3. Set Ableton tempo to match
python scripts/ableton_push.py set-tempo --bpm 92

# 4. Build the rig
python scripts/ableton_push.py setup-rig --template ableton/templates/iron-static-default.hcl

# 5. Push the MIDI into a clip
python scripts/ableton_push.py push-midi --file midi/sequences/take1_unknown_v1.mid --track Rev2-A --clip 0

# 6. Fire it
python scripts/ableton_push.py fire --track Rev2-A --clip 0
```

## MIDI Channel Map (from default template)

| Track | MIDI Ch | Instrument |
|---|---|---|
| Digitakt | 1 | Elektron Digitakt MK1 |
| Rev2-A | 2 | Sequential Rev2 Layer A |
| Rev2-B | 3 | Sequential Rev2 Layer B |
| Take5 | 4 | Sequential Take 5 |
| Subharmonicon | 5 | Moog Subharmonicon |
| DFAM | 6 | Moog DFAM |
| Minibrute2S | 7 | Arturia Minibrute 2S |

## Troubleshooting

- **Connection refused**: IronStatic Remote Script is not loaded or Ableton is not running
- **Timeout**: Ableton is busy or the Remote Script crashed — restart Ableton and reload the script
- **Track not found**: Run `status` first to confirm track names match exactly
- **Clip slot occupied**: The `create_clip` command will error if a clip already exists in that slot — clear it in Ableton first

---

## Max for Live Device (.amxd) Format

### CRITICAL: .amxd is a binary container, NOT plain JSON

`.amxd` files cannot be created by simply renaming a `.maxpat` or `.json` file. Ableton will silently reject plain JSON files — you'll see a "no" cursor when trying to drag them onto tracks.

**Binary format**: `ampf` magic header → `aaaa` section → `meta` section → `ptch` + uint32_LE length + JSON payload + `\n\x00` terminator.

**Build script** (use this every time you need to create or update an .amxd):
```python
import struct, json

TEMPLATE = "/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/Max Devices/Max Audio Effect.amxd"
with open(TEMPLATE, "rb") as f:
    tpl = f.read()
ptch_offset = tpl.index(b'ptch')
fixed_header = tpl[:ptch_offset + 4]   # everything up to and including 'ptch'

with open("my-device.maxpat") as f:
    doc = json.load(f)
json_bytes = json.dumps(doc, indent="\t", separators=(',', ' : ')).encode('utf-8') + b'\n\x00'
amxd = fixed_header + struct.pack('<I', len(json_bytes)) + json_bytes
with open("my-device.amxd", "wb") as f:
    f.write(amxd)
```

### Device type is determined by `plugin~`/`plugout~`, NOT classname

- **Audio Effect** (works on any track including Master): patcher must contain `plugin~` → `plugout~` passthrough. No `classname` field needed.
- **MIDI Effect**: must contain `midiin`/`midiout`. Use `Max MIDI Effect.amxd` as template header.
- **Instrument**: must contain `plugout~` but no `plugin~`. Use `Max Instrument.amxd` as template header.
- Do NOT set `"classname": "MxDLiveAudioEffect"` — this field is not valid and causes rejection.
- DO set `"classnamespace": "box"` — this is required.

### Installing the device

Ableton will NOT accept `.amxd` files dragged from arbitrary filesystem paths. Two options:
1. **User Library** (recommended): copy to `~/Music/Ableton/User Library/Presets/Audio Effects/Max Audio Effect/`
2. **Places**: add the folder as a Place in Ableton's browser sidebar, then drag from there.

### JS files and autowatch

- Place `session_reporter.js` in the same directory as the `.amxd`
- `patcherrelativepath: "."` in `dependency_cache` tells Max to look in the same dir
- `autowatch = 1` in the JS reloads automatically when the file changes on disk
- `LiveAPI` only works when the device is loaded inside Ableton — NOT in standalone Max

## Script: [ableton_push.py](../../scripts/ableton_push.py)
## Remote Script: [IronStatic/__init__.py](../../ableton/remote_script/IronStatic/__init__.py)
