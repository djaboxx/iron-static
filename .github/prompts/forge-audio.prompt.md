---
description: Generate a structured audio creation spec for a specific sonic element, calibrated to the active song's brainstorm and reference digest. Optionally attempts audio generation via Google Lyria.
agent: The Alchemist
tools: [search/codebase, edit/editFiles, terminal, read/problems]
argument-hint: "target element (e.g. 'kick loop', 'bass texture', 'corroded pad')"
---

# Forge Audio Workflow

Design a complete audio generation spec for the specified element and optionally produce
audio via Lyria — always calibrated to the active song context.

## Step 1: Load Context

Read the active song:

```bash
python scripts/manage_songs.py list
```

Then read (in order):
1. `database/songs.json` — `slug`, `key`, `scale`, `bpm`, `brainstorm_path`
2. File at `brainstorm_path` — the creative brief
3. Most recent `knowledge/references/YYYY-MM-DD.md` — aesthetic targets

## Step 2: Load the Skill

Load the `gemini-forge` skill from `.github/skills/gemini-forge/SKILL.md` before proceeding.

## Step 3: Name the Element

Translate `${input:element:kick loop}` into a precise, concrete element name.

Examples:
- "kick" → "industrial kick with sub tail"
- "texture" → "abrasive feedback texture"
- "pad" → "granular corroded pad atmosphere at ${bpm}bpm"

## Step 4: Run the Forge

```bash
python scripts/gemini_forge.py \
  --target "${input:element:kick loop}" \
  --model fast
```

Add `--context "..."` if Dave provided extra mood or constraint words.
Add `--generate` only if Dave explicitly asked for audio output (requires Vertex AI config).

## Step 5: Report the Spec

Return all five spec sections to Dave:

1. **GENERATION PROMPT** — copy-paste ready for Suno, Udio, or Lyria
2. **TECHNICAL PARAMETERS** — BPM, key, duration, stereo field
3. **HARDWARE PARALLEL** — which rig instrument produces this natively
4. **INTEGRATION NOTES** — arrangement placement, frequency collision guidance
5. **IRON STATIC FIT** — HIGH / MEDIUM / LOW with one-sentence rationale

## Step 6: Score Decision

| Score | Action |
|---|---|
| HIGH | Proceed — recommend generation |
| MEDIUM | Ask Dave: AI audio or build the hardware parallel? |
| LOW | Stop — explain why and propose an alternative element |

## Step 7: Handoffs

After delivering the spec, offer:

- **Evaluate the result** → The Critic
- **Build the hardware patch instead** → The Sound Designer
- **Load generated audio into session** → The Live Engineer
- **Verify harmonic content** → The Theorist
