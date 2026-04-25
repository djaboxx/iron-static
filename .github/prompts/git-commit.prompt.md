---
description: Stage and commit all pending changes — generates a conventional commit message from git diff, confirms with Dave before committing.
tools: [execute, read]
---

# Git Commit Workflow

Stage, review, and commit all pending work with a meaningful commit message.

## Step 1: Survey the Diff

Run:
```bash
git status --short
git diff --stat HEAD
```

Read the diff to understand what changed:
```bash
git diff HEAD
```

For new/untracked files, check their content before staging.

## Step 2: Generate Commit Message

Write a [Conventional Commits](https://www.conventionalcommits.org/) message based on what changed:

**Format:**
```
<type>(<scope>): <short summary>

<body — what changed and why, if not obvious>
```

**Types:**
- `feat` — new capability added (new script, new prompt, new preset, new skill)
- `fix` — bug fixed (script error, broken config, wrong value)
- `chore` — maintenance (deps, gitignore, config, non-functional changes)
- `docs` — documentation or knowledge files only
- `midi` — MIDI patterns, sequences, or templates
- `preset` — instrument presets or patch docs
- `session` — session notes, learnings, brainstorms
- `refactor` — code restructured without behavior change

**Scope examples:** `scripts`, `prompts`, `ableton`, `instruments`, `knowledge`, `database`, `midi`, `outputs`

**Rules:**
- Subject line ≤72 chars
- If multiple unrelated changes exist, group by type in the body
- Never mention "copilot", "AI", or "generated" — commits read as band work
- Don't commit `.env`, `*.pyc`, `outputs/audio/`, or anything in `.gitignore`

## Step 3: Stage and Show

Stage all tracked changes plus explicitly confirmed untracked files:
```bash
git add -u
# For untracked files that should be committed, add explicitly:
# git add <path>
```

Show what will be committed:
```bash
git diff --cached --stat
```

**Present the proposed commit message to Dave for approval before committing.**

## Step 4: Commit

After Dave confirms:
```bash
git commit -m "<type>(<scope>): <summary>" -m "<body if needed>"
```

Then report: files committed, commit hash, and whether a `git push` is needed.

## Step 5: Push (optional)

Ask Dave whether to push:
```bash
git push
```

Do not push without confirmation.
