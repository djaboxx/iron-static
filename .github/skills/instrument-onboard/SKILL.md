---
name: instrument-onboard
description: "Fully onboard a new instrument into the IRON STATIC repo: folder structure, manual index, MIDI parameter map, and SysEx capture wiring."
---

# SKILL: instrument-onboard

## Purpose
Fully onboard a new instrument into the IRON STATIC repo: add it to the instrument
registry, download its manual, index the manual, build its MIDI parameter map, and
wire it into the SysEx capture pipeline.

---

## When to Use This Skill
- Adding a new hardware instrument to the rig
- "Onboard the [instrument name]"
- Building a param map for an instrument that doesn't have one yet

---

## Onboarding Checklist

Work through these steps in order. Each step is idempotent — safe to re-run.

### Step 1 — Create instrument folder structure

```bash
SLUG="new-instrument-slug"
mkdir -p instruments/$SLUG/{manuals,presets/raw}
touch instruments/$SLUG/presets/.keep
```

Create `instruments/$SLUG/README.md` with:
- Instrument name and manufacturer
- Role in the IRON STATIC rig
- MIDI channel assignment (see channel table in `copilot-instructions.md`)
- Key features relevant to the band's sound
- Link to manufacturer page

### Step 2 — Assign a short key and MIDI channel

Add the instrument to the two registries:

**`scripts/sysex_capture.py` — `INSTRUMENTS` dict:**
```python
"newkey": {
    "name": "Manufacturer Instrument Name",
    "slug": "new-instrument-slug",
    "mfr_id": (0xXX,),           # from MIDI Implementation appendix
    "device_id_range": (0xYY, 0xZZ),  # or "device_id": 0xYY for fixed ID
    "can_parse": True,            # False if format is proprietary
    "parser": "sequential",       # or "raw"
    "commands": {
        0x02: "single_program_dump",
        0x06: "all_programs_dump",
    },
    "name_offset": None,          # fill in after Step 5
    "name_length": 20,
    "min_unpacked_bytes": N,      # from manual: total program bytes
},
```

**`scripts/index_manuals.py` — `INSTRUMENT_SLUGS` dict:**
```python
"newkey": "new-instrument-slug",
```

**`copilot-instructions.md` — MIDI channel table** (if assigning a new channel)

### Step 3 — Get the manual

**Option A — Download from manufacturer:**
```bash
curl -L "https://manufacturer.com/path/to/manual.pdf" \
  -o "instruments/new-instrument-slug/manuals/Manual-Name.pdf"
```

**Option B — Already have the PDF:**
Copy to `instruments/new-instrument-slug/manuals/`.

Verify: the PDF should be > 500KB and open cleanly.

### Step 4 — Index the manual

```bash
source .venv/bin/activate
python scripts/index_manuals.py --instrument newkey
```

This produces:
- `instruments/[slug]/manuals/[name].txt` — searchable full text
- `instruments/[slug]/manuals/[name].index.json` — page/section index

Verify: `python scripts/index_manuals.py list`

### Step 5 — Find the MIDI Implementation appendix

Use `manual-lookup` skill to locate the parameter table:

```
grep_search(
  query="Program Parameter\|NRPN\|SysEx\|parameter number",
  includePattern="instruments/[slug]/manuals/[name].txt",
  isRegexp=True
)
```

Look for a table with columns like:
```
NRPN    Value Range    Description
0       0-120          Osc 1 Frequency
1       0-100          Osc 1 Fine Tune
...
```

Also record:
- **Manufacturer SysEx ID** (1 or 3 bytes after `F0`)
- **Device ID byte** and whether it's configurable (offset by global setting)
- **Program dump command byte** (e.g. `0x02` = single, `0x06` = bank)
- **Name offset** — byte index of the ASCII preset name in the unpacked data
- **Total program byte count** — used for size-based disambiguation

### Step 6 — Build the parameter map

```bash
python3 -c "
import re, json
from pathlib import Path

txt = open('instruments/[slug]/manuals/[name].txt').read()
# ... parse the parameter table from the .txt ...
# Use the same regex approach as the Rev2 map build

out = Path('database/midi_params')
out.mkdir(exist_ok=True)
(out / '[key].json').write_text(json.dumps({
    'instrument': '[key]',
    'source_manual': '[name].pdf',
    'source_section': 'Appendix X: MIDI Implementation',
    'notes': [],
    'params': { str(k): {
        'name': name,
        'nrpn_a': k,
        'nrpn_b': nrpn_b_or_none,
        'value_range': vrange
    } for k, ... }
}, indent=2))
"
```

The parameter map JSON schema:
```json
{
  "instrument": "key",
  "source_manual": "Manual-Name.pdf",
  "source_section": "Appendix E: MIDI Implementation",
  "notes": ["any caveats about the mapping"],
  "params": {
    "0": { "name": "Osc 1 Freq", "nrpn_a": 0, "nrpn_b": null, "value_range": "0-120" },
    "1": { "name": "Osc 1 Freq Fine", "nrpn_a": 1, "nrpn_b": null, "value_range": "0-100" }
  }
}
```

Store at: `database/midi_params/[key].json`

### Step 7 — Set name_offset in the INSTRUMENTS dict

Find the `name_offset` by looking for "patch name" or "program name" in the MIDI
appendix of the `.txt` file. It's the byte index (in the unpacked data) where the
ASCII preset name begins.

Update `scripts/sysex_capture.py`:
```python
"name_offset": 184,   # example: byte 184 of the unpacked Layer A data
```

Verify by running:
```bash
python scripts/sysex_capture.py parse \
  --file instruments/[slug]/presets/raw/[dump].syx \
  --instrument [key]
```
The preset name should now match what the instrument displays.

### Step 8 — Test SysEx capture end to end

```bash
# Start listener
python scripts/sysex_capture.py capture --port "PORT NAME" --instrument [key]

# On the hardware: initiate a SysEx dump (see SKILL.md for sysex-capture)
# Or replay via SysEx Librarian through IAC Driver iron-static
```

Confirm:
- [ ] Raw `.syx` written to `instruments/[slug]/presets/raw/`
- [ ] JSON preset written to `instruments/[slug]/presets/`
- [ ] `parameters` field contains named keys, not just an index array
- [ ] `name` field matches what the instrument displays

### Step 9 — Update copilot-instructions.md

Add the instrument to the **Instrument Rig** section and **MIDI Channels** table.

---

## Instrument Capability Reference

| Capability | Can Parse? | Notes |
|---|---|---|
| Sequential/DSI (Rev2, Take5, OB-6, etc.) | ✅ | DSI 7-bit packing, known NRPN table |
| Elektron (Digitakt, Digitone, Analog4) | ⚠️ raw | Proprietary; use Elektron Transfer |
| Moog (patch-memory models: Sub 37, Matriarch) | 🔍 check | Some Moog have SysEx dumps |
| Moog (no memory: DFAM, Subharmonicon) | ❌ | Panel-state only; use create-preset |
| Arturia (MiniLab, KeyLab, etc.) | 🔍 check | Varies by model |
| Roland (JX series, etc.) | 🔍 check | Usually parseable; Roland SysEx well-documented |

---

## Re-using This Skill for Param Map Updates

If you add firmware and the parameter list changes, re-run from Step 5.
The `.index.json` mtime check in `index_manuals.py` will detect the updated PDF
and re-index automatically.
