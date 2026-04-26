---
name: gemini-listen
description: Qualitative audio analysis via Gemini — answers the aesthetic questions librosa can't. Is this heavy enough? Does it fit IRON STATIC? What's fighting the mix?
argument-hint: "[path-to-audio-file] [optional: question in quotes]"
user-invocable: true
disable-model-invocation: false
---

# Skill: gemini-listen

## What This Skill Does

Sends an audio file to Gemini's multimodal API and returns aesthetic, qualitative analysis
in the context of IRON STATIC's sonic palette. Where `analyze-audio` gives you numbers
(key, BPM, spectral data), `gemini-listen` gives you judgment:

1. **Does this feel heavy enough?**
2. **What textures are dominant and do they fit the aesthetic?**
3. **What's working vs. fighting in the mix?**
4. **Three concrete, rig-specific suggestions to push it further.**

Gemini receives the IRON STATIC aesthetic brief (NIN / LOG / RTJ / Modeselector palette,
full instrument rig) plus the active song's key, scale, and BPM as context — so its
suggestions name actual hardware.

## When to Use

- After recording a rough take and wanting a gut-check before committing to a direction
- When evaluating a reference track for IRON STATIC inspiration
- When The Critic needs to evaluate a rendered mix or stem
- Before pushing a new preset to hardware — render a test clip and run it through
- When librosa says "key: A, BPM: 95" but you need to know if it *sounds* right
- When a loop or sample is being considered for the Digitakt sample pool

## Setup

`google-genai` is already in `scripts/requirements.txt` and installed in the venv.

```bash
source .venv/bin/activate
# google-genai is already installed — no additional steps needed
```

Set your Gemini API key:

```bash
export GOOGLE_API_KEY="your-key-here"
# or
export GEMINI_API_KEY="your-key-here"
```

Get an API key at [aistudio.google.com](https://aistudio.google.com). The free tier supports
audio analysis with `gemini-2.0-flash`.

## Usage

### Via CLI script

```bash
# Full structured analysis (default)
python scripts/gemini_listen.py --file audio/recordings/raw/take1.wav

# Custom question
python scripts/gemini_listen.py --file audio/references/ref.mp3 \
  --question "Is this heavy enough for IRON STATIC? What needs to change?"

# JSON output (for scripting or agent pipelines)
python scripts/gemini_listen.py --file audio/samples/drums/loop.wav --output json

# Specific model
python scripts/gemini_listen.py --file stems/bass.wav --model gemini-2.5-pro

# Skip active song context
python scripts/gemini_listen.py --file reference.wav --no-song-context
```

### Via Arc chat

Provide the audio file path and ask:
- "Listen to this recording and tell me if it fits the IRON STATIC aesthetic"
- "Run gemini-listen on `audio/recordings/raw/session1.wav`"
- "Evaluate this stem: does the bass sit right?"
- "What would you change about this mix to make it heavier?"

### Integration with The Critic

The Critic should run `gemini-listen` as part of any sound evaluation workflow:

```bash
# Render audio first, then evaluate
python scripts/gemini_listen.py --file renders/patch-test.wav \
  --question "Evaluate this patch as a Rev2 replacement for when the hardware is offline."
```

## Analysis Output

Default structured analysis covers:

```
1. PERCEIVED KEY / MODE / SCALE
   Best guess + confidence level

2. TEMPO
   Estimated BPM range, feel (rigid/swung/loose)

3. DOMINANT TEXTURES
   Timbres, layers, spectral character in plain language

4. ENERGY & DYNAMICS
   Where it hits, where it breathes, dynamic range assessment

5. IRON STATIC FIT: [high / medium / low]
   Honest aesthetic rating with specific reasoning

6. WHAT'S WORKING
   Elements that land correctly in the IRON STATIC palette

7. WHAT'S FIGHTING
   Elements that undermine the aesthetic (too clean, wrong frequency, etc.)

8. THREE CONCRETE SUGGESTIONS
   Actionable changes naming specific instruments from the rig
   (e.g., "run the lead through Operator FM into Roar")
```

## Supported File Formats

Gemini Files API accepts: `.wav`, `.mp3`, `.aiff`, `.aif`, `.flac`, `.ogg`, `.m4a`

For large files (>20MB), prefer `.mp3` or `.flac` for faster upload.

## Script: [gemini_listen.py](../../scripts/gemini_listen.py)

Key flags:
- `--file PATH` — audio file to analyze (required)
- `--question TEXT` — custom question (default: full structured analysis)
- `--output text|json` — output format (default: text)
- `--model MODEL` — Gemini model (default: gemini-2.0-flash)
- `--no-song-context` — skip loading active song key/scale/BPM from `database/songs.json`

## Notes

- The script automatically loads the active song's key, scale, and BPM from `database/songs.json`
  and passes this context to Gemini so suggestions stay in the song's harmonic world.
- Files are uploaded to the Gemini Files API and deleted immediately after analysis.
- For stems in GCS, pull locally first with the `gcs-audio` skill before running analysis.
- `gemini-2.0-flash` is recommended for speed. Use `gemini-2.5-pro` for the most detailed critique.
- This skill complements `analyze-audio` (librosa numbers) — run both for full coverage.
