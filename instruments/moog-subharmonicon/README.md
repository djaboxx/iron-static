# Moog Subharmonicon

**Role in IRON STATIC**: Semi-modular polyrhythmic drone and sub-bass machine. Creates rhythmic weirdness that nothing else in the rig can.

## Overview

The Subharmonicon is a semi-modular analog synthesizer with 2 VCOs, each with 2 subharmonic oscillators, and 4 sequencer rows with independent clock dividers. It generates complex polyrhythmic sequences from a single master clock, creating patterns that feel simultaneously inevitable and strange.

**It has no patch memory.** All patches are documented as physical cable configurations + panel knob positions.

## Signal Flow

```
Digitakt MIDI Clock Out → Subharmonicon Clock In (or use internal oscillator clock)
Subharmonicon Audio Out → Audio Interface / Ableton
```

## Architecture

```
VCO 1 ─┬─ SUB 1 (÷ integer 2–16 of VCO 1)
        └─ SUB 2 (÷ different integer)
VCO 2 ─┬─ SUB 3
        └─ SUB 4

4 Sequencers × 4 steps each, each clocked independently
Rhythmic clock divisions: /2, /3, /4, /6, /8, /12, /16 of master clock

VCF (Ladder filter) → VCA → Output
```

## What It Does for IRON STATIC

- **Subharmonic depth**: Pure, analog sub frequencies that sit below the DFAM kick
- **Polyrhythmic drift**: 4 sequencers at different rates create patterns that take 48, 96, or 192+ steps to repeat
- **Drone + pulse**: Can sustain a tonal center while producing rhythmic accents
- **FM between VCOs**: VCO 1 can frequency-modulate VCO 2 for bell-like metallic tones

## Patch Sheet Format

Since the Subharmonicon has no memory, document patches as:

```markdown
# Patch: [Name]
**Created**: YYYY-MM-DD
**Clock Source**: [Digitakt MIDI / Internal]
**BPM context**: [e.g., 120 BPM]

## VCO Settings
- VCO 1 Frequency: [approx Hz or semitone relative to A440]
- VCO 1 Sub 1 Division: [integer, e.g., 4]
- VCO 1 Sub 2 Division: [integer, e.g., 6]
- VCO 2 Frequency: [...]
- VCO 2 Sub 3 Division: [...]
- VCO 2 Sub 4 Division: [...]

## Sequencer
- SEQ 1 Rate: [clock division] | Steps: [n1, n2, n3, n4 in semitones]
- SEQ 2 Rate: [...]
- SEQ 3 Rate: [...]
- SEQ 4 Rate: [...]

## Filter
- Cutoff: [approx — o'clock notation]
- Resonance: [approx]
- Envelope Amount: [approx]

## Patch Cables
- [Source] → [Destination]: [purpose]
- ...

## Sound Description
[What it sounds like; when to use it in a song]
```

Patch sheets: `instruments/moog-subharmonicon/presets/`

## Manual

Place Subharmonicon manual PDF here: `instruments/moog-subharmonicon/manuals/`

Official documentation: https://www.moogmusic.com/products/subharmonicon

## Workflow Tips

1. Set SEQ 1 and SEQ 2 to different prime-number-adjacent divisions for maximum drift
2. Tune VCO 1 to the root of the song key; set SUB 1 division to 2 (one octave down)
3. Use Digitakt as master clock — MIDI clock output to Subharmonicon clock in
4. Keep filter mostly open; use envelope with slow attack for gradual emergence
5. FM amount from VCO1→VCO2 at low levels adds subtle harmonic complexity; high amounts create clang
