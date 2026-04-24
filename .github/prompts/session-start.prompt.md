---
description: Begin a studio session — load session state, check active song, propose what to work on next based on what's incomplete.
agent: The Arranger
tools: [codebase, search, fetch]
---

# Session Start Workflow

Orient to the current state of the project and propose the highest-value next action.

## Step 1: Load Full Context

Read all of the following:
- [database/songs.json](../../database/songs.json) — active song, status, key, BPM
- [knowledge/band-lore/manifesto.md](../../knowledge/band-lore/manifesto.md) — the aesthetic filter
- [knowledge/production/mixing-notes.md](../../knowledge/production/mixing-notes.md) — what's been learned
- [knowledge/sound-design/synthesis-notes.md](../../knowledge/sound-design/synthesis-notes.md) — preset/synthesis state
- If `outputs/live_state.json` exists, read it — that's the live Ableton session state

Check what presets exist:
- [instruments/sequential-take5/presets/catalog.json](../../instruments/sequential-take5/presets/catalog.json)
- [instruments/sequential-rev2/presets/catalog.json](../../instruments/sequential-rev2/presets/catalog.json)

## Step 2: Assess

Answer these questions:
1. What song is active? What is its current lifecycle stage?
2. What sections of the arrangement are defined vs. missing?
3. What instruments have presets documented for this song?
4. What are the open questions — harmonic, structural, sound design?

## Step 3: Propose

Give Dave a prioritized list of 3 things to work on this session, with reasoning. For each:
- What it is
- Which agent to use (and the `/theory-first`, `/new-patch` prompt to invoke, or handoff to use)
- Why it's the highest-value use of time right now

Be direct. If the project is missing a structural backbone, say so. If the bass patch is wrong, say so.
