# Production Notes — IRON STATIC

Mixing, arrangement, and production knowledge accumulated during sessions.

---

## Frequency Map for the Rig

Each instrument should own a primary frequency zone to avoid mud:

| Zone | Hz Range | Primary Owner | Secondary |
|---|---|---|---|
| Sub | 20–60 Hz | Subharmonicon | DFAM kick |
| Bass | 60–200 Hz | Minibrute 2S | Rev2 Layer B |
| Low Mid | 200–600 Hz | Rev2 chords | Digitakt samples |
| Mid | 600–2kHz | Take 5 leads | Rev2 Layer A |
| Upper Mid | 2–6kHz | Minibrute 2S lead | Take 5 |
| High | 6–16kHz | Digitakt hi-hats | |
| Air | 16kHz+ | Reverb tails | |

**Avoid**: Rev2 Layer A and Take 5 competing in the same 1–3kHz range without EQ carving.

---

## Arrangement Architecture

### Song Section Templates

**Intro**: Stripped. Subharmonicon drone + sparse Digitakt pattern. Build anticipation.

**Verse**: Kick + bass (Minibrute 2S) + one harmonic layer (Rev2 or Take 5). Leave space.

**Pre-chorus**: Add second harmonic layer. Increase hi-hat density. Raise filter on Rev2 pad.

**Chorus/Drop**: Full rig. Digitakt full pattern, Rev2 chords + Take 5 lead + DFAM accents + Sub.

**Breakdown**: Remove everything except one element (drone, kick only, bass only). Maximum tension.

**Build**: Add layers one at a time, 4 or 8 bars each. Digitakt conditional trigs reveal new patterns.

**Outro**: Mirror the intro. Dissolve layers in reverse order. End on drone.

---

## Dynamics Principles

1. **Contrast creates impact**: The drop hits harder if the section before it is emptier.
2. **Three layers maximum** in any section to avoid mud (except the climax).
3. **One thing moves at a time**: If the filter sweeps, the pitch should stay. If the pattern changes, the texture should hold.
4. **Use negative space**: A measure with only kick and sub is more powerful than adding more.

---

## Digitakt as Arrangement Tool

The Digitakt's **pattern chains** allow arranging a full song by chaining patterns A01 → A02 → A03 etc. Plan song sections as Digitakt patterns:

| Pattern | Section | Notes |
|---|---|---|
| A01 | Intro | Sparse, kick only + Subharmonicon clock |
| A02 | Verse | Kick + snare + bass MIDI |
| A03 | Pre-chorus | Add hi-hats, reveal chord MIDI |
| A04 | Chorus | Full pattern, all tracks active |
| A05 | Breakdown | Kick only, long trig conditions |
| A06 | Build | Accumulating conditional trigs |
| A07 | Chorus (reprise) | Same as A04, more p-locks |
| A08 | Outro | Mirror of A01, slower filter |

---

## Ableton Session Template

Structure all sessions the same way for consistency:

```
[IRON STATIC Session Template]
├── DRUMS
│   ├── Digitakt (Audio In L/R) → Drum bus
│   └── DFAM (Audio In) → Drum bus
├── BASS
│   └── Minibrute 2S (Audio In) → Bass bus
├── SYNTHS
│   ├── Rev2 (Audio In L/R) → Synth bus
│   └── Take 5 (Audio In L/R) → Synth bus
├── SUB / DRONES
│   └── Subharmonicon (Audio In) → Sub bus
├── MASTER BUS
│   └── Glue compressor + Limiter
└── MIDI OUT
    ├── MIDI 1: Digitakt Auto-Ch
    ├── MIDI 2: Rev2 Layer A
    ├── MIDI 3: Rev2 Layer B
    ├── MIDI 4: Take 5
    ├── MIDI 5: Subharmonicon
    ├── MIDI 6: DFAM
    └── MIDI 7: Minibrute 2S
```

Template location: `ableton/templates/`

---

## Mix Reference Targets

| Aspect | Target |
|---|---|
| LUFS (integrated) | -14 LUFS (streaming) / -10 LUFS (louder masters) |
| Peak | -1 dBTP |
| Kick transient | Should punch through in mono check |
| Low end | Check in mono: sub and bass should not cancel |
| Reference tracks | See `audio/references/` |
