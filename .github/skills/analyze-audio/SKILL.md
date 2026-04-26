---
name: analyze-audio
description: Analyze an audio file for key, BPM, spectral characteristics, and suggest instrument patch/arrangement ideas for IRON STATIC.
argument-hint: "[path-to-audio-file] [optional: focus=key|bpm|spectrum|all]"
user-invocable: true
disable-model-invocation: false
---

# Skill: analyze-audio

## What This Skill Does

Given an audio file (or description of one), this skill:
1. Identifies or estimates the musical key and scale
2. Detects or estimates BPM / tempo
3. Describes the spectral character (sub presence, mid density, high-end texture)
4. Identifies dominant timbres and likely instruments/sounds
5. Suggests how the IRON STATIC rig could respond to, complement, or contrast with the audio

## When to Use

- When Dave drops a reference track and wants to understand what makes it work
- When analyzing a new recording or sample for integration into the live rig
- When identifying the key/BPM of a sample before loading it into the Digitakt
- When comparing a mix to a reference target

## Setup

Install audio analysis dependencies:

```bash
source .venv/bin/activate
pip install -r scripts/requirements.txt
```

Key libraries used: `librosa`, `numpy`, `scipy`, `soundfile`

## Usage

### Via CLI script

```bash
python scripts/analyze_audio.py audio/references/my-reference.wav
python scripts/analyze_audio.py audio/recordings/raw/take1.wav --focus bpm
python scripts/analyze_audio.py audio/samples/drums/kick_heavy.wav --focus spectrum
```

### Via Arc chat

Describe the audio or paste the file path and ask:
- "Analyze this file and tell me what key and BPM it's in"
- "What's the spectral character of this recording?"
- "How should I program the Digitakt to sit under this reference?"

## Analysis Outputs

Arc should return:

```
FILE: [filename]
KEY: [detected key + scale, e.g. "E minor (Aeolian)"]
BPM: [estimated BPM]
TIME SIGNATURE: [estimated]
SPECTRAL CHARACTER:
  - Sub (20–80Hz): [present/absent/dominant]
  - Bass (80–250Hz): [description]
  - Mids (250–4kHz): [description]
  - Highs (4kHz+): [description]
DOMINANT TIMBRES: [list of likely sound sources]
SUGGESTED RIG RESPONSE:
  - Digitakt: [drum programming suggestion]
  - [Relevant synth]: [patch/role suggestion]
  - Arrangement note: [what this track needs or has too much of]
```

## Script: [analyze_audio.py](../../scripts/analyze_audio.py)

The script uses `librosa` for key/BPM detection and spectral analysis. Run `python scripts/analyze_audio.py --help` for full options.

## Notes

- For WAV/AIFF files stored with Git LFS, run `git lfs pull` first
- For PDFs or reference images (e.g. a waveform screenshot), describe the content and Arc will estimate based on description
- BPM detection is most accurate on isolated drum tracks; use `--focus bpm` for best results on full mixes
