# Chord Vocabulary — IRON STATIC

Chord types used in IRON STATIC compositions, filtered for heavy electronic context.
All voicings are keyboard-friendly for Rev2 / Take 5.

---

## Core Chord Types

### Power Chord (5th)
- **Intervals**: Root + P5
- **Character**: Neutral, heavy, open — the backbone of metal register
- **Use**: Riff anchors, unison layers with bass, DFAM accent roots
- **Rev2 voicing**: Two notes, stacked — leave octave doubling to oscillator spread

### Minor Triad
- **Intervals**: Root + m3 + P5
- **Character**: Dark, grounded, familiar
- **Use**: Foundation for most harmonic sections
- **Rev2 voicing**: Root position or first inversion; spread via detune for weight

### Minor 7th
- **Intervals**: Root + m3 + P5 + m7
- **Character**: Dark with motion, jazz-adjacent heaviness
- **Use**: Sustained pads, transitional moments
- **Rev2 voicing**: Close voicing on Layer A; m7 on Layer B for depth

### Diminished Triad
- **Intervals**: Root + m3 + d5 (tritone)
- **Character**: Unstable, tense, threatening
- **Use**: Tension moments, chromatic passing chords
- **Rev2 voicing**: Keep tight — spread reduces the instability

### Fully Diminished 7th
- **Intervals**: Root + m3 + d5 + d7 (every m3)
- **Character**: Maximum tension, symmetric, unsettling — same chord every 3 frets
- **Use**: Breakdown sections, horror textures
- **Take 5 voicing**: Excellent — 4-note chord fits 4-voice polyphony cleanly

### Augmented Triad
- **Intervals**: Root + M3 + A5
- **Character**: Unresolved, floating, forward motion without destination
- **Use**: Pre-drop suspense, transitional chords
- **Rev2 voicing**: Layer B shifted up a half step for slow modulation effect

### Flat-II Major (Neapolitan)
- **Intervals**: ♭II root + M3 + P5
- **Character**: Dark, dramatic, "heavy" motion — classic Phrygian move
- **Use**: Primary harmonic movement in Phrygian-based songs
- **Example in A Phrygian**: B♭ major → A minor = the signature iron-static move
- **Rev2 voicing**: Let the ♭II sit on downbeat, resolve to i

### Minor 9th
- **Intervals**: Root + m3 + P5 + m7 + M9
- **Character**: Lush darkness, cinematic
- **Use**: Atmospheric pads, intro/outro layers
- **Rev2 voicing**: Omit the 5th in tight voicings; use Layer B for the 9th

---

## Quartal & Quintal Voicings

Stacking 4ths or 5ths instead of 3rds — no obvious major/minor quality, open and modern.

- **Quartal**: A–D–G–C (all perfect 4ths)
- **Quintal**: A–E–B–F# (all perfect 5ths)
- **Character**: Ambiguous, electronic, cold — sounds machine-made
- **Use**: Pads that need to hang without committing to tonal center
- **Rev2 voicing**: Arpeggiator across quartal stack at low rate = texture

---

## Tritone Substitution

Replace any dominant chord with the dominant a tritone away.
- **Example**: G7 → D♭7 (or D♭ major)
- **Character**: Unexpected, jarring, machine-like motion
- **Use**: Add unpredictability to otherwise predictable progressions
- **Rev2 patch note**: Works best with a stabby envelope — short A, short D

---

## Progressions for Heavy Electronic Context

### Phrygian vamp (IRON STATIC default)
```
i — ♭II — i — ♭II
```
In A Phrygian: `Am — B♭ — Am — B♭`

### Phrygian modal climb
```
i — ♭VII — ♭VI — ♭VII
```
In A Phrygian: `Am — G — F — G`

### Diminished tension build
```
i — i — vii° — ♭II
```
Resolves back to i with maximum tension via the diminished passing chord.

### Locrian collapse (maximum instability)
```
i° — ♭II — i°
```
The i chord itself is diminished — use only in breakdown / noise sections.

### Dorian lift (emotional release)
```
i — IV — ♭VII — i
```
The major IV in Dorian is the "hope" chord — use for a brief lift before returning to darkness.

---

## Voicing Notes for the Rig

| Instrument | Max Voices | Best Chord Types |
|---|---|---|
| Rev2 Layer A | 8 | Full 4-note chords, dense pads |
| Rev2 Layer B | 8 | Counter-voicing, inversions, extensions |
| Take 5 | 5 | Diminished 7ths (4 notes), triads + doubling |
| Subharmonicon | 2 VCOs + 4 subs | Power chords, octave drones |
| Minibrute 2S | 1 (mono) | Root/bass notes only |
| Pigments | Poly (software) | Full chord textures, spreads, evolving pads |
