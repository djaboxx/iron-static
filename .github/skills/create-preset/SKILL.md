---
name: create-preset
description: Generate, document, or reconstruct instrument presets for the IRON STATIC rig using MIDI implementation charts and panel-state notation.
argument-hint: "[instrument-slug] [preset-name] [optional: source=midi-chart|description|audio]"
user-invocable: true
disable-model-invocation: false
---

# Skill: create-preset

## What This Skill Does

Given an instrument and a sonic goal, this skill:
1. References the instrument's MIDI implementation chart (from the manual in `instruments/[slug]/manuals/`)
2. Generates a structured preset description — either as MIDI CC/NRPN parameter values, or as a panel-state document for non-memory instruments
3. Outputs the preset in the repo's standard format
4. Optionally suggests how the preset fits into the IRON STATIC aesthetic

## When to Use

- Creating a new patch for a specific sound goal ("I need a grinding, detuned poly lead on the Rev2")
- Documenting a panel state for the Subharmonicon, DFAM, or Minibrute 2S (patchable instruments with no memory)
- Reconstructing a sound from a recording or reference description
- Building a preset library for a specific song or session

## Instrument Capabilities

### MIDI-programmable (parameter dump / CC / NRPN):
- **Elektron Digitakt MK1** — SysEx pattern dumps, MIDI CC for performance params
- **Sequential Rev2** — NRPN for all 512 parameters per patch; full SysEx dumps
- **Sequential Take 5** — NRPN for patch parameters; SysEx dumps

### Panel-state only (document as human-readable patch sheets):
- **Moog Subharmonicon** — Document as: VCO tunings, subharmonic intervals, sequencer row values, patch cable list
- **Moog DFAM** — Document as: sequencer pitch/velocity rows, VCO settings, filter settings, envelope settings, patch cables
- **Arturia Minibrute 2S** — Document as: panel knob positions, patch matrix connections, sequencer pattern

## Preset File Formats

### MIDI-dumpable instruments (JSON):
```json
{
  "instrument": "rev2",
  "name": "Grind Lead",
  "description": "Detuned sawtooth lead with filter self-oscillation and slow PWM. For mid-forward aggressive parts.",
  "aesthetic_tags": ["aggressive", "lead", "mid-heavy"],
  "parameters": {
    "DCO_A_WAVE": 3,
    "DCO_A_DETUNE": 15,
    "FILTER_CUTOFF": 64,
    "FILTER_RESONANCE": 90,
    "ENV_FILTER_AMOUNT": 40,
    "AMP_ENV_ATTACK": 0,
    "AMP_ENV_DECAY": 45,
    "AMP_ENV_SUSTAIN": 80,
    "AMP_ENV_RELEASE": 20
  },
  "midi_channel": 2,
  "nrpn_dump": []
}
```

### Native Live devices in racks (JSON — pushable via apply-preset):
```json
{
  "instrument": "dfam-rack",
  "name": "DFAM Rack Rust Protocol",
  "description": "3-chain Collision rack for DFAM: membrane hit, tube tone, noise burst.",
  "aesthetic_tags": ["percussive", "industrial", "physical-model"],
  "target": {"track": "DFAM", "device": 0},
  "parameters": {},
  "chains": {
    "0": {
      "_name": "Hit",
      "Mallet Volume": 0.80,
      "Mallet Stiffness": 0.78,
      "Res 1 Type": 3,
      "Res 1 Tune": -24,
      "Res 1 Decay": 0.22
    },
    "1": {
      "_name": "Tone",
      "Res 1 Type": 6,
      "Res 2 On/Off": 1.0,
      "Res 2 Tune": -24
    },
    "2": {
      "_name": "Noise",
      "Mallet On/Off": 0.0,
      "Res 1 On/Off": 0.0,
      "Noise On/Off": 1.0,
      "Noise Filter Type": 2
    }
  }
}
```
Use `get-params --track <T> --device <D> --chain <N>.0` to enumerate all available parameter names before filling in values.

To apply this preset to Live: `ableton_push.py apply-preset --track DFAM --device 0 --preset <path>`

### Panel-state instruments (Markdown):
```markdown
# Patch: [Name]
**Instrument**: Moog DFAM
**Created**: YYYY-MM-DD
**Description**: [What it sounds like and when to use it]

## Sequencer
| Step | Pitch (V) | Velocity |
|------|-----------|----------|
| 1    | 2.5       | max      |
...

## Panel Settings
- VCO 1 FREQ: 12 o'clock
- VCO 2 FREQ: slightly flat of 12
- FM AMOUNT: 9 o'clock
- FILTER CUTOFF: 1 o'clock
- FILTER RES: 3 o'clock
...

## Patch Cables
- [none] / [list any modular connections]
```

## Usage

### Via CLI

```bash
python scripts/create_preset.py --instrument rev2 --name "grind-lead" --description "detuned aggressive mid lead"
python scripts/create_preset.py --instrument dfam --name "thud-kick" --format panel-state
```

### Via Copilot chat

- "Create a Rev2 preset for a slow, evolving pad in E minor — something cinematic but heavy"
- "Document this DFAM panel state as a preset called 'Industrial Kick'"
- "What NRPN values would give me aggressive filter modulation on the Take 5?"

## Output Location

- JSON presets: `instruments/[slug]/presets/[name].json`
- Panel-state docs: `instruments/[slug]/presets/[name].md`

## Script: [create_preset.py](../../scripts/create_preset.py)

Reads MIDI implementation data from `instruments/[slug]/manuals/midi-impl.json` if present. Falls back to Copilot's built-in knowledge of instrument parameters.

## Security Note

Never include personal credentials or SysEx authentication tokens in preset files.
