# Session Learnings — 2026-04-25

*Active song: Instrumental Convergence — D aeolian @ 72 BPM*
*Checkpoint: 11:19*

## What We Figured Out

- **Agent handoff context matters.** The Alchemist's original 4 handoffs ("Evaluate this audio", "Load this into the session", etc.) were written for Lyria audio generation workflows. When the Alchemist runs a brainstorm instead, those buttons are wrong — there's no audio, and "build a hardware patch" is The Sound Designer's job. Handoffs need to be authored for the *output type*, not the *agent type*.

- **Critique output must be written to disk to survive context compaction.** The Critic's brainstorm evaluation previously only existed in chat. The Alchemist revision handoffs were pointing at "the critique above" — which evaporates when context compacts. The fix: The Critic writes `YYYY-MM-DD-critique.md` on every brainstorm evaluation, and all revision handoffs now reference the file on disk by path.

- **The Critic and The Alchemist can form a feedback loop.** Wiring `Critic → "Revise the brainstorm" → Alchemist → run_brainstorm --force → Critic` creates a revision cycle that can run until the brainstorm satisfies the critique. Both agents now have handoffs that close the loop. The cached critique file is the shared brief between them.

- **The session summarizer does not capture conversation learnings.** `run_session_summarizer.py` reads `outputs/live_state.json` and Ableton state — it has no knowledge of what was figured out in conversation. Those learnings were being lost at context compaction. Fix: dedicated `YYYY-MM-DD-learnings.md` format + `/checkpoint` prompt.

- **Copilot needs to be explicitly told to read learnings files at session start.** Adding the learnings file to the "always useful" table in `copilot-instructions.md` is not enough on its own — the instruction needs to be a hard rule with a specific lookback window. Added: "At the start of every session, Copilot should check for any `*-learnings.md` file from the past 7 days and read it before doing any substantive work."

- **The Alchemist's description was too narrow.** It said "audio generation specialist" — which implied its only job was Lyria/Suno. It actually runs brainstorms, synthesizes feed digests, and generates audio specs. The description now reads: "Gemini's operational voice — runs weekly brainstorms, synthesizes feed digests, generates structured audio specs, and optionally generates audio via Lyria."

- **The harmonic check after a brainstorm belongs to The Theorist, not The Critic.** The Critic evaluates creative decisions (does this work? does it serve the song?). The Theorist validates theory (does this key/scale/BPM hold up? what chord vocab fits?). The original Alchemist handoffs conflated these. Now: The Critic gets "Critique the brainstorm", The Theorist gets "Check the harmonic direction."

## What Failed and Why

- **`session-close.prompt.md` had invalid tool aliases** (`search/codebase`, `read/problems`) → these are silently ignored by VS Code. Fixed to valid aliases: `[read, search, execute, edit, todo]`. Root cause: the original aliases were path-style names that predate the valid alias list. Any agent or prompt file using path-style tool names will silently lose those tools.

## Decisions Made

| Decision | Reasoning |
|---|---|
| Critique file lives at `knowledge/brainstorms/YYYY-MM-DD-critique.md` | Same directory as the brainstorm file being critiqued. Naming convention makes them obviously paired. One critique file per brainstorm date — overwrite on each `--force` revision cycle. |
| `/checkpoint` appends to existing file rather than overwriting | Multiple checkpoints per session is the expected pattern. Append preserves the full trail of mid-session discoveries. |
| `/session-close` writes learnings *before* critique | Learnings are the most valuable artifact. If the session close gets interrupted, the learnings should already be on disk. |
| The Theorist owns harmonic verification, The Critic owns aesthetic evaluation | These are different questions. Conflating them in a handoff causes the wrong agent to get the task. |

## Correct Configurations / Commands

```bash
# Revise the brainstorm after critique (overwrites today's brainstorm)
python scripts/run_brainstorm.py --force

# Check active song context
python scripts/manage_songs.py list

# See all session changes
git status --short

# Brainstorm file location (today)
knowledge/brainstorms/2026-04-25.md

# Critique file location (today) — written by The Critic after a brainstorm eval
knowledge/brainstorms/2026-04-25-critique.md

# Learnings file location (today) — written by /checkpoint
knowledge/sessions/2026-04-25-learnings.md
```

## Open Questions

- [ ] `brainstorm-critique.md` orphan file in `knowledge/brainstorms/` — written manually this session before the `YYYY-MM-DD-critique.md` convention was established. Should be deleted or renamed to `2026-04-25-critique.md`.
- [ ] The `run_brainstorm.py --force` flag needs to be verified — does it actually support `--force`? The brainstorm script was not inspected for this flag during the session.
- [ ] The `/checkpoint` prompt references "from the current conversation" — but Copilot has no API to introspect the conversation. In practice, the checkpoint relies on the agent synthesizing learnings from memory of what happened in this context window. This is the fundamental limitation. If context has already compacted before `/checkpoint` is invoked, some learnings may already be lost.
- [ ] All session changes are uncommitted. Large batch of modified and untracked files needs a commit.

## Next Session Priority

Invoke "Revise the brainstorm" handoff from The Critic to send the brainstorm back to The Alchemist with the critique as brief — the current brainstorm needs structural risk and the Machine's voice needs to arrive earlier and carry more weight.
