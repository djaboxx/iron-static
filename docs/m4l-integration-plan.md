# IRON STATIC — Max for Live Integration Plan

**Scope**: Copilot ↔ Ableton Live 12 integration via custom M4L devices  
**Source research**: Live 12 Manual (ch7, 10, 11, 16, 17, 19, 31, 32), Cycling '74 Live API + LOM reference  
**Related**: `knowledge/production/m4l-device-concepts.md`, `ableton/skills/ableton-push/SKILL.md`

---

## 1. What Live 12 Provides Natively (No M4L Needed)

Understanding what Live already does well prevents us from building things we don't need to build.

### MIDI Tools (ch11) — Built-in Pattern Work
Live 12 ships 11 Transformation tools and 4 Generator tools, all scale-aware and accessible from Clip View:

| Category | Tools | IRON STATIC Use Cases |
|---|---|---|
| **Transformations** | Arpeggiate, Chop, Connect, Glissando, LFO, Ornament, Quantize, Recombine, Span, Strum, Time Warp | Rhythmic chopping, velocity shaping, glissando for hardware synths |
| **Generators** | Rhythm, Seed, Shape, Stacks | Euclidean drum patterns, chord progressions in odd meters, seeded texture generation |
| **M4L (bundled)** | Velocity Shaper, Euclidean | Euclidean rhythms across 4 voices; custom velocity envelopes |

**Key property**: All MIDI Tools are scale-aware — when a clip scale is set (via `root_note`/`scale_name`), tools operate in scale degrees not semitones. This connects cleanly to the `scale-broadcaster.amxd` device concept.

**Conclusion**: We do NOT need to write custom MIDI transformation scripts for most standard operations. The MIDI Tools handle them. What we need M4L for is **injecting externally-generated patterns** (from `midi_craft.py`) and **reading state back out** to Copilot.

---

### Clip Recording (ch19) — What's Already Available
- **Capture MIDI**: Live is always listening on armed/monitored tracks. Pressing Capture MIDI retrieves whatever you just played — no record button needed. Tempo auto-detected on first capture. This is the primary live improv capture tool.
- **Overdub recording**: Build drum patterns layer by layer in looping Session clips.
- **Step recording**: Add notes with transport stopped — useful for precise pattern entry.
- **MIDI quantization**: Both pre-record (Record Quantization chooser) and post-record (Quantize MIDI Tool or `Ctrl+Shift+U`).

**Conclusion**: For live performance recording, the native tools are sufficient. M4L adds value for **programmatic injection** (script → clip) not manual recording.

---

### M4L Modulator Devices (ch32) — Built-in Parameter Control
Live's built-in M4L devices cover a lot of modulation ground already:

| Device | What it does | IRON STATIC relevance |
|---|---|---|
| **LFO** | Maps LFO to any 8 automatable params | Pigments macro modulation, filter sweeps |
| **Envelope Follower** | Amplitude → parameter; sidechain-able | Kick → Pigments filter cutoff, dynamic control |
| **Expression Control** | MIDI/MPE → parameter (Velocity, Modwheel, Pitchbend, Pressure, Keytrack, Random, Increment, Slide) | Map Digitakt velocity/CC to hardware/software parameters |
| **Shaper** / **Shaper MIDI** | Breakpoint envelope → parameter | Custom LFO shapes for industrial texture |
| **Envelope MIDI** | ADSR-triggered by MIDI notes | Per-note parameter modulation |

**Key detail on Expression Control**: 5 Mod Source tabs, each independently mappable to 8 automatable parameters each, with Modulate (additive) or Remote Control (exclusive) modes. **This device alone may replace the need for `pigments-macro-lens.amxd`** for basic macro control — unless we need Copilot to *read* Pigments macro state programmatically.

---

## 2. The Integration Gap — What Requires M4L

The gap between what Live provides natively and what the Copilot integration needs:

| Capability Needed | Native Live | Requires M4L |
|---|---|---|
| Generate MIDI in Python and write into a clip | ✗ | ✓ |
| Read full session state as JSON (tracks, tempos, clips) | ✗ | ✓ |
| Programmatically set scene tempos/time signatures | ✗ | ✓ |
| Real-time two-way comms with Python scripts | ✗ (file-based Remote Script only) | ✓ (UDP/OSC bridge) |
| Observe Live's root_note/scale and broadcast to hardware | ✗ | ✓ |
| Map Digitakt MIDI notes → track arm/disarm | ✗ | ✓ (or MIDI Remote Map) |
| Read Pigments plugin device params back to Copilot | ✗ | ✓ |
| Fire scenes programmatically from scripts | ✗ | ✓ |

---

## 3. M4L Device Feasibility Assessment

Seven devices were proposed in `knowledge/production/m4l-device-concepts.md`. Here's the assessment against the actual Live API and LOM capabilities:

### Device 1: `iron-static-bridge.amxd` — OSC Bridge
**Feasibility: HIGH**  
**LOM coverage confirmed**:
- `live_set tracks N clip_slots M clip` → `add_new_notes`, `get_all_notes_extended` ✓
- `live_set tempo`, `root_note`, `scale_name`, `is_playing` ✓  
- `live_set scenes N` → `fire` ✓

**Implementation notes**:
- Use `udpreceive 7400` and `udpsend localhost 7401` Max objects
- Use `js` + `LiveAPI` JavaScript class for all track/clip iteration (much cleaner than chained `live.path` objects)
- Use `live.thisdevice` → `deferlow` → `live.object` chain (not `loadbang`)
- Format outgoing data as JSON strings via `js` → pipe through `udpsend`

**Risk**: OSC message parsing and JSON serialization in Max `js` is verbose but well-documented. The `LiveAPI` callback model requires careful handling to avoid double-bangs on observe events.

---

### Device 2: `session-reporter.amxd` — State Snapshot
**Feasibility: HIGH**  
**LOM coverage confirmed**:
- All track properties (name, arm, mute, playing_slot_index) ✓
- Scene properties (name, tempo, time_signature_numerator/denominator) ✓
- PluginDevice class_name + name for device identification ✓

**Implementation notes**:
- `js` with `LiveAPI` iteration over `live_set tracks` and `live_set scenes` children
- Write to `outputs/live_state.json` via `js` file I/O (`java.io.FileWriter`)
- Add a `[button]` labeled "Dump State" + OSC `/reporter/dump` trigger from bridge
- Initialize via `live.thisdevice` → `live.object` → `get id` → then iterate

**Risk**: Low. This is the most straightforward device — read-only LOM queries.

---

### Device 3: `pattern-injector.amxd` — Script → Clip MIDI Writer
**Feasibility: HIGH**  
**LOM coverage confirmed**:
- `clip_slots M create_clip length` ✓ (creates empty clip)
- Clip → `add_new_notes {notes: [...]}` ✓
- Clip → `remove_notes_extended` ✓
- `live_set tracks N clip_slots M fire` ✓

**Implementation notes**:
- Receives notes either via MIDI `notein` OR via OSC from bridge (preferred — richer data, includes velocity and duration)
- Two modes: "Replace" clears clip first with `remove_notes_extended`, then writes; "Overdub" calls `add_new_notes` directly
- Target clip slot = currently selected clip (observe `live_set view selected_scene_index` + track context)
- Pattern length in bars → passed to `create_clip` as beat count (1 bar = 4 beats at 4/4)

**Risk**: Medium. The `add_new_notes` call requires precise dict format. Test against a known-good note dict before integrating with `midi_craft.py`.

---

### Device 4: `scene-tempo-map.amxd` — Scene Tempo Programmer
**Feasibility: HIGH**  
**LOM coverage confirmed**:
- `live_set scenes N set tempo X` ✓
- `live_set scenes N set time_signature_numerator X` ✓
- `live_set scenes N set time_signature_denominator X` ✓
- `live_set scenes N set name X` ✓

**Implementation notes**:
- Load JSON config via `js` `java.io.BufferedReader`
- UI: file path text box + "Load" + "Apply" buttons
- On Apply: iterate JSON array, set each scene's properties via `LiveAPI.set()`
- Add `live_set get scenes` count check to avoid out-of-bounds

**Risk**: Low. Pure write-only LOM operations. The only gotcha is scene index alignment (JSON must match scene order).

**IRON STATIC use case**: Load `ableton/m4l/configs/[song-slug]_scenes.json` → press Apply → all scene tempos and time signatures set in one shot. Scene config files live alongside their song in `ableton/m4l/configs/`.

---

### Device 5: `pigments-macro-lens.amxd` — Pigments Parameter Observer
**Feasibility: MEDIUM**  
**LOM coverage confirmed**:
- `this_device canonical_parent devices` → iterate, find PluginDevice by name ✓
- `DeviceParameter value` observe ✓
- `PluginDevice selected_preset_index` get/set ✓

**Revised scope**: The built-in **Expression Control** device already handles MIDI → Pigments macro mapping for live performance. `pigments-macro-lens.amxd` is most valuable specifically for **Copilot reading back Pigments state** — knowing which preset is selected and what the macro values are at any moment. This is narrower than originally scoped.

**Implementation notes**:
- On load (`live.thisdevice` bang): scan track devices, find PluginDevice where `name contains "Pigments"`
- Observe the 4 Macro DeviceParameter values
- Emit CC20–23 on ch8 for each macro change (for controller feedback)
- Report preset name + macro values over OSC to bridge

**Risk**: Medium. Iterating device chain to find a PluginDevice by name is robust if the plugin is loaded, but fragile if Pigments is missing or renamed. Add a fallback status indicator.

**Defer**: Build this after devices 1–4. Its immediate value is lower since Expression Control handles the live performance side.

---

### Device 6: `scale-broadcaster.amxd` — Key/Scale Monitor
**Feasibility: HIGH**  
**LOM coverage confirmed**:
- `live_set observe root_note` → 0–11 ✓
- `live_set observe scale_name` → string ✓

**Implementation notes**:
- Simple `live.observer` → `midiout` → output CC 0 (root) + CC 1 (scale index) on ch16
- Scale name → index map in `js` (Minor=0, Major=1, Dorian=2, etc.)
- Also write to a watch file for scripts to poll

**Risk**: Very low. This is ~20 Max objects.

**Hardware impact**: Rev2 and Take 5 don't auto-respond to MIDI CC for transposition — they'd need preset patches listening on ch16. This device is more useful for **Copilot awareness** (knowing current key context) than hardware auto-response unless Rev2/Take5 presets are specifically configured.

---

### Device 7: `arm-dispatcher.amxd` — MIDI Note → Track Arm Router
**Feasibility: HIGH**  
**LOM coverage confirmed**:
- `live_set tracks N set arm 1` ✓
- Can also use native MIDI Remote Map (no M4L needed!)

**Revised assessment**: Live's built-in MIDI Remote Map can assign MIDI notes to track Arm buttons directly — no M4L required. Only build `arm-dispatcher.amxd` if we need **exclusive-arm behavior** (arming one track auto-disarms all others) or if we want to script the mapping programmatically.

**IRON STATIC use**: With 6+ hardware instruments and Digitakt as controller, exclusive arm routing is actually useful. Build it if performance workflow requires it.

---

## 4. Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  IRON STATIC Copilot Integration Data Flow                      │
│                                                                 │
│  Python Scripts                   Ableton Live 12               │
│  ─────────────────                ─────────────────             │
│  midi_craft.py                    iron-static-bridge.amxd       │
│    → generate note dict           ├── OSC recv :7400            │
│    → UDP/OSC → :7400              ├── LOM: add_new_notes        │
│                                   ├── LOM: fire scene           │
│  analyze_audio.py                 ├── LOM: set tempo            │
│    → audio features               └── OSC send :7401            │
│    → suggest root/scale               ↓                         │
│                                   session-reporter.amxd         │
│  scripts/session_query.py         └── outputs/live_state.json   │
│    → read live_state.json             ↑ read by Copilot         │
│    → answer "what's in Live?"                                   │
│                                   pattern-injector.amxd         │
│  Copilot (this agent)             ├── receives notes via bridge │
│    → reads live_state.json        ├── create_clip / add_notes   │
│    → generates patterns           └── fires clip                │
│    → sends OSC commands                                         │
│                                   scene-tempo-map.amxd          │
│  ableton/m4l/configs/             └── reads JSON config         │
│    [song-slug]_scenes.json            sets scene tempos/meters  │
│    → consumed by scene-tempo-map                                │
│                                                                 │
│  Hardware (MIDI ch16)                                           │
│  ─────────────────────                                          │
│  scale-broadcaster.amxd → CC0 root_note, CC1 scale → Rev2/Take5│
└─────────────────────────────────────────────────────────────────┘
```

---

## 5. MIDI Tools vs. Custom M4L: Decision Guide

| If you want to... | Use |
|---|---|
| Arpeggiate, chop, strum, quantize, recombine notes in a clip | MIDI Tools (native, no M4L) |
| Generate Euclidean rhythms interactively | Euclidean M4L MIDI Tool (bundled) |
| Generate chord progressions within a scale | Stacks Generator (native) |
| Inject notes generated by `midi_craft.py` | `pattern-injector.amxd` |
| Apply Euclidean patterns from a Python script | `midi_craft.py` → bridge → `pattern-injector.amxd` |
| Modulate Pigments macros from a MIDI controller live | Expression Control (native M4L, no custom) |
| Read Pigments preset + macro state in Copilot | `pigments-macro-lens.amxd` |
| Set all scene tempos/meters from a JSON file | `scene-tempo-map.amxd` |
| Know what's in the current Live Set right now | `session-reporter.amxd` |
| Communicate between Python scripts and Live | `iron-static-bridge.amxd` |
| Map hardware MIDI controls to track parameters | Expression Control or MIDI Remote Map (no custom M4L) |
| Broadcast key/scale to hardware on ch16 | `scale-broadcaster.amxd` |

---

## 6. Build Order and Milestones

### Milestone 0: Foundation (before first amxd)
- [ ] Create `ableton/m4l/` directory for AMXD files
- [ ] Create `ableton/m4l/configs/` for JSON config files
- [ ] Install Max for Live (confirm bundled with Live Suite or add-on)
- [ ] Verify `outputs/` directory exists for state dumps

### Milestone 1: Situational Awareness
Build `session-reporter.amxd` first — it's the simplest device and immediately gives Copilot full session awareness without needing two-way communication.

- [ ] Build `session-reporter.amxd`
- [ ] Test: dump `outputs/live_state.json` from an active session
- [ ] Add script `scripts/session_query.py` — reads `live_state.json`, answers questions

### Milestone 2: Two-Way Bridge
Build `iron-static-bridge.amxd` — unlocks all programmatic control from Python.

- [ ] Build `iron-static-bridge.amxd` with OSC recv/send
- [ ] Test: Python `udpsend` → `/song/state` → get JSON back
- [ ] Test: `/song/tempo 140` → Live tempo changes
- [ ] Test: `/scene/fire 0` → first scene fires

### Milestone 3: Pattern Injection
Complete the generate → inject loop.

- [ ] Build `pattern-injector.amxd`
- [ ] Update `midi_craft.py` to emit OSC via bridge instead of writing `.mid` files
- [ ] Test: generate 8-bar Rev2 line → inject into clip → fire
- [ ] Test overdub mode: layer pattern onto existing clip

### Milestone 4: Scene Tempo Map
Directly useful for any odd-meter song. Scene configs are per-song JSON files.

- [ ] Build `scene-tempo-map.amxd`
- [ ] Create `ableton/m4l/configs/[active-song-slug]_scenes.json` for the active song
- [ ] Test: load JSON → Apply → verify all scene tempos/meters in Live

### Milestone 5: Hardware Integration
Nice-to-have, after the above is working.

- [ ] Build `scale-broadcaster.amxd`
- [ ] Test: change root_note in Live → CC0 broadcast on ch16
- [ ] Build `pigments-macro-lens.amxd`
- [ ] Build `arm-dispatcher.amxd` (only if MIDI Remote Map is insufficient)

---

## 7. Learning Path for Dave

If you want to understand and maintain these devices, here's the progression:

### Level 1: Understanding the LOM (1–2 hours)
Read the [Live API Overview](https://docs.cycling74.com/userguide/m4l/live_api_overview/) and scan the [LOM reference](https://docs.cycling74.com/userguide/m4l/live_object_model). Focus on:
- The `live_set tracks N clip_slots M clip` path
- What `add_new_notes` expects
- What `live.thisdevice` does and why it replaces `loadbang`

### Level 2: Max Fundamentals (2–4 hours)
Work through the **Building Max Devices Pack** (free from Ableton's site) — it's designed exactly for Live integration. Focus on:
- `live.path`, `live.object`, `live.observer` trio
- `js` object with `LiveAPI` for looping over collections
- `live.remote~` for realtime control
- AMXD save/freeze workflow

### Level 3: Building the Reporter First
Start with `session-reporter.amxd` — read-only, no complex state management, immediate feedback. Follow the `js` + `LiveAPI` pattern from the LOM docs.

### Level 4: OSC in Max
`udpreceive` / `udpsend` are standard Max objects. OSC formatting uses `prepend`, `list`, and `route` objects. The `js` object can format JSON strings for outgoing messages.

### Level 5: Iterate and Test with Real Sets
Always test against a real `.als` session. If no active song session exists yet, use any available session as a parse fixture — but keep fixture outputs out of `outputs/` (put them in `outputs/fixtures/` to distinguish from live session data).

---

## 8. What Copilot Needs to Execute This Plan

For Copilot to provide maximum help building and debugging these devices, feed it:

| Data | Format | Why it helps |
|---|---|---|
| Current `outputs/live_state.json` | JSON | Full session context — track names, devices, playing state |
| `outputs/clips.csv` | CSV | MIDI clip inventory for the active song — which clips are available for injection |
| `database/songs.json` | JSON | Active song context — slug, key, scale, BPM, .als path |
| Max patcher screenshots | PNG | Diagnose wiring issues in amxd patches |
| Ableton log output | Text | Diagnose M4L loading errors (use `analyze-ableton-logs` skill) |
| SysEx dumps from hardware | .syx | Instrument preset state (when available) |
| Panel-state descriptions | Text/MD | Subharmonicon, DFAM, Minibrute patch context |
| Describe what you're hearing | Prose | Sound design and arrangement suggestions |
| Record current improvisation | Audio | Copilot can analyze key, BPM, tonal center |

---

*Last updated: Based on Live 12 Manual (v12.2.x), Cycling '74 Live API docs (Max 8 LOM reference)*  
*See also: `knowledge/production/m4l-device-concepts.md` for full LOM/API reference*
