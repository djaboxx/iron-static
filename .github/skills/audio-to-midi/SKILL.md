---
name: audio-to-midi
description: Convert audio files (stems or full mixes) to MIDI sequences for the IRON STATIC rig. Handles stem separation via Demucs and pitch/note transcription via Basic Pitch.
argument-hint: "[path-to-audio-file] [optional: stems=true instrument=bass|drums|other]"
user-invocable: true
disable-model-invocation: false
---

# Skill: audio-to-midi

## What This Skill Does

Given an audio file (recording, stem, reference, or sample), this skill:
1. Optionally separates a full mix into stems (drums, bass, other) using **Demucs**
2. Transcribes audio to MIDI notes using **Basic Pitch** (Spotify's open-source pitch tracker)
3. Saves `.mid` files to `midi/sequences/` with proper IRON STATIC naming convention
4. Suggests which rig instrument should receive each resulting MIDI track

## When to Use

- Converting a bass recording to MIDI to route to the Subharmonicon or Minibrute 2S
- Transcribing a drum recording to trigger the Digitakt or DFAM
- Pulling melodic content from a reference track to adapt for the Rev2 or Take 5
- Extracting a rhythm from a sample to build a Digitakt pattern around

## Setup

Install dependencies (heavier than other skills — first run will download ML models ~100MB):

```bash
source .venv/bin/activate
pip install basic-pitch demucs
```

Or via requirements:
```bash
pip install -r scripts/requirements.txt
```

> **Note**: `basic-pitch` uses ONNX Runtime by default (no GPU needed). Demucs uses PyTorch.
> First run of each tool downloads model weights automatically.

## Usage

### Via CLI script

```bash
# Transcribe a single stem directly to MIDI
python scripts/audio_to_midi.py audio/recordings/raw/my_bass.aif

# Separate a full mix first, then transcribe all stems
python scripts/audio_to_midi.py audio/recordings/raw/full_mix.wav --stems

# Transcribe only the bass stem from a separated mix
python scripts/audio_to_midi.py audio/recordings/raw/full_mix.wav --stems --stem-type bass

# Specify output dir (default: midi/sequences/)
python scripts/audio_to_midi.py audio/recordings/raw/take1.wav --output midi/sequences/
```

### Via Arc chat

- "Convert this bass recording to MIDI for the Subharmonicon"
- "Split this mix into stems and give me MIDI for all of them"
- "Transcribe the melody in this reference to MIDI so I can load it on the Rev2"

## Outputs

```
midi/sequences/[source-slug]_bass_v1.mid
midi/sequences/[source-slug]_drums_v1.mid
midi/sequences/[source-slug]_other_v1.mid
```

After transcription, Arc will suggest which instrument to assign each track to based on register and content:

```
TRANSCRIPTION RESULT:
  Source: [filename]
  Output: midi/sequences/[slug]_bass_v1.mid

MIDI ASSIGNMENT SUGGESTIONS:
  bass.mid     → Minibrute 2S (ch 7) or Subharmonicon (ch 5)
  drums.mid    → Digitakt (load as MIDI trigger source)
  other.mid    → Rev2 Layer A (ch 2) or Take 5 (ch 4)
```

## Workflow: Full Mix → MIDI → Rig

```
Full mix WAV/AIF
    │
    ▼ (Demucs stem separation)
bass.wav  drums.wav  other.wav
    │
    ▼ (Basic Pitch transcription)
bass.mid  drums.mid  other.mid
    │
    ▼ (Route to rig)
Subharmonicon / DFAM / Rev2
```

## Notes

- Basic Pitch is best on monophonic or bass-heavy material — exactly what IRON STATIC records
- For drum MIDI: hits are mapped to GM pitches; remap in Digitakt to match your sample slots
- Stem separation is imperfect on heavily distorted or compressed material — use on clean recordings for best results
- MIDI files can be dropped directly into Ableton or into the Digitakt via MIDI import (Overbridge)

## Script: [audio_to_midi.py](../../scripts/audio_to_midi.py)
