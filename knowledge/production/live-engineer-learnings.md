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

