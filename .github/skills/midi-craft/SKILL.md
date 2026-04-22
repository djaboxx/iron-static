---
name: midi-craft
description: Compose, generate, or evolve MIDI sequences and patterns in the IRON STATIC aesthetic. Outputs .mid files or Digitakt-compatible pattern descriptions.
argument-hint: "[concept or song idea] [optional: instrument=digitakt|rev2|take5 bpm=120 key=Em time=4/4]"
user-invocable: true
disable-model-invocation: false
---

# Skill: midi-craft

## What This Skill Does

Given a creative brief, this skill:
1. Composes a MIDI sequence or rhythmic pattern suited to the IRON STATIC aesthetic
2. Outputs it as a standard MIDI file (`.mid`) or describes it as a step-sequencer pattern
3. Annotates it with performance notes and parameter lock suggestions for the Digitakt
4. Can evolve or mutate an existing pattern (make it heavier, add polyrhythm, invert the groove)

## When to Use

- Starting a new song idea from a concept ("I want something in 7/8 that feels like a machine breaking down")
- Creating complementary parts for an existing sketch
- Generating variations of a pattern to develop a groove
- Translating a rhythmic or melodic idea into MIDI for the Digitakt or a synth
- Exploring polyrhythmic combinations with the Subharmonicon / DFAM / Digitakt together

## IRON STATIC MIDI Aesthetic

When writing sequences, prioritize:
- **Odd and compound meters**: 7/8, 5/4, 11/16, 6/8 alongside 4/4
- **Polyrhythm**: layers with different cycle lengths (e.g., 16-step vs. 12-step vs. 10-step)
- **Silence as rhythm**: negative space, rests, pauses that create weight
- **Conditional variation**: Digitakt's `trig conditions` should be suggested where relevant
- **Velocity dynamics**: sequences should breathe — not all hits at max velocity
- **Chromaticism and dissonance**: approach notes, half-step tensions, tritones welcome
- **Root movement**: bass/sub lines that move unexpectedly, not just I–V–I

## Default MIDI Channel Map

Reference `copilot-instructions.md` for the full channel map. Default starting points:
- Digitakt patterns: described as 16-step or 32-step grids
- Rev2: channel 2 (Layer A)
- Take 5: channel 4
- Subharmonicon: described as sequencer row values + clock ratios
- DFAM: described as pitch/velocity rows
- Minibrute 2S: channel 7

## Output Format

### MIDI file output
```
midi/sequences/[concept-slug]_[instrument]_v1.mid
midi/patterns/[pattern-name]_[instrument].mid
```

### Digitakt pattern description
```
PATTERN: [Name]
BPM: [x]    TIME SIG: [x/x]    LENGTH: [16 or 32 steps]

TRACK 1 — Kick (sample: [name]):
  Steps: [1]....[5]......[9]....[13].....
  Velocity: 127, 80, -, 95, -, -, 127, -...
  p-locks: step 5: filter cutoff 40; step 13: sample start +10

TRACK 2 — Snare:
  ...

MIDI TRACK A — Rev2 (ch 2):
  Notes: E2, G2, B2 (Eminor chord, step 1 only), release on step 4
  CC: [parameter lock suggestions]
```

## Usage

### Via CLI

```bash
python scripts/midi_craft.py --concept "heavy 7/8 groove" --bpm 140 --key Em --output midi/sequences/
python scripts/midi_craft.py --pattern "hi-hat polyrhythm" --steps 16 --instrument digitakt
python scripts/midi_craft.py --evolve midi/patterns/existing_pattern.mid --variation "heavier, slower decay"
```

### Via Copilot chat

- "Write a 7/8 drum pattern for the Digitakt that sounds like machinery breaking down"
- "Create a Rev2 bass sequence in E minor that moves every 12 steps (against a 16-step kick)"
- "Take this pattern and add polyrhythm — offset the hi-hat by 3 steps"
- "Write a Subharmonicon patch setup that creates rhythmic subharmonic interference at 120 BPM"

## Script: [midi_craft.py](../../scripts/midi_craft.py)

Uses `mido` for MIDI file generation. Patterns can be exported as `.mid` files directly loadable into Ableton.

## Theory Notes Baked In

- Default scale palette: Aeolian, Phrygian, Locrian, Diminished, Whole-tone
- Default chord vocabulary: minor, minor 7, minor 9, diminished, augmented, sus4, power chords
- Preferred root notes for the aesthetic: E, A, D, B, F# (guitar-adjacent, heavy)

## Notes

- Subharmonicon and DFAM patterns are output as panel-state descriptions, not MIDI files (hardware sequencers with no MIDI note input)
- Digitakt patterns can be described in XML/JSON for future SysEx import tooling
- `.mid` files are tracked as binary (`-text`) in `.gitattributes`
