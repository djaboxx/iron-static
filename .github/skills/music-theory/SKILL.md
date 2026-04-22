---
name: music-theory
description: Answer music theory questions in the context of heavy electronic music. Covers scales, modes, chord progressions, rhythm, arrangement, and the specific constraints of the IRON STATIC instrument rig.
argument-hint: "[theory question or concept] [optional: context=composition|arrangement|harmony|rhythm]"
user-invocable: true
disable-model-invocation: false
---

# Skill: music-theory

## What This Skill Does

This skill provides grounded, practical music theory answers filtered through the IRON STATIC aesthetic. It doesn't just answer "what notes are in D Phrygian" — it answers "what does D Phrygian sound like on the Rev2, when would you use it in a heavy electronic context, and what chord movements make it hit hardest."

## When to Use

- Planning the harmonic content of a new song
- Choosing a scale or mode for a specific emotional target
- Building chord progressions that work for electronic metal
- Understanding rhythmic concepts (polyrhythm, metric modulation, odd time)
- Analyzing a reference track's harmonic or rhythmic structure
- Deciding on key relationships between parts (e.g., what key does the DFAM accent line live in?)

## Theory Scope

### Scales & Modes (core palette for IRON STATIC)
| Scale/Mode | Character | Use Case |
|---|---|---|
| Natural Minor (Aeolian) | Dark, familiar, heavy | Foundation for most parts |
| Phrygian | Dark, Spanish, tense | Aggressive riffs, tension sections |
| Phrygian Dominant | Exotic, threatening | Lead lines over metal grooves |
| Locrian | Unstable, dissonant | Maximum tension, breakdown sections |
| Diminished (octatonic) | Symmetric, unsettling | Industrial texture, chromatic movement |
| Whole Tone | Dreamy, floating, unresolved | Ambient / transitional sections |
| Chromatic | No center, maximum dissonance | Noise / breakdown sections |
| Dorian | Minor with major 6th — hopeful-dark | Melodic lead lines, emotional anchor |

### Chord Vocabulary
- Power chords (5ths) — foundation of metal register
- Minor triads, minor 7ths, minor 9ths
- Diminished triads and fully diminished 7ths (tension)
- Augmented chords (unsettling forward motion)
- Flat-II major (Neapolitan) — classic "heavy" move
- Tritone substitutions — unexpected, machine-like
- Quartal and quintal voicings — open, modern, electronic

### Rhythm Vocabulary
- 4/4 with displacement and syncopation
- 7/8, 5/4, 11/16, 13/8 — odd meters
- Polyrhythm: 3-against-4, 5-against-4, 7-against-8
- Metric modulation: changing feel without changing tempo
- Euclidean rhythms — even distribution of hits (great for electronic patterns)
- Hemiola — 2-against-3 feel across a measure

### Arrangement Concepts
- **Textural density**: how many layers, when to strip back
- **Tension/release architecture**: building to and away from climax
- **Frequency layering**: sub, bass, mid, high each doing different rhythmic jobs
- **Call and response**: Digitakt pattern vs. synth melody
- **Repetition and variation**: repeat until hypnotic, then break it

## Usage

### Via Copilot chat

- "What's the difference between Phrygian and Phrygian Dominant and when would I choose one over the other?"
- "Give me 4 chord progressions in E minor that would work for heavy electronic music"
- "How do I create a polyrhythm between the DFAM (4-step loop) and Digitakt (16-step)?"
- "What key should the Subharmonicon drone be in if the Rev2 is playing in A minor?"
- "Explain metric modulation and give me an example I could actually use on the Digitakt"
- "What's a good chord progression that would make the Take 5 sound threatening?"

## Answer Format

Copilot should structure theory answers as:

```
CONCEPT: [Name]
IN PLAIN TERMS: [1–2 sentence explanation without jargon]
HOW IT SOUNDS: [Emotional/timbral description]
IN THE RIG: [How to implement on the IRON STATIC hardware]
EXAMPLE:
  [Scale degrees, chord names, or step-sequencer notation]
RELATED CONCEPTS: [links to adjacent theory ideas]
```

## Reference Files

- `knowledge/music-theory/scales-and-modes.md` — Detailed scale reference
- `knowledge/music-theory/chord-vocabulary.md` — Chord type reference
- `knowledge/music-theory/rhythm-patterns.md` — Rhythmic vocabulary with Digitakt examples
- `knowledge/sound-design/synthesis-notes.md` — How theory maps to synthesis parameters

## Notes

- Always contextualize theory answers within the actual rig (Digitakt, Rev2, Take 5, Subharmonicon, DFAM, Minibrute 2S)
- Prefer practical over academic framing — "this will make the riff feel heavier" over "this is the VII♭ borrowed from parallel major"
- When in doubt, suggest E minor or A minor as starting keys — guitar-adjacent, physically natural on most keyboards
