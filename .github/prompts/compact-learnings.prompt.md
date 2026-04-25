---
description: Distill all session learnings into a compact topic-organized digest. Run at end of any multi-checkpoint session or before session-start if the digest is stale.
agent: copilot
tools: [execute, read, edit]
---

# Compact Learnings

Synthesize all session checkpoint learnings into a single scannable digest.

## Step 1: Run the Compactor

```bash
python scripts/compact_learnings.py
```

This reads every `knowledge/sessions/*-learnings.md` file, calls Gemini (pro tier) to distill them into topic-organized bullets, and writes `knowledge/sessions/learnings-digest.md`.

If `GEMINI_API_KEY` is not available, fall back to raw extraction:
```bash
python scripts/compact_learnings.py --no-llm
```

## Step 2: Read the Digest

Read `knowledge/sessions/learnings-digest.md` in full. Verify:
- The "Critical Rules" section at the bottom captures the most important non-obvious facts
- No active blockers or open questions from recent checkpoints are missing
- The digest is short enough to read in 30 seconds

## Step 3: Report Back

Report:
- How many topic sections were generated
- How many bullet entries total
- The "Critical Rules" section verbatim (paste it)
- Flag any learnings from `*-learnings.md` files that appear to be MISSING from the digest (things that should be critical but weren't included)

If anything important is missing, run with `--force` to regenerate:
```bash
python scripts/compact_learnings.py --force
```
