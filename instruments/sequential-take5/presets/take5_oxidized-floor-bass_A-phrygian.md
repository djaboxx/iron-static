# Patch: Oxidized Floor Bass
**Instrument**: Sequential Take 5  
**Created**: 2026-04-23  
**Song**: Rust Protocol (A Phrygian, 95 BPM)  
**MIDI Channel**: 4  
**Description**: Heavy industrial sub bass. Fat saw + sub oscillator foundation, tightly filtered with a punchy snap-open envelope. Sits below the Digitakt kick without competing with the DFAM. Mod wheel opens the filter for live expressiveness.

---

## Concept

Two detuned saws in unison + sub oscillator. The filter is almost closed at rest — the envelope punches it wide open on every attack (instant snap), then clamps back down fast. Result: that classic "thwack-thud" heavy bass where you feel the note attack but the sub sustains underneath. Very Lamb of God low-end meets NIN industrial floor.

---

## Oscillators

### OSC 1
| Parameter | Value | Notes |
|-----------|-------|-------|
| Octave | 16' | Fat but defined — not so low it gets muddy |
| Shape | Saw | Maximum harmonics for filter to sculpt |
| Level | 80% (knob at ~4 o'clock) | Primary source |

### OSC 2
| Parameter | Value | Notes |
|-----------|-------|-------|
| Octave | 16' | Same octave as OSC 1 |
| Fine Tune | +7 cents (knob slightly right of center) | Slight chorus thickens without detuning |
| Shape | Saw | Matches OSC 1 |
| Key Track | On | Filter follows pitch up the neck |
| Level | 50% (knob at ~2 o'clock) | Thickens without muddying |

### Sub Oscillator (tracks OSC 1, one octave down)
| Parameter | Value |
|-----------|-------|
| Level | 80% (knob at ~4 o'clock) |

### Noise
| Parameter | Value |
|-----------|-------|
| Level | 0 | Clean — save noise for pads |

---

## Filter

| Parameter | Value | Notes |
|-----------|-------|-------|
| Cutoff | 35% (~10 o'clock) | Mostly closed at rest — envelope does the work |
| Resonance | 25% (~9:30) | Character without screaming |
| Env Amount | 70% (~3:30) | Big punch — envelope opens filter wide on attack |
| Key Amount | On | Filter cutoff tracks keyboard pitch |
| Audio Mod | 0 | Off |

---

## Envelope 1 (Filter)

| Segment | Value | Notes |
|---------|-------|-------|
| Attack | 0 (fully left) | Instant snap — filter opens on impact |
| Decay | 45% (~1:30) | ~150ms at 95 BPM — closes fast for punch |
| Sustain | 20% (~9 o'clock) | Drops back near-closed; the sub holds underneath |
| Release | 15% (~8:30) | Quick tail |

---

## Envelope 2 (Amp)

| Segment | Value | Notes |
|---------|-------|-------|
| Attack | 0 (fully left) | Instant — tight, punchy |
| Decay | 55% (~2 o'clock) | Medium, lets note bloom |
| Sustain | 75% (~3:30) | Holds well for sustained root notes |
| Release | 20% (~9 o'clock) | Clean release, no long bleed |

---

## LFO 1

| Parameter | Value | Notes |
|-----------|-------|-------|
| Shape | Triangle | Smooth |
| Rate | 8% (fully left, ~8 o'clock) | Very slow — barely breathing |
| Amount | 15% | Subtle filter movement, not modulation |
| Destination | Filter Cutoff (via mod matrix slot 1) | |

---

## Modulation Matrix

| Slot | Source | Destination | Amount | Notes |
|------|--------|-------------|--------|-------|
| 1 | LFO 1 | Cutoff | +15% | Slow breath on filter |
| 2 | Mod Wheel | Cutoff | +40% | Performance: open filter with wheel for riff emphasis |
| 3 | Velocity | Env 1 Amount | +25% | Hit harder → bigger filter snap |

---

## Effects

| Parameter | Value | Notes |
|-----------|-------|-------|
| FX Type | Reverb | Subtle room — not wet |
| FX Mix | 10% (~8:30) | Just enough air |
| Reverb Size | 30% | Small-medium room |
| Reverb Decay | 25% | Short — keeps the low end tight |
| Reverb Pre-Delay | 10% | Small pre-delay keeps the transient dry |

---

## Glide

| Parameter | Value | Notes |
|-----------|-------|-------|
| Glide | 5% (~8 o'clock) | Micro-portamento for legato slides |
| Mode | Legato | Only glides when notes overlap — staccato stays punchy |

---

## Playing Notes

- **Root riff**: Play root A (any register at 16' octave) — should feel like a floor vibration
- **Mod wheel at 0**: Tight, closed attack. Mod wheel up: open and growling for fills
- **For harder Phrygian bite**: try the ♭II (B♭) → root resolution with glide engaged
- **Layer with**: Digitakt kick on beat 1 — the Take 5 sub fills the space between kicks. DFAM can play complementary higher-register percussion without collision since its filter is tuned higher

---

## Variations

| Variation | Change | Character |
|-----------|--------|-----------|
| More industrial | Raise resonance to 50%, raise filter env amount to 85% | Acid-adjacent filter snap |
| Smoother drone | Filter cutoff 60%, env amount 20%, sustain 90% | Sustained background sub |
| Grindy lead bass | Switch both OSCs to Pulse, pulse width ~45%, raise OSC 2 detune to +15 cents | Mid-forward growl |
