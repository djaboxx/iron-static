---
name: Instrument Conventions
description: Naming, file structure, and documentation standards for IRON STATIC instrument presets and patches.
applyTo: "instruments/**"
---

## Instrument slug reference
Use these exact slugs in all file names and JSON keys:
- `digitakt` — Elektron Digitakt MK1
- `rev2` — Sequential Rev2
- `take5` — Sequential Take 5
- `subharmonicon` — Moog Subharmonicon
- `dfam` — Moog DFAM
- `minibrute2s` — Arturia Minibrute 2S
- `pigments` — Arturia Pigments

## Preset file naming
- MIDI-dumpable params: `[instrument-slug]_[descriptive-name]_[bpm-or-key-if-relevant].json`
- Panel-state docs (semi-modular gear): `[descriptive-name].md`
- SysEx dumps: `[instrument-slug]_[bank-or-preset-desc]_[date].syx`

## NRPN format (for Rev2 / Take 5 JSON presets)
Each parameter entry:
```json
{ "nrpn_msb": 0, "nrpn_lsb": 0, "value": 0, "name": "human-readable-name" }
```
Top-level keys: `instrument`, `slug`, `key`, `bpm`, `parameters` (array).

## Catalog requirements
Every preset directory must contain a `catalog.json` listing all presets with their slug, name, key/bpm context, and status (`draft`/`active`/`archived`).

## Semi-modular patch sheets
Subharmonicon, DFAM, and Minibrute 2S have no memory. Document patches as Markdown with:
1. Panel state (knob positions, switch states)
2. Patch cable matrix (source → destination)
3. Context (song, BPM, intended role)

## MIDI channel defaults
| Instrument | Channel |
|---|---|
| Digitakt (auto-channel) | 1 |
| Rev2 Layer A | 2 |
| Rev2 Layer B | 3 |
| Take 5 | 4 |
| Subharmonicon | 5 |
| DFAM | 6 |
| Minibrute 2S | 7 |
| Pigments | 8 |
