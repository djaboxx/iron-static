---
description: Begin a studio session — run song-review, assess current state, and propose the highest-value next workflow.
agent: The Producer
tools: [codebase, editFiles, terminal, search, agent]
---

# Session Start

Run the `song-review` workflow. Orient to the current state of the project and hand Dave a prioritized action list with the specific agent and workflow to invoke for each item.

## Instructions

Run the Producer's `song-review` workflow:

1. **The Arranger**: Read `database/songs.json`, `knowledge/band-lore/manifesto.md`, `knowledge/production/mixing-notes.md`, `knowledge/sound-design/synthesis-notes.md`, and any preset catalogs. Assess what sections are defined, what's missing, and what the current energy arc looks like.

2. **The Critic**: Evaluate everything documented for the active song — presets, patterns, structure, open questions. Be direct. If something is wrong or predictable, say so.

3. **Synthesize**: Produce a prioritized list of exactly 3 things to work on this session. For each:
   - What it is
   - Which Producer workflow or agent + prompt to invoke (`theory-to-hardware`, `patch-and-critique [instrument]`, `/new-patch`, `/theory-first`)
   - Why it's the highest-value use of time right now

After presenting the 3 options, wait for Dave to choose one — then dispatch the appropriate workflow.
