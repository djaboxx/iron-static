# Audio Generation Spec: corroded texture

**Song**: rust-protocol  
**Date**: 2026-04-24  

---

## GENERATION PROMPT

At 95 BPM, generate a low-end dominant, unsettling industrial texture in an A Phrygian Dominant mood, designed for granular manipulation into pads. Imagine a slowly grinding metallic erosion, imbued with a deep, resonant sub-bass undertow, reminiscent of Nine Inch Nails' textural depth and Modeselektor's physical bass pressure. Incorporate the sound of decaying steel, heavily processed field recordings of scraping and tearing metal, and a pervasive dread akin to The Haxan Cloak's atmospheric noise layers. The sound should feel jagged, corrosive, and unstable, built from both digital synthesis and heavily filtered noise, leaving distinct sonic space for percussive and melodic elements while maintaining a "contained" aggression, embodying IRON STATIC's heavy, weird, electronic, and intentional aesthetic.

## TECHNICAL PARAMETERS

- BPM: 95.0
- Key centre: A (implied by the Phrygian Dominant scale's harmonic tension)
- Suggested duration: 16 bars (to allow for sufficient evolution and subsequent chopping)
- Time signature: 4/4
- Frequency focus: Sub/low-mid dominant (20-250 Hz) for the foundational rumble, with high-frequency metallic transients and scraping details above 5kHz to provide grit and definition.
- Stereo field: Wide, with slow, evolving LFO-driven pan modulation to create internal movement, ensuring the sub-bass remains a strong mono presence.

## HARDWARE PARALLEL

**Arturia Pigments** is the primary instrument for this, as it's the named "granular texture bed" in the brainstorm.

*   **Engine 1 (Sample/Granular):** Load raw, metallic-sounding field recordings (scraping metal, creaking industrial structures, distant impacts). Set to Granular mode: long grain size (200-500ms), low density (10-20%), high random spread for pitch and pan, slow modulation of "position" with a multi-stage envelope or a very slow, free-running LFO (rate ~0.1-0.5 Hz).
*   **Engine 2 (Wavetable):** Select a harsh, digital wavetable or one with clear metallic harmonics. Modulate wavetable position slowly (~0.2-0.8 Hz) to create a subtle, evolving timbre. Blend this subtly with Engine 1.
*   **Filter:** One multimode filter, set to Low-Pass, cutoff around 1-2 kHz, high resonance (approaching self-oscillation). Modulate the cutoff with a slow, attenuated LFO (e.g., LFO 2 with a triangle shape, depth 10-15%).
*   **FX Rack:**
    *   **Multiband Compressor:** To glue the low-end and high-end texture.
    *   **Bitcrusher/Distortion:** Placed before reverb, set to a subtle but audible level for added grit and harmonic instability.
    *   **Delay:** A diffuse, modulated delay (e.g., Tape Delay) with medium feedback, short delay time, and high wetness.
    *   **Reverb:** A large, dark hall or shimmer reverb with a long decay time (6-8 seconds), adding a vast, decaying sense of space.

*   **Fallback/Layering:**
    *   **Elektron Digitakt:** Load long, decaying samples of resonant metal objects or processed white noise. Apply extreme bit reduction, overdrive, and use LFOs on sample start/end points, filter cutoff, and pan to create evolving noise layers. Route to a long, dark internal reverb.
    *   **Arturia Minibrute 2S:** Noise output fed through the Steiner-Parker filter in high-pass mode, with high resonance. Slowly sweep the cutoff manually or with a very slow LFO. Brute Factor engaged at 20-30% for subtle saturation and instability.

## INTEGRATION NOTES

This "corroded texture" acts as a foundational atmospheric and rhythmic element, emphasizing the "Tetanus Pulse" concept. It directly functions as the "Pigments granular pad" specified in the brainstorm.

*   **Relationship to other elements:** It provides a bed of sonic erosion, supporting the underlying groove without directly participating in the main beat. Its sub-bass component should be carefully mixed to not clash with the Subharmonicon's melodic drone or the DFAM's low-end percussion. The metallic high-end should complement, rather than compete with, the Minibrute 2S lead's serrated edge.
*   **Frequency Avoidance:** Strictly avoid the fundamental frequencies of the Digitakt's kick drum (60-80 Hz) and the Minibrute's lead. Ensure its sub-bass undertow (below 60 Hz) is clean and distinct from the Subharmonicon's focused melodic low end. The low-mids (250-800 Hz) should generally be kept clear to allow the main rhythmic and melodic elements to cut through.
*   **Arrangement Placement (referencing brainstorm):**
    *   **Intro:** Introduced very subtly, almost imperceptibly, as a faint, distant hum or rumble, underlying the "I-beam" reverb tail.
    *   **Build:** Fades in slowly, increasing its presence as a dense, low-end drone under the Subharmonicon.
    *   **Drop:** Remains as a background element, providing weight and grit, possibly with automated filter sweeps to accentuate certain impacts.
    *   **Breakdown:** **This is its most prominent section.** The Pigments granular pad enters prominently here, using the scraping metal source, before its pitch automation downward.
    *   **Climax:** Returns at full intensity, adding to the chaotic wall of sound, with more high-frequency aggression and unstable elements.
    *   **Outro:** Decays alongside the "I-beam" tail, leaving a lingering sense of corrosive aftermath.

## IRON STATIC FIT

HIGH. It perfectly embodies the "industrial texture" and "heavy, weird, electronic, intentional" aesthetic, directly supporting the "corrosion as a design feature" concept of "Tetanus Pulse" as outlined in the brainstorm.