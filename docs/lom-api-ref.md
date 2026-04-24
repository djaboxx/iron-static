# Live Object Model (LOM) — API Reference

> Source: https://docs.cycling74.com/apiref/lom/  
> Ableton Live version: **12.3.5** (docs date)  
> Indexed: 2025 — IRON STATIC reference copy

## Overview

The LOM is a hierarchy of objects representing everything in a Live Set. Access starts from two root paths:
- `live_set` → the Song object (current Live Set)
- `live_app` → the Application object

Objects are accessed via path strings like `live_set tracks 2 devices 0 chains 1 devices 0`.

---

## ⭐ Critical Findings (Live 12.3 New APIs)

> **These did NOT exist before Live 12.3.** If you've been told "LOM can't create devices," that was true before 12.3. It is no longer true.

### `Track.insert_device(device_name, target_index?)`
- Inserts a native Live device into a track's device chain by **name as shown in Live's UI**
- `target_index` is optional; omitting inserts at end
- **Only native Live devices** — no M4L or plug-ins
- Example: `track.insert_device("Instrument Rack")`, `track.insert_device("Collision")`
- Throws if index is invalid or device type doesn't fit at that position

### `Chain.insert_device(device_name, target_index?)`
- Same semantics as `Track.insert_device` but targets a rack chain
- Lets you populate individual chains of a rack

### `RackDevice.insert_chain(index?)`
- Inserts a new empty chain into a RackDevice
- Index optional; inserts at end if omitted
- For Drum Racks: new chain has `in_note = "All Notes"` — set `DrumChain.in_note` to the pad's note value

### Programmatic Rack Build Workflow
```
1. track.insert_device("Instrument Rack")           → creates empty rack at device[0]
2. rack.insert_chain()                              → chain[0]
3. rack.chains[0].insert_device("Collision")        → device in chain[0]
4. rack.insert_chain()                              → chain[1]
5. rack.chains[1].insert_device("Collision")        → device in chain[1]
6. rack.chain_selector.value = <target>             → select active chain
```

---

## Object Reference

### Song
**Path:** `live_set`

#### Children
| Child | Type | Access |
|---|---|---|
| `tracks` | list of Track | read-only, observe |
| `return_tracks` | list of Track | read-only, observe |
| `scenes` | list of Scene | read-only, observe |
| `visible_tracks` | list of Track | read-only, observe |
| `master_track` | Track | read-only |
| `view` | Song.View | read-only |
| `cue_points` | list of CuePoint | read-only, observe |
| `groove_pool` | GroovePool | read-only |
| `tuning_system` | TuningSystem | read-only, observe |

#### Properties
| Property | Type | Access | Notes |
|---|---|---|---|
| `tempo` | float | observe | BPM, 20.0–999.0 |
| `root_note` | int | observe | 0=C … 11=B |
| `scale_name` | unicode | observe | Name as shown in Live |
| `scale_intervals` | list | read-only, observe | Intervals from root |
| `scale_mode` | bool | observe | Scale Mode on/off |
| `signature_numerator` | int | observe | |
| `signature_denominator` | int | observe | |
| `is_playing` | bool | observe | Transport running |
| `current_song_time` | float | observe | Playback position in beats |
| `record_mode` | bool | observe | Arrangement Record |
| `session_record` | bool | observe | Session Overdub |
| `metronome` | bool | observe | |
| `overdub` | bool | observe | MIDI Arrangement Overdub |
| `loop` | bool | observe | Arrangement loop |
| `loop_start` | float | observe | |
| `loop_length` | float | observe | |
| `swing_amount` | float | observe | 0.0–1.0 |
| `groove_amount` | float | observe | 0.0–1.0 |
| `clip_trigger_quantization` | int | observe | 0=None, 4=1 Bar, 7=1/4, etc. |
| `midi_recording_quantization` | int | observe | 0=None, 5=1/16, etc. |
| `appointed_device` | Device | read-only, observe | Blue-hand device |
| `can_capture_midi` | bool | read-only, observe | |
| `name` | symbol | read-only | Set name |
| `file_path` | symbol | read-only | OS path to .als |
| `can_redo` | bool | read-only | |
| `can_undo` | bool | read-only | |
| `exclusive_arm` | bool | read-only | From prefs |
| `exclusive_solo` | bool | read-only | From prefs |
| `re_enable_automation_enabled` | bool | read-only, observe | |
| `session_record_status` | int | read-only, observe | |
| `is_ableton_link_enabled` | bool | observe | |
| `back_to_arranger` | bool | observe | |

#### Functions
| Function | Parameters | Returns | Notes |
|---|---|---|---|
| `create_scene` | `index` | new Scene | -1 = append at end |
| `delete_scene` | `index` | | |
| `duplicate_scene` | `index` | | |
| `create_midi_track` | `index` | | -1 = append |
| `create_audio_track` | `index` | | -1 = append |
| `create_return_track` | | | |
| `delete_track` | `index` | | |
| `duplicate_track` | `index` | | |
| `move_device` | `device, target, target_position` | int (position) | |
| `find_device_position` | `device, target, target_position` | int | Nearest valid position |
| `start_playing` | | | From insert marker |
| `stop_playing` | | | |
| `continue_playing` | | | |
| `stop_all_clips` | `quantized (optional)` | | 0=immediate |
| `capture_midi` | `destination (optional)` | | 0=auto, 1=session, 2=arrangement |
| `capture_and_insert_scene` | | | Captures playing clips → new scene |
| `undo` | | | |
| `redo` | | | |
| `re_enable_automation` | | | |
| `tap_tempo` | | | |
| `trigger_session_record` | `record_length (optional)` | | |
| `jump_by` | `beats` | | Relative jump |
| `jump_to_next_cue` | | | |
| `jump_to_prev_cue` | | | |
| `get_current_beats_song_time` | | `bars.beats.sixteenths.ticks` | |
| `set_or_delete_cue` | | | Toggle cue at current position |
| `play_selection` | | | Arrangement selection |

---

### Track
**Path:** `live_set tracks N`

#### Children
| Child | Type | Access |
|---|---|---|
| `clip_slots` | list of ClipSlot | read-only, observe |
| `arrangement_clips` | list of Clip | read-only, observe |
| `devices` | list of Device | read-only, observe |
| `mixer_device` | MixerDevice | read-only |
| `group_track` | Track | read-only |
| `view` | Track.View | read-only |
| `take_lanes` | list of TakeLane | read-only, observe |

#### Properties
| Property | Type | Access | Notes |
|---|---|---|---|
| `name` | symbol | observe | |
| `arm` | bool | observe | Not on return/master |
| `mute` | bool | observe | Not on master |
| `solo` | bool | observe | Bypasses exclusive solo logic |
| `color` | int | observe | 0x00rrggbb |
| `color_index` | long | observe | |
| `is_foldable` | bool | read-only | 1 for Group Tracks |
| `fold_state` | int | | 0=expanded, 1=folded |
| `is_grouped` | bool | read-only | Within a Group Track |
| `is_frozen` | bool | read-only, observe | |
| `can_be_armed` | bool | read-only | 0 for return/master |
| `can_be_frozen` | bool | read-only | |
| `can_show_chains` | bool | read-only | Has Instrument Rack with chains |
| `is_showing_chains` | bool | observe | |
| `has_audio_input` | bool | read-only | |
| `has_audio_output` | bool | read-only | 1 for audio + MIDI w/ instruments |
| `has_midi_input` | bool | read-only | |
| `has_midi_output` | bool | read-only | MIDI tracks w/ no instrument |
| `playing_slot_index` | int | read-only, observe | -1=arrangement, -2=stop |
| `fired_slot_index` | int | read-only, observe | Blinking slot |
| `implicit_arm` | bool | observe | Push-only second arm state |
| `is_visible` | bool | read-only | |
| `muted_via_solo` | bool | read-only, observe | |
| `back_to_arranger` | bool | observe | |
| `input_routing_type` | dictionary | observe | `display_name`, `identifier` |
| `input_routing_channel` | dictionary | observe | |
| `output_routing_type` | dictionary | observe | |
| `output_routing_channel` | dictionary | observe | |
| `output_meter_level` | float | read-only, observe | |
| `input_meter_level` | float | read-only, observe | |
| `performance_impact` | float | read-only, observe | |

#### Functions
| Function | Parameters | Notes |
|---|---|---|
| `insert_device` | `device_name, target_index?` | **Live 12.3** — native devices only |
| `delete_device` | `index` | |
| `create_midi_clip` | `start_time, length` | Arrangement only |
| `create_audio_clip` | `file_path, position` | Arrangement only |
| `duplicate_clip_slot` | `index` | Like Duplicate in context menu |
| `duplicate_clip_to_arrangement` | `clip, destination_time` | |
| `delete_clip` | `clip` | |
| `stop_all_clips` | | |
| `jump_in_running_session_clip` | `beats` | |
| `create_take_lane` | | |

---

### Device
**Path:** `live_set tracks N devices M`  
Also: `live_set tracks N devices M chains L devices K`

#### Children
| Child | Type | Access |
|---|---|---|
| `parameters` | list of DeviceParameter | read-only, observe |
| `view` | Device.View | read-only |

#### Properties
| Property | Type | Access | Notes |
|---|---|---|---|
| `name` | symbol | observe | Title bar name |
| `class_name` | symbol | read-only | e.g. `Operator`, `MxDeviceAudioEffect`, `PluginDevice` |
| `class_display_name` | symbol | read-only | Human-readable original name |
| `type` | int | read-only | 0=undefined, 1=instrument, 2=audio_effect, 4=midi_effect |
| `is_active` | bool | read-only, observe | 0 if device or its rack is off |
| `can_have_chains` | bool | read-only | 1 for Racks |
| `can_have_drum_pads` | bool | read-only | 1 for Drum Racks |
| `latency_in_samples` | int | read-only, observe | |
| `latency_in_ms` | float | read-only, observe | |
| `can_compare_ab` | bool | read-only | Live 12.3 |
| `is_using_compare_preset_b` | bool | observe | Live 12.3 |

#### Functions
| Function | Parameters | Notes |
|---|---|---|
| `store_chosen_bank` | `script_index, bank_index` | Hardware control surfaces |
| `save_preset_to_compare_ab_slot` | | Live 12.3 |

---

### RackDevice
**Path:** `live_set tracks N devices M`  
Inherits all Device children/properties/functions. Listed below: unique members.

#### Children
| Child | Type | Access | Notes |
|---|---|---|---|
| `chains` | list of Chain | read-only, observe | Rack's chains |
| `return_chains` | list of Chain | read-only, observe | |
| `chain_selector` | DeviceParameter | read-only | Convenience accessor |
| `drum_pads` | list of DrumPad | read-only, observe | All 128; only top-level Drum Rack |
| `visible_drum_pads` | list of DrumPad | read-only, observe | 16 visible pads |

#### Properties
| Property | Type | Access | Notes |
|---|---|---|---|
| `can_show_chains` | bool | read-only | Instrument Rack capable of chain view |
| `is_showing_chains` | bool | observe | |
| `has_drum_pads` | bool | read-only, observe | Drum Rack with pads |
| `has_macro_mappings` | bool | read-only, observe | Any macro is mapped |
| `visible_macro_count` | int | read-only, observe | |
| `variation_count` | int | read-only, observe | Live 11.0 |
| `selected_variation_index` | int | | Live 11.0 |

#### Functions
| Function | Parameters | Notes |
|---|---|---|
| `insert_chain` | `index?` | **Live 12.3** — adds empty chain |
| `add_macro` | | Live 11.0 — increases visible macro count |
| `remove_macro` | | Live 11.0 |
| `randomize_macros` | | Live 11.0 |
| `store_variation` | | Live 11.0 |
| `recall_selected_variation` | | Live 11.0 |
| `recall_last_used_variation` | | Live 11.0 |
| `delete_selected_variation` | | Live 11.0 |
| `copy_pad` | `source_index, destination_index` | Drum Rack only |

---

### Chain
**Path:** `live_set tracks N devices M chains L`  
Also: nested chains via `... chains L devices K chains P`

#### Children
| Child | Type | Access |
|---|---|---|
| `devices` | list of Device | read-only, observe |
| `mixer_device` | ChainMixerDevice | read-only |

#### Properties
| Property | Type | Access | Notes |
|---|---|---|---|
| `name` | unicode | observe | |
| `color` | int | observe | 0x00rrggbb |
| `color_index` | long | observe | |
| `is_auto_colored` | bool | observe | Inherits track/chain color |
| `mute` | bool | observe | Chain Activator off |
| `solo` | bool | observe | Solo switch |
| `muted_via_solo` | bool | read-only, observe | |
| `has_audio_input` | bool | read-only | |
| `has_audio_output` | bool | read-only | |
| `has_midi_input` | bool | read-only | |
| `has_midi_output` | bool | read-only | |

#### Functions
| Function | Parameters | Notes |
|---|---|---|
| `insert_device` | `device_name, target_index?` | **Live 12.3** — native devices only |
| `delete_device` | `index` | |

---

### Clip
**Path:** `live_set tracks N clip_slots M clip`  
Also: `live_set tracks N arrangement_clips M`

#### Children
| Child | Type | Access |
|---|---|---|
| `view` | Clip.View | read-only |

#### Properties
| Property | Type | Access | Notes |
|---|---|---|---|
| `name` | symbol | observe | |
| `color` | int | observe | 0x00rrggbb |
| `length` | float | read-only | Loop length (looped) or start-to-end |
| `loop_start` | float | observe | Beats or seconds (unwarped) |
| `loop_end` | float | observe | |
| `looping` | bool | observe | |
| `start_marker` | float | observe | |
| `end_marker` | float | observe | |
| `is_midi_clip` | bool | read-only | |
| `is_audio_clip` | bool | read-only | |
| `is_playing` | bool | | |
| `is_recording` | bool | read-only, observe | |
| `is_triggered` | bool | read-only | Launch button blinking |
| `is_overdubbing` | bool | read-only, observe | |
| `is_session_clip` | bool | read-only | |
| `is_arrangement_clip` | bool | read-only | |
| `muted` | bool | observe | Clip Activator |
| `notes` | bang | observe | MIDI only — bangs on change |
| `has_envelopes` | bool | read-only, observe | Has automation |
| `playing_position` | float | read-only, observe | Current playback pos |
| `launch_mode` | int | observe | 0=Trigger, 1=Gate, 2=Toggle, 3=Repeat |
| `launch_quantization` | int | observe | 0=Global, 1=None, 2=8Bars, etc. |
| `legato` | bool | observe | |
| `velocity_amount` | float | observe | 0.0–1.0, Live 11.0 |
| `signature_numerator` | int | observe | |
| `signature_denominator` | int | observe | |
| `groove` | Groove | observe | Live 11.0 |
| `warping` | bool | observe | Audio only |
| `warp_mode` | int | observe | 0=Beats, 1=Tones, 2=Texture, 3=Re-Pitch, 4=Complex, 6=Complex Pro |
| `pitch_coarse` | int | observe | ±48 semitones, audio only |
| `pitch_fine` | float | observe | ±50 cents, audio only |
| `gain` | float | observe | 0.0–1.0, audio only |

#### Functions (MIDI)
| Function | Parameters | Notes |
|---|---|---|
| `add_new_notes` | `{"notes": [...]}` | Dict with note list; Live 11.0 |
| `get_all_notes_extended` | `dict(optional)` | Returns all notes; Live 11.1 |
| `get_notes_extended` | `from_pitch, pitch_span, from_time, time_span` | Filtered; Live 11.0 |
| `get_notes_by_id` | `list of note_ids` | Live 11.0 |
| `get_selected_notes_extended` | `dict(optional)` | Live 11.0 |
| `apply_note_modifications` | `{"notes": [...]}` | In-place modify; Live 11.0 |
| `remove_notes_by_id` | `list of note_ids` | Live 11.0 |
| `remove_notes_extended` | `from_pitch, pitch_span, from_time, time_span` | Live 11.0 |
| `duplicate_notes_by_id` | `note_ids, destination_time?, transposition_amount?` | Live 11.1.2 |
| `duplicate_region` | `region_start, region_length, destination_time, pitch?, transposition_amount?` | |
| `duplicate_loop` | | Doubles loop length |
| `select_all_notes` | | |
| `deselect_all_notes` | | |
| `select_notes_by_id` | `list of note_ids` | Live 11.0.6 |
| `quantize` | `quantization_grid, amount` | |
| `quantize_pitch` | `pitch, quantization_grid, amount` | |
| `clear_all_envelopes` | | Remove all automation |
| `clear_envelope` | `device_parameter` | |
| `crop` | | |

#### Note Specification Dict
```python
{
    "pitch": int,          # 0–127, 60=C3
    "start_time": float,   # beats, absolute clip time
    "duration": float,     # beats
    "velocity": float,     # 0–127 (default 100)
    "mute": bool,          # default False
    "probability": float,  # 0.0–1.0 (default 1.0)
    "velocity_deviation": float,  # -127 to 127 (default 0)
    "release_velocity": float     # default 64
}
```

#### Functions (General)
| Function | Parameters | Notes |
|---|---|---|
| `fire` | | Press Clip Launch button |
| `stop` | | Only if this clip is playing |
| `set_fire_button_state` | `state` | Simulate held launch |
| `move_playing_pos` | `beats` | Relative jump |
| `scrub` | `beat_time` | Respects global quantization |
| `stop_scrub` | | |

---

### ClipSlot
**Path:** `live_set tracks N clip_slots M`

#### Children
| Child | Type | Notes |
|---|---|---|
| `clip` | Clip | `id 0` if slot empty |

#### Properties
| Property | Type | Access |
|---|---|---|
| `has_clip` | bool | read-only, observe |
| `is_playing` | bool | read-only |
| `is_recording` | bool | read-only |
| `is_triggered` | bool | read-only, observe |
| `has_stop_button` | bool | observe |
| `will_record_on_start` | bool | read-only |
| `controls_other_clips` | bool | read-only, observe — Group Track |
| `playing_status` | int | read-only, observe — Group Track (0/1/2) |
| `is_group_slot` | bool | read-only |

#### Functions
| Function | Parameters | Notes |
|---|---|---|
| `create_clip` | `length` | Empty MIDI clip; MIDI tracks only |
| `create_audio_clip` | `path` | Audio tracks only |
| `delete_clip` | | |
| `duplicate_clip_to` | `target_clip_slot` | Overrides target if non-empty |
| `fire` | `record_length?, launch_quantization?` | |
| `stop` | | |
| `set_fire_button_state` | `state` | |

---

### Scene
**Path:** `live_set scenes N`

#### Children
| Child | Type | Access |
|---|---|---|
| `clip_slots` | list of ClipSlot | read-only, observe |

#### Properties
| Property | Type | Access | Notes |
|---|---|---|---|
| `name` | symbol | observe | |
| `color` | int | observe | 0x00rrggbb |
| `is_empty` | bool | read-only | No filled slots |
| `is_triggered` | bool | read-only, observe | Scene blinking |
| `tempo` | float | observe | -1 if tempo disabled |
| `tempo_enabled` | bool | observe | |
| `time_signature_numerator` | int | observe | -1 if disabled |
| `time_signature_denominator` | int | observe | -1 if disabled |
| `time_signature_enabled` | bool | observe | |

#### Functions
| Function | Parameters | Notes |
|---|---|---|
| `fire` | `force_legato?, can_select_scene_on_launch?` | Fires all clips; selects scene |
| `fire_as_selected` | `force_legato?` | Fires selected scene → advances to next |
| `set_fire_button_state` | `state` | |

---

### DeviceParameter
**Path:** `live_set tracks N devices M parameters L`

#### Properties
| Property | Type | Access | Notes |
|---|---|---|---|
| `name` | symbol | read-only | Short name (automation chooser) |
| `original_name` | symbol | read-only | Name before macro assignment |
| `value` | float | observe | Internal value; set to change |
| `display_value` | float | observe | GUI-visible value |
| `min` | float | read-only | |
| `max` | float | read-only | |
| `default_value` | float | read-only | Only for non-quantized params |
| `is_quantized` | bool | read-only | Bool/enum = 1; float/int = 0 |
| `is_enabled` | bool | read-only | Can be modified by user |
| `state` | int | read-only, observe | 0=active, 1=inactive/changeable, 2=locked |
| `automation_state` | int | read-only, observe | 0=none, 1=active, 2=overridden |
| `value_items` | StringVector | read-only | Possible values for quantized params |

#### Functions
| Function | Parameters | Returns | Notes |
|---|---|---|---|
| `re_enable_automation` | | | |
| `str_for_value` | `value` | symbol | String rep of given value |
| `__str__` | | symbol | String rep of current value |

---

### Application
**Path:** `live_app`

The Application object. Useful for version detection and view management. See `Application.View` for showing/hiding panels.

---

### MixerDevice
**Path:** `live_set tracks N mixer_device`

Controls volume, panning, sends. Access via `track.mixer_device`.

Key parameters accessible as children:
- `volume` — track volume fader (DeviceParameter)
- `panning` — panning (DeviceParameter)
- `sends` — list of send DeviceParameters

---

## Object Hierarchy Summary

```
live_set (Song)
├── tracks[] (Track)
│   ├── clip_slots[] (ClipSlot)
│   │   └── clip (Clip)
│   ├── arrangement_clips[] (Clip)
│   ├── devices[] (Device / RackDevice / PluginDevice / MaxDevice / etc.)
│   │   ├── parameters[] (DeviceParameter)
│   │   └── [if RackDevice]:
│   │       ├── chains[] (Chain)
│   │       │   ├── devices[] (Device)
│   │       │   │   └── parameters[] (DeviceParameter)
│   │       │   └── mixer_device (ChainMixerDevice)
│   │       ├── return_chains[] (Chain)
│   │       ├── drum_pads[] (DrumPad)
│   │       └── chain_selector (DeviceParameter)
│   └── mixer_device (MixerDevice)
├── return_tracks[] (Track)
├── master_track (Track)
├── scenes[] (Scene)
│   └── clip_slots[] (ClipSlot)
├── cue_points[] (CuePoint)
└── groove_pool (GroovePool)
```

---

## Notes on Class Names

When checking `device.class_name`:
- `"MxDeviceAudioEffect"` = Max for Live Audio Effect
- `"MxDeviceMidi"` = Max for Live MIDI Effect
- `"MxDeviceInstrument"` = Max for Live Instrument
- `"PluginDevice"` = VST/AU plug-in
- `"InstrumentGroupDevice"` = Instrument Rack
- `"AudioEffectGroupDevice"` = Audio Effect Rack
- `"MidiEffectGroupDevice"` = MIDI Effect Rack
- `"DrumGroupDevice"` = Drum Rack
- `"Collision"`, `"Operator"`, `"Wavetable"` = native instrument names
- `"Compressor2"`, `"AutoFilter"`, `"Eq8"` = native effect names

## Limitations

- `Track.insert_device` and `Chain.insert_device`: **native devices only**, no M4L or plug-ins
- `device.parameters`: only **automatable** parameters are exposed
- `DeviceParameter.value`: setting this adds an undo step; use `live.remote~` for real-time no-undo control
- `Track.devices` is read-only (list) — you cannot set it directly; use `insert_device` or `delete_device`
- `RackDevice.chains` is read-only — use `insert_chain` to add chains
- Unwarped audio clips: note position values in seconds, not beats
- Nested Drum Racks always return 0 drum pads; only top-level rack has 128 pads

## IronStatic Remote Script — What's Now Possible

With Live 12.3 APIs, the Remote Script can:
1. **Build Instrument Racks from scratch** — `track.insert_device("Instrument Rack")`, then chain by chain
2. **Populate rack chains with native devices** — e.g., 3 chains of Collision for DFAM layering
3. **Control chain selector** via `rack.chain_selector.value`
4. **Read/write any automatable parameter** on any device via `device.parameters[L].value`
5. **Create MIDI clips, inject notes, fire clips** — already working
6. **Create/name/fire scenes** — already working
7. **Set scene tempo and time signature** per-scene

## What's Still Not Possible via LOM

- Loading plug-ins (VST/AU/M4L) via `insert_device` — only native devices
- Loading presets by file path (no load_preset API)
- Drag-and-drop browser operations from Remote Script (browser.load_item exists but is M4L/Max-only, not Remote Script)
- Creating Group Tracks (no group_tracks API)
- Changing device order beyond insert/delete (no move within same chain)
