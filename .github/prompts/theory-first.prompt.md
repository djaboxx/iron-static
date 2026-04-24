---
description: Start from theory — analyze harmonic/rhythmic content, then arrange it, then design sounds. Full Theorist → Arranger → Sound Designer chain.
mode: agent
agent: The Theorist
tools: [search/codebase, edit/editFiles, terminal, search, read/problems]
argument-hint: "what you want to explore (e.g. 'verse progression', 'rhythmic motif for the drop', 'bridge harmony')"
---

# Theory-First Workflow

Start with harmonic and rhythmic analysis, then hand off to The Arranger for structure, then to The Sound Designer for patches.

## Step 1: Load Active Song Context

Read:
- [database/songs.json](../../database/songs.json) — active song key, scale, BPM
- [knowledge/music-theory/scales-and-modes.md](../../knowledge/music-theory/scales-and-modes.md) — what's already documented
- [knowledge/music-theory/rhythm-patterns.md](../../knowledge/music-theory/rhythm-patterns.md) — existing rhythmic vocabulary

## Step 2: Analyze — ${input:focus:harmonic content for the active section}

Provide a full theory analysis using the output format in your instructions:
- Harmonic content: chord vocabulary, key moves, tension/release map
- Rhythm: Euclidean patterns or polyrhythm structures, metric center
- Hardware map: translate everything to physical instrument settings

If this generates new theory knowledge worth keeping, append it to `knowledge/music-theory/scales-and-modes.md` or `knowledge/music-theory/rhythm-patterns.md`.

## Step 3: Hand Off

Use the **"Arrange this harmonic content"** handoff to pass the analysis to The Arranger.
The Arranger will structure it into sections. From there, use "Build sounds for this section" to route to The Sound Designer.

**Full chain**: The Theorist → The Arranger → The Sound Designer → The Critic
