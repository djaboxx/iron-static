---
name: gemini-forge
description: Use Gemini to generate structured audio creation specs from active song context, and optionally generate audio via Google Lyria. Produces prompts for Suno/Udio/Lyria and hardware fallback patches.
argument-hint: "[target element] [optional: extra context in quotes]"
user-invocable: true
disable-model-invocation: false
---

# Skill: gemini-forge

## What This Skill Does

Reads the active song's brainstorm, reference digest, key/scale/BPM, and asks Gemini
to produce a **complete audio generation spec** for a named sonic element.

The spec gives you four things:
1. **A generation prompt** — paste directly into Suno, Udio, or Google Lyria
2. **Technical parameters** — BPM, key, duration, frequency focus, stereo field
3. **Hardware parallel** — what instrument in the rig produces this natively
4. **Integration notes** — where in the arrangement this element lives and what it must avoid

If `--generate` is passed, the script calls **Lyria 3** through the same Gemini API using
your existing `GEMINI_API_KEY` — no Vertex AI, no `GOOGLE_CLOUD_PROJECT` needed.
Two Lyria models are available: `clip` (30-second loop, MP3) and `pro` (full-length, MP3 or WAV).

This is not `gemini-listen`. `gemini-listen` evaluates audio that already exists.
`gemini-forge` generates specs (and optionally audio) for elements that don't exist yet.

## When to Use

- When you need a drum loop, bass texture, ambient pad, industrial noise layer, or
  any other sample element and want it designed to fit the active song
- When you want a detailed prompt for Suno / Udio / Lyria but need it calibrated
  against the brainstorm, reference digest, and current key/scale
- When you want to know what the hardware parallel for a generated element would be
  (so you can evaluate whether to use the AI audio or build it on the rig instead)
- When The Alchemist agent is running a forge-audio workflow

## Output Files

| File | Description |
|---|---|
| `audio/generated/specs/[song-slug]_[element]_[date].md` | Always generated — the full spec |
| `audio/generated/[song-slug]_[element]_[date].wav` | Only if `--generate` succeeds |

**Audio files are never committed to git.** Use the `gcs-audio` skill to upload them
to GCS and update `database/gcs_manifest.json`.

## Setup

```bash
# Already installed in the repo venv
pip install google-genai>=1.0.0

# Required env var — the same key used for all Gemini calls
export GEMINI_API_KEY="your-key-here"
```

No Vertex AI, no `GOOGLE_CLOUD_PROJECT`, no additional SDK needed.
Lyria 3 is part of the Gemini API and uses the same `GEMINI_API_KEY`.

## Usage

### CLI

```bash
# Generate a spec for a kick loop
python scripts/gemini_forge.py --target "kick loop"

# Add extra context
python scripts/gemini_forge.py --target "bass texture" --context "sub-heavy, corroded, slow attack"

# Use the pro model for deeper brainstorm synthesis
python scripts/gemini_forge.py --target "pad atmosphere" --model pro

# Generate a 30-second loop via Lyria 3 Clip
python scripts/gemini_forge.py --target "industrial hit" --generate

# Generate a longer texture via Lyria 3 Pro (WAV output)
python scripts/gemini_forge.py --target "corroded pad atmosphere" --generate --lyria-model pro

# JSON output for scripting or agent pipelines
python scripts/gemini_forge.py --target "snare transient" --output json

# Skip active song context (generic IRON STATIC spec)
python scripts/gemini_forge.py --target "noise texture" --no-song-context
```

### Via Arc chat (Alchemist agent)

1. Make sure `database/songs.json` has an active song
2. Ask: "Forge a kick loop spec for this song"
3. The Alchemist reads the brainstorm and references, runs the script, returns the spec
4. Take the GENERATION PROMPT section and paste into your audio generator of choice
5. Evaluate the result with `gemini-listen` if needed
6. Upload to GCS with `gcs-audio` skill

## Prompt Context Sources (in order)

The forge prompt includes:
1. IRON STATIC aesthetic brief (NIN / LOG / RTJ / Modeselector / Mayhem palette)
2. Active song: key, scale, BPM, concept/title
3. Brainstorm file at `song.brainstorm_path` (or most recent in `knowledge/brainstorms/`)
4. Most recent reference digest (`knowledge/references/YYYY-MM-DD.md`)
5. Your `--target` and optional `--context`

## Lyria 3 Model Guide

| Model flag | API model | Best for | Output | Duration |
|---|---|---|---|---|
| `clip` (default) | `lyria-3-clip-preview` | Drum loops, bass stabs, short textures | MP3, 44.1kHz stereo | 30 seconds |
| `pro` | `lyria-3-pro-preview` | Pads, evolving atmospheres, full arrangements | MP3 or WAV, 44.1kHz stereo | A couple of minutes |

Use `clip` for loop-able material (drum loops, bass riffs, sample textures).
Use `pro` for longer, evolving atmospheres or full arrangements.
Both use `GEMINI_API_KEY` — no additional credentials.

All generated audio includes Google's SynthID watermark (inaudible).

## After Forging

- **Evaluate**: Run `gemini-listen` on any generated audio to get aesthetic feedback
- **Catalog**: Use `gcs-audio` skill to upload to GCS and update the manifest
- **Compare**: Hand off to The Sound Designer to compare against hardware patch options
- **Use it**: Load the `.wav` into the Digitakt sample pool or an Ableton Simpler/Sampler track
