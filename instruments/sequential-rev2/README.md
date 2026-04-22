# Sequential Rev2

**Role in IRON STATIC**: Main polyphonic analog synth — pads, detuned leads, evolving textures, and heavy chord stabs.

## Overview

The Rev2 is a 16-voice (8+8 bi-timbral) polysynth with analog signal path (Curtis filters), deep modulation matrix, arpeggiator/sequencer, and full NRPN control. It's the harmonic workhorse of the rig.

## Signal Flow

```
Digitakt MIDI Track → Rev2 MIDI In (ch 2 Layer A, ch 3 Layer B)
Rev2 Audio Out (L/R) → Audio Interface / Ableton
```

## Key Features for IRON STATIC

- **Bi-timbral**: Run two completely different patches simultaneously (Layer A + B)
- **16 voices**: Thick, wall-of-sound pads possible
- **Oscillator detuning**: Detune OSC2 against OSC1 for beating/chorus effect without effects
- **Curtis filter (Prophet-style)**: Low-pass with 4-pole slope — warm, aggressive resonance
- **Mod matrix**: 4 mods per layer — assign LFOs, envelopes, velocity, aftertouch to any destination
- **Arpeggiator**: Full arpeggiator with gate/BPM sync — good for rhythmic pad textures
- **Polyphonic portamento**: Glide on chords for slow morphing

## MIDI / NRPN

The Rev2 is fully NRPN-addressable — every parameter has an NRPN number. This enables:
- Real-time parameter automation from Ableton
- Full preset dumps via SysEx
- Digitakt MIDI track p-locks for parameter changes per step

Key NRPNs documented in: `instruments/sequential-rev2/manuals/midi-impl.md`

## Preset Format

JSON with parameter values + NRPN numbers. See `create-preset` skill.

Presets: `instruments/sequential-rev2/presets/`

## Manual

Place Rev2 manual PDF here: `instruments/sequential-rev2/manuals/`

Official documentation: https://www.sequential.com/product/rev2/

## Workflow Tips

1. Layer A = main harmonic voice (pad or chord), Layer B = bass or counter-melody
2. Slight detune between OSC1 and OSC2 makes everything sound bigger
3. Use filter envelope decay + resonance for aggressive pluck sounds
4. Slow LFO on filter cutoff = evolving pad texture without external effects
5. Route Digitakt MIDI track velocity → filter amount for dynamics from the sequencer
