---
name: slice-and-rack
description: Gemini-guided creative audio chopper + Ableton Drum Rack builder. Sends audio to Gemini for musically creative chop point suggestions, slices the file, and builds a .adg Drum Rack preset ready to drag into Live.
argument-hint: "[path-to-audio-file] [optional: --slices N --context 'focus description']"
user-invocable: true
disable-model-invocation: false
---

# Skill: slice-and-rack

## What This Skill Does

Takes a generated (or recorded) audio file and turns it into an Ableton Drum Rack preset:

1. **Uploads the audio to Gemini** — Gemini listens to the whole file and proposes N creative chop points with reasoning for each cut
2. **Slices the file** — Python cuts at those timestamps using `soundfile`
3. **Builds a `.adg` Drum Rack preset** — each slice loaded into a Simpler pad (C1–F2 default layout)
4. **Saves to the repo** — `.adg` committed in `ableton/racks/`, WAV slices uploaded to GCS

This is NOT transient-based. Gemini picks moments that matter musically:
textural ruptures, density shifts, spectral surprises, rhythmic gaps, tonal anomalies.

Designed to work downstream of `gemini-forge` — but works on any audio file.

## When to Use

- After `gemini-forge --generate` produces a drum loop or texture you want to chop
- When you have a recorded sample and want to use it as a multi-pad kit
- When you want to load a generated Lyria loop onto the Digitakt (slice → export individual slices → load)
- When The Alchemist finishes a forge and hands off to The Live Engineer

## File Locations

| Path | Description | Git? |
|---|---|---|
| `ableton/racks/[slug]_[source]_[date].adg` | Drum Rack preset | **YES — committed** |
| `audio/generated/slices/[slug]_[source]_[date]/slice_NN_Xs.wav` | Individual slice WAVs | GCS only |
| `audio/generated/slices/[slug]_[source]_[date]/chop_metadata.json` | Gemini chop reasoning | **YES — committed** |

## Usage

### CLI

```bash
# Chop a generated loop into 8 pads (default)
python scripts/chop_and_rack.py --file audio/generated/rust-protocol_kick-loop_2026-04-24.mp3

# Specify number of slices
python scripts/chop_and_rack.py --file loop.wav --slices 16

# Give Gemini creative direction for the chops
python scripts/chop_and_rack.py --file loop.wav --context "focus on textural ruptures and spectral density drops"

# Custom rack name
python scripts/chop_and_rack.py --file loop.wav --rack-name "Rust Chops v1"

# Dry run — see Gemini's chop suggestions without writing files
python scripts/chop_and_rack.py --file loop.wav --dry-run

# Push slices to GCS immediately after chopping
python scripts/chop_and_rack.py --file loop.wav --push-gcs

# Use a stronger model for better analysis
python scripts/chop_and_rack.py --file loop.wav --model gemini-2.5-pro
```

### Typical forge → chop → rack workflow

```bash
# 1. Generate audio with Lyria
python scripts/gemini_forge.py --target "industrial drum loop" --generate

# 2. Chop the generated audio
python scripts/chop_and_rack.py \
  --file audio/generated/rust-protocol_industrial-drum-loop_2026-04-24.mp3 \
  --slices 8 \
  --context "find rhythmically interesting moments, prefer textural contrast"

# 3. Drag the .adg into Ableton
# Open ableton/racks/rust-protocol_industrial-drum-loop_2026-04-24.adg

# 4. Push slices to GCS
python scripts/gcs_sync.py push audio/generated/slices/rust-protocol_industrial-drum-loop_2026-04-24/ --tag rust-protocol

# 5. Commit rack + metadata
git add ableton/racks/ audio/generated/slices/ database/gcs_manifest.json
git commit -m "feat(racks): add Gemini chop rack for industrial-drum-loop"
```

## What Gemini Does (Not Transients)

The chop prompt explicitly tells Gemini NOT to use transient detection. Instead it looks for:
- **Textural ruptures** — where the character of the sound changes significantly
- **Spectral density shifts** — where frequency content thins or thickens
- **Rhythmic gaps** — natural breath points in the material
- **Tonal anomalies** — moments of harmonic surprise or noise intrusion
- **Contrast points** — anything that would be interesting to trigger independently

You can steer this with `--context`. Examples:
- `"find the quietest moments and cut just before them"`
- `"prioritize sub-bass heavy segments for the first four pads"`
- `"treat the first half as a texture set, second half as transient hits"`

## Drum Rack Pad Layout

Default pad assignment (MIDI note → pad):

| Pad | MIDI Note | Label |
|---|---|---|
| 1 | C1 (36) | Slice 00 |
| 2 | D1 (38) | Slice 01 |
| 3 | E1 (40) | Slice 02 |
| 4 | F1 (41) | Slice 03 |
| 5 | G1 (43) | Slice 04 |
| 6 | A1 (45) | Slice 05 |
| 7 | B1 (47) | Slice 06 |
| 8 | C2 (48) | Slice 07 |

Up to 16 pads supported. Each pad uses a Simpler in one-shot mode (no warping, no loop).

## Using Slices on the Digitakt

Each slice WAV in `audio/generated/slices/*/` is a standard 44.1kHz stereo WAV.
To use on the Digitakt:
1. Pull slices from GCS: `python scripts/gcs_sync.py pull audio/generated/slices/[dir]/`
2. Copy individual WAVs to your Digitakt via USB sample transfer
3. Assign to tracks on the Digitakt as one-shot samples

## Requirements

```bash
pip install google-genai>=1.0.0 soundfile numpy
```

`soundfile` and `numpy` should already be in `scripts/requirements.txt`.

## Script: [chop_and_rack.py](../../scripts/chop_and_rack.py)

Key flags:
- `--file PATH` — audio file to chop (required)
- `--slices N` — number of pads/slices (2–16, default 8)
- `--context TEXT` — creative direction for Gemini's chop selection
- `--rack-name NAME` — name for the drum rack preset
- `--model MODEL` — Gemini model (default: gemini-2.0-flash, use 2.5-pro for best results)
- `--date YYYY-MM-DD` — override output date
- `--push-gcs` — auto-push slices to GCS after chopping
- `--dry-run` — print Gemini's chop suggestions without writing files
- `--no-song-context` — skip active song key/scale/BPM context
