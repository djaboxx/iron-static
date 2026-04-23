#!/usr/bin/env python3
"""Extract CC/NRPN table from the Analog Rytm MKII manual text and write JSON.

Usage:
  python3 scripts/extract_rytm_midi_params.py

Writes: database/midi_params/rytm.json
"""
import json
from pathlib import Path
import re

ROOT = Path(__file__).parent.parent
TXT = ROOT / "instruments" / "elektron-analog-rytm" / "manuals" / "Analog-Rytm-MKII-User-Manual_ENG_OS1.72_250130.txt"
OUT = ROOT / "database" / "midi_params" / "rytm.json"

text = TXT.read_text()
# Locate APPENDIX C start and end (APPENDIX D)
start = text.find("APPENDIX C: MIDI")
end = text.find("APPENDIX D:")
if start == -1:
    raise SystemExit("APPENDIX C not found")
lines = text.splitlines()

params = {}
i = 0
while i < len(lines):
    ln = lines[i]
    if 'NRPN MSB' in ln and 'CC MSB' in ln:
        # detect column starts
        p_cc_msb = ln.find('CC MSB')
        p_cc_lsb = ln.find('CC LSB')
        p_nrpn_msb = ln.find('NRPN MSB')
        p_nrpn_lsb = ln.find('NRPN LSB')
        # advance to data rows
        i += 1
        while i < len(lines):
            row = lines[i]
            # stop if we reached a new top-level section or blank separator of >2 lines
            if row.strip().startswith('C.') or row.strip().startswith('APPENDIX'):
                break
            if 'NRPN MSB' in row and 'CC MSB' in row:
                break
            if not row.strip():
                i += 1
                continue
            # slice fields by column indices (fall back if positions not found)
            try:
                name = row[:p_cc_msb].strip()
                cc_msb_s = row[p_cc_msb:p_cc_lsb].strip() if p_cc_msb != -1 and p_cc_lsb != -1 else ''
                cc_lsb_s = row[p_cc_lsb:p_nrpn_msb].strip() if p_cc_lsb != -1 and p_nrpn_msb != -1 else ''
                nrpn_msb_s = row[p_nrpn_msb:p_nrpn_lsb].strip() if p_nrpn_msb != -1 and p_nrpn_lsb != -1 else ''
                nrpn_lsb_s = row[p_nrpn_lsb:].strip() if p_nrpn_lsb != -1 else ''
            except Exception:
                i += 1
                continue
            # skip header-like rows
            if name.lower().startswith('parameter') or not name:
                i += 1
                continue
            # parse numbers where present
            try:
                nrpn_msb = int(nrpn_msb_s) if nrpn_msb_s else None
                nrpn_lsb = int(nrpn_lsb_s) if nrpn_lsb_s else None
            except ValueError:
                i += 1
                continue
            try:
                cc_msb = int(cc_msb_s) if cc_msb_s else None
            except ValueError:
                cc_msb = None
            try:
                cc_lsb = int(cc_lsb_s) if cc_lsb_s else None
            except ValueError:
                cc_lsb = None
            if nrpn_msb is None or nrpn_lsb is None:
                i += 1
                continue
            nrpn_num = nrpn_msb * 128 + nrpn_lsb
            params[str(nrpn_num)] = {
                'name': re.sub(r"\s{2,}", ' ', name),
                'cc_msb': cc_msb,
                'cc_lsb': cc_lsb,
                'nrpn_msb': nrpn_msb,
                'nrpn_lsb': nrpn_lsb,
            }
            i += 1
        continue
    i += 1

out = {
    "instrument": "rytm",
    "source_manual": TXT.name,
    "notes": [
        "Entries keyed by 14-bit NRPN number = NRPN_MSB*128 + NRPN_LSB",
        "cc_msb/cc_lsb may be null when not listed in a given table row.",
        "Verify name offsets for SysEx parsing separately; name_offset left unset in sysex_capture.py unless you ask.",
    ],
    "params": params,
}

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(out, indent=2))
print(f"Wrote {OUT}")
