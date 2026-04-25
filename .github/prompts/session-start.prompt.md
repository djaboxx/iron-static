---
description: Begin a studio session — read the active brainstorm seed, run song-review, and propose the highest-value next workflow.
agent: The Producer
tools: [search/codebase, edit/editFiles, terminal, search, agent, read/problems]
---

# Session Start

The brainstorm is the week's creative seed. Read it first. Then run `song-review` and hand Dave a prioritized action list grounded in it.

## Step 0: Load Learnings Digest (MANDATORY — do this before anything else)

Check if `knowledge/sessions/learnings-digest.md` exists. If it does, read it in full.

This file contains distilled knowledge from all previous sessions — things that took effort to discover, configurations that work, rules that prevent re-learning. **Do not skip this step.** If you skip it, you will repeat mistakes that were already solved.

If the file does not exist, run:
```bash
python scripts/compact_learnings.py --no-llm
```
Then read the output.

Also check `knowledge/sessions/` for any `*-learnings.md` file dated within the past 7 days that is NOT yet reflected in the digest (i.e., newer than the digest's generated date). If found, read it too.

## Step 1: Load the Brainstorm Seed

Read `database/songs.json`. Find the active song's `brainstorm_path` field. Read that file in full.

If no `brainstorm_path` is set: note this and continue — the review will surface it as the first priority.

Extract from the brainstorm:
- **Working Title** (Section 1) — the proposed new direction or evolution
- **Arrangement Blueprint** (Section 2) — section structure and energy arc
- **Sound Design Challenge** (Section 3) — which instrument, what patch
- **Rhythm Pattern** (Section 4) — polyrhythmic or odd-meter idea
- **Conceptual Direction** (Section 5) — the soul of the idea

This brainstorm is the lens through which everything else is evaluated.

## Step 2: Run `song-review`

1. **The Arranger**: Read `knowledge/band-lore/manifesto.md`, `knowledge/production/mixing-notes.md`, `knowledge/sound-design/synthesis-notes.md`, and any preset catalogs. Assess what sections are defined, what's missing, and what the current energy arc looks like — judged against the brainstorm's arrangement blueprint.

2. **The Critic**: Evaluate everything documented for the active song — presets, patterns, structure — against both the manifesto and the brainstorm's conceptual direction. Be direct. If something contradicts the brainstorm's intent, say so.

## Step 3: Propose 3 Actions

Give Dave a prioritized list of exactly 3 things to work on this session. Each item must trace back to the brainstorm:
- What it is (tied to a specific brainstorm section)
- Which Producer workflow or prompt to invoke (`theory-to-hardware`, `patch-and-critique [instrument]`, `/new-patch`, `/theory-first`)
- Why it's the highest-value use of time right now

After presenting the 3 options, wait for Dave to choose — then dispatch the appropriate workflow.
