---
description: End a studio session — The Critic evaluates all work from this session, then triggers the session summarizer to commit notes to knowledge/.
agent: The Critic
tools: [read, search, execute, edit, todo]
---

# Session Close Workflow

Evaluate everything that happened this session, then commit the summary to knowledge/.

## Step 1: Audit the Session

Read whatever exists for the active song:
- [database/songs.json](../../database/songs.json) — song state
- Any new preset files added to `instruments/*/presets/`
- Any new MIDI patterns in `midi/patterns/` or `midi/sequences/`
- Any new content in `knowledge/`

Check git for what changed this session:
```bash
git log --oneline -10
git diff HEAD~5 --name-only
```

## Step 2: Capture Session Learnings

Before evaluating, write the learnings file. This is the most important step — it preserves hard-won knowledge that the session summary won't capture.

Write to `knowledge/sessions/YYYY-MM-DD-learnings.md` (today's date). If a checkpoint file already exists from `/checkpoint` runs during the session, **append** a final "Session Close" block to it rather than creating a new file.

Include:
- **What We Figured Out** — things that were not obvious before this session. Root causes, correct configurations, resolved ambiguities.
- **What Failed and Why** — approaches tried that didn't work. The *why* is the valuable part.
- **Decisions Made** — choices that were explicitly debated and resolved. Include reasoning.
- **Correct Commands / Configs** — exact commands or settings that work (especially things that took multiple tries).
- **Open Questions** — unresolved blockers or things that need verification next session.
- **Next Session Priority** — one sentence: the single highest-value thing to do at the start of the next session.

## Step 3: Evaluate

For everything produced this session, apply the full critique format from your instructions:
- What works?
- What doesn't?
- What's the challenge to the creator for next session?
- Does it serve the active song?

Be honest. Don't soften it because the session is over.

## Step 4: Trigger Session Summarizer

After your critique is complete, run the session summarizer to commit notes:
```bash
gh workflow run session-summarizer.yml
```
This writes a session summary to `knowledge/sessions/` and commits it back to the repo.

## Step 4: Hand Off (optional)

If the critique identified a specific issue to address next session, use the appropriate handoff:
- Sound design problem → "Revise the sound design" → The Sound Designer
- Structural problem → "Revise the arrangement" → The Arranger
- Theory problem → "Revise the harmonic content" → The Theorist
