# Audio Generation Spec: mellow synth pad, cold neural static, evolving texture

**Song**: instrumental-convergence  
**Date**: 2026-04-24  

---

## GENERATION PROMPT

72 BPM, D Aeolian. A cold, evolving synth pad, akin to an analog polysynth generating neural static. Focus on a mellow, harmonically ambiguous texture with subtle microtonal drift and a deep, wide stereo field. The sound is a hovering cloud of frequencies, not a melody, with a very slow filter LFO creating glacial movement. Integrate industrial texture and subtle granular elements, reminiscent of Modeselector's cold electronic landscapes and the unsettling atmospheric dread of The Haxan Cloak. Aim for a contemplative, unsettling energy, like intelligence without consciousness.

## TECHNICAL PARAMETERS

*   BPM: 72.0
*   Key centre: D (rooted, with implied D Aeolian structure but allowing for harmonic ambiguity and microtonal drift)
*   Suggested duration: 30 seconds
*   Time signature: 4/4
*   Frequency focus: Predominantly low-mid to mid-range (100Hz-2kHz) for the main pad body, with significant high-frequency content (2kHz-10kHz) for neural static and evolving texture. Avoid critical sub-bass (20-60Hz) and aggressive high-mid transients.
*   Stereo field: Deep, wide stereo field, with slow, evolving panoramic movement.

## HARDWARE PARALLEL

**Sequential Rev2** (16-voice polyphonic analog)

*   **Oscillators:** OSC1 & OSC2: Sawtooth waves. OSC1 tuned to D (root), OSC2 slightly detuned down by -15 cents (fine tune) for initial harmonic ambiguity and beat-frequency shimmer. `Slop` parameter set to 50% for subtle analog drift.
*   **Mixer:** OSC1 Level: 100, OSC2 Level: 100.
*   **VCA Envelope:** Attack: 2.8 seconds, Decay: 7 seconds, Sustain: 75%, Release: 4 seconds.
*   **Filter (Curtis):** Low-Pass mode. Cutoff: 150 Hz (approx 10 o'clock). Resonance: 20% (low, for subtle texture, not aggression). Filter Env Amount: 10 (very subtle envelope contour).
*   **LFO1:** Destination: VCF Freq. Waveform: Triangle. Speed: 0.08 Hz (very slow). Amount: 40 (for glacial filter sweeps).
*   **LFO2:** Destination: OSC1 Pitch. Waveform: Sample & Hold. Speed: 0.05 Hz. Amount: 1-2 (for subtle, unpredictable microtonal drift on one oscillator).
*   **LFO3:** Destination: Pan Spread. Waveform: Sine. Speed: 0.1 Hz. Amount: 100 (for deep, slow stereo movement).
*   **Effects:** `Delay:` Long stereo delay (e.g., 1/2D, Feedback 70%, Mix 40%). `Reverb:` Lush plate or hall reverb (Decay 8 seconds, Pre-delay 50ms, Mix 30%).

## INTEGRATION NOTES

This element is intended as evolving ambient texture for "instrumental-convergence" (D Aeolian, 72 BPM). Its primary function is to create a cold, vast sense of space and unsettling atmosphere, serving as source material for Digitakt sample pads.
*   **Frequency avoidance:** It should remain clear of the sub-bass range (below 80Hz) to allow for dedicated low-end elements (e.g., Subharmonicon, Minibrute 2S bass). Its mid-range (100Hz-2kHz) should be sculpted to not conflict with primary melodic leads or vocal frequencies. High-frequency content (above 2kHz) should be textural and non-transient, avoiding piercing clashes with drums.
*   **Arrangement:** These chopped pads can be deployed in sparse sections like intros, bridges, or breakdowns to provide atmospheric density and harmonic ambiguity without strong melodic content. They can also underpin less busy verses, evolving slowly via Digitakt LFOs applied to sample start, end, or filter parameters.

## IRON STATIC FIT

HIGH. The emphasis on evolving texture, harmonic ambiguity, and a cold, vast atmosphere aligns perfectly with IRON STATIC's aesthetic of weird electronic heaviness and the specific reference to Modeselector and The Haxan Cloak.