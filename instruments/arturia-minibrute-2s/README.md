# Arturia Minibrute 2S

**Role in IRON STATIC**: Patchable semi-modular mono synth + 2×8 step sequencer. Provides aggressive mono bass lines, screaming leads, and modular-adjacent weirdness.

## Overview

The Minibrute 2S is a semi-modular monosynth with a patchbay, a distinctive Steiner-Parker filter, the "Brute Factor" (wavefolder/saturation/feedback control), and a built-in 2×8-step sequencer. It's the most aggressive-sounding synth in the rig — especially with Brute Factor cranked.

**It has no patch memory.** Patches are documented as panel-state + patch matrix descriptions.

## Signal Flow

```
Digitakt MIDI Track (ch 7) → Minibrute 2S MIDI In
OR Minibrute 2S Sequencer → runs independently (clock from Digitakt)
Minibrute 2S Audio Out (Main) → Audio Interface / Ableton
```

## Architecture

```
VCO (Sawtooth, Square, Triangle, White Noise) 
  → ULTRASAW (additional oscillators with slight detune)
  → METALIZER (waveshaping for metallic tones)
  → Brute Factor (feedback/saturation path)
  → Steiner-Parker Filter (BP, LP, HP, Notch)
  → VCA
  → Output

LFO 1 + LFO 2 → patchable destinations
Envelope 1 (AMP) + Envelope 2 (MOD) → patchable
Patchbay: ~36 patch points (CV/gate ins and outs)
2×8 Sequencer (2 rows, 8 steps each, linked or independent)
```

## What It Does for IRON STATIC

- **Brute bass**: Sawtooth + Brute Factor = thick, aggressive mono bass
- **Screaming leads**: High resonance + Steiner HP filter = cutting, aggressive lead sounds
- **Metallic textures**: Metalizer waveshaping + FM = industrial bell/clang
- **Self-patching weirdness**: Patch envelope out → oscillator pitch for unpredictable pitch modulation
- **Sequences**: 2-row sequencer allows a melody + bass or two complementary patterns

## Patch Sheet Format

```markdown
# Patch: [Name]
**Created**: YYYY-MM-DD
**Clock Source**: [Digitakt MIDI / Internal]

## Oscillator
- Waveform: [Saw / Square / Triangle / Noise — knob position]
- Ultrasaw: [amount — o'clock]
- Metalizer: [amount — o'clock]
- Sub Oscillator: [level — o'clock, octave: -1 / -2]
- Noise: [level — o'clock]

## Brute Factor
- Amount: [o'clock — 7=off, max right = full feedback]

## Filter (Steiner-Parker)
- Mode: [LP / BP / HP / Notch]
- Cutoff: [o'clock]
- Resonance: [o'clock]
- Envelope Amount: [o'clock]
- LFO Amount: [o'clock]

## Envelopes
- ENV 1 (AMP): Attack [o'clock] | Decay [o'clock] | Sustain [o'clock] | Release [o'clock]
- ENV 2 (MOD): Attack [o'clock] | Decay [o'clock] | Sustain [o'clock] | Release [o'clock]

## LFO 1
- Rate: [o'clock] | Waveform: [Sine/Square/Triangle/S&H] | Destination: [from panel position]

## LFO 2
- Rate: [o'clock] | Waveform: [...] | Destination: [...]

## Sequencer
- Row 1: [step values in semitones relative to root, 8 steps]
- Row 2: [step values, or "off"]
- Glide: [on steps: list step numbers]

## Patchbay Connections
- [Source jack] → [Destination jack]: [purpose]
- ...

## Sound Description
[What it sounds like; when to use it]
```

Patch sheets: `instruments/arturia-minibrute-2s/presets/`

## Manual

Place Minibrute 2S manual PDF here: `instruments/arturia-minibrute-2s/manuals/`

Official documentation: https://www.arturia.com/products/hardware-synths/minibrute2s/

## Workflow Tips

1. **Brute Factor**: Keep it under 50% for musical use; beyond that = controlled chaos / feedback
2. **Ultrasaw**: Use at ~9–10 o'clock for classic detuned synth bass; higher = swarm effect
3. **Steiner HP mode**: For screaming leads, flip to HP and raise cutoff — very unique sound not available on most synths
4. **Self-patch ENV2 to VCO pitch**: Set ENV2 decay fast, amount high = pitch drop per note attack
5. **Sequence with Digitakt**: Use MIDI ch 7 from Digitakt to pitch the Minibrute 2S while running its own sequencer for rhythm
6. **Subharmonicon pairing**: Route Minibrute 2S audio into Subharmonicon's external input (if patching) for filter coloring
