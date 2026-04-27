# Ableton Session & Clip Learning Plan

> **Goal**: Build a systematic, queryable knowledge map of every `.als` session and `.alc` clip on disk — our own projects, User Library templates, Pack demo sets, and Splice backups — so Arc can pull patterns, device chains, and structural ideas when building new sessions or generating MIDI.

---

## Current State (April 2026)

### What we already have

| Script | Does what | Gaps |
|---|---|---|
| `scripts/parse_als.py` | Parses a single `.als` → JSON summary + clips CSV + devices JSON | Single-file only; no key/scale detection; raw XML snippets for devices, not clean chains |
| `scripts/extract_midi_clips.py` | Extracts MIDI notes from `.als` → one `.mid` per clip | Single-file only; needs BPM context to be accurate |
| `scripts/pattern_learn.py` | Learns rhythm + pitch profiles from live clips or `.mid`/`.alc` files; generates variations | Requires running Live OR pre-separated `.mid` files; no disk scanner; no ALC standalone mode |
| `scripts/index_pack_presets.py` | Indexes `.adv`/`.adg` preset files → `database/pack_presets.json` | Doesn't touch `.als` or `.alc` |
| `.github/prompts/learn-packs.prompt.md` | Runs `pattern_learn.py learn-packs` on Pack dirs | Scope limited to Packs; no personal projects; no knowledge map |

### What's on disk

From `find ~ -name "*.als"` (April 2026):

| Category | Count (approx.) | Example paths |
|---|---|---|
| **Personal projects** | ~20 | `~/Jams/BlackSanta`, `~/Desktop/MetalCore/Grinder`, `~/Desktop/ThisAintHard`, `~/MusicScraps/Ventura Project` |
| **User Library templates** | ~8 | `~/Music/Ableton/User Library/Templates/`, `ChannelStrips/`, `Defaults/` |
| **Ableton Pack demo sets** | ~70 | `~/Music/Ableton/Packs/Beat Tools/Sets/`, `Building Max Devices/`, `Max for Live Essentials/` |
| **Splice backups** | ~15 | `~/Library/Application Support/com.splice.Splice/studio/backup/` |
| **Desktop templates** | ~5 | `~/Desktop/Templates/BrewstersSession`, `~/Desktop/Basic Project/` |

ALC files: concentrated in Pack `MIDI Clips/` folders (e.g., `Trap Drums by Sound Oracle` has 40+ rhythm + 808 bass clips). More exist in other packs not yet counted.

---

## What We're Building

A six-phase pipeline:

```
DISCOVER → PARSE → PROFILE → CATALOG → MAP → QUERY
```

Each phase produces durable artifacts committed to the repo. Phases are idempotent — re-running updates only changed/new files.

---

## Phase 1: Discovery

**New script**: `scripts/scan_ableton_library.py`

Walks a configurable list of search roots (default: `~`, excluding system directories), finds all `.als` and `.alc` files, classifies each, and writes a discovery manifest.

### Classification rules

| Class | Detection heuristic |
|---|---|
| `personal_project` | Path under `~/Jams/`, `~/Desktop/`, `~/MusicScraps/`, `~/git/*/ableton/sessions/` |
| `user_template` | Path under `~/Music/Ableton/User Library/` |
| `pack_demo` | Path under `~/Music/Ableton/Packs/` |
| `splice_backup` | Path under `~/Library/Application Support/com.splice.Splice/` |
| `iron_static` | Path under `~/git/iron-static/ableton/sessions/` |
| `unknown` | Anything else |

### Deduplication

Splice backups often contain multiple timestamped copies of the same project. The scanner should:
- Group by project slug (directory name stripped of timestamps)
- Keep only the **most recent** copy per slug
- Flag others as `duplicate: true` in the manifest (don't parse them)

### Output

`database/ableton_discovery.json`:

```json
{
  "generated_at": "2026-04-27T00:00:00Z",
  "als_files": [
    {
      "path": "/Users/darnold/Desktop/MetalCore/Grinder Project/Grinder.als",
      "class": "personal_project",
      "slug": "grinder",
      "mtime": "2025-05-12T12:00:00",
      "size_bytes": 48200,
      "duplicate": false
    }
  ],
  "alc_files": [
    {
      "path": "/Users/darnold/Music/Ableton/Packs/Trap Drums by Sound Oracle/MIDI Clips/Beacon Kit 70 bpm.alc",
      "class": "pack_demo",
      "pack_name": "Trap Drums by Sound Oracle",
      "mtime": "2023-01-10T12:00:00",
      "size_bytes": 3100
    }
  ],
  "stats": {
    "als_total": 122,
    "alc_total": 87,
    "als_by_class": {"personal_project": 20, "user_template": 8, "pack_demo": 72, "splice_backup": 0, "iron_static": 4},
    "skipped_duplicates": 15
  }
}
```

**CLI**:
```bash
python scripts/scan_ableton_library.py \
  --roots ~ \
  --exclude "~/Library/Application Support/com.splice.Splice" \
  --output database/ableton_discovery.json
```

---

## Phase 2: Batch Parsing

**Extended script**: `scripts/parse_als.py` gains a `--batch` mode (and a new `scripts/parse_alc.py` for ALC-only).

### ALS batch parse

For each non-duplicate ALS in the discovery manifest, extract:

1. **Session metadata**: creator, Ableton version, tempo(s), time signature(s), scene count, scene names
2. **Track list**: name, type (MIDI/Audio/Return/Master), device chain summary, clip slot count
3. **Device chains**: per track — ordered list of device names + types (Ableton native vs. VST/AU). Don't store the raw XML; store structured records.
4. **MIDI clip inventory**: all session + arrangement clips with name, length (bars), notes count, is_drum (channel 10 or track name heuristic)
5. **Key/scale**: read from `LiveSet/Scale/RootNote` and `LiveSet/Scale/ScaleName` (Live 12 stores this). Fall back to MIDI note analysis if not present.
6. **BPM**: from `LiveSet/MasterTrack/AutomationEnvelopes` + `Tempo` node

### ALC parse

ALC files are also gzipped XML. Their root is a `<LiveSet>` with a single `<MidiClip>` or `<AudioClip>` node.

**New script**: `scripts/parse_alc.py`

Extract:
- Clip name (from filename if not in XML)
- Length in beats
- All notes: pitch, start_time, duration, velocity
- Is-drum heuristic: check if pitches are all < 35 or names contain "Kit", "Drum", "Perc"
- BPM hint from filename (e.g., "70 bpm" in "Beacon Kit 70 bpm.alc")

### Key/scale detection from MIDI notes

When Live's stored scale is absent (older projects), detect key by:
1. Histogram of all note pitches (mod 12 = pitch class)
2. Correlate against all 12 major + 7 modal profiles (Krumhansl-Schmuckler simplified)
3. Store `detected_key`, `detected_scale`, `detection_confidence` (0.0–1.0)

This is a ~40-line function. Add to `scripts/parse_als.py` as `detect_key_from_notes(note_list)`.

### Output

Each parsed session writes to `database/ableton_catalog/` (one JSON per source file, named by slug):

```
database/ableton_catalog/
  grinder.json
  thisainthard.json
  ventura.json
  beat-tools--in-the-heart.json
  trap-drums--beacon-kit-70bpm.alc.json
  ...
```

The catalog entry schema:

```json
{
  "source_path": "/Users/darnold/Desktop/MetalCore/Grinder Project/Grinder.als",
  "class": "personal_project",
  "slug": "grinder",
  "ableton_version": "11.3",
  "tempo": 138.0,
  "time_signature": "4/4",
  "scene_count": 8,
  "track_count": 12,
  "key": "E",
  "scale": "phrygian",
  "key_source": "live_stored",
  "tracks": [
    {
      "name": "Kick",
      "type": "MidiTrack",
      "is_drum": true,
      "clip_count": 4,
      "devices": [
        {"name": "Drum Rack", "type": "native"},
        {"name": "Compressor", "type": "native"}
      ]
    }
  ],
  "clips": [
    {
      "name": "Intro Kick",
      "track": "Kick",
      "length_bars": 2,
      "notes_count": 16,
      "is_drum": true,
      "midi_file": "midi/patterns/learned/grinder/grinder_kick_intro.mid"
    }
  ],
  "device_chain_fingerprint": "DrumRack+Compressor|Wavetable+AutoFilter+Reverb|Operator+EQ8",
  "parsed_at": "2026-04-27T00:00:00Z"
}
```

**CLI**:
```bash
# Batch parse all ALS in discovery manifest
python scripts/parse_als.py --batch database/ableton_discovery.json \
  --catalog-dir database/ableton_catalog \
  --extract-midi midi/patterns/learned

# Parse a single ALC
python scripts/parse_alc.py \
  "/Users/darnold/Music/Ableton/Packs/Trap Drums by Sound Oracle/MIDI Clips/Beacon Kit 70 bpm.alc" \
  --catalog-dir database/ableton_catalog
```

---

## Phase 3: Pattern Profiling

**Existing script**: `scripts/pattern_learn.py` — extend with `learn-catalog` subcommand.

For every `.mid` file extracted in Phase 2 (stored in `midi/patterns/learned/`), run the existing `analyze_rhythm` + `analyze_pitch` + `analyze_velocity` pipeline. Write profiles to `midi/patterns/learned/<slug>/`.

Also directly parse every ALC from the discovery manifest using `parse_alc.py` output — no intermediate `.mid` needed.

Profile schema (already established in `pattern_learn.py`):
```json
{
  "source_slug": "grinder",
  "source_class": "personal_project",
  "clip_name": "Intro Kick",
  "track_name": "Kick",
  "is_drum": true,
  "bpm": 138.0,
  "length_beats": 8.0,
  "rhythm": {"density": 0.5, "grid": "16th", "euclidean_approx": [8, 16], "swing_ratio": 1.02},
  "pitch": {"is_melodic": false, "root_note": 36, "notes_used": [36, 38, 42, 46], "range_semitones": 10},
  "velocity": {"mean": 100, "std": 15, "humanized": true},
  "tags": ["kick", "drum", "16th", "8-bar"]
}
```

**New field**: `source_class` — lets Arc filter by "only personal projects" or "only packs" when matching.

**CLI**:
```bash
python scripts/pattern_learn.py learn-catalog \
  --catalog-dir database/ableton_catalog \
  --midi-dir midi/patterns/learned \
  --output-dir midi/patterns/learned/profiles
```

---

## Phase 4: Knowledge Catalog

**New script**: `scripts/build_ableton_knowledge.py`

Aggregates all catalog entries + pattern profiles into:

1. `database/ableton_catalog.json` — flat array of all catalog entries, optimized for programmatic query
2. `database/device_chain_index.json` — unique device chains seen across all sessions, with frequency counts
3. `database/session_structure_index.json` — common session structures (track naming conventions, typical track counts, scene counts by genre/class)

### Device chain index structure

```json
{
  "chains": [
    {
      "fingerprint": "DrumRack+Compressor+DrumBuss",
      "seen_in": ["grinder", "ventura", "beat-tools--the-grind"],
      "count": 3,
      "typical_track_role": "drums"
    },
    {
      "fingerprint": "Wavetable+AutoFilter+EQ8+Reverb",
      "seen_in": ["thisainthard", "deranged"],
      "count": 2,
      "typical_track_role": "pad"
    }
  ]
}
```

This is the "map of knowledge" — after processing all sessions, we know which device chains appear repeatedly, what they're typically used for, and which sessions demonstrate them best.

---

## Phase 5: Knowledge Map Generation

**New script**: `scripts/generate_ableton_knowledge_map.py`

Reads the catalog + indexes and writes structured markdown to `knowledge/ableton/`:

```
knowledge/ableton/
  README.md              — index + how-to-query
  sessions-map.md        — all sessions, classified, with key stats
  device-chains.md       — device chains by role, most-used first
  patterns-library.md    — pattern profiles by type (drum, bass, lead, pad) + key/scale
  templates-guide.md     — User Library templates + what each one sets up
  pack-clips.md          — ALC clips by pack + role tag
```

### sessions-map.md structure

```markdown
## Personal Projects

| Slug | BPM | Key/Scale | Tracks | MIDI Clips | Notable chains |
|---|
| grinder | 138 | E Phrygian | 12 | 28 | DrumRack+Comp, Wavetable+AutoFilter |
| ventura | 108 | — | 8 | 14 | Operator+EQ8, Pigments+Reverb |

## Templates

| Slug | Purpose | Tracks |
|---|
| brewsters-session | Full band template | 16 |
| simple-pigments | Pigments-only template | 4 |
```

### patterns-library.md structure

```markdown
## Drum Patterns (sorted by density)

| Slug | Clip | BPM | Grid | Density | Source |
|---|
| grinder_kick_intro | Intro Kick | 138 | 16th | 0.50 | personal_project |
| trap-drums--beacon-kit | Beacon Kit | 70 | 16th | 0.44 | pack_demo |

## Melodic Patterns — E Phrygian

| Slug | Clip | BPM | Notes used | Range | Source |
|---|
| thisainthard_bass_v1 | Bass Riff 1 | 140 | E2 G2 A2 B2 | 7st | personal_project |
```

---

## Phase 6: Arc Integration

### Active-song query

**New script**: `scripts/query_ableton_catalog.py`

Given the active song's key, scale, BPM, reads `database/ableton_catalog.json` + pattern profiles and returns:

1. **Best matching clips** — patterns whose key/scale overlap with the active song + BPM within ±20%
2. **Template suggestions** — sessions whose structure fits the active song's track count / section count
3. **Device chain suggestions** — chains seen in similar-tempo personal projects

```bash
python scripts/query_ableton_catalog.py \
  --key E --scale phrygian --bpm 108 \
  --top 5
```

Output goes to `outputs/catalog_query.json` + printed as a human-readable list.

### Arc reads this at session start

Add to `/session-start` prompt Step 0:
> If `database/ableton_catalog.json` exists, read `knowledge/ableton/sessions-map.md` and `knowledge/ableton/patterns-library.md` for session context.

---

## New Scripts Summary

| Script | Purpose | Inputs | Outputs |
|---|---|---|---|
| `scan_ableton_library.py` | Discover all ALS + ALC on disk | Search roots config | `database/ableton_discovery.json` |
| `parse_als.py` (extended) | Batch-parse ALS → catalog entries + MIDI | Discovery manifest | `database/ableton_catalog/` + `midi/patterns/learned/` |
| `parse_alc.py` (new) | Parse a single ALC → clip profile | ALC path | `database/ableton_catalog/*.alc.json` |
| `pattern_learn.py` (extended) | Profile all learned MIDI from catalog | Catalog dir + MIDI dir | `midi/patterns/learned/profiles/` |
| `build_ableton_knowledge.py` | Aggregate catalog → indexes | Catalog dir + profiles | `database/ableton_catalog.json`, `device_chain_index.json`, `session_structure_index.json` |
| `generate_ableton_knowledge_map.py` | Catalog + indexes → markdown | Catalog + indexes | `knowledge/ableton/*.md` |
| `query_ableton_catalog.py` | Query catalog against active song | Active song context | `outputs/catalog_query.json` |

---

## New Skill

A new skill `learn-als` (or expand `parse-als`) should document the full pipeline run order:

```bash
# Full pipeline — run once to bootstrap, re-run when new sessions are added
python scripts/scan_ableton_library.py
python scripts/parse_als.py --batch database/ableton_discovery.json --catalog-dir database/ableton_catalog --extract-midi midi/patterns/learned
python scripts/pattern_learn.py learn-catalog --catalog-dir database/ableton_catalog --midi-dir midi/patterns/learned
python scripts/build_ableton_knowledge.py
python scripts/generate_ableton_knowledge_map.py
```

And a query command Arc can run mid-session:

```bash
python scripts/query_ableton_catalog.py --key E --scale phrygian --bpm 108 --top 5
```

---

## Update `/learn-packs` Prompt

The existing `/learn-packs` prompt only covers `~/Music/Ableton/Packs` and `~/Music/Ableton/User Library`. It should be updated to invoke the full pipeline above, not just `pattern_learn.py learn-packs`. The new prompt should:

1. Run `scan_ableton_library.py` (or just ALS if specifically invoked for packs)
2. Batch-parse all discovered files
3. Run `pattern_learn.py learn-catalog`
4. Run `build_ableton_knowledge.py` + `generate_ableton_knowledge_map.py`
5. Run `query_ableton_catalog.py` with active song context
6. Surface the 3–5 best matches

---

## Priority Build Order

1. **`scan_ableton_library.py`** — the foundation. Nothing else runs without the discovery manifest.
2. **`parse_als.py --batch` + `parse_alc.py`** — the data. All downstream depends on clean catalog entries.
3. **`build_ableton_knowledge.py`** — the aggregation. Turns individual entries into searchable indexes.
4. **`generate_ableton_knowledge_map.py`** — the output Arc reads.
5. **`query_ableton_catalog.py`** — active-song matching, highest day-to-day value.
6. **`pattern_learn.py learn-catalog`** — the deepest analysis layer, run last.

---

## What This Unlocks

After this pipeline runs on the 120+ ALS files and 80+ ALC files on disk:

- Arc knows which device chains Dave actually uses (not just what's theoretically possible)
- Arc can say "your `Grinder` session used `Wavetable + AutoFilter + EQ8` for bass — that might work here"
- Arc can pull drum patterns from personal projects that match the active song's BPM within 20%
- Arc can identify structural templates (`BrewstersSession` has 16 tracks with 8 scenes — use it as scaffold)
- Pattern profiler finds MIDI clips in Pack libraries that overlap with E Phrygian and can be transposed
- The knowledge map is committed to the repo — every future session starts with it already loaded
