---
name: manual-lookup
description: "Look up specifications, parameters, MIDI implementation details, and operational procedures from any IRON STATIC instrument manual."
---

# SKILL: manual-lookup

## Purpose
Look up specifications, parameters, MIDI implementation details, and operational
procedures from any IRON STATIC instrument manual — without re-parsing the PDF.

---

## When to Use This Skill
- "How do I set the Rev2's filter cutoff via MIDI?"
- "What's the sequencer step limit on the Digitakt?"
- "Show me the Subharmonicon's patching guide"
- "What SysEx command requests a Take 5 program dump?"
- Any question where the answer lives in an instrument manual

---

## Index Files

Every manual has two pre-built index files alongside it:

| File | Purpose |
|---|---|
| `instruments/[slug]/manuals/[name].txt` | Full extracted text — use `grep_search` on this |
| `instruments/[slug]/manuals/[name].index.json` | Page count + detected section headings |

Regenerate with:
```bash
source .venv/bin/activate
python scripts/index_manuals.py                     # all instruments
python scripts/index_manuals.py --instrument rev2   # one instrument
python scripts/index_manuals.py --force             # re-index even if up to date
python scripts/index_manuals.py list                # show status
```

---

## Instrument → Manual File Map

| Key | Folder | Manual txt |
|---|---|---|
| `rev2` | `sequential-rev2` | `Prophet-Rev2-Users-Guide-1.2.4.txt` |
| `take5` | `sequential-take5` | `Take-5-Users-Guide-v2_3.txt` |
| `digitakt` | `elektron-digitakt-mk1` | `Digitakt-User-Manual_ENG_OS1.52A.txt` |
| `dfam` | `moog-dfam` | `DFAM-User-Guide.txt` |
| `subharmonicon` | `moog-subharmonicon` | `Subharmonicon-User-Guide.txt` |
| `minibrute2s` | `arturia-minibrute-2s` | `MiniBrute-2S-Manual-EN.txt` |

---

## Lookup Workflow

### Step 1 — Check index exists
```python
# Quick status check
python scripts/index_manuals.py list
```
If status shows `NOT INDEXED`, run the indexer first.

### Step 2 — Search the .txt file
Use `grep_search` with the `.txt` path as `includePattern`:

```
grep_search(
  query="Filter Cutoff",
  includePattern="instruments/sequential-rev2/manuals/Prophet-Rev2-Users-Guide-1.2.4.txt"
)
```

Results include line numbers and surrounding text. The format is:
```
=== PAGE N ===
[page content]
```
so you always know which page a result is on.

### Step 3 — Read context around the hit
Use `read_file` to read ±20 lines around any interesting match.

### Step 4 — Navigate by section
Read `.index.json` to find section titles and their page numbers:
```python
import json
idx = json.load(open("instruments/sequential-rev2/manuals/Prophet-Rev2-Users-Guide-1.2.4.index.json"))
# Find section by keyword
for s in idx["sections"]:
    if "MIDI" in s["title"]:
        print(s["page"], s["title"])
```
Then `grep_search` for `=== PAGE N ===` to jump to that page in the .txt.

---

## Parameter Maps

For instruments with MIDI-programmable parameters, structured param maps live in
`database/midi_params/[key].json`. These contain the full NRPN index → parameter
name mapping extracted from the manual appendix.

| Instrument | Map file | Status |
|---|---|---|
| Rev2 | `database/midi_params/rev2.json` | ✅ 138 params |
| Take 5 | `database/midi_params/take5.json` | ❌ not yet built |
| Digitakt | N/A | Proprietary format |

To query the param map:
```python
import json
params = json.load(open("database/midi_params/rev2.json"))["params"]
# Look up by index
print(params["15"])  # → {"name": "Filter Cutoff", "nrpn_a": 15, ...}
```

To build a new param map, use the `instrument-onboard` skill.

---

## Tips

- **Page markers**: The .txt format uses `=== PAGE N ===` as page separators. Always
  searchable: `grep_search(query="=== PAGE 85 ===")`
- **Multi-word search**: `grep_search` with `isRegexp=True` for things like
  `"SysEx.*program|program.*SysEx"`
- **Cross-manual search**: Use the same approach on multiple `.txt` files in parallel
- **Section headings**: The `.index.json` sections list is heuristic — short title-case
  lines detected automatically. Not all sections are captured, but MIDI Implementation
  appendices, chapter titles, and major headings are reliably found.
