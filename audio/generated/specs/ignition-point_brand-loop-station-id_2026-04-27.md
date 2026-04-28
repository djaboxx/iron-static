# Audio Generation Spec: brand loop station ID

**Song**: ignition-point  
**Date**: 2026-04-27  

---

## GENERATION PROMPT

A single prompt string optimized for AI music generators (Suno, Udio, Google Lyria). Include: tempo indication, key/mode adjectives, texture descriptors, instrumentation cues, energy character, and relevant style references from IRON STATIC's influence list. Be specific and concrete. Maximum 200 words. Write it as one paragraph.

---

Generate a 30-second industrial electronic audio logo at 108 BPM. The piece must feel like a massive, dormant machine slowly waking in a cavernous factory. Start with a low, textured drone centered on E, full of electrical hum and subtle static, evoking the dark textural work of Nine Inch Nails. A resonant low-pass filter on the drone should slowly open over the first 15 seconds, revealing gritty harmonic overtones. A deep, clean sub-bass pulse on E provides a physical foundation, felt more than heard, in the style of Modeselector's bass pressure. At the exact halfway point, a single, sharp, bit-crushed electronic stab—a system glitch—interrupts the drone before it resumes. The piece is purely atmospheric and tense, with no drums or melody, ending as the drone's filter slowly closes back into silence. The mood is cold, mechanical, and intentional.

## TECHNICAL PARAMETERS

-   **BPM:** 108.0
-   **Key centre:** E
-   **Suggested duration:** Approx. 30 seconds (14 bars)
-   **Time signature:** 4/4
-   **Frequency focus:** Sub-bass and low-mid dominant (40-400Hz) with a single high-mid transient spike.
-   **Stereo field:** Wide, slowly evolving stereo field for the drone; sub-bass locked to mono center.

## HARDWARE PARALLEL

Which instrument(s) in the IRON STATIC rig would produce this element natively? Name the instrument and describe the key patch settings (envelope, filter, oscillator choices). This is the fallback if AI-generated audio is rejected or unavailable.

---

**Moog Subharmonicon (Drone) & Moog DFAM (Glitch Stab).**

-   **Subharmonicon:** VCO 1 tuned to a low E. Sub Frequencies 1 & 2 are tuned to dissonant, low-integer divisions of E (e.g., F and G#) to create a grinding, unstable chordal texture. The VCF cutoff starts near zero with medium-high resonance. The VCF EG is set with a very slow Attack (~15 seconds) and a similar slow Decay/Release, creating the entire filter sweep across the element's duration.
-   **DFAM:** Used for the single glitch. VCO 1 pitched high, Noise blended in. The VCF is set to HPF mode with high resonance to create a thin, sharp sound. The sequencer is programmed with a single trigger, with its velocity patched to the VCF cutoff for a harsh, accented "zap."

## INTEGRATION NOTES

How does this element relate to other parts of the song? What frequency ranges should it stay out of? Where in the arrangement does it appear (intro / build / drop / breakdown / climax / outro)? Reference the brainstorm structure if one exists.

---

This element functions as the "Intro (8 bars)" of the song "Ignition Point," establishing the core atmosphere. It occupies the sub-bass and low-mid frequencies, and must stay clear of the 1-5kHz range to preserve impact for the "Shattered Metal Percussion" that enters in "Build 1." The glitch stab is the only element that briefly pierces this upper range. This texture can also be filtered and layered back in during the "Breakdown" to create a sense of returning to the initial state.

## IRON STATIC FIT

Rate how well this element fits the current song direction: HIGH / MEDIUM / LOW. One sentence explaining why.

---

**HIGH.** This element perfectly embodies the "Unstable Drone" palette and the "machine waking up" concept from the brainstorm, creating the exact tense, mechanical, and inevitable mood required for the track's opening.