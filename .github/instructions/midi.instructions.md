---
name: MIDI File Conventions
description: File naming, channel routing, and content standards for MIDI sequences and patterns.
applyTo: "midi/**"
---

## File naming
`[song-slug]_[instrument-slug]_[version].mid`

Examples:
- `rust-protocol_take5_v1.mid`
- `rust-protocol_rev2-pad_v2.mid`
- `rust-protocol_digitakt-kick_v1.mid`

## Channel routing (match active session MIDI channel map)
| Channel | Instrument |
|---|---|
| 1 | Digitakt (auto-channel) |
| 2 | Rev2 Layer A |
| 3 | Rev2 Layer B |
| 4 | Take 5 |
| 5 | Subharmonicon |
| 6 | DFAM |
| 7 | Minibrute 2S |
| 8 | Pigments |

## Active song context
Always check `database/songs.json` for the active song's key, scale, and BPM before generating or editing MIDI.
Use the `SessionStart` hook context if available — it provides:
- Active song title, slug, key, scale, BPM, time signature

## Scale/note constraints
Generated notes must respect the active song's scale unless deliberately stepping outside it for tension.
For A Phrygian (current active): A B♭ C D E F G — root A, flat-2 (B♭) is the signature tension note.

## Tempo
Set MIDI file tempo to match the active song BPM. Default: 95 BPM for `rust-protocol`.

## Directory structure
- `midi/sequences/` — full arrangement clips, one per instrument
- `midi/patterns/` — loopable cells (4-16 bars), suitable for Digitakt pattern injection
- `midi/templates/` — blank or skeleton files for starting new songs
