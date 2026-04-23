# SKILL: parse-als

## Purpose
Parse Ableton Live `.als` project files (gzipped XML) and extract a machine-readable summary including:
- track list and per-track device references
- session and arrangement clip metadata
- global tempo and time signature
- CSV export of clip ranges and a JSON index of devices

This skill is intended to be used by Copilot agents to automate project audits, clip mapping, and device inventory.

## Usage
Run the helper script:

```bash
source .venv/bin/activate
python3 scripts/parse_als.py "/path/to/Project.als" outputs/project_summary.json
```

The script writes:
- `outputs/project_summary.json` — main JSON summary
- `outputs/Project_clips.csv` — CSV of session + arrangement clips
- `outputs/Project_devices.json` — per-track device index

## When to Use
- Auditing large Ableton projects for clip ranges and instrument usage
- Preparing migration or offline analysis of projects
- Building tooling to map MIDI clips to external hardware

## Limitations
- Ableton stores some device/plugin metadata in external project folders; the exported `.als` may not include full preset files. When devices are not listed inline, look in the Live Project `Devices`/`Presets` folders or the bundled `User Library`.
- Plugin/device details may be partial (name present, but not vendor/preset). The script reports raw XML snippets to aid manual resolution.

## Next Steps
- Add a helper to scan an Ableton Project folder to find referenced plugin preset files.
- Extract MIDI note data into MIDI files per clip (future enhancement).
