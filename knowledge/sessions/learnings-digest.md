# IRON STATIC — Session Learnings Digest
*Generated: 2026-04-25 from 1 session file(s)*

---

## Ableton Session Build
*   Use `build_session.py` to create a new session from a blueprint config; use `generate_als.py` to inject devices into an existing session.
*   The script must reconstruct `DrumBranch` and `InstrumentBranch` elements from an ADG's `BranchPresets` element.
*   The `Branches` element inside an ADG's `Device` definition is always empty and must be populated by the script.
*   Every reconstructed rack branch requires its own deep-copied `MixerDevice` template or Live will not load the rack.
*   The session at `ableton/sessions/Internal Project/2Percent.als` is the authoritative XML template for rack branch structure.

## ADG Preset Format
*   Rack content lives in `GroupDevicePreset > BranchPresets`, not `Device > DrumGroupDevice > Branches`.
*   Pack ADGs with `<RelativePath>` children cause "Base types can't have children" errors and must be fixed.
*   Drum pad MIDI note mapping is stored in `DrumBranchPreset > ZoneSettings > ReceivingNote`.
*   Instrument branch key mapping is stored in `InstrumentBranch > ZoneSettings > KeyRange`.
*   All rack branches, including instrument branches, use a `MidiToAudioDeviceChain`.

## Scripts
*   Build a new session from a blueprint:
    ```bash
    python3 scripts/build_session.py --config path/to/config.json --out path/to/session.als
    ```
*   Fix `RelativePath` errors in pack ADGs with this regex in `_extract_device_from_adg`:
    ```python
    re.sub(r'<RelativePath[^>]*>.*?</RelativePath>', '<RelativePath Value="" />', xml, flags=re.DOTALL)
    ```
*   Generate or update the learnings digest at session end:
    ```bash
    python3 scripts/compact_learnings.py
    ```
*   Use `compact_learnings.py --no-llm` for an offline fallback digest generation.

## Agent Wiring & Workflow
*   Critiques and learnings must be written to disk (`*-critique.md`, `*-learnings.md`) to survive context compaction.
*   The `/session-start` prompt must read `knowledge/sessions/learnings-digest.md` to persist knowledge.
*   The Critic agent evaluates aesthetic choices; The Theorist agent validates music theory.
*   Append mid-session discoveries to the daily learnings file using the `/checkpoint` prompt.
*   Agent handoff buttons must be designed for the specific *output type* (e.g., brainstorm text) not just the agent that created it.

## Critical Rules
*   ADG rack `Branches` are always empty; content is in `BranchPresets` and must be reconstructed by our script.
*   Pack ADG `<RelativePath>` elements must be replaced with `<RelativePath Value="" />` to prevent session load errors.
*   Use `build_session.py` for new sessions from a blueprint; do not misuse `generate_als.py`.
*   Always read the `learnings-digest.md` at session start to prevent re-discovering solved problems.
*   Every reconstructed rack branch needs its own `MixerDevice` template or the entire rack will be invalid.
*   Write critiques and learnings to disk via prompts (`/checkpoint`) before context is lost.