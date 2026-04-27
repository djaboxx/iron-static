# IRON STATIC — Database

This directory contains structured knowledge databases for the IRON STATIC rig. Data is stored as JSON for easy querying and editing, with potential SQLite migration for larger datasets.

## Files

| File | Contents | Managed by |
|---|---|---|
| `instruments.json` | Canonical instrument registry with specs and MIDI channel assignments | hand-edited |
| `songs.json` | Song registry — lifecycle tracking from in-progress through release to archive | `scripts/manage_songs.py` |
| `voices.json` | Voice/persona registry — VELA and any future named voices, with prompts and MIDI ranges | hand-edited |
| `feeds.json` | RSS/Atom feed registry consumed by `feed-digest.yml` and `scripts/run_feed_digest.py` | hand-edited |
| `plugins.json` | VST/AU plugin inventory scanned from the system | `scripts/scan_plugins.py` |
| `ableton_devices.json` | Live 12 stock device parameter map (Operator, Wavetable, Drum Rack, etc.) | `scripts/discover_devices.py` |
| `device_library.json` | Combined library of native + plugin devices used for session generation | `scripts/build_db.py` |
| `pack_presets.json` | Index of `.alc`/`.adg`/`.mid` content from installed Ableton Packs | `scripts/index_pack_presets.py` |
| `gcs_manifest.json` | Manifest of audio assets stored in the GCS bucket (path → checksum/size/uploaded_at) | `scripts/gcs_sync.py` |
| `iron_static.db` | SQLite mirror of selected JSON tables for fast queries (built on demand) | `scripts/build_db.py` |
| `midi_params/` | Per-instrument MIDI CC and parameter maps (`<slug>.json`) used by `push_preset.py`, `midi_control.py` | hand-edited / extracted from manuals |

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
