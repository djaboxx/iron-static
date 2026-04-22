# Synthesis Notes — IRON STATIC Sound Design Reference

Practical synthesis techniques mapped to the IRON STATIC rig. Organized by sound goal.

---

## Bass Sounds

### Analog Sub Bass (Minibrute 2S)
- **OSC**: Sawtooth, sub oscillator -1 octave, noise off
- **Brute Factor**: 0 (off) to 9 o'clock for subtle warmth
- **Filter**: LP, cutoff at 10 o'clock, resonance low
- **Env 1 (AMP)**: Attack 0, decay medium, sustain full, release short
- **Env 2 (MOD) → Filter**: Small positive amount for slight pluck on attack
- **Key**: Keep cutoff dark — sub bass should feel more than be heard distinctly

### Aggressive Mono Bass (Minibrute 2S with Brute Factor)
- **OSC**: Sawtooth + sub, Ultrasaw at 9 o'clock
- **Brute Factor**: 12–2 o'clock range for aggression
- **Filter**: LP, cutoff 11 o'clock, resonance at 10 o'clock
- **Tip**: Brute Factor feedback creates a grinding, almost distorted tone — essential for metal bass

### Sequential Sub Bass (Rev2 Layer B)
- **OSC A**: Sawtooth, octave -2
- **OSC B**: Sawtooth, slight detune
- **Filter**: Low cutoff, low resonance — warm and supportive
- **Use**: When you need a polyphonic bass layer under Rev2 Layer A chords

---

## Lead Sounds

### Screaming Mono Lead (Minibrute 2S)
- **Filter**: HP mode, cutoff at 12–2 o'clock
- **Resonance**: High (12–2 o'clock) — the Steiner-Parker HP resonance is unique and cutting
- **OSC**: Sawtooth + square mix, no sub
- **Brute Factor**: Moderate for edge
- **Portamento**: Add glide on the sequencer steps for expressive lines

### Detuned Poly Lead (Rev2 Layer A)
- **OSC A**: Sawtooth
- **OSC B**: Sawtooth, detune +5 to +15
- **Filter**: LP, cutoff at 12 o'clock, resonance 10–11
- **Mod matrix**: LFO1 → Filter cutoff, slow rate (synced to 1/8 or 1/4)
- **Character**: Wide, moving, fills space in the upper mid register

---

## Pad Sounds

### Industrial Texture Pad (Rev2 Layer A)
- **OSC A**: Pulse wave, PWM from LFO
- **OSC B**: Sawtooth, tune +7 (perfect 5th) for added mass
- **Filter**: LP, slow envelope opening (attack ~800ms), resonance low
- **Mod**: LFO2 → Pan (slow), LFO1 → Filter cutoff (very slow)
- **Use**: Atmospheric under a groove; should breathe slowly in the background

### Drone (Subharmonicon)
- **VCO 1**: Tune to root note
- **Sub 1**: Division 2 (one octave down)
- **Sub 2**: Division 3 (perfect 5th down, approximately)
- **Filter**: Open, slow envelope on VCF
- **Sequencer**: All four rows set to same pitch = pure drone with rhythmic accents from clock
- **Use**: Underpinning long sections; can be slowly pitch-shifted by retuning VCO between patterns

---

## Percussion Sounds

### Moog Kick (DFAM)
- **VCO 1 Pitch**: Lowest setting; ENV amount max → pitch falls from attack
- **VCO 2 Pitch**: Same as VCO 1 (or +5–10 for additional tone)
- **FM**: Low amount
- **Filter**: Open cutoff, high resonance = more tone in the kick body
- **Env Attack**: 0; Decay: short-medium (~9–11 o'clock)
- **VCA Decay**: Match envelope

### Industrial Clang (DFAM)
- **VCO 1**: High pitch (2–3 o'clock)
- **VCO 2**: Slightly different high pitch (for beating/dissonance)
- **FM Amount**: Medium-high → metallic character
- **Filter**: LP, high resonance (self-oscillation area), medium cutoff
- **Env Decay**: Short = clang; medium = gong-like ring

---

## Noise / Texture

### White Noise Layer (Minibrute 2S or DFAM)
- Use noise oscillator mixed low into any sound for added air and texture
- In filter HP mode (Minibrute 2S): noise + HP = breathy, hissy texture — like industrial steam

### Oscillator Sync (Rev2)
- **OSC A** hard synced to **OSC B**: creates nasal, aggressive tones as OSC B pitch sweeps
- Sweep OSC B pitch from LFO or MIDI CC for a characteristic "sync sweep" effect
- Very NIN-adjacent

---

## Processing Notes (Ableton)

These are processing approaches applied in Ableton, not on the hardware:
- **All mono synths** (Minibrute, DFAM) → Ableton: Utility (make stereo with Haas delay ~10–20ms)
- **Rev2 pads** → Light reverb (large hall, low mix ~15%), long pre-delay
- **Digitakt kick** → Ableton Drum Rack bus: Glue Compressor, Saturator for harmonic content
- **Sub frequencies** (Subharmonicon) → HPF at 30Hz to remove sub-sub rumble; Multiband comp for control
