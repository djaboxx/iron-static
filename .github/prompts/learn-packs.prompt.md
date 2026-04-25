---
description: Scan local Ableton Pack MIDI files, build statistical pattern profiles, commit to the repo, and surface the most useful profiles for the active song.
agent: agent
tools: [execute, read/problems, edit/editFiles, 'github/*', ms-python.python/getPythonEnvironmentInfo, ms-python.python/getPythonExecutableCommand, ms-python.python/installPythonPackage, ms-python.python/configurePythonEnvironment]
argument-hint: "optional: path to a specific pack directory (e.g. ~/Music/Ableton/Packs/Beat Tools)"
---

# Learn Packs

Scan all MIDI/ALC files in the local Ableton library, extract statistical pattern profiles, commit them, and surface the best ones for the active song context.

## Step 1: Check Dependencies

Verify `mido` is installed (required for `.mid` parsing):

```bash
python -c "import mido; print(mido.__version__)" 2>/dev/null || pip install mido
```

## Step 2: Run the Learn

If a specific pack directory was given as `${input:pack_dir:all packs}`, use it explicitly:

```bash
# Specific pack:
python scripts/pattern_learn.py learn-packs --pack-dir "${input:pack_dir:}"

# Or scan all packs (default — ~/Music/Ableton/Packs + User Library):
python scripts/pattern_learn.py learn-packs
```

This reads `.mid` and `.alc` files directly from disk — **no Live session required**.
Profiles are written to `midi/patterns/learned/packs/`.

## Step 3: Verify Output

```bash
python scripts/pattern_learn.py list
```

Check the count of new profiles. Note any parse errors or skipped files in the output.

## Step 4: Surface Active-Song-Relevant Profiles

Read `database/songs.json` to get the active song's `key`, `scale`, and `bpm`.

Then scan the new profiles in `midi/patterns/learned/packs/` and identify the 3–5 most useful ones for the current song:
- **Rhythmic match**: density and grid resolution that fits the song's BPM and feel
- **Pitch relevance**: `notes_used` that overlap with the active song's scale/key
- **Tonal character**: `is_melodic: false` for drum/perc patterns, `true` for melodic leads

Report them as a short list with file name + why each is relevant.

## Step 5: Commit

```bash
git add midi/patterns/learned/packs/
git commit -m "feat: learn pack pattern profiles from local Ableton library"
git push
```

## Step 6: Suggest Next Action

Based on the profiles surfaced in Step 4, propose one concrete next step:
- If a strong drum pattern was found: suggest `generate --profile <path> --push` to inject a variation into the active session
- If a melodic pattern fits the active scale: suggest it as a starting point for a MIDI craft session
- If nothing fits: note that and suggest running `midi-craft` from scratch instead
