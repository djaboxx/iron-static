# Session Learnings — 2026-04-25

*Active song: Instrumental Convergence — D aeolian @ 72 BPM*
*Checkpoint: 11:19*

---

# Session Learnings — 2026-04-25 (Checkpoint 2)

*Active song: Instrumental Convergence — D aeolian @ 72.0 BPM*
*Checkpoint: ~session end*

## What We Figured Out

- **`build_session.py` is the correct tool for fresh sessions — not `generate_als.py`.** `generate_als.py` requires existing track names in a base `.als`. When track names come from a new brainstorm blueprint and don't exist in any prior session, `build_session.py` creates the session from scratch using `device_library.json` fuzzy search. This distinction cost significant time before it was resolved.

- **Pack ADGs store `<RelativePath>` as a container with `RelativePathElement` children. Live requires a self-closing leaf.** When `_extract_device_from_adg` parses a pack ADG (e.g. `808 Depth Charger Kit.adg`, `GranularStretch Kit.adg`), the `<RelativePath>` element contains child `<RelativePathElement>` nodes. Live's XML parser treats `RelativePath` as a "base type" (string leaf) — any children cause "Base types can't have children". The fix: replace the entire `<RelativePath>...</RelativePath>` block with `<RelativePath Value="" />` in `_extract_device_from_adg`.

- **Two sequential XML errors appeared in the pack ADGs, each masking the next.** First error: "Required attribute 'Value' missing" — fixed by adding `Value=""`. Second error: "Base types can't have children" — fixed by also stripping the child nodes. The final fix handles both in one regex that replaces the entire element.

- **`build_session.py` works cleanly for core library devices (no child `RelativePath` nodes).** Only pack ADGs trigger this issue. The 5 core library tracks in this session (808 Core Kit, Metallic Noise Pluck, Noise Bass, Inclement Drone Pad, Metal Pad) loaded without any XML patching needed.

## What Failed and Why

- **First fix: add `Value=""` to `<RelativePath>` without removing children** → Live accepted the attribute but still rejected with "Base types can't have children". Live treats `RelativePath` as a primitive string type — adding `Value=""` is necessary but not sufficient if children remain.

- **`generate_als.py --list` on v1/v2/base sessions** → none of the existing sessions had the blueprint track names (Sub Drone, Bass Voice, Choir Pads, etc. instead of DRM_Grid_KickSnare, BASS_Interrogator, etc.). Wrong tool entirely.

## Decisions Made

| Decision | Reasoning |
|---|---|
| `GranularStretch Kit` as `TEX_Witness_Vocal` device | Granulator III (M4L) is not in `device_library.json` as an ADG. Closest available pack preset. Sound Designer must swap to Granulator III manually. |
| `build_session.py` over `generate_als.py` for new sessions | No existing session has blueprint track names. `generate_als.py` is an injector (modifies existing), `build_session.py` is a builder (creates fresh). |
| 7 scenes — one per arrangement section | FRAGMENTS / INTERROGATION P1 / P2 / ESC / REJECTION / SYSTEM FAILURE / ECHO — exact section structure from brainstorm rev-3 |

## Correct Configurations / Commands

```bash
# Build a fresh session from blueprint config
python3 scripts/build_session.py \
  --config ableton/m4l/configs/<song-slug>-internal.json \
  --out ableton/sessions/<song-slug>_v3.als

# Dry run first — validates device resolution without writing
python3 scripts/build_session.py \
  --config ableton/m4l/configs/<song-slug>-internal.json \
  --dry-run -v

# Open in Live
open 'ableton/sessions/<song-slug>_v3.als'
```

```python
# The fix in _extract_device_from_adg (build_session.py) for pack ADGs:
device_xml = re.sub(
    r'<RelativePath(?!\s+Value=)[^>]*>.*?</RelativePath>',
    '<RelativePath Value="" />',
    device_xml,
    flags=re.DOTALL,
)
```

## Open Questions

- [ ] `TEX_Witness_Vocal` track: needs Granulator III (M4L) loaded manually — GranularStretch Kit is a placeholder. Requires a Gemini TTS audio source to load into Granulator III.
- [ ] Scene names are not set in the session — the 7 scenes are unnamed. Need to set via Remote Script or manually in Live: FRAGMENTS, INTERROGATION P1, INTERROGATION P2, INTERROGATION ESC, REJECTION, SYSTEM FAILURE, ECHO.
- [ ] `BASS_Interrogator`: Sound Designer needs to program the D + G# tritone sequence. Noise Bass preset is loaded but sequence is empty.
- [ ] `DRM_Grid_Perc_7_16`: 808 Core Kit loaded but needs reprogramming to a single metallic hit repeated 7 steps (7/16 pattern).
- [ ] Revision-3 brainstorm has not been critiqued. Known regression: `TEX_Witness_Vocal` spec calls for "Sampler with granular mode" in rev-3 (should be Granulator III — this was correct in rev-2).

## Next Session Priority

Start The Sound Designer on `BASS_Interrogator` (D + G# tritone sequence + distortion chain) — it's the structural spine of INTERROGATION and nothing else in that section can be evaluated until the bass is running.

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
