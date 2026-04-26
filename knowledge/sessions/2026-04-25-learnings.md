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

---

# Session Learnings — 2026-04-25 (Checkpoint 3)

*Active song: Instrumental Convergence — D aeolian @ 72.0 BPM*
*Checkpoint: ~late session — branch reconstruction fix complete*

## What We Figured Out

- **ADG rack preset `Branches` is always empty — real content is in `BranchPresets`.** The single most blocking bug this session. `GroupDevicePreset > Device > DrumGroupDevice > Branches` has 0 children in every ADG rack file. The actual per-pad/per-zone devices live in a sibling element: `GroupDevicePreset > BranchPresets > [Drum|Instrument]BranchPreset[N] > DevicePresets > AbletonDevicePreset > Device > [inner device]`. This is true for ALL Core Library rack presets (drum racks and instrument racks).

- **DrumBranchPreset's note mapping is in `ZoneSettings`, not `BranchInfo`.** In ADG presets, the pad-to-MIDI-note mapping is stored as `DrumBranchPreset > ZoneSettings > ReceivingNote`. In the session `.als` format, this maps to `DrumBranch > BranchInfo > ReceivingNote`. The element names differ between the ADG and session formats.

- **`InstrumentBranch` uses `ZoneSettings > KeyRange + VelocityRange`, not `BranchInfo`.** Drum branches use `BranchInfo` in session format; instrument rack branches use `ZoneSettings`. This is the core structural divergence between the two rack types.

- **Both branch types use `MidiToAudioDeviceChain` inside `DeviceChain` — not `AudioToAudioDeviceChain`.** Even instrument rack branches (which pass audio signals) use `MidiToAudioDeviceChain`. This was confirmed from the `2Percent.als` reference session.

- **`MixerDevice` template must be included in every branch with all `Id="1"` — `_renumber_ids` handles the rest.** Each `DrumBranch`/`InstrumentBranch` needs a full `MixerDevice` element (volume, pan, routing, speaker). Using `Id="1"` throughout as a placeholder is safe — the `_renumber_ids` pass assigns real unique IDs. Without `MixerDevice`, Live refuses to load the rack.

- **The fix is a new function `_reconstruct_branches_from_adg(gp, device)`** called before serialization in `_extract_device_from_adg`. It detects an empty `Branches` element, iterates `BranchPresets`, builds `DrumBranch`/`InstrumentBranch` elements, and appends them. Tested: Ironman Kit → 16 DrumBranch elements, each with 1 OriginalSimpler, correct ReceivingNote values.

- **The reference session `2Percent.als` is the authoritative structural template for branch XML.** Located at `ableton/sessions/Internal Project/2Percent.als`. Contains populated `DrumGroupDevice` with full 16-branch structure. Used to extract the `MixerDevice` template and verify `DrumBranch`/`InstrumentBranch` child ordering.

## What Failed and Why

- **Extracting `device` from `dev_wrapper` and serializing immediately** → resulted in empty racks. Live loaded the session, showed rack devices in tracks, but all racks had no pads/instruments. Root cause was the empty `Branches` — the rack shell was there, the content was not.

- **Assuming `Branches` inside the ADG `Device` would be populated** → wrong assumption. ADG is a *preset* format, not an *instance* format. Ableton appears to defer branch population to session load time when loading from the library — but `build_session.py` bypasses the library and inlines the device XML, so the `Branches` must be reconstructed manually.

## Decisions Made

| Decision | Reasoning |
|---|---|
| Use `copy.deepcopy` for each branch's inner device and MixerDevice | ET elements are mutable — sharing references between branches would cause all branches to point to the same object. `deepcopy` ensures independence. |
| Default drum pad ReceivingNote = `36 + i` if ZoneSettings is missing | MIDI note 36 = C1 (standard kick position). Sequential assignment upward gives each pad a unique note even if the preset lacks explicit mapping. |
| InstrumentBranch KeyRange default = full range (0–127) | Instrument rack single-branch presets (Noise Bass, pads) should respond to all notes. Narrowing the key range is the Sound Designer's call, not ours. |

## Correct Configurations / Commands

```bash
# Smoke test branch reconstruction for any ADG
python3 -c "
import xml.etree.ElementTree as ET, sys
sys.path.insert(0, 'scripts')
import build_session as bs
device_xml = bs._extract_device_from_adg('/path/to/Preset.adg')
root = ET.fromstring(device_xml)
branches = root.find('Branches')
print(f'Branches: {len(list(branches))}')
"

# Full session rebuild (now produces populated racks)
python3 scripts/build_session.py \
  --config ableton/m4l/configs/instrumental-convergence-v1.json \
  --out ableton/sessions/instrumental-convergence_v3.als \
  --verbose
```

## Open Questions

- [ ] Live has not confirmed whether the rebuilt v3 session loads without "corrupt" dialog — verify in Live immediately.
- [ ] TEX_Witness_Vocal is empty (intentional) — Granulator III + Gemini TTS audio still needed.
- [ ] Scene names still unnamed (7 scenes). Set via Remote Script or manually.
- [ ] BASS_Interrogator: Noise Bass pitch tracking unverified. Need to confirm before programming D/G# sequence.
- [ ] DRM_Grid_Perc_7_16: AG Techno Kit loaded but needs reprogramming to 7-step metallic loop.

## Next Session Priority

Confirm v3 session loads with populated racks in Live, then hand off to The Sound Designer to start `BASS_Interrogator` (D + G# tritone sequence) — it is the structural spine of INTERROGATION and nothing else in that section is evaluable until the bass is running.

---

# Session Learnings — 2026-04-25 (Checkpoint 4)

*Active song: Instrumental Convergence — D aeolian @ 72.0 BPM*
*Checkpoint: end of session — learnings compaction system built*

## What We Figured Out

- **Session learnings were being lost at context compaction — now fixed with a two-tier system.** Raw checkpoints go into `knowledge/sessions/YYYY-MM-DD-learnings.md` (append-only, multiple per session). At session end, `/compact-learnings` distills ALL learnings files into `knowledge/sessions/learnings-digest.md` via Gemini (pro tier). The digest is what the next session reads — not the raw files.

- **`/session-start` Step 0 is now mandatory digest reading.** Before brainstorm, before song-review, before anything else — Copilot reads `learnings-digest.md`. If it doesn't exist, `compact_learnings.py --no-llm` generates a fallback from bullet extraction. If any `*-learnings.md` is newer than the digest, that file is also read. This is the mechanism for cross-session knowledge persistence.

- **`compact_learnings.py` has a freshness check.** It skips regeneration if the digest is <12h old AND no learnings files are newer than it. Use `--force` to override. `--no-llm` skips Gemini and just extracts "What We Figured Out" bullets from each file. `--dry-run` prints without writing.

- **The digest is organized by topic, not by date.** Gemini is instructed to group entries under practical topic headers ("Ableton Session Build", "ADG Preset Format", "Agent Wiring", etc.) and end with a "Critical Rules" section — the 5–7 things that must never be forgotten. This makes it scannable in 30 seconds.

- **`/compact-learnings` is a new prompt** at `.github/prompts/compact-learnings.prompt.md`. It runs the script, reads the digest, verifies the Critical Rules section is correct, and flags anything missing. Should be run at end of any multi-checkpoint session.

## What Failed and Why

- Nothing failed in this work. The design was clear from the start of the task.

## Decisions Made

| Decision | Reasoning |
|---|---|
| Gemini `pro` tier for compaction | The digest is a high-stakes synthesis document — it needs to be accurate and well-organized. `fast` tier risks low-quality grouping that wastes more time than it saves. |
| `--no-llm` fallback as default when API unavailable | A partial digest (raw bullets) is better than no digest. The `/session-start` Step 0 can always generate something even offline. |
| Digest replaces per-file reading at session start | Raw learnings files grow unboundedly. If `/session-start` read all `*-learnings.md` files every time, the context cost would compound. The digest is the single compact reference. |
| `knowledge/sessions/learnings-digest.md` as the canonical path | Same directory as the raw files. Named clearly. Referenced by exact path in `copilot-instructions.md` "Always Useful" table. |

## Correct Configurations / Commands

```bash
# Generate digest with Gemini (end of session)
python scripts/compact_learnings.py

# Generate without Gemini (offline / CI fallback)
python scripts/compact_learnings.py --no-llm

# Force regenerate even if digest is fresh
python scripts/compact_learnings.py --force

# Dry run — print without writing
python scripts/compact_learnings.py --dry-run
```

```
# New prompt location
.github/prompts/compact-learnings.prompt.md   → invoke as /compact-learnings

# Updated prompt
.github/prompts/session-start.prompt.md       → Step 0 now reads learnings-digest.md

# Updated instructions
.github/copilot-instructions.md               → digest in "Always Useful" table
                                              → /compact-learnings in prompts table
                                              → updated session-start > note
```

## Open Questions

- [ ] `/compact-learnings` has not been run with live Gemini yet — `--no-llm` was tested and works, but the actual Gemini synthesis is untested this session. Run at session end to validate.
- [ ] All session changes are still uncommitted. Should be committed before session close.
- [ ] TEX_Witness_Vocal, scene names, BASS_Interrogator sequence, DRM_Grid_Perc_7_16 reprogramming — all still open from Checkpoint 3.

## Next Session Priority

Run `/compact-learnings` at the start (to generate the first real Gemini-synthesized digest), then hand off to The Sound Designer for BASS_Interrogator — the D + G# tritone is the spine of the whole arrangement.

---

# Session Learnings — 2026-04-25

*Active song: Instrumental Convergence — D aeolian @ 72 BPM*
*Checkpoint: 5 (Keyboard Shortcuts)*

## What We Figured Out

- **VS Code keybindings are always global** — there is no workspace-scoped `keybindings.json`. Scoping is achieved via the `when` clause using `workspaceFolderBasename == 'iron-static'`. This makes the bindings inert in any other workspace without needing a separate file.
- **Chord prefix pattern for agent management** — `cmd+a` was chosen as the agent chord prefix (mirrors `cmd+w` for workspace ops). All 14 bindings use this prefix with a second key. Falls through to native "select all" behavior in any non-iron-static workspace.
- **VS Code has no `chat.openWithAgent` command** — there is no single action to open a new chat AND switch to a specific agent. The workaround is: `cmd+a [1-9]` opens the agent `.agent.md` file in the editor, which can then be attached with `#` in the chat input. Agent selection in the chat dropdown remains a manual click.
- **`workbench.action.files.openFile` with `args.uri`** accepts `${workspaceFolder}` as a variable — can target workspace-relative files without hardcoding the absolute path.
- **Comments are valid in VS Code `keybindings.json`** — the file accepts `// ...` comments even though it's JSON-ish (JSONC). This breaks standard `json.load()` parsing from Python, but VS Code reads it fine.

## What Failed and Why

- **Python `json.load()` on keybindings.json** → fails because VS Code keybindings.json is JSONC (allows `//` comments). Use a JSONC-aware parser or strip comments first if scripting against it.
- **Trying to scope keybindings via a workspace settings file** → VS Code does not support workspace-level `keybindings.json`. Only `settings.json` is workspace-scoped. `when` context is the only solution.

## Decisions Made

| Decision | Reasoning |
|---|---|
| Use `cmd+a` as the agent chord prefix | Consistent with existing `cmd+w` (workspace) and `cmd+b` (sidebar) chord patterns already in the file |
| `cmd+a [1-9]` opens agent file rather than switching chat agent | VS Code limitation — no command exists to switch agent programmatically. Opening the file is the best available proxy. |
| Scope with `workspaceFolderBasename == 'iron-static'` | Cleaner than duplicating all bindings with negation clauses for other workspaces |

## Correct Configurations / Commands

```
# Full cmd+a chord reference (iron-static workspace only)
cmd+a cmd+a    → New chat session
cmd+a cmd+h    → Chat history picker
cmd+a cmd+q    → Quick chat popup
cmd+a cmd+f    → Focus chat panel
cmd+a cmd+e    → Open Copilot Edits view
cmd+a 1        → The Arranger
cmd+a 2        → The Sound Designer
cmd+a 3        → The Theorist
cmd+a 4        → The Critic
cmd+a 5        → The Live Engineer
cmd+a 6        → The Alchemist
cmd+a 7        → The Publicist
cmd+a 8        → The Visual Artist
cmd+a 9        → The Mix Engineer
```

```
# Other chord prefixes in keybindings.json
cmd+w          → Workspace management (add folder, save workspace, close, etc.)
cmd+b          → Sidebar / auxiliary bar toggles
cmd+e          → Editor / explorer panel toggles
cmd+j          → Panel toggles (maximize, show/hide)
cmd+g          → GitLens (blame, etc.)
cmd+l cmd+l    → Copilot model picker
cmd+m cmd+d    → Markdown preview (for .md, .prompt.md, .agent.md, .skill.md files)
```

## Open Questions

- [ ] `cmd+a cmd+a` (new chat) may conflict with "select all" in edge cases where the `when` context briefly evaluates wrong. Verify in practice.
- [ ] No `/show-shortcuts` prompt existed before this session — now created. Confirm it renders correctly in chat via `/show-shortcuts`.
- [ ] All session changes (keybindings, new prompt file, copilot-instructions.md) should be committed.

## Next Session Priority

Commit the uncommitted files (`copilot-instructions.md`, `learn-packs.prompt.md`, `show-shortcuts.prompt.md`), then run `/compact-learnings` to synthesize all five 2026-04-25 checkpoints into the digest before the next session.

---

# Session Learnings — 2026-04-25 (Checkpoint 3 — Arc naming + Ignition Point session)

*Active song: Ignition Point — E phrygian @ 116.0 BPM*
*Checkpoint: evening session*

## What We Figured Out

- **Arc is the in-band persona name for the Copilot AI half of IRON STATIC.** "Copilot" as a band-member name was turned off — too tool-flavored. "Arc" was chosen: electrical arc (spark that crosses the gap between Dave and the machine), compositional arc, short enough to say in the room. 19 persona replacements in `copilot-instructions.md`, 13 across SKILL files. "GitHub Copilot" and "VS Code Copilot chat" product references preserved.

- **GCS `blob.make_public()` is incompatible with uniform bucket-level access.** `iron-static-files` has uniform access enabled. Legacy ACL calls (including `make_public()`) return HTTP 400 "Cannot get legacy ACL for an object when uniform bucket-level access is enabled." Fix: grant `allUsers:objectViewer` at the bucket IAM level via `gsutil iam ch allUsers:objectViewer gs://iron-static-files`, then use the plain public URL (`https://storage.googleapis.com/{bucket}/{blob}`). Do NOT use `blob.generate_signed_url()` with ADC user credentials — ADC user tokens cannot sign (requires SA key or impersonation).

- **`blob.generate_signed_url()` with ADC user credentials raises `AttributeError: you need a private key to sign credentials`.** User OAuth tokens (`google.oauth2.credentials.Credentials`) don't have a private key. `generate_signed_url(version="v4")` requires service account credentials. The simpler path for public media is IAM-level public access, not signed URLs.

- **`scripts/midi_craft.py` has two duplicate `main()` and `euclidean_rhythm()` definitions.** The second `main()` (legacy flat-arg interface, drum-only) shadows the first (full subcommand interface with `clips` mode). `--song` and subcommands like `clips` are only in the first `main()` which never runs. The `euclidean_rhythm()` Bjorklund implementation also had a bug: returns empty list when hits divides evenly into steps. Fixed with Bresenham's line algorithm.

- **The correct `midi_craft.py` drum invocation (for now) is legacy flat args without a subcommand positional.** `python scripts/midi_craft.py --concept "..." --bpm 116 --steps 16` works. Adding `drum` as a positional arg causes "unrecognized arguments" because the second `main()` parses only flat args. Until the duplicate is resolved, avoid subcommands.

- **MIDI patterns for Ignition Point were crafted by hand with mido when `midi_craft.py` failed.** THE ANVIL (drums, Bresenham E(6,16) kick), THE SUBSTRATE (E2→F2 E Phrygian 2-bar bass), and THE SPARK (15-step E4/G4/B3 counter-rhythm, phases 1 step/bar) all written as inline mido code. Patterns pushed to Ableton tracks 0, 3, 4.

- **`load-preset` by name works when the preset `.adg` is on disk.** `python scripts/ableton_push.py load-preset --track 4 --preset "B.Beetlez Dark Dronepluck"` loaded the instrument onto the bare MIDI track correctly. The track name updates in Live to reflect the preset name. Presets indexed as "indexed but not found on disk" cannot be loaded this way.

- **`create-clip` must be called before `push-midi`.** Pushing MIDI into an empty slot returns "No clip in track N slot M". Always: `create-clip` → `push-midi`.

## What Failed and Why

- `python scripts/midi_craft.py --concept "..." drum` (with subcommand positional) → "unrecognized arguments: drum" — second `main()` runs, doesn't accept subcommands.
- `euclidean_rhythm(6, 16)` returned `[]` — Bjorklund implementation terminates early when `hits` divides evenly into `steps`. Fixed to Bresenham.
- `python scripts/generate_promo_image.py --output-prefix arc_intro` → "unrecognized arguments" — the flag doesn't exist. Use default output path and rename manually after generation.
- `blob.make_public()` on `iron-static-files` → HTTP 400 — uniform bucket-level access blocks legacy ACL. Fixed with `gsutil iam ch allUsers:objectViewer`.
- `blob.generate_signed_url(version="v4")` with ADC → `AttributeError: you need a private key` — user credentials can't sign. Don't use signed URLs with ADC.

## Decisions Made

| Decision | Reasoning |
|---|---|
| Arc as the in-band persona name | Electrical arc = spark crossing the gap between Dave and machine. Short, heavy, compositional meaning. "Copilot" reads as tool not partner. |
| `gsutil iam ch allUsers:objectViewer` on `iron-static-files` | Social media images need to be publicly accessible for Instagram's media container API to fetch them. Simpler than managing SA keys for signed URLs. Accept that social/ prefix is public. |
| `ignition-point` as Arc's first song | Deserves its own song rather than grafted onto `instrumental-convergence`. E Phrygian flat-2 = grinding, straining-against-structure sound. Gemini's brainstorm concept: phase transitions, system failure as chorus. |
| 15-step THE SPARK sequence | Phases 1 step each bar against the 16-step ANVIL — designed to never resolve, like a recurring system error. Brainstorm specified this exactly. |

## Correct Configurations / Commands

```bash
# Fix euclidean_rhythm: Bresenham's line (drop-in replacement for broken Bjorklund)
def euclidean_rhythm(hits, steps):
    pattern, bucket = [], 0
    for _ in range(steps):
        bucket += hits
        if bucket >= steps:
            bucket -= steps
            pattern.append(1)
        else:
            pattern.append(0)
    return pattern

# Make GCS bucket publicly readable (uniform access compatible)
gsutil iam ch allUsers:objectViewer gs://iron-static-files

# Post to Instagram with image + caption file
python scripts/post_instagram.py \
  --image outputs/social/brand_profile.png \
  --caption-file outputs/social/my_caption.txt

# Full Ignition Point session push sequence
python scripts/ableton_push.py set-tempo --bpm 116
python scripts/ableton_push.py create-clip --track 0 --clip 0 --length 2
python scripts/ableton_push.py push-midi --file midi/sequences/ignition-point_digitakt_v1.mid --track 0 --clip 0
python scripts/ableton_push.py load-preset --track 4 --preset "B.Beetlez Dark Dronepluck"
python scripts/ableton_push.py fire --track 0 --clip 0
python scripts/ableton_push.py fire --track 4 --clip 0

# Rename persona in all shared brain files (protects "GitHub Copilot" product refs)
python3 -c "
import re, glob
for path in ['.github/copilot-instructions.md'] + glob.glob('.github/skills/*/SKILL.md'):
    c = open(path).read()
    open(path,'w').write(re.sub(r'(?<!GitHub )Copilot', 'Arc', c))
"
```

## Open Questions

- [ ] `midi_craft.py` has duplicate `main()` and `euclidean_rhythm()` — needs cleanup so `clips` subcommand actually works with `--song ignition-point`. Currently the second `main()` shadows everything.
- [ ] THE SUBSTRATE bass (track 3 — "4-Noise Bass") has no instrument check — does the existing Noise Bass preset in that track produce usable E Phrygian sub? Needs ears.
- [ ] THE SPARK clip fired but the dark drone pluck may be too slow for a counter-rhythm role. May need to swap to a sharper Operator FM preset.
- [ ] `docs/fb_login.htm` + `docs/fb_login_files/` are untracked browser-saved HTML from the Facebook portal setup. Should be deleted.
- [ ] Brand images (`outputs/social/brand_profile.png`, `brand_repo.png`, arc intro image) should be uploaded to GCS via `gcs-audio` skill and added to `gcs_manifest.json`.
- [ ] GitHub repo social preview not set — upload `outputs/social/brand_repo.png` at github.com/djaboxx/iron-static/settings.

## Next Session Priority
Run `/compact-learnings` to distill today's three checkpoints into `learnings-digest.md`, then fire all three Ignition Point clips together and evaluate whether THE SPARK needs a sharper instrument.
