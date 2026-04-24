---
name: extract-midi-clips
description: "Extract MIDI notes from Ableton .als clips and export them as standard .mid files using scripts/extract_midi_clips.py."
---

# SKILL: extract-midi-clips

## Purpose
Extract MIDI notes from Ableton `.als` clips and export them as standard `.mid` files.

Files
-----
- `scripts/extract_midi_clips.py` — script that parses an `.als` and writes one `.mid` per clip.

Usage
-----
Run from repository root (virtualenv with `mido` installed):

```bash
python3 scripts/extract_midi_clips.py \
  "/path/to/project/Ventura.als" \
  outputs/midi_clips --ticks 480 --tempo 120
```

Notes
-----
- The script interprets `Time` and `Duration` attributes on `MidiNoteEvent` as beats. It converts them to MIDI ticks using `--ticks` (`480` by default).
- Pitch mapping: the script reads each `KeyTrack`'s `<MidiKey Value="NN"/>` and computes note pitch as `MidiKey + (NoteId - 1)`.
- If `MidiKey` is missing for a KeyTrack, those notes are skipped.

Integration
-----------
Agents can call `scripts/extract_midi_clips.py` to batch-export MIDI from Ableton projects and attach the resulting `.mid` files to tasks or further processing pipelines.
