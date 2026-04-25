#!/usr/bin/env python3
"""
pattern_learn.py — learn MIDI patterns from live Ableton clips, then generate
variations in a complementary but distinct style.

The learning pipeline:
  1. Pull clip notes directly from a running Live session (via IronStatic Remote Script)
  2. Analyze the pattern: rhythm grid, pitch vocabulary, velocity shaping, density
  3. Store a profile JSON to midi/patterns/learned/<song>_<track>_<slot>.json
  4. Generate new patterns that are statistically inspired by what you built —
     same density range, same pitch palette, different rhythmic choices.

Usage:
    # Learn all clips that have notes
    python scripts/pattern_learn.py learn --all

    # Learn a specific clip
    python scripts/pattern_learn.py learn --track 0 --slot 0

    # Generate a new pattern inspired by learned profiles
    python scripts/pattern_learn.py generate --profile midi/patterns/learned/rust-protocol_0_0.json

    # List learned profiles
    python scripts/pattern_learn.py list

    # Inspect a profile
    python scripts/pattern_learn.py show --profile midi/patterns/learned/rust-protocol_0_0.json
"""

import argparse
import json
import logging
import math
import random
import sys
from pathlib import Path

log = logging.getLogger(__name__)

LEARNED_DIR = Path("midi/patterns/learned")
GENERATED_DIR = Path("midi/patterns/generated")
PACKS_DIR = Path("midi/patterns/learned/packs")
REFERENCES_DIR = Path("midi/patterns/learned/references")

# --------------------------------------------------------------------------
# Pattern analysis
# --------------------------------------------------------------------------

def analyze_rhythm(notes: list[dict], clip_length: float) -> dict:
    """Extract rhythmic features from a note list."""
    if not notes:
        return {"density": 0.0, "hit_positions": [], "ioi": [], "grid": "16th",
                "euclidean_approx": [0, 16], "swing_ratio": 1.0}

    # Quantize to a 64th-note grid (resolution 0.0625 beats = 1/64)
    resolution = 0.0625
    grid_slots = int(round(clip_length / resolution))
    hit_set = set()
    for n in notes:
        slot = int(round(n["start_time"] / resolution))
        hit_set.add(slot % grid_slots)

    hit_positions = sorted(n["start_time"] for n in notes)
    # Inter-onset intervals
    ioi = [hit_positions[i+1] - hit_positions[i] for i in range(len(hit_positions)-1)]
    if hit_positions:
        ioi.append(clip_length - hit_positions[-1] + hit_positions[0])  # wrap

    # Dominant grid: find the smallest interval that's common
    if ioi:
        min_ioi = min(i for i in ioi if i > 0.001)
        if min_ioi <= 0.125 + 0.02:
            grid = "16th"
        elif min_ioi <= 0.25 + 0.02:
            grid = "8th"
        else:
            grid = "quarter"
    else:
        grid = "16th"

    # Grid slots for density calculation
    grid_res = {"16th": 0.25, "8th": 0.5, "quarter": 1.0}[grid]
    total_slots = int(clip_length / grid_res)
    density = len(hit_set) / max(total_slots, 1)

    # Closest Euclidean approximation: [hits, steps] in 16th-note grid
    sixteen_slots = int(clip_length / 0.25)
    hits_16th = sum(1 for n in notes if True)  # count unique 16th-note positions
    euclid_hits = min(hits_16th, sixteen_slots)

    # Swing detection: compare even/odd 8th note positions
    even_onsets = [n["start_time"] for n in notes if (int(n["start_time"] / 0.25)) % 2 == 1]
    expected_offbeat = 0.25  # straight 8ths
    if even_onsets:
        avg_offset = sum(t % 0.5 for t in even_onsets) / len(even_onsets)
        swing_ratio = avg_offset / expected_offbeat if expected_offbeat > 0 else 1.0
    else:
        swing_ratio = 1.0

    return {
        "density": round(density, 3),
        "hit_positions": [round(p, 4) for p in hit_positions],
        "ioi": [round(i, 4) for i in ioi],
        "grid": grid,
        "euclidean_approx": [euclid_hits, sixteen_slots],
        "swing_ratio": round(swing_ratio, 3),
    }


def analyze_pitch(notes: list[dict]) -> dict:
    """Extract pitch and melodic features."""
    if not notes:
        return {"notes_used": [], "intervals": [], "register": "mid",
                "is_melodic": False, "pitch_distribution": {}}

    pitches = sorted(set(n["pitch"] for n in notes))
    ordered = [n["pitch"] for n in sorted(notes, key=lambda x: x["start_time"])]

    # Intervals between consecutive pitches
    intervals = [abs(ordered[i+1] - ordered[i]) for i in range(len(ordered)-1)]

    # Register: median pitch
    median_pitch = sorted(n["pitch"] for n in notes)[len(notes)//2]
    if median_pitch < 48:
        register = "low"
    elif median_pitch < 72:
        register = "mid"
    else:
        register = "high"

    # Melodic vs. rhythmic: if pitch range > 2 semitones it's melodic
    pitch_range = max(pitches) - min(pitches) if pitches else 0
    is_melodic = pitch_range > 2

    # Distribution: pitch → count
    dist = {}
    for n in notes:
        k = str(n["pitch"])
        dist[k] = dist.get(k, 0) + 1

    return {
        "notes_used": pitches,
        "intervals": intervals,
        "register": register,
        "is_melodic": is_melodic,
        "pitch_range": pitch_range,
        "pitch_distribution": dist,
    }


def analyze_velocity(notes: list[dict]) -> dict:
    """Extract velocity dynamics."""
    if not notes:
        return {"mean": 100, "variance": 0, "accents": [], "profile": []}

    vels = [n["velocity"] for n in notes]
    mean = sum(vels) / len(vels)
    variance = sum((v - mean) ** 2 for v in vels) / len(vels)

    # Find accent positions: notes with velocity > mean + 1 std dev
    std = math.sqrt(variance)
    accents = [i for i, n in enumerate(
        sorted(notes, key=lambda x: x["start_time"])) if n["velocity"] > mean + std]

    return {
        "mean": round(mean, 1),
        "variance": round(variance, 1),
        "std": round(std, 1),
        "accents": accents,
        "profile": vels,
    }


def build_profile(track_index: int, slot_index: int, track_name: str,
                  clip_data: dict, song_meta: dict) -> dict:
    """Build a full analysis profile from raw clip note data."""
    notes = clip_data.get("notes", [])
    clip_length = clip_data.get("clip_length", 4.0)

    return {
        "source": {
            "song":         song_meta.get("slug", "unknown"),
            "track_index":  track_index,
            "track_name":   track_name,
            "slot_index":   slot_index,
            "clip_name":    clip_data.get("clip_name", ""),
        },
        "meta": {
            "bpm":          song_meta.get("bpm", 120.0),
            "key":          song_meta.get("key", "?"),
            "scale":        song_meta.get("scale", "?"),
            "length_beats": clip_length,
            "note_count":   len(notes),
        },
        "rhythm":   analyze_rhythm(notes, clip_length),
        "pitch":    analyze_pitch(notes),
        "velocity": analyze_velocity(notes),
        "notes":    notes,  # preserve originals for reference
    }


# --------------------------------------------------------------------------
# Pattern generation from a profile
# --------------------------------------------------------------------------

def _euclidean(hits: int, steps: int, offset: int = 0) -> list[int]:
    """Bjorklund Euclidean rhythm."""
    if hits <= 0:
        return [0] * steps
    if hits >= steps:
        return [1] * steps
    groups = [[1]] * hits + [[0]] * (steps - hits)
    while True:
        remainder = groups[len(groups) - (len(groups) % hits or hits):]
        groups = groups[:len(groups) - len(remainder)]
        if not remainder:
            break
        groups = [a + b for a, b in zip(groups, remainder)] + groups[len(remainder):]
        if len(groups) <= hits:
            break
    flat = []
    for g in groups:
        flat.extend(g)
    flat = flat[:steps]
    # rotate by offset
    offset = offset % steps
    return flat[offset:] + flat[:offset]


def generate_from_profile(profile: dict, variation_seed: int | None = None) -> list[dict]:
    """
    Generate new notes inspired by a learned profile.
    
    Style principles:
    - Use the same pitch vocabulary but reorder it
    - Match density within ±15%
    - Match velocity dynamics (mean + variance) but with different accent positions
    - Use a different Euclidean or displaced rhythm at the same grid resolution
    - Add a random rotation/offset to break the exact pattern
    """
    rng = random.Random(variation_seed)

    rhythm   = profile["rhythm"]
    pitch_p  = profile["pitch"]
    vel_p    = profile["velocity"]
    length   = profile["meta"]["length_beats"]

    # --- Rhythm ---
    grid_res = {"16th": 0.25, "8th": 0.5, "quarter": 1.0}.get(rhythm["grid"], 0.25)
    steps    = int(round(length / grid_res))
    euclid   = rhythm["euclidean_approx"]

    # Vary hit count: ±20% and offset by 1–3 steps
    base_hits = max(1, euclid[0])
    varied_hits = max(1, min(steps, base_hits + rng.randint(-max(1, base_hits//5), max(1, base_hits//5))))
    rotation = rng.randint(1, max(1, steps // 4))
    grid = _euclidean(varied_hits, steps, offset=rotation)

    # --- Pitch selection ---
    pitches = pitch_p.get("notes_used", [60])
    if not pitches:
        pitches = [60]

    # Shuffle pitch order — pull from the same pool but reorder
    shuffled_pitches = list(pitches)
    rng.shuffle(shuffled_pitches)
    pitch_cycle = shuffled_pitches * (steps // len(shuffled_pitches) + 1)

    # --- Velocity shaping ---
    v_mean   = vel_p.get("mean", 100)
    v_std    = max(1, math.sqrt(vel_p.get("variance", 100)))
    accents  = set(vel_p.get("accents", []))

    notes = []
    pitch_idx = 0
    for step, hit in enumerate(grid):
        if not hit:
            continue
        start = step * grid_res

        # Velocity: use gaussian noise around mean, louder at random accent positions
        if step in accents or rng.random() < 0.2:
            vel = int(min(127, max(1, v_mean + v_std * rng.uniform(0.5, 1.5))))
        else:
            vel = int(min(127, max(1, v_mean + rng.gauss(0, v_std * 0.5))))

        pitch = pitch_cycle[pitch_idx % len(pitch_cycle)]
        pitch_idx += 1

        dur = grid_res * rng.uniform(0.4, 0.85)  # articulated, not legato
        notes.append({
            "pitch":      int(pitch),
            "start_time": round(float(start), 4),
            "duration":   round(float(dur), 4),
            "velocity":   vel,
            "mute":       False,
        })

    return notes


# --------------------------------------------------------------------------
# .mid file parser (for learn-file and learn-packs)
# --------------------------------------------------------------------------

def parse_mid_file(mid_path: Path) -> dict:
    """Parse a standard .mid file into our clip note format.

    Merges all tracks, returns:
        {"notes": [...], "bpm": float, "clip_length": float}
    where clip_length is in beats.
    """
    try:
        import mido
    except ImportError:
        log.error("mido not installed. Run: pip install mido")
        raise

    mid = mido.MidiFile(str(mid_path))
    ticks_per_beat = mid.ticks_per_beat

    # Extract tempo from first set_tempo message across all tracks
    tempo = 500000  # default = 120 BPM
    for track in mid.tracks:
        for msg in track:
            if msg.type == "set_tempo":
                tempo = msg.tempo
                break

    bpm = round(60_000_000 / tempo, 2)

    # Merge all tracks into a single note list
    notes = []
    for track in mid.tracks:
        abs_tick = 0
        active = {}  # (channel, note) -> (start_beats, velocity)
        for msg in track:
            abs_tick += msg.time
            start_beats = abs_tick / ticks_per_beat
            if msg.type == "note_on" and msg.velocity > 0:
                active[(msg.channel, msg.note)] = (start_beats, msg.velocity)
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in active:
                    s, vel = active.pop(key)
                    dur = start_beats - s
                    if dur < 0.001:
                        dur = 0.125  # default short note if malformed
                    notes.append({
                        "pitch": msg.note,
                        "start_time": round(s, 4),
                        "duration": round(dur, 4),
                        "velocity": vel,
                    })

    # Clip length: use the MIDI file length (seconds → beats)
    file_length_beats = mid.length * bpm / 60.0
    if not file_length_beats or file_length_beats < 0.01:
        file_length_beats = max(
            (n["start_time"] + n["duration"] for n in notes),
            default=4.0,
        )
    # Round to nearest bar (4 beats)
    clip_length = max(4.0, round(file_length_beats / 4.0) * 4.0)

    return {"notes": notes, "bpm": bpm, "clip_length": clip_length}


def parse_alc_file(alc_path: Path) -> dict:
    """Parse an Ableton Live Clip (.alc) file into our clip note format.

    .alc files are gzip-compressed XML.  Notes live in <KeyTracks> where each
    <KeyTrack> carries a <MidiKey Value="N"/> (MIDI pitch) and <Notes> with
    <MidiNoteEvent Time="..." Duration="..." Velocity="..."/> children.
    Clip length comes from <Loop><LoopEnd Value="N"/></Loop> (in beats).
    Tempo from <Tempo><Manual Value="N"/></Tempo>.
    """
    import gzip
    import xml.etree.ElementTree as ET

    with gzip.open(str(alc_path), 'rb') as f:
        xml_bytes = f.read()

    root = ET.fromstring(xml_bytes)

    # Tempo
    bpm = 120.0
    tempo_el = root.find('.//Tempo/Manual')
    if tempo_el is not None:
        try:
            bpm = float(tempo_el.get('Value', 120.0))
        except (TypeError, ValueError):
            pass

    # Clip length from Loop
    clip_length = 4.0
    loop_end = root.find('.//Loop/LoopEnd')
    if loop_end is not None:
        try:
            clip_length = float(loop_end.get('Value', 4.0))
        except (TypeError, ValueError):
            pass
    if clip_length < 0.01:
        clip_length = 4.0

    # Notes from KeyTracks
    notes = []
    for key_track in root.findall('.//KeyTrack'):
        midi_key_el = key_track.find('MidiKey')
        if midi_key_el is None:
            continue
        try:
            pitch = int(midi_key_el.get('Value', 60))
        except (TypeError, ValueError):
            continue
        for ev in key_track.findall('.//MidiNoteEvent'):
            enabled = ev.get('IsEnabled', 'true')
            if enabled.lower() == 'false':
                continue
            try:
                start = float(ev.get('Time', 0))
                dur = float(ev.get('Duration', 0.125))
                vel = int(float(ev.get('Velocity', 64)))
            except (TypeError, ValueError):
                continue
            notes.append({
                'pitch': pitch,
                'start_time': round(start, 4),
                'duration': round(max(dur, 0.001), 4),
                'velocity': max(1, min(127, vel)),
            })

    notes.sort(key=lambda n: n['start_time'])
    return {'notes': notes, 'bpm': bpm, 'clip_length': clip_length}


def parse_als_file(als_path: Path) -> list[dict]:
    """Parse an Ableton Live Set (.als) and return all MIDI clips as a list.

    Each entry:
        {
            "track_name": str,
            "clip_name":  str,
            "notes":      [...],
            "bpm":        float,
            "clip_length": float,
        }

    Only clips that contain at least one enabled note are included.
    """
    import gzip
    import xml.etree.ElementTree as ET

    with gzip.open(str(als_path), 'rb') as f:
        xml_bytes = f.read()

    root = ET.fromstring(xml_bytes)

    # Global tempo (used when a clip has no per-clip tempo override)
    bpm = 120.0
    tempo_el = root.find('.//Tempo/Manual')
    if tempo_el is not None:
        try:
            bpm = float(tempo_el.get('Value', 120.0))
        except (TypeError, ValueError):
            pass

    clips = []

    live_set = root.find('LiveSet')
    tracks_node = live_set.find('Tracks') if live_set is not None else root.find('.//Tracks')
    if tracks_node is None:
        return clips

    for track in tracks_node:
        if track.tag != 'MidiTrack':
            continue

        name_el = track.find('Name/EffectiveName')
        track_name = name_el.get('Value', '') if name_el is not None else ''

        # Clips live inside ClipSlotList/ClipSlot/ClipSlot/MidiClip
        # OR ArrangementClips/MidiClip (arrangement view)
        midi_clips = list(track.findall('.//MidiClip'))

        for mc in midi_clips:
            # Clip name
            cn_el = mc.find('Name')
            clip_name = cn_el.get('Value', '') if cn_el is not None else ''

            # Clip length from Loop
            clip_length = bpm  # fallback
            loop_end = mc.find('Loop/LoopEnd')
            if loop_end is not None:
                try:
                    clip_length = float(loop_end.get('Value', 4.0))
                except (TypeError, ValueError):
                    clip_length = 4.0
            else:
                clip_length = 4.0
            if clip_length < 0.01:
                clip_length = 4.0

            # Notes
            notes = []
            for key_track in mc.findall('.//KeyTrack'):
                midi_key_el = key_track.find('MidiKey')
                if midi_key_el is None:
                    continue
                try:
                    pitch = int(midi_key_el.get('Value', 60))
                except (TypeError, ValueError):
                    continue
                for ev in key_track.findall('.//MidiNoteEvent'):
                    if ev.get('IsEnabled', 'true').lower() == 'false':
                        continue
                    try:
                        start = float(ev.get('Time', 0))
                        dur = float(ev.get('Duration', 0.125))
                        vel = int(float(ev.get('Velocity', 64)))
                    except (TypeError, ValueError):
                        continue
                    notes.append({
                        'pitch': pitch,
                        'start_time': round(start, 4),
                        'duration': round(max(dur, 0.001), 4),
                        'velocity': max(1, min(127, vel)),
                    })

            if not notes:
                continue

            notes.sort(key=lambda n: n['start_time'])
            clips.append({
                'track_name': track_name,
                'clip_name': clip_name,
                'notes': notes,
                'bpm': bpm,
                'clip_length': clip_length,
            })

    return clips


def cmd_learn_session(args):
    """Extract MIDI clips from an .als session file and learn them all."""
    als_path = Path(args.file)
    if not als_path.exists():
        log.error("File not found: %s", als_path)
        sys.exit(1)

    out_dir = REFERENCES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    session_tag = getattr(args, "tag", None) or als_path.stem
    log.info("Parsing %s …", als_path)

    try:
        clip_list = parse_als_file(als_path)
    except Exception as e:
        log.error("Failed to parse %s: %s", als_path.name, e)
        sys.exit(1)

    if not clip_list:
        print(f"No MIDI clips with notes found in {als_path.name}")
        return

    print(f"Found {len(clip_list)} MIDI clip(s) in '{als_path.stem}'. Learning …\n")
    saved = 0
    skipped = 0
    song = _active_song()

    for i, clip in enumerate(clip_list):
        track_name = clip['track_name'] or f"track{i}"
        clip_name = clip['clip_name'] or f"clip{i}"
        tag = f"{session_tag} / {track_name} / {clip_name}"

        safe_tag = (
            tag.replace("/", "-").replace("\\", "-")
               .replace(" ", "_").replace(":", "")[:80]
        )
        out_path = out_dir / f"{safe_tag}.json"

        if out_path.exists() and not getattr(args, "force", False):
            log.debug("Already learned, skipping: %s", out_path.name)
            skipped += 1
            continue

        clip_data = {
            "notes": clip["notes"],
            "clip_length": clip["clip_length"],
            "clip_name": tag,
        }
        song_meta = {
            "slug": session_tag,
            "bpm": clip["bpm"],
            "key": song.get("key", "?"),
            "scale": song.get("scale", "?"),
        }

        profile = build_profile(0, 0, tag, clip_data, song_meta)
        profile["source"]["song"] = session_tag
        profile["source"]["track_name"] = track_name
        profile["source"]["clip_name"] = clip_name
        profile["source"]["als_file"] = str(als_path)

        out_path.write_text(json.dumps(profile, indent=2))
        print(f"  learned: {out_path.name}  ({len(clip['notes'])} notes)")
        saved += 1

    print(f"\n{saved} profile(s) saved to {out_dir}/  |  {skipped} skipped")


# --------------------------------------------------------------------------
# Active song context
# --------------------------------------------------------------------------

def _active_song() -> dict:
    db_path = Path("database/songs.json")
    if not db_path.exists():
        return {}
    data = json.loads(db_path.read_text())
    for song in data.get("songs", []):
        if song.get("status") == "active":
            return song
    return {}


# --------------------------------------------------------------------------
# CLI commands
# --------------------------------------------------------------------------

def cmd_learn(args):
    from bridge_client import BridgeClient

    song = _active_song()
    song_slug = song.get("slug", "unknown")

    LEARNED_DIR.mkdir(parents=True, exist_ok=True)

    with BridgeClient() as b:
        info = b.get_session_info()
        if info.get("status") != "success":
            log.error("Cannot reach Live: %s", info.get("message"))
            sys.exit(1)

        tracks = info["result"]["tracks"]

        if args.all:
            targets = [(t["index"], t["name"], s) for t in tracks
                       for s in range(8)]  # scan 8 slots per track
        elif getattr(args, "name", None):
            r = b.clip_find_by_name(args.name, getattr(args, "on_track", None))
            if r.get("status") != "success":
                log.error("clip not found: %s", r.get("message"))
                sys.exit(1)
            match = r["result"]
            if "matches" in match:
                log.error("multiple clips named '%s' — use --on-track to narrow:\n%s",
                          args.name,
                          "\n".join("  track {} slot {}".format(m["track_name"], m["clip_index"]) for m in match["matches"]))
                sys.exit(1)
            targets = [(match["track_index"], match["track_name"], match["clip_index"])]
        else:
            targets = [(args.track, None, args.slot)]

    saved = []
    with BridgeClient() as b:
        for track_idx, track_name, slot_idx in targets:
            # Resolve track name if not given
            if track_name is None:
                tr = next((t for t in info["result"]["tracks"] if t["index"] == track_idx), {})
                track_name = tr.get("name", f"track{track_idx}")

            r = b.clip_notes(track_idx, slot_idx)
            if r.get("status") != "success":
                if not args.all:
                    log.error("track %d slot %d: %s", track_idx, slot_idx, r.get("message"))
                    sys.exit(1)
                continue  # skip empty slots in --all mode

            notes = r["result"].get("notes", [])
            if not notes:
                log.debug("track %d slot %d: empty, skipping", track_idx, slot_idx)
                continue

            profile = build_profile(track_idx, slot_idx, track_name, r["result"], song)
            fname = f"{song_slug}_{track_idx}_{slot_idx}.json"
            out   = LEARNED_DIR / fname
            out.write_text(json.dumps(profile, indent=2))
            saved.append(str(out))
            print(f"learned: {out}  ({len(notes)} notes, {profile['rhythm']['density']:.0%} density)")

    if not saved:
        print("No clips with notes found.")
    else:
        print(f"\n{len(saved)} profile(s) saved to {LEARNED_DIR}/")


def cmd_generate(args):
    try:
        import mido
    except ImportError:
        log.error("mido not installed. Run: pip install mido")
        sys.exit(1)

    profile_path = Path(args.profile)
    if not profile_path.exists():
        log.error("Profile not found: %s", profile_path)
        sys.exit(1)

    profile = json.loads(profile_path.read_text())
    notes   = generate_from_profile(profile, variation_seed=args.seed)

    song_slug = profile["source"]["song"]
    track_idx = profile["source"]["track_index"]
    slot_idx  = profile["source"]["slot_index"]
    bpm       = profile["meta"].get("bpm", 95.0)
    length    = profile["meta"]["length_beats"]

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    slug = f"{song_slug}_{track_idx}_{slot_idx}_v{args.seed or 'rnd'}"

    # Write notes JSON (for bridge_client clip write)
    notes_json = GENERATED_DIR / f"{slug}.json"
    notes_json.write_text(json.dumps({"notes": notes}, indent=2))

    # Write MIDI file
    mid_path = GENERATED_DIR / f"{slug}.mid"
    _write_midi(notes, mid_path, bpm, length)

    print(f"generated: {notes_json}  ({len(notes)} notes)")
    print(f"midi:      {mid_path}")

    if args.push:
        from bridge_client import BridgeClient
        slot_target = args.push_slot if args.push_slot is not None else slot_idx
        with BridgeClient() as b:
            r = b.clip_write(track_idx, slot_target, notes_json)
            if r.get("status") == "success":
                print(f"pushed to track {track_idx} slot {slot_target}")
            else:
                log.error("push failed: %s", r.get("message"))


def _write_midi(notes: list[dict], output_path: Path, bpm: float, length_beats: float):
    import mido
    ticks_per_beat = 480
    tempo = int(60_000_000 / bpm)
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))

    events = []
    for n in notes:
        on_tick  = int(n["start_time"] * ticks_per_beat)
        off_tick = int((n["start_time"] + n["duration"]) * ticks_per_beat)
        events.append((on_tick,  "on",  n["pitch"], n["velocity"]))
        events.append((off_tick, "off", n["pitch"], 0))

    events.sort(key=lambda e: (e[0], 0 if e[1] == "off" else 1))
    last = 0
    for tick, kind, pitch, vel in events:
        delta = max(0, tick - last)
        msg_type = "note_on" if kind == "on" else "note_off"
        track.append(mido.Message(msg_type, channel=0, note=pitch, velocity=vel, time=delta))
        last = tick

    end_tick = int(length_beats * ticks_per_beat)
    track.append(mido.MetaMessage("end_of_track", time=max(0, end_tick - last)))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(output_path))


def cmd_list(args):
    profiles = sorted(LEARNED_DIR.glob("*.json")) if LEARNED_DIR.exists() else []
    if not profiles:
        print(f"No profiles in {LEARNED_DIR}/ — run 'learn' first.")
        return
    print(f"{'Profile':<45} {'Track':<16} {'Notes':>5} {'Density':>8} {'Grid':<6} {'Melodic'}")
    print("-" * 95)
    for p in profiles:
        try:
            d = json.loads(p.read_text())
            src = d["source"]
            meta = d["meta"]
            rhy = d["rhythm"]
            pch = d["pitch"]
            print(f"{p.name:<45} {src['track_name']:<16} {meta['note_count']:>5} "
                  f"{rhy['density']:>7.0%} {rhy['grid']:<6} {'yes' if pch['is_melodic'] else 'no'}")
        except Exception:
            print(f"  {p.name}  (unreadable)")


def cmd_show(args):
    p = Path(args.profile)
    if not p.exists():
        log.error("Not found: %s", p)
        sys.exit(1)
    d = json.loads(p.read_text())
    # Print without raw notes array for readability
    display = {k: v for k, v in d.items() if k != "notes"}
    print(json.dumps(display, indent=2))
    print(f"\n({d['meta']['note_count']} notes stored)")


def cmd_learn_file(args):
    """Analyze a .mid file on disk and save a pattern profile."""
    mid_path = Path(args.file)
    if not mid_path.exists():
        log.error("File not found: %s", mid_path)
        sys.exit(1)

    subdir = getattr(args, "subdir", None) or "packs"
    out_dir = PACKS_DIR if subdir == "packs" else REFERENCES_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    tag = getattr(args, "tag", None) or mid_path.stem
    # Sanitize tag for filesystem
    safe_tag = tag.replace("/", "-").replace("\\", "-").replace(" ", "_")[:60]

    log.info("Parsing %s …", mid_path)
    parsed = parse_mid_file(mid_path)

    song = _active_song()
    clip_data = {
        "notes": parsed["notes"],
        "clip_length": parsed["clip_length"],
        "clip_name": tag,
    }
    source_bpm = parsed["bpm"]
    song_meta = {
        "slug": safe_tag,
        "bpm": source_bpm,
        "key": song.get("key", "?"),
        "scale": song.get("scale", "?"),
    }

    profile = build_profile(0, 0, tag, clip_data, song_meta)
    # Overwrite slug with the tag name so it's meaningful
    profile["source"]["song"] = subdir
    profile["source"]["track_name"] = tag
    profile["source"]["mid_file"] = str(mid_path)

    fname = f"{safe_tag}.json"
    out_path = out_dir / fname
    out_path.write_text(json.dumps(profile, indent=2))
    print(f"learned: {out_path}  ({len(parsed['notes'])} notes, {profile['rhythm']['density']:.0%} density, {source_bpm} BPM)")


def cmd_learn_packs(args):
    """Scan Ableton Pack directories for .mid files and learn them all."""
    import os

    pack_roots = []
    if getattr(args, "pack_dir", None):
        pack_roots.append(Path(args.pack_dir))
    else:
        default = Path.home() / "Music" / "Ableton" / "Packs"
        user_lib = Path.home() / "Music" / "Ableton" / "User Library"
        if default.exists():
            pack_roots.append(default)
        if user_lib.exists():
            pack_roots.append(user_lib)

    if not pack_roots:
        log.error("No pack directories found. Specify --pack-dir explicitly.")
        sys.exit(1)

    PACKS_DIR.mkdir(parents=True, exist_ok=True)

    found = []
    for root in pack_roots:
        for p in root.rglob("*.mid"):
            found.append(p)
        for p in root.rglob("*.MID"):
            found.append(p)
        for p in root.rglob("*.alc"):
            found.append(p)
        for p in root.rglob("*.ALC"):
            found.append(p)

    if not found:
        print(f"No .mid/.alc files found under {', '.join(str(r) for r in pack_roots)}")
        return

    print(f"Found {len(found)} clip file(s) (.mid + .alc). Learning …\n")
    saved = 0
    skipped = 0
    for clip_path in found:
        # Build a descriptive tag from pack name + file name
        parts = clip_path.parts
        try:
            pack_idx = next(i for i, p in enumerate(parts) if "Packs" in p or "User Library" in p)
            tag_parts = parts[pack_idx + 1:]
        except StopIteration:
            tag_parts = parts[-2:]

        suffix = clip_path.suffix.lower()
        tag = " / ".join(tag_parts)
        for ext in (".mid", ".MID", ".alc", ".ALC"):
            tag = tag.replace(ext, "")

        try:
            if suffix == ".alc":
                parsed = parse_alc_file(clip_path)
            else:
                parsed = parse_mid_file(clip_path)
        except Exception as e:
            log.debug("Skip %s — parse error: %s", clip_path.name, e)
            skipped += 1
            continue

        if not parsed["notes"]:
            log.debug("Skip %s — no notes", clip_path.name)
            skipped += 1
            continue

        safe_tag = tag.replace("/", "-").replace("\\", "-").replace(" ", "_")[:80]
        out_path = PACKS_DIR / f"{safe_tag}.json"
        if out_path.exists() and not getattr(args, "force", False):
            log.debug("Already learned, skipping: %s", out_path.name)
            skipped += 1
            continue

        clip_data = {"notes": parsed["notes"], "clip_length": parsed["clip_length"], "clip_name": tag}
        profile = build_profile(0, 0, tag, clip_data, {"slug": "packs", "bpm": parsed["bpm"], "key": "?", "scale": "?"})
        profile["source"]["song"] = "packs"
        profile["source"]["track_name"] = tag
        profile["source"]["mid_file"] = str(clip_path)
        out_path.write_text(json.dumps(profile, indent=2))
        print(f"  learned: {out_path.name}  ({len(parsed['notes'])} notes)")
        saved += 1

    print(f"\n{saved} profile(s) saved to {PACKS_DIR}/  |  {skipped} skipped")


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    p = argparse.ArgumentParser(
        description="Learn MIDI patterns from Live clips and generate inspired variations.")
    sub = p.add_subparsers(dest="command", required=True)

    # learn
    lrn = sub.add_parser("learn", help="Pull clip notes from Live and analyze")
    grp = lrn.add_mutually_exclusive_group(required=True)
    grp.add_argument("--all", action="store_true",
                     help="Scan all tracks/slots for clips with notes")
    grp.add_argument("--track", type=int, metavar="TRACK_IDX")
    grp.add_argument("--name", metavar="CLIP_NAME",
                     help="Find and learn a clip by its name in Live")
    lrn.add_argument("--slot", type=int, default=0, metavar="SLOT_IDX")
    lrn.add_argument("--on-track", default=None, metavar="TRACK_NAME",
                     help="Restrict --name search to a specific track")
    lrn.add_argument("-v", "--verbose", action="store_true")

    # generate
    gen = sub.add_parser("generate",
                         help="Generate a new pattern inspired by a learned profile")
    gen.add_argument("--profile", required=True, metavar="PROFILE_JSON")
    gen.add_argument("--seed", type=int, default=None,
                     help="Random seed for reproducible generation")
    gen.add_argument("--push", action="store_true",
                     help="Push the generated pattern into Live immediately")
    gen.add_argument("--push-slot", type=int, default=None,
                     help="Slot index to push to (default: same slot as source)")

    # list
    sub.add_parser("list", help="List all learned profiles")

    # show
    shw = sub.add_parser("show", help="Inspect a learned profile")
    shw.add_argument("--profile", required=True, metavar="PROFILE_JSON")

    # learn-file
    lf = sub.add_parser("learn-file", help="Learn a pattern from a .mid file on disk")
    lf.add_argument("--file", required=True, metavar="PATH", help="Path to .mid file")
    lf.add_argument("--tag", default=None, metavar="NAME",
                    help="Descriptive name for this pattern (defaults to filename stem)")
    lf.add_argument("--subdir", choices=["packs", "references"], default="packs",
                    help="Sub-directory to store the profile in (default: packs)")

    # learn-packs
    lp = sub.add_parser("learn-packs", help="Scan Ableton packs for .mid/.alc files and learn them all")
    lp.add_argument("--pack-dir", default=None, metavar="DIR",
                    help="Override pack directory (default: ~/Music/Ableton/Packs/)")
    lp.add_argument("--force", action="store_true",
                    help="Re-learn files that already have a profile")

    # learn-session
    ls_ = sub.add_parser("learn-session", help="Extract and learn all MIDI clips from an Ableton .als file")
    ls_.add_argument("--file", required=True, metavar="PATH", help="Path to .als session file")
    ls_.add_argument("--tag", default=None, metavar="NAME",
                     help="Session label (defaults to filename stem)")
    ls_.add_argument("--force", action="store_true",
                     help="Re-learn clips that already have a profile")

    args = p.parse_args()
    if getattr(args, "verbose", False):
        logging.getLogger().setLevel(logging.DEBUG)

    if args.command == "learn":
        cmd_learn(args)
    elif args.command == "generate":
        cmd_generate(args)
    elif args.command == "list":
        cmd_list(args)
    elif args.command == "show":
        cmd_show(args)
    elif args.command == "learn-file":
        cmd_learn_file(args)
    elif args.command == "learn-packs":
        cmd_learn_packs(args)
    elif args.command == "learn-session":
        cmd_learn_session(args)


if __name__ == "__main__":
    main()
