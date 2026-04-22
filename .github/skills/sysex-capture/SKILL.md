# SKILL: sysex-capture

## Purpose
Receive a MIDI SysEx dump from any IRON STATIC instrument, parse the data, and catalog it as structured preset files in the repository.

---

## When to Use This Skill
- Dave says "do a SysEx dump" / "capture my presets" / "I sent you a SysEx"
- Any request involving receiving, parsing, or cataloging SysEx data from hardware
- Converting a raw `.syx` file from disk into a structured JSON preset

---

## Instrument Capability Matrix

| Instrument | Key | SysEx? | Parseable? | Notes |
|---|---|---|---|---|
| Sequential Prophet Rev2 | `rev2` | ✅ | ✅ | Full program dump; DSI 7-bit packing; 512 params |
| Sequential Take 5 | `take5` | ✅ | ✅ | Full program dump; DSI 7-bit packing |
| Elektron Digitakt MK1 | `digitakt` | ✅ | ⚠️ raw only | Proprietary Elektron format; use Elektron Transfer for restore |
| Arturia MiniBrute 2S | `minibrute2s` | ⚠️ limited | ⚠️ raw only | Minimal SysEx; panel-state is better |
| Moog Subharmonicon | `subharmonicon` | ❌ | ❌ | No patch memory; use `create-preset` skill |
| Moog DFAM | `dfam` | ❌ | ❌ | No patch memory; use `create-preset` skill |

---

## Workflow

### Step 1 — Identify the instrument and port

```bash
source .venv/bin/activate
python scripts/sysex_capture.py list-ports
```

This prints all available MIDI input ports. The instrument needs to be connected and recognised by the OS (USB-MIDI or via the Digitakt's MIDI DIN output → USB interface).

### Step 2 — Start the listener

```bash
python scripts/sysex_capture.py capture \
  --port "YOUR PORT NAME" \
  --instrument rev2
```

Optionally add `--timeout 30` to stop automatically after 30 seconds of silence.

The script will print "Listening..." — then proceed to the instrument.

### Step 3 — Initiate the SysEx dump on the hardware

**Sequential Rev2:**
1. Press `GLOBALS`
2. Navigate to `MIDI` → `Send Program`
3. Choose `Send Current Program` (single) or `Send All Programs` (bank dump)
4. Press `Enter`

**Sequential Take 5:**
1. Press `GLOBALS`
2. Navigate to `MIDI` → `Send Program`
3. Choose current or all

**Elektron Digitakt:**
1. Hold `FUNC` + press `SETTINGS`
2. Navigate to `MIDI` → `SYSEX DUMP`
3. Select what to dump (Pattern / Sound / Project)
4. Press `YES`

### Step 4 — Review output

The script saves:
- `instruments/[slug]/presets/raw/dump_YYYYMMDD_HHMMSS.syx` — raw bytes, always
- `instruments/[slug]/presets/[name]_[date]_[index].json` — parsed preset (if parseable)
- `instruments/[slug]/presets/catalog.json` — running catalog of all captured presets

### Step 5 — Re-parse / re-catalog (if needed)

To parse an existing `.syx` file:
```bash
python scripts/sysex_capture.py parse \
  --file instruments/sequential-rev2/presets/raw/dump_20260422_120000.syx \
  --instrument rev2
```

To re-catalog all raw dumps for an instrument:
```bash
python scripts/sysex_capture.py catalog --instrument rev2
```

---

## Preset JSON Format

For Sequential instruments (parseable):
```json
{
  "instrument": "rev2",
  "command": "single_program_dump",
  "bank": 0,
  "program": 0,
  "name": "Brass Stack",
  "unpacked_bytes": 512,
  "raw_hex": "...",
  "parameters_raw": [0, 127, 64, ...],
  "captured_at": "2026-04-22T12:00:00",
  "parse_note": ""
}
```

For raw-only instruments (Digitakt, MiniBrute 2S):
```json
{
  "instrument": "digitakt",
  "command": "raw",
  "raw_hex": "...",
  "byte_count": 1024,
  "captured_at": "2026-04-22T12:00:00",
  "note": "Elektron SysEx format is proprietary..."
}
```

---

## Improving the Sequential Parser

The `parameters_raw` array contains the unpacked 8-bit parameter values in the order defined by the instrument's MIDI Implementation appendix. The current parser:
- Extracts parameter names via heuristic ASCII scan (reliable for program name)
- Does NOT yet map individual parameter indices to knob names

To add full parameter mapping for the Rev2 or Take 5:
1. Load the instrument manual: `instruments/[slug]/manuals/`
2. Find the SysEx appendix (usually titled "MIDI Implementation" or "SysEx Parameter List")
3. Build a `PARAM_MAP = {index: "parameter_name"}` dict in `scripts/sysex_capture.py`
4. Update `parse_sequential()` to replace `parameters_raw` with a named dict

Once `name_offset` is confirmed from the manual, set it in the `INSTRUMENTS["rev2"]` dict.

---

## File Naming Convention

Raw dumps: `dump_YYYYMMDD_HHMMSS.syx`
Parsed presets: `[name-slug]_YYYY-MM-DD_[index].json`
Catalog: `catalog.json` (append-mode; replace with `catalog` subcommand to regenerate)

---

## Dependencies

```
mido>=1.3.0
python-rtmidi>=1.4.9
```

Both are in `scripts/requirements.txt`. Install:
```bash
source .venv/bin/activate && pip install mido python-rtmidi
```

---

## Troubleshooting

**"No ports found" / instrument not showing up:**
- Ensure USB cable is data-capable (not charge-only)
- Check macOS `Audio MIDI Setup.app` → MIDI Studio — device should appear
- Restart the MIDI system: `pkill -f coreaudiod` (use with caution)

**"Unrecognized SysEx header":**
- The instrument's manufacturer ID doesn't match any known entry in `INSTRUMENTS`
- Capture still saves raw `.syx` — run `parse --instrument [slug]` to force a raw-save result

**Sequential presets show "Unnamed":**
- `name_offset` is not yet set in the script
- Extract correct offset from the manual appendix and set `"name_offset": <value>` in `INSTRUMENTS["rev2"]`

**Digitakt SysEx won't parse:**
- Expected behaviour — Elektron format is proprietary
- Use the raw `.syx` with Elektron Transfer to restore patterns/projects
- MIDI channel assignments and pattern notes can be documented via the `create-preset` skill
