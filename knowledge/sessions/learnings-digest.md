# IRON STATIC — Session Learnings Digest
*Generated: 2026-04-25 from 1 session file(s)*

---

## Ableton Session Build
*   Use `build_session.py` to create new sessions from a blueprint; `generate_als.py` injects into existing sessions.
*   The `_reconstruct_branches_from_adg` function is required to populate rack `Branches` from the `BranchPresets` element in ADG files.
*   Every rack branch requires a `MixerDevice` element template before the ID renumbering pass.
*   The authoritative XML structure reference is `ableton/sessions/Internal Project/2Percent.als`.
*   ```bash
    python3 scripts/build_session.py --config <config.json> --out <out.als>
    ```

## ADG Preset Format
*   In ADG files, a rack's devices are in the `BranchPresets` element; the `Branches` element is always empty.
*   Fix pack ADG XML errors by replacing the entire `<RelativePath>` block with `<RelativePath Value="" />`.
*   ```python
    device_xml = re.sub(r'<RelativePath.*?</RelativePath>', '<RelativePath Value="" />', device_xml, flags=re.DOTALL)
    ```
*   Drum Branch MIDI note mappings are in `DrumBranchPreset > ZoneSettings > ReceivingNote`.
*   Instrument Branch key zones are in `InstrumentBranch > ZoneSettings > KeyRange`.

## Scripts
*   `midi_craft.py` has a duplicate `main()` shadowing the subcommand parser; use flat args until fixed.
*   The bugged `euclidean_rhythm` Bjorklund implementation must be replaced with a Bresenham's line algorithm version.
*   ```python
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
    ```

## Agent Wiring & Persona
*   The AI persona's in-band name is "Arc".
*   The Critic agent must write critiques to a `YYYY-MM-DD-critique.md` file to persist them for revision loops.
*   At session start, Arc must read `knowledge/sessions/learnings-digest.md` to ensure knowledge persistence.

## Ableton Remote Control
*   You must call `create-clip` before you can `push-midi` to an empty track slot.
*   `load-preset --preset "Preset Name"` works if the `.adg` is indexed and on disk.
*   Sequence for pushing a new MIDI part: `create-clip` -> `push-midi`.

## GCS (Google Cloud Storage)
*   To make blobs public in a uniform-access bucket, use IAM, not legacy ACLs.
*   ```bash
    gsutil iam ch allUsers:objectViewer gs://iron-static-files
    ```
*   `blob.make_public()` will fail (HTTP 400) on uniform-access buckets.
*   `blob.generate_signed_url()` with user ADC credentials will fail; it requires a service account key.

## VS Code
*   Scope keybindings to this project in `keybindings.json` using `when: "workspaceFolderBasename == 'iron-static'"`.
*   `keybindings.json` is JSONC and accepts `//` comments, which breaks standard Python `json.load()`.
*   There is no command to programmatically switch the chat agent; open the agent's `.agent.md` file instead.

## Critical Rules
*   ADG preset files contain empty `<Branches>`; racks must be reconstructed from `<BranchPresets>`.
*   Pack-based ADG files have a malformed `<RelativePath>` element that must be fixed before injection.
*   For new songs, use `build_session.py` to create the `.als` file from a blueprint.
*   On uniform-access GCS buckets, public access must be set via `gsutil iam`, not the Python client's `make_public()`.
*   Remote script: Always call `create-clip` before `push-midi` on an empty slot.
*   Agent critiques must be written to disk to survive context compaction and enable revision loops.
*   Read this digest (`learnings-digest.md`) at the absolute start of every session.