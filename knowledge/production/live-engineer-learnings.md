# Live Engineer — Learnings Log

Operational knowledge captured by The Live Engineer across sessions.  
Format: dated entries, appended at the bottom. Do not edit old entries — only add new ones.

---

## 2026-04-24 — Remote Script deploys to app bundle, NOT user prefs

**Context**: Deployed Remote Script changes to `~/Library/Preferences/Ableton/...` and they were silently ignored.  
**What worked**: Deploy to `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/MIDI Remote Scripts/IronStatic/`. Always run `python scripts/deploy_remote_script.py` after any edit. Recompile `.pyc` immediately — stale `.pyc` shadows the updated `.py` completely.  
**Why it matters**: Changes to the wrong path produce zero error messages. You'll spend a session debugging a script that was never actually loaded.

---

## 2026-04-24 — `generate_als.py` requires exact Internal.als track name as device key

**Context**: Tried to use a partial device name in the config JSON and got a silent no-op.  
**What worked**: Run `python3 scripts/generate_als.py --list-devices` to get exact track names from `Internal.als`. Use those verbatim as config keys. `"pigments"` is the special-case string for Arturia Pigments VST3.  
**Why it matters**: Wrong device key = track gets no instrument, no error thrown.

---

## 2026-04-24 — `push-midi` requires `create-clip` first

**Context**: Tried to push MIDI into an empty clip slot directly — command returned an error.  
**What worked**: Always run `create-clip --track X --clip N --length L` before `push-midi`. Clip length must match the pattern exactly (in beats): 4=1bar, 16=4bars, 32=8bars, 64=16bars.  
**Why it matters**: Ableton does not auto-create the clip on push. Silent failure or error depending on Remote Script version.

---

---

## 2026-04-24 — `build_session.py`: Default MIDI Track template has pre-existing duplicate IDs

**Context**: Building ALS sessions from `Default MIDI Track.als` as the track skeleton. Sessions opened in Live with "Invalid Pointee Id" error.

**What worked**: Three-layer fix:
1. `_renumber_ids(xml, base)` — assigns a unique sequential ID to EVERY `Id="N"` occurrence (occurrence-based, not value-based). Updates `PointeeId` references via first-occurrence mapping.
2. Device XML injected RAW before renumbering — track infrastructure + device renumbered in one pass. No separate device ID management needed.
3. Final global `_renumber_ids` over the ENTIRE assembled XML — eliminates pre-existing infrastructure duplicates from the skeleton.

**Why it matters**: `Default MIDI Track.als` is a per-track template, not a standalone valid session. It has duplicate `Id=` values everywhere (e.g. `<AutomationEnvelope Id="1">` appears 8 times). Additive offset produces 8 elements with the same shifted value. Full sequential renumbering is the only correct approach.

---

## 2026-04-25 — ADG devices: `AutomationTarget` and `ModulationTarget` must have non-zero IDs

**Context**: Sessions built from `.adg` preset files (Instrument Racks) caused "Invalid Pointee Id" in Live even after fixing `LockId`, `LomIdView`, and `<Pointee Id="0">`. Root cause was ~18 `AutomationTarget Id="0"` and ~16 `ModulationTarget Id="0"` elements per ADG device — these are the per-parameter automation hooks, and Live validates that every one has a non-zero ID at load time. ADG files store them as `Id="0"` (unassigned) — that's valid for a preset file but invalid in an `.als` session.

**What worked**: In `_extract_device_from_adg()`, replace every `AutomationTarget Id="0"` and `ModulationTarget Id="0"` with sequential placeholder IDs (starting at 100, above the MacroSnapshot IDs of 1–3 already in some ADGs) BEFORE the `_renumber_ids` pass. This lets `_renumber_ids` promote them all to globally unique IDs.

```python
_tc: list[int] = [100]
def _bump_target(m):
    v = _tc[0]; _tc[0] += 1
    return f"{m.group(1)}Id=\"{v}\""
device_xml = re.sub(
    r'(<(?:AutomationTarget|ModulationTarget)\s+)Id="0"',
    _bump_target, device_xml,
)
```

**Why it matters**: `_renumber_ids` skips `Id="0"` by design (0 is the null sentinel). Any element that needs a real ID must enter the renumber pass with a non-zero value. This applies to ALL `Id=`-bearing elements in ADG devices: `AutomationTarget`, `ModulationTarget`, `Pointee`, and the root device tag itself if it has `Id="0"`.

**Also needed (applied earlier)**: Zero out `LockId` and `LomIdView` non-zero values, bump `<Pointee Id="0" />` to `<Pointee Id="1" />`.

---

## 2026-04-25 — Pack ADGs have `<RelativePath>` with children; Live requires a self-closing leaf

**Context**: Built `instrumental-convergence_v3.als` using `build_session.py`. Two pack devices (`808 Depth Charger Kit`, `GranularStretch Kit`) caused corrupt session errors. Core library devices (Noise Bass, Metal Pad, etc.) loaded fine.

**Error sequence**: First attempt → "Required attribute 'Value' missing (at line 887)". Fixed by adding `Value=""`. Second attempt → "Base types can't have children (at line 888)". Root cause: `RelativePath` is a string primitive in Live's schema. Pack ADGs store it as a container element with `<RelativePathElement Dir="..." />` children. Both the missing attribute AND the children must be fixed.

**What worked**: Replace the entire `<RelativePath ...>...</RelativePath>` block (including all children) with `<RelativePath Value="" />` in `_extract_device_from_adg`:
```python
device_xml = re.sub(
    r'<RelativePath(?!\s+Value=)[^>]*>.*?</RelativePath>',
    '<RelativePath Value="" />',
    device_xml,
    flags=re.DOTALL,
)
```

**Why it matters**: This affects any pack ADG (installed pack, not core library). The core library devices use `<RelativePath Value="" />` natively. Pack devices do not. `build_session.py` now handles this automatically.

**Applies to**: `build_session.py` → `_extract_device_from_adg`. `generate_als.py` uses a different device injection path and may need the same fix if pack devices are added there.

---

## 2026-04-25 — `build_session.py` vs `generate_als.py`: use the right tool

**Context**: Spent time trying to use `generate_als.py` for an `instrumental-convergence` session with blueprint track names (DRM_Grid_KickSnare, BASS_Interrogator, etc.).

**What failed**: `generate_als.py --list` on all existing sessions showed tracks with different names (Sub Drone, Bass Voice, etc.). `generate_als.py` is an **injector** — it replaces devices on tracks that already exist by name in a base `.als`.

**What worked**: `build_session.py` — creates a fresh session from a JSON config. Fuzzy-searches `database/device_library.json` (1991 entries) for device presets by name. Use this whenever the brainstorm blueprint introduces new track names.

**Rule**: New brainstorm blueprint = new track names = `build_session.py`. Modifying devices on an existing session = `generate_als.py`.

---

## 2026-04-25 — ADG rack presets: `Branches` is always empty — reconstruct from `BranchPresets`

**Context**: Built `instrumental-convergence_v3.als` from blueprint. All drum rack and instrument rack tracks loaded in Live but showed empty racks (no pads, no instruments).

**Root cause**: In ADG rack preset files, `GroupDevicePreset > Device > [DrumGroupDevice|InstrumentGroupDevice] > Branches` is always an empty element (0 children). The actual per-branch device content lives in a sibling element: `GroupDevicePreset > BranchPresets > [Drum|Instrument]BranchPreset[N] > DevicePresets > AbletonDevicePreset > Device > [inner device]`.

**What failed**: `_extract_device_from_adg` returned the rack shell with empty `Branches` — Live loaded the rack with no pads.

**What worked**: Added `_reconstruct_branches_from_adg(gp, device)` that iterates `BranchPresets`, extracts the inner device from each `DevicePresets[0] > Device`, and builds complete `DrumBranch`/`InstrumentBranch` elements with a `MixerDevice` template inside `DeviceChain > MidiToAudioDeviceChain`. For drum racks, `BranchInfo > ReceivingNote` comes from `ZoneSettings > ReceivingNote` on the preset.

**Key structure facts**:
- `DrumBranchPreset`: `ZoneSettings` has `ReceivingNote`, `SendingNote`, `ChokeGroup`
- `InstrumentBranch`: needs `ZoneSettings > KeyRange + VelocityRange` (not `BranchInfo`)
- `MixerDevice` template must use `Id="1"` on all AutomationTarget/Pointee — `_renumber_ids` assigns real unique IDs
- Both branch types use `DeviceChain > MidiToAudioDeviceChain > Devices` (not AudioToAudioDeviceChain)

**Verification**: Ironman Kit (drum rack) → 16 DrumBranch elements, each with 1 OriginalSimpler device. ReceivingNote correct (e.g. 92).

---

## 2026-04-27 — build_session.py is the correct tool for new sessions with custom track names

**Context**: Tried to use `generate_als.py` for a new song session from brainstorm Blueprint. It failed — all 6 tracks "not found" in base ALS because track names like `[Drone] 3AM` don't exist in Internal.als.

**What worked**: `build_session.py --config <json> --out <path>` creates brand-new tracks with custom names. Config format:
```json
{
  "name": "session-name",
  "bpm": 108.0,
  "key": "E",
  "scale": "phrygian",
  "scenes": 8,
  "tracks": [
    {"name": "[Drone] 3AM",  "device": null,      "color": 4},
    {"name": "[Perc] Beat",  "device": "Built-In", "color": 11}
  ]
}
```
- `null` = empty MIDI track (Sound Designer drags device in Live)
- `"Built-In"` = blank core Drum Rack (from device_library.json)
- `"pigments"` = Arturia Pigments VST3 (hardcoded template)
- Wavetable, Operator, Meld are NOT in device_library.json as blank instruments → use `null` + handoff note

**Why it matters**: `generate_als.py` = inject devices into EXISTING tracks in a base ALS. `build_session.py` = CREATE new tracks with custom names. Wrong tool wastes time — DRY RUN showed 0 matches all silently skipped.

**Verify**: `EffectiveName` values in ALS are correct even when `ableton_push.py status` shows old session. Live may ask to save previous session on `open`. BPM in songs.json was 116 (old) — update to 108 to match brainstorm.

---

## 2026-04-27 — `create-track` auto-loads Pigments (default instrument template); must delete before `insert-device`

**Context**: Created a new MIDI track via `create-track --name "Query Arp"`, then immediately tried `insert-device --device-name "Meld"`. Got error: "Device chains cannot have more than one instrument each."

**What worked**: Always run `get-devices --track X` after `create-track`. Ableton's default MIDI track template may already have an instrument (in this session, Arturia Pigments was auto-populated). Delete it first: `delete-device --track X --device 0`, then insert the intended instrument.

**Why it matters**: `create-track` does not create a blank track — it uses whatever Live's default template has loaded. Never assume a new track is empty.

---

## 2026-04-27 — `apply-preset` works on non-rack native devices with flat `parameters` key

**Context**: Needed to batch-push 36 parameters to Meld (non-rack instrument) in one round-trip.

**What worked**: `apply-preset --track X --device N --preset path/to/file.json` with JSON format `{"name": "...", "parameters": {"Param Name": value, ...}}`. No `chains` key needed for non-rack devices. All parameter names must match exactly the names returned by `get-params`.

**Why it matters**: Confirmed the `apply-preset` command is not limited to rack devices — it works on any native device with a flat `parameters` map. Saves round-trip overhead vs individual `set-param` calls, and creates a named preset file for the audit trail.
