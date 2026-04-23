# M4L Device Concepts for IRON STATIC Copilot Integration

Indexed from:
- https://docs.cycling74.com/legacy/max8/vignettes/live_api_overview
- https://docs.cycling74.com/legacy/max8/vignettes/live_object_model

---

## Live Object Model — Key Capabilities

### Root Paths
| Path | Class | What it unlocks |
|------|-------|-----------------|
| `live_set` | Song | Transport, tempo, scale, tracks, scenes, cue points, MIDI capture |
| `live_set view` | Song.View | Currently selected track, scene, clip, parameter |
| `live_set tracks N` | Track | Arm, mute, solo, devices, clips, routing |
| `live_set tracks N clip_slots M clip` | Clip | Full MIDI note R/W, loop, fire, quantize |
| `live_set tracks N devices M` | Device / PluginDevice | Parameters, preset switching |
| `live_set tracks N devices M parameters L` | DeviceParameter | Value get/set/observe, automation state |
| `live_set scenes N` | Scene | Per-scene tempo/time-sig, fire, name |
| `control_surfaces N` | ControlSurface | Grab MIDI controls, register custom controls, send SysEx |
| `this_device` | Device | Self-reference from inside any M4L patch |

### Critical Clip Functions (MIDI R/W)
```
call get_all_notes_extended        → all notes as dict {pitch, start_time, duration, velocity, ...}
call get_notes_extended from_pitch pitch_span from_time time_span
call add_new_notes {notes: [...]}  → write new notes
call apply_note_modifications      → update existing notes in-place
call remove_notes_by_id            → delete by note_id
call remove_notes_extended         → delete by pitch/time range
call quantize quantization_grid amount
call duplicate_loop
call clear_all_envelopes
```
Clip `notes` property: observe → bangs when note list changes.

### Device Parameter Control
- `live.object set value X` → writes parameter, goes into undo history
- `live.remote~ id N` → realtime control, **bypasses undo**, deactivates automation

### PluginDevice-specific
- `get presets` → list of preset names
- `set selected_preset_index N` → switch preset

### Transport & Song-level
```
call start_playing / stop_playing / continue_playing
call capture_midi destination   (0=auto, 1=session, 2=arrangement)
call trigger_session_record record_length
set tempo / observe tempo
set root_note / observe root_note   (0=C … 11=B)
set scale_name / observe scale_name
observe is_playing
call set_or_delete_cue
call jump_to_next_cue / jump_to_prev_cue
```

### Scene Control
```
call fire [force_legato] [can_select_scene_on_launch]
call fire_as_selected   → fires then advances to next scene
set tempo / set time_signature_numerator / set time_signature_denominator
```

### ControlSurface (MaxForLive surface)
```
call register_midi_control name status number  → returns LOM id
call grab_control id                            → exclusive ownership
call grab_midi                                  → forward all surface MIDI to M4L
call send_receive_sysex sysex_message          → SysEx round-trip
call send_midi midi_message
```

---

## Proposed M4L Devices for Copilot Integration

### 1. `iron-static-bridge.amxd` — Copilot OSC Bridge
**Type**: MIDI Effect (invisible, always-on, on master or a dedicated track)

**Purpose**: The primary integration layer. Exposes a UDP/OSC server inside Ableton so that `scripts/*.py` can directly read and write Live state without polling `.als` files.

**Key LOM used**:
- `live_set tracks N clip_slots M clip` → `add_new_notes`, `get_all_notes_extended`
- `live_set` → `tempo`, `root_note`, `scale_name`, `is_playing`, `capture_midi`
- `live_set view selected_track` → dynamically tracks what's selected
- `live_set scenes N` → `fire`

**Exposed commands (OSC)**:
```
/clip/get_notes  track_idx slot_idx          → returns JSON note dict
/clip/set_notes  track_idx slot_idx {notes}  → add_new_notes
/clip/fire       track_idx slot_idx
/scene/fire      scene_idx
/song/tempo      bpm
/song/state                                  → returns playing, tempo, scale, armed tracks
```

**Why this matters for Copilot**: Right now I can only push MIDI to Ableton via the IronStatic Remote Script (file-based or HTTP). With this bridge I can generate a pattern in `midi_craft.py`, send it via OSC, and it lands inside a live clip in real time — no file round-trip.

---

### 2. `pattern-injector.amxd` — Script-to-Clip MIDI Writer
**Type**: MIDI Effect (one per target track)

**Purpose**: Listens for incoming MIDI CC / note data from `this_device canonical_parent` track context and writes it into the currently selected clip slot using `add_new_notes`. Companion to `midi_craft.py` — after generating a `.mid`, this device ingests it directly.

**Key LOM used**:
- `this_device canonical_parent` → navigate to own track
- `live_set tracks N clip_slots M` → `create_clip length`, `fire`
- Clip → `add_new_notes`, `remove_notes_extended`

**Inputs**:
- Receives raw MIDI notes from `notein`
- Toggle: "replace" vs "overdub" mode
- Pattern length knob (in bars)

**Workflow**:
1. Script generates notes via `midi_craft.py` → sends over MIDI
2. Device writes them into target clip
3. OR: device creates a new clip slot, fills it, fires it

---

### 3. `pigments-macro-lens.amxd` — Pigments Parameter Observer
**Type**: MIDI Effect (on the Pigments track)

**Purpose**: Scans the device chain of its own track, finds the Pigments `PluginDevice`, and surfaces live-updating parameter values + preset list. Transmits CC20–23 for Macros M1–M4 back out to MIDI so a controller or another script can see real Pigments state.

**Key LOM used**:
- `this_device canonical_parent devices` → iterate, match `class_name == "PluginDevice"` and `name contains "Pigments"`
- `DeviceParameter` → `value`, `name`, observe changes
- `PluginDevice.presets`, `PluginDevice.selected_preset_index`

**Outputs**:
- MIDI CC20-23 reflecting Macro M1–M4 values (allows hardware controller feedback)
- OSC: `/pigments/preset_name`, `/pigments/m1` … `/pigments/m4`
- Sets `live.remote~` on each macro param for sub-millisecond no-undo control from `live.remote~`

**Why this matters for Copilot**: I can read actual Pigments state at any time, not just infer it from preset files.

---

### 4. `session-reporter.amxd` — Live Set State Snapshot
**Type**: MIDI Effect (master track)

**Purpose**: On demand (or periodically), dumps the full session state as a JSON file that `scripts/` can read. This gives me full situational awareness at any time without parsing `.als`.

**Emitted JSON structure**:
```json
{
  "tempo": 140.0,
  "scale": { "root_note": 2, "scale_name": "Minor" },
  "is_playing": true,
  "tracks": [
    {
      "index": 0, "name": "Kick", "arm": false, "mute": false,
      "playing_slot": 2,
      "devices": [{"name": "Drum Rack", "class_name": "InstrumentGroupDevice"}]
    }
  ],
  "scenes": [
    { "index": 0, "name": "Intro", "tempo": 130.0, "is_triggered": false }
  ]
}
```

**Key LOM used**:
- `live_set tracks`, `live_set scenes`
- Track: `name`, `arm`, `mute`, `playing_slot_index`, `devices`
- Scene: `name`, `tempo`, `time_signature_numerator`
- `js` object + `LiveAPI` JavaScript class (cleaner for iteration)

**Trigger methods**: Button in device UI, `/reporter/dump` OSC, or `loadbang`-equivalent via `live.thisdevice`

---

### 5. `scene-tempo-map.amxd` — Scene Tempo / Time Sig Programmer
**Type**: MIDI Effect (master track)

**Purpose**: Allows me to script scene tempo and time signature assignments from a JSON config file — critical for IRON STATIC's odd-meter transitions. Load a file, press apply, all scenes get their tempos/meters set.

**Key LOM used**:
- `live_set scenes N set tempo X`
- `live_set scenes N set time_signature_numerator X`
- `live_set scenes N set time_signature_denominator X`
- `live_set scenes N set name X`

**Input**: JSON file path (loaded via `js` `new java.io.File`)
**Example config**:
```json
[
  { "name": "A - Grid Lock",  "tempo": 140, "num": 7, "den": 8 },
  { "name": "B - Breakdown",  "tempo": 68,  "num": 4, "den": 4 },
  { "name": "C - Re-Entry",   "tempo": 140, "num": 5, "den": 4 }
]
```

---

### 6. `scale-broadcaster.amxd` — Key/Scale State Monitor
**Type**: MIDI Effect (master track)

**Purpose**: Observes `root_note` and `scale_name` via `live.observer`, broadcasts changes as MIDI CC so hardware (Rev2, Take 5) can be auto-transposed, and writes state to a watch file that `scripts/` can read.

**Key LOM used**:
- `live_set observe root_note`
- `live_set observe scale_name`

**MIDI output**:
- CC 0 on ch16 = root_note (0–11)
- CC 1 on ch16 = scale_index (mapped from name)

**Why this matters**: When I change the scale in Live, hardware synths can auto-respond if they're listening on ch16.

---

### 7. `arm-dispatcher.amxd` — MIDI Note → Track Arm Router
**Type**: MIDI Effect

**Purpose**: Maps MIDI notes C1–B1 to tracks 0–11. Note on = arm that track (and disarm others). Enables performance arming from the Digitakt's MIDI tracks.

**Key LOM used**:
- `live_set tracks N set arm 1`
- `live_set tracks observe arm`

---

## Implementation Notes

### Max Objects to use
- `live.thisdevice` — always use instead of `loadbang` to ensure API is ready
- `live.path` second outlet → `deferlow` → `live.object` (for notification-driven updates)
- `js` + `LiveAPI` object — better for iteration over track/device lists than raw `live.path` chains
- `udpreceive` / `udpsend` — for OSC bridge (use port 7400 for incoming, 7401 for outgoing)

### File locations
- `.amxd` files: `ableton/racks/` (existing M4L racks) or new `ableton/m4l/` subfolder
- JSON config files consumed by devices: `ableton/m4l/configs/`
- State dumps from `session-reporter`: `outputs/live_state.json`

### Priority Order
1. **`iron-static-bridge.amxd`** — unlocks everything; build this first
2. **`session-reporter.amxd`** — gives Copilot situational awareness immediately
3. **`pattern-injector.amxd`** — completes the generate→inject loop
4. **`scene-tempo-map.amxd`** — directly useful for Ventura and future songs
5. **`pigments-macro-lens.amxd`** — useful once Pigments performance workflow solidifies
6. **`scale-broadcaster.amxd`** — nice-to-have for live hardware response
7. **`arm-dispatcher.amxd`** — performance utility
