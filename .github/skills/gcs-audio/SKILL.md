---
name: gcs-audio
description: Upload audio files (recordings, stems, samples, references) to GCS, update the manifest, and safely commit. Enforces the rule that audio never goes into git directly.
argument-hint: "[path or directory to upload] [optional: --tag song-slug --dry-run]"
user-invocable: true
disable-model-invocation: false
---

# Skill: gcs-audio

## What This Skill Does

Manages the full lifecycle for large audio files in the IRON STATIC repo:
1. Uploads audio file(s) to the GCS bucket via `scripts/gcs_sync.py`
2. Updates `database/gcs_manifest.json` with the new entries
3. Commits the manifest update so the repo tracks what's in GCS
4. Handles the reverse: pull a file from GCS back to local disk when needed

The pre-commit hook blocks any staged file in `audio/` that isn't in the manifest.
**This skill is the correct path for getting audio into the repo safely.**

## When to Use

- After recording a raw take and dropping it in `audio/recordings/raw/`
- After exporting stems from Ableton into `audio/recordings/stems/`
- After downloading a reference track into `audio/references/`
- After adding a new sample to `audio/samples/`
- When pulling a file back from GCS onto a new machine or after a fresh clone

## Directory Map

| Local path | Purpose | GCS prefix |
|---|---|---|
| `audio/recordings/raw/` | Raw session recordings | `audio/recordings/raw/` |
| `audio/recordings/stems/` | Exported Ableton stems | `audio/recordings/stems/` |
| `audio/references/` | Reference tracks for A/B | `audio/references/` |
| `audio/samples/drums/` | Drum samples | `audio/samples/drums/` |
| `audio/samples/synths/` | Synth samples | `audio/samples/synths/` |
| `audio/samples/fx/` | FX/texture samples | `audio/samples/fx/` |
| `audio/generated/` | Lyria / forge-generated audio | `audio/generated/` |

> **Note**: `audio/generated/specs/` contains `.md` spec files — these ARE committed to git normally.
> Only the audio files (`.mp3`, `.wav`) inside `audio/generated/` go to GCS.

## Workflow

### Push a single file
```bash
python scripts/gcs_sync.py push audio/recordings/raw/my-take.wav --tag rust-protocol
```

### Push an entire directory
```bash
python scripts/gcs_sync.py push audio/recordings/raw/ --tag rust-protocol
```

### Dry run first (see what would upload)
```bash
python scripts/gcs_sync.py push audio/recordings/raw/ --tag rust-protocol --dry-run
```

### Check what's in GCS vs. what's local
```bash
python scripts/gcs_sync.py status
python scripts/gcs_sync.py status --prefix audio/recordings/raw/
```

### Pull a file back from GCS
```bash
python scripts/gcs_sync.py pull audio/recordings/raw/my-take.wav
```

### After pushing — commit the updated manifest
```bash
git add database/gcs_manifest.json
git commit -m "chore: add [filename] to GCS [tag: song-slug]"
git push origin main
```

## Full Step-by-Step for a New Recording

1. Drop the file in the right directory (e.g. `audio/recordings/raw/`)
2. Run the push — always tag it with the active song slug:
   ```bash
   python scripts/gcs_sync.py push audio/recordings/raw/rust-protocol_raw_2026-04-23.wav --tag rust-protocol
   ```
3. Commit only the manifest (NOT the audio file):
   ```bash
   git add database/gcs_manifest.json
   git commit -m "chore: upload rust-protocol_raw_2026-04-23.wav to GCS"
   git push origin main
   ```
4. If you try to `git add` the audio file itself, the pre-commit hook will block the commit and tell you to run this skill first.

## What the Pre-Commit Hook Enforces

The hook at `.github/hooks/pre-commit` blocks commits that:
- Stage any file from `audio/recordings/`, `audio/references/`, or `audio/samples/` that is NOT in `database/gcs_manifest.json`
- Stage any file over 5 MB that isn't an LFS pointer

Error message you'll see if you try to skip this:
```
[pre-commit] COMMIT BLOCKED — large file violations:
  BLOCKED: audio/recordings/raw/my-take.wav (42.3 MB)
    → This file lives in a GCS-managed directory.
      Upload it first:  python scripts/gcs_sync.py push audio/recordings/raw/ --tag <song>
      Then re-stage the updated database/gcs_manifest.json and try again.
```

## Auth Notes

### Local (Dave's machine)
Uses gcloud ADC — no extra setup needed if `gcloud auth application-default login` was run once.
```bash
gcloud auth application-default login
```

### GitHub Actions (CI)
The `gcs-sync.yml` workflow uses `GCS_SA_KEY` secret + `GCS_BUCKET` repo variable. These are already configured in the repo.

## Manifest Format

`database/gcs_manifest.json` tracks every file in GCS:
```json
{
  "bucket": "iron-static-files",
  "last_updated": "2026-04-23T...",
  "files": {
    "audio/recordings/raw/rust-protocol_raw_2026-04-23.wav": {
      "sha256": "abc123...",
      "size": 44369920,
      "uploaded": "2026-04-23T...",
      "tags": ["rust-protocol"]
    }
  }
}
```

## File Naming Convention

Follow the repo convention for audio files:
```
[category]_[description]_[bpm][key].[ext]
```
Examples:
- `rust-protocol_raw-take1_95bpm-Aphrygian.wav`
- `drums_kick-heavy_95bpm.wav`
- `ref_lambofgod-redneck.mp3`

## Checking GCS Is Configured

```bash
# Verify bucket is set
echo $GCS_BUCKET

# List everything in the bucket
python scripts/gcs_sync.py status
```

If `GCS_BUCKET` is empty, check the GitHub Actions repo variable or set it locally:
```bash
export GCS_BUCKET=iron-static-files
```

## Generated Audio (Lyria / forge-audio)

`audio/generated/` has two layers:
- `audio/generated/specs/` — spec `.md` files → **committed to git normally**
- `audio/generated/*.mp3` / `*.wav` — Lyria output → **GCS only, never git**

When `gemini_forge.py --generate` runs successfully it auto-pushes the audio file to GCS
(if `GCS_BUCKET` is set). If not, it prints the manual command.

### Manual upload after local forge run
```bash
# Upload a specific generated file
python scripts/gcs_sync.py push audio/generated/rust-protocol_kick-loop_2026-04-24.mp3 --tag rust-protocol

# Commit only the manifest
git add database/gcs_manifest.json
git commit -m "chore: upload rust-protocol_kick-loop_2026-04-24.mp3 to GCS"
```

### Pull a generated file to a new machine
```bash
python scripts/gcs_sync.py pull audio/generated/rust-protocol_kick-loop_2026-04-24.mp3
```

### Run forge-audio from CI (generates + auto-pushes to GCS)
Use the `forge-audio.yml` workflow via `gh workflow run` or the GitHub Actions UI:
```bash
gh workflow run forge-audio.yml \
  -f target="kick loop" \
  -f context="grimy 808 sub, A phrygian dominant, 95 BPM" \
  -f generate_audio=true \
  -f lyria_model=clip
```

