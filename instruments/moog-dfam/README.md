# Moog DFAM (Drummer From Another Mother)

**Role in IRON STATIC**: Analog percussion synthesizer. Provides tonal, tuneable drum sounds with a distinctive Moog character — especially kicks, industrial toms, and noise-based percussion.

## Overview

The DFAM is a semi-modular analog percussion synthesizer with an 8-step sequencer, 2 VCOs, Moog ladder filter, and voltage-controlled everything. It sounds like a drum machine that's been taken apart and put back together wrong — in the best possible way.

**It has no patch memory.** All patches are documented as panel-state snapshots + patch cable descriptions.

## Signal Flow

```
Digitakt MIDI Track (ch 6) → DFAM MIDI In (for step advance via MIDI)
OR
Digitakt CV/Gate Out → DFAM EXT IN (via modular adapter)
DFAM Audio Out → Audio Interface / Ableton
```

Note: DFAM can be clocked externally (advancing steps via trigger input) or run its own internal sequencer.

## Architecture

```
VCO 1 ──┐
         ├─► VCF (Ladder) ─► VCA ─► Output
VCO 2 ──┘

8-step sequencer → VCO Pitch (per step), VCA Level (per step)
Noise source → available for FM or filter input
Envelope (ADSR decay controls) → VCF + VCA
```

## What It Does for IRON STATIC

- **Moog Kick**: VCO pitch drop via envelope = classic analog kick with sub depth
- **Industrial toms**: Tune VCOs to musical intervals, use filter for tone shaping
- **Metal percussion**: High resonance + noise = industrial clang and texture
- **Accent lines**: Program chromatic or intervallic pitch sequences for melodic percussion
- **FM percussion**: VCO2 FM into VCO1 at high rates = metallic, bell, cymbal-like tones

## Patch Sheet Format

```markdown
# Patch: [Name]
**Created**: YYYY-MM-DD
**Clock Source**: [Internal / External Trigger / DFAM advance via Digitakt MIDI]
**BPM context**: [e.g., 140 BPM]

## Sequencer
| Step | Pitch (turn position) | Velocity (turn position) |
|------|-----------------------|--------------------------|
| 1    | min (low kick)        | max                      |
| 2    | 12 o'clock (mid tom)  | 9 o'clock                |
| ...  | ...                   | ...                      |

## VCO Settings
- VCO 1 Frequency: [o'clock / approx Hz]
- VCO 2 Frequency: [o'clock / approx Hz]
- FM Amount (VCO2→VCO1): [o'clock]
- Noise: [on/off, level]

## Filter
- Cutoff: [o'clock]
- Resonance: [o'clock]
- Envelope Amount: [o'clock]

## Envelope
- Attack: [o'clock]
- Decay: [o'clock]

## VCA Decay
- [o'clock]

## Tempo / Rate
- Internal rate: [o'clock] OR external clock source

## Patch Cables
- [Source] → [Destination]: [purpose]

## Sound Description
[What it sounds like; when to use it in a song]
```

Patch sheets: `instruments/moog-dfam/presets/`

## Manual

Place DFAM manual PDF here: `instruments/moog-dfam/manuals/`

Official documentation: https://www.moogmusic.com/products/dfam

## Workflow Tips

1. **Classic analog kick**: Min pitch on step 1, high envelope amount, VCA decay ~9 o'clock
2. **Sequence in unison with Digitakt**: Clock DFAM from Digitakt; set DFAM to 8 steps for an off-beat accent layer
3. **Pitch the toms**: Set different VCO pitches per step to create a pitched percussion sequence — tune to key of song
4. **Noise into FM**: Route noise → FM input for industrial texture on hi-hat-like sounds
5. **Subharmonicon pairing**: Tune DFAM VCO 1 to same root as Subharmonicon VCO 1 — they'll reinforce each other's subharmonics
