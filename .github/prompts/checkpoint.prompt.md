---
description: Mid-session checkpoint — extract and cache what was learned this session before context compacts.
---

# Checkpoint Workflow

Capture what was figured out this session. The goal is not task status — it's **learnings**: things that took effort to discover, things that failed and why, decisions made and the reasoning behind them. Future sessions should not have to re-learn these.

## Step 1: Capture Current State

Run:
```bash
python scripts/manage_songs.py list
git status --short
git log --oneline -10
```

Read:
- `database/songs.json` — active song context
- Any files modified this session (from git status)

## Step 2: Write the Learnings File

Write to:
```
knowledge/sessions/YYYY-MM-DD-learnings.md
```

Use today's date. If the file already exists, **append** a new timestamped block — do not overwrite. Multiple checkpoints per session are expected.

Use this exact format:

```markdown
# Session Learnings — YYYY-MM-DD

*Active song: [title] — [key] [scale] @ [bpm] BPM*
*Checkpoint: HH:MM*

## What We Figured Out
Things that were not obvious before this session. Root causes found, correct configurations discovered, concepts clarified. Specifically: what is different now from what we assumed at the start?

- [Learning 1]
- [Learning 2]

## What Failed and Why
Approaches tried that didn't work. Include the reason — if we know it. The reason is the valuable part. Forgetting that X failed is bad. Forgetting *why* X failed means we'll try it again.

- [What was tried] → [Why it failed]

## Decisions Made
Choices that were explicitly debated and resolved. Include the reasoning so we don't re-open the debate.

| Decision | Reasoning |
|---|---|
| [What was decided] | [Why] |

## Correct Configurations / Commands
Exact commands, paths, or settings that work. Especially useful for things that took multiple tries to get right.

```bash
# [What this does]
[command]
```

## Open Questions
Things we still don't know. Things that need verification. Blockers that weren't resolved.

- [ ] [Question or unresolved issue]

## Next Session Priority
One sentence: the single most valuable thing to do at the start of the next session.
```

## Step 3: Confirm

Report back:
- The file path written
- The count of learnings captured (how many items in "What We Figured Out")
- The top open question, if any
- Remind Dave to invoke `/checkpoint` again before the session ends or before switching to a long multi-agent workflow
