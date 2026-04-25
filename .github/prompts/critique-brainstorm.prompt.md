---
description: Have The Critic evaluate the latest brainstorm and write the verdict to knowledge/brainstorms/YYYY-MM-DD-critique.md. Invoke after /run-brainstorm to close the feedback loop.
agent: The Critic
tools: [read, edit, search, execute, web, agent, todo]
---

# Critique Brainstorm Workflow

Evaluate the latest IRON STATIC brainstorm and write the critique to disk.

## Step 1: Load Evaluation Context

Read these files in full before forming any opinion:

1. `knowledge/band-lore/manifesto.md` — the aesthetic standard. Everything is measured against this.
2. `database/songs.json` — active song context. Key, scale, BPM. Does the brainstorm fit?
3. The most recent brainstorm: `knowledge/brainstorms/` — find the latest `YYYY-MM-DD.md` file.

If a previous critique exists for the same date (`YYYY-MM-DD-critique.md`), read it too — note what was already flagged. Don't repeat yourself; either the issue was fixed or it wasn't.

## Step 2: Evaluate

Apply The Critic's mandate: does it work? does it serve the song? does it earn its place?

Evaluate each section:

- **Section 1 — Song Idea**: Does the working title carry weight without announcing its subject? Is the key/scale rationale actually earned or just justified? Is the unexpected element genuinely unexpected?
- **Section 2 — Arrangement Blueprint**: Is the structure dangerous? Would a listener who's heard two heavy electronic tracks in their life be surprised? Does each section earn its bar count at this BPM? Is every transition a choice, not a default?
- **Section 3 — Sound Design Palette**: Are the sound descriptions specific enough to act on? Do the sounds serve distinct structural roles, or are two of them doing the same job?
- **Section 4 — Rhythm Pattern**: Run the math. Does the stated polyrhythm behave the way it's described? Does the groove concept actually create the tension it claims to?
- **Section 5 — Conceptual Direction**: Is the Machine's voice specific and personally invested, or is it performing concern? Is the Human side more than a political summary? Do the two voices create real friction, or do they arrive at the same conclusion?
- **Session Blueprint (Section 6)**: Are the suggested devices correct for the described sounds? Flag any mismatches (wrong tool = wrong result from the first session).

## Step 3: Write the Critique to Disk

Write the critique to:
```
knowledge/brainstorms/YYYY-MM-DD-critique.md
```

Use the same date as the brainstorm being evaluated. If the file already exists, **overwrite it** — this is the current verdict, not a running log.

Format:
```
CRITIQUE: "[Working Title]" brainstorm — YYYY-MM-DD
Song context: [title], [key] [scale], [bpm] BPM

THE VERDICT: [one paragraph summary — lead with the strongest weakness]

WHAT WORKS:
  - [specific thing, specific reason]
  - ...

WHAT DOESN'T:
  - [specific thing, specific reason — include math or logic checks where relevant]
  - ...

THE CHALLENGE:
  [One direct challenge to the human collaborator and/or the Machine. Not a question — a provocation.]

VERDICT ON FIT:
  Does this serve [active song title] ([key] [scale], [bpm] BPM)? [Yes/Partially/No — then why.]
```

## Step 4: Surface the Critique

After writing the file, present the full critique in chat. State the file path it was written to.

Then offer handoffs:
- **Revise the brainstorm** → The Alchemist (use `run_brainstorm.py --force --critique YYYY-MM-DD-critique.md`)
- **Check the harmonic direction** → The Theorist
- **Take this to the Arranger** → The Arranger
