# Rhythm Patterns — IRON STATIC Reference

Practical rhythmic vocabulary for heavy electronic music. Patterns are notated as 16-step grids unless noted.

`X` = hit, `.` = rest, `x` = soft hit (lower velocity)

---

## Core Drum Patterns

### Standard Heavy 4/4
```
KICK:  X . . . X . . . X . . . X . . .
SNARE: . . . . X . . . . . . . X . . .
HAT:   x . x . x . x . x . x . x . x .
```
The foundation. Use parameter locks on the hat for variation.

### Half-time Feel (common in heavy/doom-influenced sections)
```
KICK:  X . . . . . . . X . . . X . . .
SNARE: . . . . . . . . X . . . . . . .
HAT:   x . x . x . x . x . x . x . x .
```
Snare on beat 3 only = massive weight and space.

### 7/8 (machine-breaking feel)
16-step grid representing 7/8: treat 14 steps as one bar (or 7 eighth notes)
```
KICK:  X . . X . . X . . X . . X . .
SNARE: . . . . X . . . . . X . . .
HAT:   x x . x x . x x . x x . x x .
       [1 2 3|4 5 6|7]
```

### Euclidean Hi-Hat — E(5,16): 5 hits over 16 steps
```
HAT:   X . . X . . X . . X . . X . . .
```
Feels syncopated and hypnotic. Great for industrial textures.

### Euclidean Kick — E(3,8): 3 hits over 8 steps (AKA the "clave")
```
KICK:  X . . X . . X .
```

---

## Polyrhythm Templates

### 3-against-4 (Digitakt + Subharmonicon)
Digitakt runs a 4-beat pattern. Subharmonicon sequencer set to 3-step cycle with clock/3.
```
Digitakt 4/4: X . . . X . . . X . . . X . . .
Sub 3-step:   X . . X . . X . . X . . X . . .
              ↑sync                   ↑resync (after 12 beats)
```

### 5-against-4
Digitakt 16-step. Layer a 20-step sequence (5 groups of 4) on Rev2 MIDI track:
```
Digitakt:  |1 2 3 4|1 2 3 4|1 2 3 4|1 2 3 4|
Rev2:      |1 2 3 4 5|1 2 3 4 5|1 2 3 4 5|1 2|
           (resync every 20 beats / 5 bars)
```

### Digitakt Conditional Trig Combos for Polyrhythm
- Track 1 (Kick): 16-step, normal trigs
- Track 2 (Accent): `1:4` condition on step 1 = fires every 4th loop = 64-step cycle
- Track 3 (Hi-hat): `%50` on certain steps = 50% chance = probabilistic variation

---

## Signature IRON STATIC Grooves

### "Machine Heartbeat" — slow, heavy, mechanical
```
BPM: 95
KICK:  X . . . . . . X . . . . X . . .
SNARE: . . . . . . . . X . . . . . . .
HAT:   . . X . . . X . . . X . . . X .
SUB:   Long drone, slow filter sweep from Subharmonicon
```
Notes: Half-time snare, displaced kick on beat 2.5, euclidean hat.

### "Static Surge" — driving, urgent, NIN-adjacent
```
BPM: 130
KICK:  X . X . X . . . X . X . X . . .
SNARE: . . . . X . x . . . . . X . x .
HAT:   X X X X X X X X X X X X X X X X  (all 16ths, velocity variation)
```
Notes: Dense straight 16th hats at lower velocity; ghost snares (x) on off-beats.

### "Polyrhythm Engine" — 7/8 with cross-pattern bass
```
BPM: 120 (in 7/8)
KICK:  X . . X . . X (7 steps)
BASS:  Minibrute 2S 8-step sequencer against Digitakt's 7/8 = constant drift
```
