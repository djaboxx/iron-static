# Audio Generation Spec: ethereal evolving pad

**Song**: rust-protocol  
**Date**: 2026-04-24  

---

## GENERATION PROMPT

At 95 BPM, generate an ethereal, slowly morphing pad in A Phrygian Dominant. The texture should be airy, spectral, and unsettling, evoking a sense of corrosive decay and unresolved tension, reflecting the "Rust Protocol" concept. Incorporate subtle industrial grit and granular shimmer, akin to Nine Inch Nails' atmospheric depth and The Haxan Cloak's evolving dread. This electronic texture should have a restrained energy, suitable for a ghost-like background element. The sound should be designed for an 8-bar loop, allowing for subsequent chopping into distinct rhythmic slices.

## TECHNICAL PARAMETERS

-   BPM: 95.0
-   Key centre: A Phrygian Dominant (A-Bb-C#-D-E-F#-G)
-   Suggested duration: 8-bar loop (approx. 20 seconds)
-   Time signature: 4/4
-   Frequency focus: Mid-range and high-frequency dominant, with a subtle low-mid rumble for atmospheric weight.
-   Stereo field: Wide and subtly animated, with slow LFO modulation on panning for spectral movement.

## HARDWARE PARALLEL

**Arturia Pigments**

-   **Engines:** Utilize two **Granular Engines** processing a metallic, scraping, or decaying sample (e.g., "scraping metal" as per the brainstorm). Alternatively, one **Wavetable Engine** with an evolving, spectral waveform and a **Granular Engine** layered beneath.
-   **Oscillators:** Granular engines should have varying `Grain Density`, `Spread`, and `Pitch Randomness` for organic, evolving texture. Ensure slight detuning between engines for width.
-   **Filter:** A gentle **Low-Pass Filter** (e.g., Multi-Mode or Formant filter for character) with a high `Resonance` setting, slowly modulated by a dedicated **LFO** (e.g., triangle wave, 1/4 or 1/2 bar rate) to create subtle, breathing sweeps. Filter `Cutoff` should be set relatively high to retain airiness.
-   **Envelopes:** Amp Envelope with a long `Attack` (5-8 seconds), full `Sustain`, and a long `Release` (5-10 seconds) to ensure a continuous, morphing presence.
-   **Modulation:** Multiple slow **LFOs** are critical:
    -   LFO 1 (slow random or sine): Granular `Position` or Wavetable `Position` for continuous evolution.
    -   LFO 2 (slow sine): Filter `Cutoff` and `Pan` position for subtle stereo movement.
    -   LFO 3 (very slow, subtle): Fine-tune `Pitch` on one engine for microtonal drift.
-   **FX:** Generous `Reverb` (large hall, long, dark decay) and a subtle, diffused `Delay` to enhance the ethereal quality. Use a `Bitcrusher` or `Distortion` with low mix and high drive to introduce controlled industrial grit.

## INTEGRATION NOTES

This pad functions as the underlying atmospheric tension, a "corrosive texture bed" that provides the sense of decay central to "Rust Protocol." It should never assume a leading role. Frequentially, it must clear the path for core elements: filter out frequencies below 80Hz to avoid crowding the Subharmonicon and Minibrute 2S bass, and carve out space in the 150-300Hz range to maintain punch from the Digitakt's kick and snare. Its high-frequency content should be carefully managed to allow the Minibrute 2S lead to cut through.

As per the arrangement blueprint for "Tetanus Pulse," this element should subtly enter during the **Build** section, becoming more prominent as the "Pigments granular pad" in the **Breakdown** where the Minibrute lead is absent. It will then return, potentially intensified or with an additional layer of distortion, during the **Climax** to add density and further the sense of overwhelming unease.

## IRON STATIC FIT

HIGH. This element perfectly aligns with the "corrosive, inevitable" mood, directly addressing the "granular texture bed" requirement for Pigments in the brainstorm, and embodying the "industrial texture" influence from Nine Inch Nails and The Haxan Cloak.