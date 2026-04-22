# IRON STATIC — Database

This directory contains structured knowledge databases for the IRON STATIC rig. Data is stored as JSON for easy querying and editing, with potential SQLite migration for larger datasets.

## Files

| File | Contents |
|---|---|
| `instruments.json` | Canonical instrument registry with specs and MIDI channel assignments |
| `presets_index.json` | Index of all presets across instruments |
| `sessions.json` | Session log — what was worked on, what came out of it |

---

## instruments.json

Canonical registry — one entry per instrument:

```json
{
  "instruments": [
    {
      "slug": "digitakt",
      "name": "Elektron Digitakt MK1",
      "type": "drum_machine_sampler",
      "midi_channels": [1, 2, 3, 4, 5, 6, 7, 8],
      "has_memory": true,
      "manual_path": "instruments/elektron-digitakt-mk1/manuals/",
      "presets_path": "instruments/elektron-digitakt-mk1/presets/"
    }
  ]
}
```
