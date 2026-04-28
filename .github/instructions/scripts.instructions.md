---
name: Scripts Conventions
description: Python scripting standards for all IRON STATIC automation scripts.
applyTo: "scripts/**"
---

## Architecture note

**New features belong in the VS Code extension (`vscode-extension/iron-static-bridge`), not here.**
Add LM tools to `src/lmTools.ts` + `package.json` schema and rebuild. Only write a new Python script for one-time batch operations with no interactive component. If in doubt, build it in the extension.

## Language and tooling
- Python 3.10+. Do not use Python 2 idioms.
- All scripts must be runnable with `/Users/darnold/venv/bin/python3` (project venv).
- MIDI I/O: use `python-rtmidi` (already in venv). Import as `import rtmidi`.
- OSC: use `python-osc` (`pythonosc`). Do not use raw sockets for OSC.
- Audio analysis: use `librosa` or `essentia`. Not `aubio`.

## Structure requirements
- Use `argparse` for all CLI arguments. No `sys.argv` indexing.
- Use `logging` (not `print`) for diagnostic output. Use `--verbose` / `-v` flag to control level.
- Guard with `if __name__ == "__main__":` always.
- Scripts must be idempotent: running twice with the same inputs must not corrupt state.

## Security
- Never embed credentials, API keys, or GCS bucket names in source. Use environment variables.
- Validate and sanitize any file paths derived from user input.
- Do not use `shell=True` in `subprocess` calls unless strictly necessary; prefer list form.

## Dependencies
- Add any new third-party imports to `scripts/requirements.txt`.
- Pin versions for reproducibility: `package==x.y.z`.

## File paths
- Always use `pathlib.Path` for file operations, not string concatenation.
- Resolve paths relative to workspace root (`Path(__file__).parent.parent`) not `os.getcwd()`.

## Output conventions
- MIDI files: `midi/sequences/[song-slug]_[instrument]_[version].mid`
- Preset JSON: `instruments/[instrument-slug]/presets/[slug].json`
- Logs and debug output: `outputs/` directory
