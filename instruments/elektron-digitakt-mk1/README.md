# Elektron Digitakt MK1

**Role in IRON STATIC**: Primary drum machine, sampler, and the central sequencer brain.

## Overview

The Digitakt is the rhythmic hub of the rig. It sequences itself (8 audio tracks of one-shot samples) and drives the other instruments via its MIDI tracks (8 MIDI tracks, channels 1–8 by default configurable per track). It's the clock master.

## Signal Flow

```
Digitakt MIDI Out → Rev2 (ch 2), Take 5 (ch 4), Subharmonicon (ch 5), DFAM (ch 6), Minibrute 2S (ch 7)
Digitakt Audio Out (Main L/R) → Audio Interface / Ableton
```

## Key Features for IRON STATIC

- **Parameter locks**: Automate any knob per-step — essential for groove variation without pattern duplication
- **Conditional trigs**: `1:2`, `A`, `B`, `%50` — create evolving patterns that never repeat exactly
- **LFO per track**: Assign LFO to sample pitch, filter, volume, pan for texture and movement
- **Retrig**: Sub-beat rolls and mechanical repeats
- **MIDI tracks**: Each MIDI track sends notes + CCs to one external instrument

## MIDI Implementation Notes

- **Auto-channel**: Default ch 1 for external control (change per-pattern)
- **MIDI tracks** default to ch 9–16 but are fully remappable
- **CC Output**: MIDI tracks output CC on configurable numbers (see manual)
- **SysEx**: Full pattern/kit dump available for backup

## Preset Format

Digitakt doesn't have "presets" in a traditional sense. Document as:
- **Kit**: Sample/synth assignments + per-track settings
- **Pattern**: 16 or 32 step grid + parameter locks + trig conditions

Kits and patterns go in: `instruments/elektron-digitakt-mk1/presets/`

## Manual

Place the Digitakt MK1 manual PDF here: `instruments/elektron-digitakt-mk1/manuals/`

Official documentation: https://www.elektron.se/en/digitakt-explorer

## Workflow Tips

1. Start with a kick pattern — establish the downbeat anchor
2. Use conditional trigs on hi-hats for humanization without effort
3. Route MIDI track 1 to Rev2 for chords; use p-locks to change chords per step
4. Use the LFO on MIDI track velocity for dynamic swells on pads
5. Set the Subharmonicon's clock input from Digitakt's MIDI clock out
