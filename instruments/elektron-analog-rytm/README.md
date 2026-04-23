# Elektron Analog Rytm — Onboarding

Manufacturer: Elektron
Model: Analog Rytm MKI/MKII

Role: Hybrid analog/drum-synth sampler — aggressive analog drums, tight transients, and extensive sequencing.

Default MIDI channel recommendation: 8 (reserved for additional hardware)

Notes:
- Elektron SysEx format is proprietary. We'll capture raw `.syx` dumps and store them in `presets/raw/`.
- For full project/kit recovery use Elektron Transfer or Overbridge where available.
- When capturing SysEx, use `scripts/sysex_capture.py capture --port "<port>" --instrument rytm`.

Folder layout:
- `manuals/` — put the instrument PDF(s) here as `*.pdf`
- `presets/raw/` — raw `.syx` dumps are saved here by `sysex_capture.py`
- `presets/` — parsed JSON presets (if parsers are implemented)

Next steps:
1. Add the official manual PDF to `manuals/`.
2. Run `python scripts/index_manuals.py --instrument rytm` to index it.
3. If MIDI Implementation appendix is available, extract the parameter map to `database/midi_params/rytm.json`.
4. Update `scripts/sysex_capture.py` `INSTRUMENTS` entry with `name_offset` after manual inspection.
