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

### Find a clip by name
```bash
# Find any clip named "phrygian-riff" anywhere in the session
python scripts/bridge_client.py clip find "phrygian-riff"

# Restrict search to a specific track
python scripts/bridge_client.py clip find "phrygian-riff" --on-track Rev2-A
```
Returns `{track_index, track_name, clip_index, clip_name}`.
If multiple clips share the name, returns a `{matches: [...]}` list — use `--on-track` to disambiguate.

### Learn a clip by name (pattern_learn)
```bash
python scripts/pattern_learn.py learn --name "phrygian-riff"
python scripts/pattern_learn.py learn --name "phrygian-riff" --on-track Rev2-A
```

### Set tempo
```bash
python scripts/ableton_push.py set-tempo --bpm 140
```

### List devices on a track
```bash
python scripts/ableton_push.py get-devices --track DFAM
# → [0] Collision  (InstrumentRack)  12 params  (2 chains)
```

### List parameters on a device
```bash
# Top-level device
python scripts/ableton_push.py get-params --track DFAM --device 0

# Device inside a rack chain (chain 0, device 0)
python scripts/ableton_push.py get-params --track DFAM --device 0 --chain 0.0
# → [0] Device On       = 1.0000  (range 0.00–1.00)
# → [1] Chain Selector  = 0.0000  (range 0.00–127.00)
# → ...
```

### Set a device parameter
```bash
# By parameter name (preferred — use exact name from get-params output)
python scripts/ableton_push.py set-param --track DFAM --device 0 \
    --param "Chain Selector" --value 64

# By parameter index
python scripts/ableton_push.py set-param --track DFAM --device 0 --param 1 --value 64

# Inside a rack chain (chain 1, device 0)
python scripts/ableton_push.py set-param --track DFAM --device 0 --chain 1.0 \
    --param "Drive" --value 0.65
```

### Scene management
```bash
# Fire a scene by index
python scripts/ableton_push.py fire-scene --index 3

# Create a new scene (appended by default)
python scripts/ableton_push.py create-scene --name "[04] Breakdown 95bpm"
```

### Device manipulation (Live 12.3+)

> These commands require **Ableton Live 12.3 or later**. They use the `Track.insert_device`,
> `RackDevice.insert_chain`, and `Chain.insert_device` LOM APIs added in that release.
> **Only native Live devices** can be inserted — no M4L or plug-ins.

```bash
# Insert a native device into a track's device chain
python scripts/ableton_push.py insert-device --track DFAM --device-name "Collision"
python scripts/ableton_push.py insert-device --track DFAM --device-name "Instrument Rack"

# Insert at a specific position (index 0 = first)
python scripts/ableton_push.py insert-device --track DFAM --device-name "Auto Filter" --target-index 1

# Insert a device into a specific chain of the first rack on the track
python scripts/ableton_push.py insert-device --track DFAM --device-name "Collision" --chain 0

# Add a new empty chain to a rack (device index 0 on the track)
python scripts/ableton_push.py insert-chain --track DFAM --device 0 --name "Tone Layer"

# Insert a chain at a specific position
python scripts/ableton_push.py insert-chain --track DFAM --device 0 --index 1 --name "Sub"
```

### Build a rack from scratch (Live 12.3+)

`build-rack` is the highest-level command — it finds or creates an Instrument Rack on a track,
then adds named chains each containing a specified device:

```bash
# Build a 3-chain Collision rack on the DFAM track
python scripts/ableton_push.py build-rack --track DFAM --rack-name "DFAM Rack" \
  --chains '[{"name":"Hit","device":"Collision"},{"name":"Tone","device":"Collision"},{"name":"Sub","device":"Collision"}]'

# After building, set the Chain Selector via set-param
python scripts/ableton_push.py set-param --track DFAM --device 0 \
    --param "Chain Selector" --value 0
```

Full DFAM rack build workflow:
```bash
# 1. Build the rack with 3 Collision chains
python scripts/ableton_push.py build-rack --track DFAM --rack-name "DFAM Rack" \
  --chains '[{"name":"Hit","device":"Collision"},{"name":"Tone","device":"Collision"},{"name":"Noise","device":"Collision"}]'

# 2. Confirm the rack was created
python scripts/ableton_push.py get-devices --track DFAM

# 3. Get the Chain Selector parameter index for automation
python scripts/ableton_push.py get-params --track DFAM --device 0 | grep -i "chain"

# 4. Select chain 0 (Hit)
python scripts/ableton_push.py set-param --track DFAM --device 0 --param "Chain Selector" --value 0
```

### Load a browser preset onto a track (no drag required)
```bash
# Load a pack preset (.adg) onto a track by browser name
python scripts/ableton_push.py load-preset \
    --track "808 Drums" --preset "808 Depth Charger Kit"

# Preset name is matched case-insensitively; .adg extension is optional.
# The track must already exist. Typical full workflow:
python scripts/ableton_push.py create-track --name "808 Drums"
python scripts/ableton_push.py load-preset --track "808 Drums" --preset "808 Depth Charger Kit"
python scripts/ableton_push.py get-devices --track "808 Drums"   # verify
```

### Apply a preset JSON to a device (batch — one round-trip)
```bash
# Push all params from a preset file to a track's device
python scripts/ableton_push.py apply-preset \
    --track DFAM --device 0 \
    --preset instruments/moog-dfam/presets/dfam-rack-rust-protocol.json

# Preset JSON format:
# {
#   "name": "DFAM Rack Rust Protocol",
#   "parameters": {},
#   "chains": {
#     "0": {"_name": "Hit", "Res 1 Decay": 0.22, "Mallet Volume": 0.8, ...},
#     "1": {"_name": "Tone", "Res 1 Type": 6, "Res 2 On/Off": 1.0, ...},
#     "2": {"_name": "Noise", "Mallet On/Off": 0.0, "Noise On/Off": 1.0, ...}
#   }
# }
# Keys starting with "_" are metadata — ignored when applying.
```

### Delete a device from a track or rack chain
```bash
# Delete device 0 from a track
python scripts/ableton_push.py delete-device --track DFAM --device 0

# Delete the device in chain 2 of rack device 0
python scripts/ableton_push.py delete-device --track DFAM --device 0 --chain 2
```

### List installed packs and search for presets
```bash
# List all installed packs
python scripts/ableton_push.py list-packs

# Search for 808 drum rack presets (.adg)
python scripts/ableton_push.py list-packs --search 808

# Search for Collision-based racks
python scripts/ableton_push.py list-packs --search Collision
```

**Pack locations on disk:**
- Installed packs: `~/Music/Ableton/Packs/<Pack Name>/`
- User presets: `~/Music/Ableton/User Library/Presets/`
- Live database: `~/Library/Application Support/Ableton/Live Database/Live-files-<version>.db`
- `list-packs` queries the most recent DB automatically.

**Installed packs on this machine (as of April 2026):**
- Beat Tools
- Drum Essentials (808 Depth Charger Kit, 808 Status Quo Kit, 808 Startup Kit, 808 Medussa Kit, 808 Aristocrat Kit, 808 Fairweather Kit, OP 808 Kit)
- Classic Synths by Katsuhiro Chiba
- Connection Kit
- Convolution Reverb
- M4L Big Three / M4L Granulator II
- Max for Live Essentials
- MIDI Tools by Philip Meyer
- Skitter and Step
- APC Step Sequencer / BeatSeeker

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

## Preset Workflow — Design → Apply

The correct workflow for dialling in device patches from scripts is:

```
1. create-preset skill → design patch → save JSON to instruments/<slug>/presets/<name>.json
2. apply-preset command → one batch round-trip pushes all params to Live
3. get-params to verify → optional readback
```

Do NOT call `set-param` in a shell loop or raw socket script — this is out-of-band and breaks the preset audit trail. Use `apply-preset`.

## MIDI Clip Workflow — Create → Push → Fire

**CRITICAL**: `push-midi` requires the clip slot to already contain a clip. Always `create-clip` first.

```bash
# Step 1: Create an empty clip in the slot (length in beats: 32 = 8 bars at 4/4)
python scripts/ableton_push.py create-clip --track DFAM --clip 0 --length 32

# Step 2: Generate the MIDI content — write it to a .mid file via midi_craft.py
# (or generate inline notes if using a custom script)

# Step 3: Push the MIDI file into the clip
python scripts/ableton_push.py push-midi \
    --file midi/sequences/rust-protocol_dfam_v1.mid \
    --track DFAM --clip 0

# Step 4: Name the clip so it's identifiable in the session
python scripts/ableton_push.py set-clip-name --track DFAM --clip 0 \
    --name "rust-protocol groove v1"

# Step 5: Fire it
python scripts/ableton_push.py fire --track DFAM --clip 0
```

**Clip length guideline** (at 4/4):
- 4 beats = 1 bar
- 16 beats = 4 bars
- 32 beats = 8 bars (default — good for most loop patterns)
- 64 beats = 16 bars

If you know the pattern length upfront, set `--length` to exactly match. Ableton will not auto-trim to note content — length determines the loop point.

### Create clip + push inline (no .mid file needed for simple patterns)

For the Sound Designer generating patterns directly (no midi_craft.py detour):
1. `create-clip` to create the slot
2. Use the Remote Script directly via a Python one-liner to push notes JSON inline — OR use `midi_craft.py` to emit the `.mid` file and then `push-midi`

The midi_craft.py path is preferred for auditability. The `.mid` file stays in `midi/sequences/` as documentation.

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

# 5. Create the clip slot, then push MIDI into it
python scripts/ableton_push.py create-clip --track Rev2-A --clip 0 --length 32
python scripts/ableton_push.py push-midi \
    --file midi/sequences/take1_unknown_v1.mid --track Rev2-A --clip 0
python scripts/ableton_push.py set-clip-name --track Rev2-A --clip 0 --name "take1"

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
