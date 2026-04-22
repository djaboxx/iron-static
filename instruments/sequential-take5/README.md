# Sequential Take 5

**Role in IRON STATIC**: Compact 5-voice analog poly — punchy chords, tight leads, quick harmonic accent parts.

## Overview

The Take 5 is a focused 5-voice polysynth in a smaller form factor. It shares Sequential DNA with the Rev2 but has a simpler architecture. It excels at punchy, in-your-face sounds — stabs, tight pads, resonant leads.

## Signal Flow

```
Digitakt MIDI Track → Take 5 MIDI In (ch 4)
Take 5 Audio Out (L/R) → Audio Interface / Ableton
```

## Key Features for IRON STATIC

- **5 voices**: Smaller voice count means thicker individual voices (fuller per-voice signal path)
- **DCO per voice + sub oscillator**: Each voice gets its own DCO plus a sub — instant low-end weight
- **Built-in effects**: Chorus, delay, reverb (use sparingly — prefer Ableton effects for consistency)
- **Filter**: Curtis-style LP filter, very musical resonance character
- **Simple mod matrix**: Less complex than Rev2 but perfectly functional for targeted patches

## MIDI / NRPN

Full NRPN control. Use for Ableton automation or Digitakt p-locks.

NRPN reference: `instruments/sequential-take5/manuals/midi-impl.md`

## Preset Format

JSON with parameter values. See `create-preset` skill.

Presets: `instruments/sequential-take5/presets/`

## Manual

Place Take 5 manual PDF here: `instruments/sequential-take5/manuals/`

Official documentation: https://www.sequential.com/product/take5/

## Workflow Tips

1. Use for parts that need to cut through the Rev2 — brighter, more aggressive filter settings
2. The sub oscillator per voice adds low-mid weight without competing with Digitakt kick
3. Bypass built-in effects and use Ableton racks for consistent processing across the mix
4. Great for 5-voice chord stabs triggered by Digitakt — use tight attack, fast decay
5. Pair with Rev2 Layer A pads: Take 5 handles the attack, Rev2 sustains
