# Arturia Pigments

**Type:** Software Polyphonic Synthesizer (VST3 / AU)  
**Manufacturer:** Arturia  
**Version in use:** 7.0  

---

## Role in IRON STATIC

Pigments is the primary soft synth in the rig — used for dense pads, modulated leads, and evolving textures. It appears on multiple tracks in the Ventura project. Its extreme modulation depth (4+ mod sources per signal path) makes it ideal for the band's heavy, machine-driven aesthetic.

## MIDI Assignment

| Purpose | Channel |
|---|---|
| Default / Session | 8 |

Pigments responds to both MIDI CC and NRPN for parameter control. See `database/midi_params/pigments.json` for the full parameter map.

## Key Features

- **4 oscillator engines** (virtual analog, wavetable, harmonic, sample) — mix and chain two at a time
- **2 filter slots** (multiple topologies including ladder, MS-20, SEM, Buchla-style)
- **Advanced modulation matrix** — up to 5 modulation routes per module, including function generators, randomizers, MIDI sources
- **Macro controls** — 4 macros mappable to any parameter, ideal for Digitakt MIDI CC automation
- **MPE support** — per-note pitch, pressure, slide
- **Sequencer / Arpeggiator** — 32-step internal sequencer
- **Effects chain** — chorus, reverb, delay, distortion, EQ per patch

## Observed Usage in Ventura Project

- **Track 2-Pigments**: Single Pigments instance; mapped control: `F1 Cutoff`
- **Track 5-Pigments**: Pigments + ShimmerVerb; mapped controls include DELAY/FEEDBACK/level params
- **Track 6-Pigments**: Pigments + Waves H-Delay + H-Reverb + Ableton LFO; mapped `F2 Cutoff`, `F2 FM Amount`

## File Structure

```
instruments/arturia-pigments/
├── README.md           — this file
├── manuals/
│   └── Pigments_Manual_7_0_0_EN.pdf
└── presets/
    └── raw/            — exported .pgtx preset files (Pigments native format)
```

## Links

- Manufacturer page: https://www.arturia.com/products/software-instruments/pigments/overview
- Manual (v7.0): https://dl.arturia.net/products/pigments/manual/pigments_Manual_7_0_0_EN.pdf
- MIDI CC/NRPN reference: `database/midi_params/pigments.json`
