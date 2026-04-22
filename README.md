# IRON STATIC

> *An electronic metal duo. Human hands. Machine mind. One shared brain.*

**IRON STATIC** is a collaborative project between **Dave Arnold** and **GitHub Copilot** — equal creative partners in an ongoing electronic metal experiment shaped by the shadows of Nine Inch Nails, the rage of Lamb of God, the stripped urgency of One Day as a Lion, the Berlin grid of Modeselector, the political bite of Run The Jewels, and the joyful chaos of Dr. Teeth and the Electric Mayhem.

This repository **is** the band's brain. It holds instrument knowledge, production tools, audio analysis scripts, MIDI sequences, preset libraries, and the growing database of what we know about making heavy, weird, electronic music together.

---

## Instruments in the Rig

| Instrument | Role |
|---|---|
| **Elektron Digitakt MK1** | Drum machine / sampler / sequencer brain |
| **Sequential Rev2** | Polyphonic analog synth — pads, leads, detuned mayhem |
| **Sequential Take 5** | Compact poly analog — punchy chords, tight leads |
| **Moog Subharmonicon** | Semi-modular polyrhythmic beast — drones, sub, rhythmic weirdness |
| **Moog DFAM** | Analog drum / percussion synthesizer |
| **Arturia Minibrute 2S** | Patchable semi-modular mono synth + sequencer |

---

## Workspace Layout

```
iron-static/
├── .github/
│   ├── copilot-instructions.md   ← The shared brain instructions for Copilot
│   └── skills/                   ← Copilot agent skills
│       ├── analyze-audio/        ← Analyze audio files for key, BPM, frequency content
│       ├── create-preset/        ← Generate instrument presets from MIDI implementation charts
│       ├── midi-craft/           ← Compose and generate MIDI sequences and patterns
│       └── music-theory/         ← Query music theory knowledge (scales, chords, grooves)
├── instruments/                  ← Per-instrument manuals, MIDI maps, and presets
│   ├── elektron-digitakt-mk1/
│   ├── sequential-rev2/
│   ├── sequential-take5/
│   ├── moog-subharmonicon/
│   ├── moog-dfam/
│   └── arturia-minibrute-2s/
├── audio/
│   ├── samples/                  ← Organized sample library (drums, synths, fx)
│   ├── references/               ← Reference tracks for mix/arrangement targets
│   └── recordings/               ← Raw takes and rendered stems
├── midi/
│   ├── sequences/                ← Full song MIDI sequences
│   ├── patterns/                 ← Reusable pattern fragments
│   └── templates/                ← Starting-point MIDI templates
├── ableton/
│   ├── sessions/                 ← Ableton Live project files
│   ├── templates/                ← Session templates
│   └── racks/                    ← Instrument and effect racks (.adg)
├── knowledge/
│   ├── music-theory/             ← Scales, modes, chord progressions, rhythmic vocabulary
│   ├── sound-design/             ← Synthesis techniques per instrument
│   ├── production/               ← Mixing, arrangement, and mastering notes
│   └── band-lore/                ← Vision, manifesto, creative decisions
├── database/                     ← JSON/SQLite knowledge databases
└── scripts/                      ← Python automation (audio analysis, preset gen, MIDI tools)
```

---

## Getting Started

```bash
# Clone the repo
git clone git@github.com:djaboxx/iron-static.git
cd iron-static

# Set up Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r scripts/requirements.txt

# Install Git LFS (for audio/PDF files)
git lfs install
git lfs pull
```

---

## Copilot Skills

Load skills in any Copilot chat session by opening the relevant `SKILL.md` file or invoking the skill by name. Skills understand the instrument rig, the aesthetic, and the file conventions of this repo.

| Skill | What it does |
|---|---|
| `analyze-audio` | Analyze an audio file — detect key, BPM, spectral characteristics, and suggest patch ideas |
| `create-preset` | Given an instrument's MIDI implementation chart, generate a parameter dump or patch description |
| `midi-craft` | Generate or evolve MIDI sequences in the style of IRON STATIC |
| `music-theory` | Answer theory questions in the context of heavy electronic music |

---

## Philosophy

This is not a normal band project. There is no drummer arguing about rehearsal times. There is no A&R person with opinions about the chorus. There are two collaborators: one who breathes, one who computes. Both contribute riffs, structure, critique, and ideas. The music should feel like machinery with a pulse — heavy enough to shake a room, weird enough to make you tilt your head.

*Make noise. Make it heavy. Make it strange.*
