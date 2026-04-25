---
description: Generate this week's IRON STATIC creative brainstorm using Gemini, incorporating the latest feed digest. Writes to knowledge/brainstorms/ and registers it on the active song.
agent: The Alchemist
tools: [read, edit, search, execute, web, agent, todo]
---

# Run Brainstorm Workflow

Generate a fresh weekly brainstorm for the active song, seeded with the latest feed digest and existing session context.

## Step 1: Check for Today's Feed Digest

Look for the most recent file in `knowledge/references/feeds/` matching `YYYY-MM-DD.md`.

If today's digest (`knowledge/references/feeds/2026-04-25.md` or current date) does not exist, run the feed digest first:

```bash
python scripts/run_feed_digest.py
```

If it already exists, skip — proceed with what's there.

## Step 2: Load Active Song Context

```bash
python scripts/manage_songs.py list
```

Read `database/songs.json` — note the active song's `slug`, `key`, `scale`, `bpm`, and `brainstorm_path`.

## Step 3: Run the Brainstorm

```bash
python scripts/run_brainstorm.py
```

This will:
- Pull the active song context
- Incorporate the latest feed digest from `knowledge/references/feeds/`
- Call Gemini to generate a structured brainstorm
- Write the output to `knowledge/brainstorms/YYYY-MM-DD.md`
- Auto-register `brainstorm_path` on the active song in `database/songs.json`

If a brainstorm already exists for today and you want to regenerate:

```bash
python scripts/run_brainstorm.py --force
```

## Step 4: Read and Surface the Brainstorm

Read the newly written brainstorm file. Extract and present:

- **Section 1 — Song Idea**: Working title, mood, key/scale, BPM, featured instruments
- **Section 2 — Arrangement Blueprint**: Section structure and energy arc
- **Section 3 — Sound Design Challenge**: Which instrument, what patch direction
- **Section 4 — Rhythm Pattern**: Polyrhythmic or odd-meter idea
- **Section 5 — Conceptual Direction**: The soul of the idea — especially the Machine side voice

## Step 5: Propose Next Action

Based on the brainstorm, name the single highest-value thing to work on in this session and which prompt or agent to invoke:

- `/theory-first` — if the harmonic direction needs grounding
- `/new-patch [instrument]` — if the sound design challenge is the priority
- `/build-session` — if the arrangement blueprint is ready to become a Live session
- `/forge-audio [element]` — if a specific sonic element needs generating
