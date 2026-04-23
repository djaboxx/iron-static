# IRON STATIC — Database

This directory contains structured knowledge databases for the IRON STATIC rig. Data is stored as JSON for easy querying and editing, with potential SQLite migration for larger datasets.

## Files

| File | Contents |
|---|---|
| `instruments.json` | Canonical instrument registry with specs and MIDI channel assignments |
| `songs.json` | Song registry — lifecycle tracking from in-progress through release to archive |
| `presets_index.json` | Index of all presets across instruments |
| `sessions.json` | Session log — what was worked on, what came out of it |

---

## songs.json

Tracks every IRON STATIC song through its lifecycle. Managed with `scripts/manage_songs.py`.

**Lifecycle states**: `in-progress` → `active` → `released` → `archived`

- Exactly **one song should be `active`** at any time. Scripts and Copilot read the active song for context-aware generation.
- `released` songs are complete and out of active rotation.
- `archived` songs are shelved, abandoned, or non-canonical (e.g., test fixtures).

### Common commands

```bash
# Add a new song
python scripts/manage_songs.py add --slug dead-channel --title "Dead Channel" --key E --scale phrygian --bpm 138

# Set it as the active song (deactivates any previous active song)
python scripts/manage_songs.py activate --slug dead-channel

# See all songs and their status
python scripts/manage_songs.py list

# When released:
python scripts/manage_songs.py release --slug dead-channel

# Archive something that's shelved or was just a test fixture:
python scripts/manage_songs.py archive --slug dead-channel --reason "shelved after demo"
```

### What "active" unlocks

When a song is active, Copilot can use it for:
- Key/scale-aware MIDI generation via `midi_craft.py`
- Scene tempo config generation for `scene-tempo-map.amxd`
- Context injection in GitHub Actions brainstorm/theory workflows
- Correct file naming for MIDI, audio, and preset outputs

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
