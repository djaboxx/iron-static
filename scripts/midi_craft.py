#!/usr/bin/env python3
"""
midi_craft.py — MIDI sequence generator for IRON STATIC.

Generates MIDI files from a musical concept, key, BPM, and instrument target.

Usage:
    python scripts/midi_craft.py --concept "heavy 7/8 kick groove" --bpm 140 --key Em
    python scripts/midi_craft.py --pattern "euclidean kick" --steps 16 --instrument digitakt
    python scripts/midi_craft.py --song rust-protocol --clips all
    python scripts/midi_craft.py --help
"""

import argparse
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# MIDI note numbers for common percussion (GM standard, Digitakt default mapping)
KICK = 36
SNARE = 38
CLOSED_HAT = 42
OPEN_HAT = 46
CLAP = 39
RIM = 37

# Scale intervals (semitones from root)
SCALES = {
    "minor": [0, 2, 3, 5, 7, 8, 10],                   # Natural minor / Aeolian
    "phrygian": [0, 1, 3, 5, 7, 8, 10],                 # Phrygian
    "phrygian_dominant": [0, 1, 4, 5, 7, 8, 10],        # Phrygian Dominant (b2, maj3)
    "dorian": [0, 2, 3, 5, 7, 9, 10],                   # Dorian
    "locrian": [0, 1, 3, 4, 6, 8, 10],                  # Locrian
    "diminished": [0, 2, 3, 5, 6, 8, 9, 11],            # Octatonic (H-W)
    "whole_tone": [0, 2, 4, 6, 8, 10],                  # Whole tone
    "major": [0, 2, 4, 5, 7, 9, 11],                    # Major / Ionian
}

NOTE_MAP = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11
}

REPO_ROOT = Path(__file__).resolve().parent.parent
SEQUENCES_DIR = REPO_ROOT / "midi" / "sequences"
PATTERNS_DIR = REPO_ROOT / "midi" / "patterns"

TICKS_PER_BEAT = 480


def ticks_per_bar(time_sig_num: int = 4) -> int:
    return TICKS_PER_BEAT * time_sig_num


def parse_key(key_str: str) -> tuple[int, str]:
    """Parse a key string like 'Em' or 'A minor' into (root_midi, scale_name)."""
    key_str = key_str.strip()
    scale = "minor"

    # Handle shorthand like "Em", "Am", "F#m"
    if key_str.endswith("m") and not key_str.endswith("maj"):
        root_name = key_str[:-1]
        scale = "minor"
    elif "minor" in key_str.lower():
        root_name = key_str.lower().replace("minor", "").strip().title()
    elif "phrygian dominant" in key_str.lower():
        root_name = key_str.lower().replace("phrygian dominant", "").strip().title()
        scale = "phrygian_dominant"
    elif "phrygian" in key_str.lower():
        root_name = key_str.lower().replace("phrygian", "").strip().title()
        scale = "phrygian"
    elif "dorian" in key_str.lower():
        root_name = key_str.lower().replace("dorian", "").strip().title()
        scale = "dorian"
    elif "major" in key_str.lower() or key_str.endswith("M"):
        root_name = key_str.rstrip("M").lower().replace("major", "").strip().title()
        scale = "major"
    else:
        root_name = key_str.title()

    root_semitone = NOTE_MAP.get(root_name, 4)  # Default to E
    root_midi = 24 + root_semitone  # C2 = 24
    return root_midi, scale


def euclidean_rhythm(hits: int, steps: int) -> list[int]:
    """Generate a Euclidean rhythm — evenly distribute 'hits' over 'steps'."""
    pattern = [0] * steps
    if hits <= 0:
        return pattern
    if hits >= steps:
        return [1] * steps

    # Bjorklund's algorithm
    groups = [[1]] * hits + [[0]] * (steps - hits)
    while len(groups) > 1:
        remainder = groups[len(groups) - (len(groups) % hits or hits):]
        groups = groups[:len(groups) - len(remainder)]
        groups = [a + b for a, b in zip(groups, remainder)] + groups[len(remainder):]

    flat = []
    for g in groups:
        flat.extend(g)
    return flat[:steps]


# ---------------------------------------------------------------------------
# Melodic clip generators
# ---------------------------------------------------------------------------

def make_note_event(tick: int, note: int, velocity: int, duration_ticks: int,
                    channel: int = 0) -> list[dict]:
    """Return note_on + note_off event pair."""
    return [
        {"type": "note_on",  "tick": tick,                   "note": note,
         "velocity": velocity, "channel": channel},
        {"type": "note_off", "tick": tick + duration_ticks,  "note": note,
         "velocity": 0,       "channel": channel},
    ]


def write_melodic_midi(events: list[dict], output_path: Path, bpm: float,
                       total_bars: int, time_sig: int = 4) -> None:
    """Write melodic note events to a MIDI file."""
    try:
        import mido
    except ImportError:
        log.error("mido not installed. Run: pip install -r scripts/requirements.txt")
        sys.exit(1)

    tempo = int(60_000_000 / bpm)
    total_ticks = total_bars * TICKS_PER_BEAT * time_sig

    mid = mido.MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    track.append(mido.MetaMessage("time_signature",
                                  numerator=time_sig, denominator=4, time=0))

    # Sort by tick, then note_off before note_on at same tick
    def sort_key(e):
        return (e["tick"], 0 if e["type"] == "note_off" else 1)

    sorted_events = sorted(events, key=sort_key)

    last_tick = 0
    for ev in sorted_events:
        delta = ev["tick"] - last_tick
        if ev["type"] == "note_on":
            track.append(mido.Message("note_on", channel=ev["channel"],
                                      note=ev["note"], velocity=ev["velocity"],
                                      time=delta))
        else:
            track.append(mido.Message("note_off", channel=ev["channel"],
                                      note=ev["note"], velocity=0, time=delta))
        last_tick = ev["tick"]

    remaining = max(0, total_ticks - last_tick)
    track.append(mido.MetaMessage("end_of_track", time=remaining))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(output_path))
    log.info("Written: %s  (%d bars, %d events)", output_path, total_bars, len(sorted_events))


def generate_take5_drop_stabs(bpm: float = 95.0) -> Path:
    """
    Take5 / Drift — chord stab on downbeat every 2 bars, Drop (8 bars).

    Note A3 only — Chord MIDI FX in Live adds Bb3 (+1) and E4 (+7).
    Amplitude: 2ms attack, 350ms decay, sustain 0% — note_off after ~400ms is correct.
    Velocity varied slightly each hit for organic feel.
    Channel: 4 (Take5 default)
    """
    bar = ticks_per_bar()  # 1920 ticks
    stab_dur = int(TICKS_PER_BEAT * 0.63)  # ~400ms at 95 BPM (covers decay tail)
    A3 = 57  # MIDI note A3
    ch = 3   # channel 4 (0-indexed = 3)

    # Stabs on bars 1, 3, 5, 7 (0-indexed: 0, 2, 4, 6)
    stab_bars = [0, 2, 4, 6]
    velocities = [100, 95, 102, 90]  # slight variation, never perfectly flat

    events = []
    for i, bar_idx in enumerate(stab_bars):
        tick = bar_idx * bar
        events.extend(make_note_event(tick, A3, velocities[i], stab_dur, channel=ch))

    output_path = SEQUENCES_DIR / "rust-protocol_take5_v1.mid"
    write_melodic_midi(events, output_path, bpm, total_bars=8)
    return output_path


def generate_subharmonicon_drone(bpm: float = 95.0) -> Path:
    """
    Subharmonicon / Operator — sustained A2 drone, 8-bar loopable clip.

    A2 held for the full clip. Chord MIDI FX in Live adds Bb2 (+1 semitone).
    The A+Bb minor-2nd interval beats against Operator's FM feedback.
    Used in scenes: Build, Drop, Breakdown, Climax — loop this same clip in each.
    Channel: 5 (Subharmonicon default)
    """
    bar = ticks_per_bar()
    total_bars = 8
    total_ticks = total_bars * bar
    A2 = 45   # MIDI note A2
    ch = 4    # channel 5 (0-indexed = 4)

    # Sustain nearly the full clip; 20-tick gap at end prevents clip-boundary
    # note truncation when Ableton loops it
    note_dur = total_ticks - 20

    events = make_note_event(0, A2, 72, note_dur, channel=ch)

    output_path = SEQUENCES_DIR / "rust-protocol_subharmonicon_v1.mid"
    write_melodic_midi(events, output_path, bpm, total_bars=total_bars)
    return output_path


def generate_rev2a_climax(bpm: float = 95.0) -> Path:
    """
    Rev2-A / Wavetable — 16-bar Climax clip, sustained A2 from bar 1.

    Enters immediately at the Climax onset (unlike Rev2-B which enters at bar 5).
    Wavetable has a 1.5s attack envelope so it swells in naturally — the note
    starts at tick 0 but the sound won't be audible until ~bar 2.
    Channel: 2 (Rev2 Layer A default)
    """
    bar = ticks_per_bar()
    total_bars = 16
    A2 = 45  # MIDI note A2
    ch = 1   # channel 2 (0-indexed = 1)

    note_dur = total_bars * bar - 20  # holds full clip, 20-tick boundary gap
    events = make_note_event(0, A2, 72, note_dur, channel=ch)

    output_path = SEQUENCES_DIR / "rust-protocol_rev2a_climax_v1.mid"
    write_melodic_midi(events, output_path, bpm, total_bars=total_bars)
    return output_path


def generate_rev2b_climax(bpm: float = 95.0) -> Path:
    """
    Rev2-B / Meld (Fold FM) — 16-bar Climax clip, enters at bar 5.

    Rev2-A (Wavetable) enters at bar 1. Rev2-B enters 4 bars later — two layers
    that arrive at different times so the Climax builds internally.
    Note: A2 — Scale MIDI FX in Live constrains to A Phrygian Dominant.
    The Meld LFO increases Fold from 0.25 → ~0.55 over the 16-bar window.
    Channel: 3 (Rev2 Layer B default)
    """
    bar = ticks_per_bar()
    total_bars = 16
    A2 = 45  # MIDI note A2
    ch = 2   # channel 3 (0-indexed = 2)

    entry_tick = 4 * bar          # enters bar 5
    exit_tick  = total_bars * bar - 20   # holds to end of clip
    note_dur   = exit_tick - entry_tick

    events = make_note_event(entry_tick, A2, 68, note_dur, channel=ch)

    output_path = SEQUENCES_DIR / "rust-protocol_rev2b_climax_v1.mid"
    write_melodic_midi(events, output_path, bpm, total_bars=total_bars)
    return output_path


def generate_minibrute_lead(bpm: float = 95.0) -> Path:
    """
    Minibrute2S / Analog — main riff in A Phrygian Dominant, 8-bar clip.

    Phrase structure: 2-bar motif × 4. Built from A Phrygian Dominant scale
    (A Bb C# D E F G). The Bb is the defining tension note — hits it early
    in every motif, resolves back to A. C# (raised 3rd, Phrygian Dominant
    colour) hits mid-phrase for harmonic surprise.

    Articulation: staccato on riff notes (short), legato on approach/resolve.
    Scale MIDI FX in Live handles any out-of-key notes.
    Channel: 7 (Minibrute 2S default)
    """
    # A Phrygian Dominant: A(0) Bb(1) C#(4) D(5) E(7) F(8) G(10)
    # Note MIDI values: A2=45, Bb2=46, C#3=49, D3=50, E3=52, F3=53, G3=55, A3=57
    A2  = 45
    Bb2 = 46
    C3  = 48   # C natural (also in scale as C# raised, but Analog filter gives it grind)
    Cs3 = 49   # C# — Phrygian Dominant colour
    D3  = 50
    E3  = 52
    F3  = 53
    G3  = 55
    A3  = 57

    ch  = 6    # channel 7 (0-indexed = 6)
    bar = ticks_per_bar()       # 1920
    s16 = TICKS_PER_BEAT // 4  # 120 ticks = 16th note
    s8  = TICKS_PER_BEAT // 2  # 240 ticks = 8th note
    s4  = TICKS_PER_BEAT       # 480 ticks = quarter note
    dot8 = s8 + s16            # 360 ticks = dotted 8th

    # 2-bar motif (3840 ticks), repeated 4× with variation
    # Motif A (bars 1-2): A→Bb stab, drop to E, rise to A3
    # Motif B (bars 3-4): same core, C# detour
    # Motif C (bars 5-6): F as low pivot, aggressive return
    # Motif D (bars 7-8): resolves on A, more space (tension before loop point)

    events = []

    def add(tick, note, vel, dur):
        events.extend(make_note_event(tick, note, vel, dur, channel=ch))

    # --- Motif A (bar 1–2) ---
    t = 0
    add(t,        A2,  100, s16)          # A2 staccato attack
    t += s8
    add(t,        Bb2, 105, s16)          # Bb2 — the tension stab (Phrygian Dominant ♭2)
    t += s16
    add(t,        A2,   90, s8)           # fall back to A
    t += s8 + s16
    add(t,        E3,   85, s16)          # E3 skip
    t += s16
    add(t,        D3,   80, s16)          # D3
    t += s16
    add(t,        E3,   88, s8)           # E3 held briefly
    t += s8
    add(t,        A3,   95, s8)           # jump to A3 — octave upper register
    t += s8 + s16
    add(t,        G3,   82, s16)          # G3 passing
    t += s16
    add(t,        E3,   80, s8)           # E3 land
    t += s8
    add(t,        D3,   78, s8)           # D3 step
    t += s8
    add(t,        A2,   90, dot8)         # A2 resolve — dotted 8th, slightly lingering
    t += dot8 + s16

    # --- Motif B (bar 3–4) — C# detour ---
    add(t,        A2,  100, s16)          # A2 attack
    t += s8
    add(t,        Bb2, 102, s16)          # Bb2 stab again
    t += s16
    add(t,        Cs3,  95, s8)           # C#3 — Phrygian Dominant raised 3rd
    t += s8 + s16
    add(t,        D3,   88, s16)          # D3
    t += s16
    add(t,        E3,   90, s16)          # E3
    t += s16
    add(t,        Cs3,  85, s8)           # C#3 return
    t += s8
    add(t,        Bb2,  90, s16)          # Bb2 descent
    t += s16
    add(t,        A2,   95, s4)           # A2 resolve — quarter note
    t += s4 + s16
    add(t,        E3,   80, s16)
    t += s16
    add(t,        D3,   78, s16)
    t += s16
    add(t,        A2,   85, s8)
    t += s8 + s8

    # --- Motif C (bar 5–6) — F as low pivot, more aggression ---
    add(t,        F3,   98, s16)          # F3 — ♭6, dark pivot
    t += s16
    add(t,        E3,   85, s16)
    t += s16
    add(t,        D3,   80, s16)
    t += s16
    add(t,        Bb2, 105, s8)           # Bb2 — sharp
    t += s8
    add(t,        A2,   95, s16)
    t += s16
    add(t,        A2,   88, s16)          # double stab A2
    t += s16
    add(t,        Cs3,  90, s8)           # C#3
    t += s8
    add(t,        D3,   85, s16)
    t += s16
    add(t,        E3,   90, dot8)
    t += dot8
    add(t,        G3,   88, s16)          # G3 neighbour
    t += s16
    add(t,        A3,   95, s8)           # A3 upper
    t += s8
    add(t,        G3,   82, s16)
    t += s16
    add(t,        E3,   80, s8)
    t += s8 + s16
    add(t,        D3,   78, s16)
    t += s16
    add(t,        A2,   90, s8)
    t += s8

    # --- Motif D (bar 7–8) — resolution, space before loop ---
    add(t,        A2,   98, s8)           # A2 strong
    t += s8
    add(t,        Bb2,  95, s16)          # Bb2 quick
    t += s16
    add(t,        A2,   90, s8)           # A2 land
    t += s8 + s8
    add(t,        E3,   85, s8)           # E3
    t += s8
    add(t,        D3,   80, s16)
    t += s16
    add(t,        Cs3,  88, s16)          # C#3
    t += s16
    add(t,        D3,   85, s8)
    t += s8
    add(t,        E3,   90, s4)           # E3 held — slight breather
    t += s4
    add(t,        A2,   95, s4 + s8)      # A2 final resolve, held into loop point
    # bar 8 ends at 8 * 1920 = 15360 — leave last 16th empty for loop breathing room

    output_path = SEQUENCES_DIR / "rust-protocol_minibrute2s_v1.mid"
    write_melodic_midi(events, output_path, bpm, total_bars=8)
    return output_path


# ---------------------------------------------------------------------------
# Drum pattern generator (original functionality)
# ---------------------------------------------------------------------------

def generate_drum_pattern(concept: str, steps: int, bpm: float) -> list[dict]:
    """Generate a drum pattern as a list of MIDI events."""
    concept_lower = concept.lower()

    kick_pattern = euclidean_rhythm(4, steps)
    snare_pattern = [0] * steps
    hat_pattern = euclidean_rhythm(8, steps)

    if "7/8" in concept_lower or "7 8" in concept_lower:
        kick_pattern = euclidean_rhythm(3, 7) + [0] * (steps - 7)
        hat_pattern = euclidean_rhythm(5, 7) + [0] * (steps - 7)
        snare_pattern[3] = 1

    elif "half" in concept_lower or "doom" in concept_lower:
        kick_pattern = [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0][:steps]
        snare_pattern = [0] * steps
        if steps >= 9:
            snare_pattern[8] = 1

    elif "euclidean" in concept_lower:
        kick_pattern = euclidean_rhythm(5, steps)
        hat_pattern = euclidean_rhythm(11, steps)

    elif "machine" in concept_lower or "industrial" in concept_lower:
        kick_pattern = euclidean_rhythm(6, steps)
        hat_pattern = [1] * steps
        snare_pattern[4] = 1
        snare_pattern[12] = 1

    if sum(snare_pattern) == 0:
        snare_pattern[4] = 1
        snare_pattern[12] = 1

    step_ticks = TICKS_PER_BEAT // 4
    events = []
    for i in range(steps):
        tick = i * step_ticks
        if kick_pattern[i]:
            events.append({"type": "note_on",  "tick": tick,    "note": KICK,
                           "velocity": 127, "channel": 9})
            events.append({"type": "note_off", "tick": tick+10, "note": KICK,
                           "velocity": 0,   "channel": 9})
        if snare_pattern[i]:
            events.append({"type": "note_on",  "tick": tick,    "note": SNARE,
                           "velocity": 100, "channel": 9})
            events.append({"type": "note_off", "tick": tick+10, "note": SNARE,
                           "velocity": 0,   "channel": 9})
        if hat_pattern[i]:
            vel = 60 if i % 4 != 0 else 90
            events.append({"type": "note_on",  "tick": tick,    "note": CLOSED_HAT,
                           "velocity": vel, "channel": 9})
            events.append({"type": "note_off", "tick": tick+10, "note": CLOSED_HAT,
                           "velocity": 0,   "channel": 9})
    return events


def write_midi(events: list[dict], output_path: Path, bpm: float, steps: int) -> None:
    """Write drum events to a MIDI file (legacy drum generator path)."""
    try:
        import mido
    except ImportError:
        log.error("mido not installed. Run: pip install -r scripts/requirements.txt")
        sys.exit(1)

    tempo = int(60_000_000 / bpm)
    mid = mido.MidiFile(ticks_per_beat=TICKS_PER_BEAT)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))

    sorted_events = sorted(events, key=lambda e: (e["tick"],
                                                   0 if e["type"] == "note_off" else 1))
    last_tick = 0
    for ev in sorted_events:
        delta = ev["tick"] - last_tick
        if ev["type"] == "note_on":
            track.append(mido.Message("note_on", channel=ev["channel"],
                                      note=ev["note"], velocity=ev["velocity"], time=delta))
        else:
            track.append(mido.Message("note_off", channel=ev["channel"],
                                      note=ev["note"], velocity=0, time=delta))
        last_tick = ev["tick"]

    pattern_end_tick = steps * (TICKS_PER_BEAT // 4)
    remaining = max(0, pattern_end_tick - last_tick)
    track.append(mido.MetaMessage("end_of_track", time=remaining))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(output_path))
    log.info("MIDI written: %s (%d events)", output_path, len(sorted_events))


# ---------------------------------------------------------------------------
# Song clip generation
# ---------------------------------------------------------------------------

SONG_CLIP_GENERATORS = {
    "rust-protocol": {
        "take5":         generate_take5_drop_stabs,
        "subharmonicon":  generate_subharmonicon_drone,
        "rev2a-climax":  generate_rev2a_climax,
        "rev2b-climax":  generate_rev2b_climax,
        "minibrute2s":   generate_minibrute_lead,
    }
}


def generate_song_clips(slug: str, clip: str, bpm: float) -> None:
    """Generate all (or a named) clip for a song slug."""
    generators = SONG_CLIP_GENERATORS.get(slug)
    if not generators:
        log.error("No clip generators defined for song '%s'. Available: %s",
                  slug, list(SONG_CLIP_GENERATORS))
        sys.exit(1)

    targets = generators if clip == "all" else {clip: generators.get(clip)}
    if clip != "all" and not generators.get(clip):
        log.error("Unknown clip '%s' for song '%s'. Available: %s",
                  clip, slug, list(generators))
        sys.exit(1)

    for name, fn in targets.items():
        log.info("Generating clip: %s / %s", slug, name)
        path = fn(bpm)
        print(f"  ✓ {path.relative_to(REPO_ROOT)}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate MIDI sequences for the IRON STATIC rig."
    )

    subparsers = parser.add_subparsers(dest="mode", help="Generation mode")

    # --- drum / concept mode (original) ---
    drum_p = subparsers.add_parser("drum", help="Generate a drum/concept pattern")
    drum_p.add_argument("--concept", default="heavy 4/4 groove",
                        help="Describe the pattern concept")
    drum_p.add_argument("--bpm", type=float, default=120.0)
    drum_p.add_argument("--key", default="Em")
    drum_p.add_argument("--steps", type=int, default=16)
    drum_p.add_argument("--instrument", default="digitakt",
                        choices=["digitakt", "rev2", "take5", "minibrute2s"])
    drum_p.add_argument("--output", default=None)

    # --- song clips mode ---
    song_p = subparsers.add_parser("clips", help="Generate arrangement clips for a song")
    song_p.add_argument("--song", default="rust-protocol",
                        help="Song slug (e.g. rust-protocol)")
    song_p.add_argument("--clip", default="all",
                        help="Clip name or 'all' (e.g. take5, subharmonicon, rev2b-climax, minibrute2s)")
    song_p.add_argument("--bpm", type=float, default=95.0,
                        help="Override BPM (default read from song slug)")

    # --- legacy flat args (backwards compat: no subcommand = drum mode) ---
    parser.add_argument("--concept", default=None)
    parser.add_argument("--bpm", type=float, default=None)
    parser.add_argument("--key", default="Em")
    parser.add_argument("--steps", type=int, default=16)
    parser.add_argument("--instrument", default="digitakt",
                        choices=["digitakt", "rev2", "take5", "minibrute2s"])
    parser.add_argument("--output", default=None)
    parser.add_argument("--song", default=None)
    parser.add_argument("--clips", default=None,
                        help="Shorthand: --clips all  (equivalent to clips subcommand)")

    args = parser.parse_args()

    # Resolve mode
    if args.mode == "clips" or args.clips:
        slug = getattr(args, "song", None) or "rust-protocol"
        clip = args.clips if args.clips else getattr(args, "clip", "all")
        bpm  = args.bpm or 95.0
        generate_song_clips(slug, clip, bpm)
        return

    if args.mode == "drum" or args.concept:
        concept = getattr(args, "concept", None) or "heavy 4/4 groove"
        bpm     = args.bpm or 120.0
        steps   = args.steps
        output  = args.output

        concept_slug = concept.lower().replace(" ", "_")[:40]
        if output:
            output_path = Path(output)
        else:
            inst = getattr(args, "instrument", "digitakt")
            output_path = PATTERNS_DIR / f"{concept_slug}_{inst}.mid"

        log.info("Generating drum pattern: '%s' at %g BPM, %d steps → %s",
                 concept, bpm, steps, output_path)
        events = generate_drum_pattern(concept, steps, bpm)
        write_midi(events, output_path, bpm, steps)
        print(f"Done: {output_path}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()


# MIDI note numbers for common percussion (GM standard, Digitakt default mapping)
KICK = 36
SNARE = 38
CLOSED_HAT = 42
OPEN_HAT = 46
CLAP = 39
RIM = 37

# Scale intervals (semitones from root)
SCALES = {
    "minor": [0, 2, 3, 5, 7, 8, 10],         # Natural minor / Aeolian
    "phrygian": [0, 1, 3, 5, 7, 8, 10],       # Phrygian
    "dorian": [0, 2, 3, 5, 7, 9, 10],         # Dorian
    "locrian": [0, 1, 3, 4, 6, 8, 10],        # Locrian
    "diminished": [0, 2, 3, 5, 6, 8, 9, 11],  # Octatonic (H-W)
    "whole_tone": [0, 2, 4, 6, 8, 10],        # Whole tone
    "major": [0, 2, 4, 5, 7, 9, 11],          # Major / Ionian
}

NOTE_MAP = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11
}


def parse_key(key_str: str) -> tuple[int, str]:
    """Parse a key string like 'Em' or 'A minor' into (root_midi, scale_name)."""
    key_str = key_str.strip()
    scale = "minor"

    # Handle shorthand like "Em", "Am", "F#m"
    if key_str.endswith("m") and not key_str.endswith("maj"):
        root_name = key_str[:-1]
        scale = "minor"
    elif "minor" in key_str.lower():
        root_name = key_str.lower().replace("minor", "").strip().title()
    elif "phrygian" in key_str.lower():
        root_name = key_str.lower().replace("phrygian", "").strip().title()
        scale = "phrygian"
    elif "dorian" in key_str.lower():
        root_name = key_str.lower().replace("dorian", "").strip().title()
        scale = "dorian"
    elif "major" in key_str.lower() or key_str.endswith("M"):
        root_name = key_str.rstrip("M").lower().replace("major", "").strip().title()
        scale = "major"
    else:
        root_name = key_str.title()

    root_semitone = NOTE_MAP.get(root_name, 4)  # Default to E
    # MIDI note 36 = C2; root in octave 2
    root_midi = 24 + root_semitone  # C2 = 24, so E2 = 28
    return root_midi, scale


def euclidean_rhythm(hits: int, steps: int) -> list[int]:
    """Generate a Euclidean rhythm — evenly distribute 'hits' over 'steps'."""
    pattern = [0] * steps
    if hits <= 0:
        return pattern
    if hits >= steps:
        return [1] * steps

    # Bjorklund's algorithm
    groups = [[1]] * hits + [[0]] * (steps - hits)
    while len(groups) > 1:
        remainder = groups[len(groups) - (len(groups) % hits or hits):]
        groups = groups[:len(groups) - len(remainder)]
        groups = [a + b for a, b in zip(groups, remainder)] + groups[len(remainder):]

    flat = []
    for g in groups:
        flat.extend(g)
    return flat[:steps]


def generate_drum_pattern(concept: str, steps: int, bpm: float) -> list[dict]:
    """Generate a drum pattern as a list of MIDI events."""
    try:
        import mido
    except ImportError:
        log.error("mido not installed. Run: pip install -r scripts/requirements.txt")
        sys.exit(1)

    concept_lower = concept.lower()

    # Default: heavy 4/4
    kick_pattern = euclidean_rhythm(4, steps)
    snare_pattern = [0] * steps
    hat_pattern = euclidean_rhythm(8, steps)

    # Modify based on concept keywords
    if "7/8" in concept_lower or "7 8" in concept_lower:
        # 7/8: use 7 steps per cycle
        kick_pattern = euclidean_rhythm(3, 7) + [0] * (steps - 7)
        hat_pattern = euclidean_rhythm(5, 7) + [0] * (steps - 7)
        snare_pattern[3] = 1  # Snare on beat 4 of 7

    elif "half" in concept_lower or "doom" in concept_lower:
        # Half-time: snare only on beat 3
        kick_pattern = [1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0][:steps]
        snare_pattern = [0] * steps
        if steps >= 9:
            snare_pattern[8] = 1  # Beat 3 in 16-step = step 9

    elif "euclidean" in concept_lower:
        kick_pattern = euclidean_rhythm(5, steps)
        hat_pattern = euclidean_rhythm(11, steps)

    elif "machine" in concept_lower or "industrial" in concept_lower:
        kick_pattern = euclidean_rhythm(6, steps)
        hat_pattern = [1] * steps  # Straight 16ths
        snare_pattern[4] = 1
        snare_pattern[12] = 1

    # Snare default: beats 2 and 4 (steps 4 and 12 in 16-step)
    if sum(snare_pattern) == 0:
        snare_pattern[4] = 1
        snare_pattern[12] = 1

    # Build MIDI events
    ticks_per_beat = 480
    step_ticks = ticks_per_beat // 4  # 16th note

    events = []
    for i in range(steps):
        tick = i * step_ticks
        if kick_pattern[i]:
            events.append({"tick": tick, "note": KICK, "velocity": 127})
        if snare_pattern[i]:
            events.append({"tick": tick, "note": SNARE, "velocity": 100})
        if hat_pattern[i]:
            vel = 60 if i % 4 != 0 else 90  # Accent on downbeats
            events.append({"tick": tick, "note": CLOSED_HAT, "velocity": vel})

    return events


def write_midi(events: list[dict], output_path: Path, bpm: float, steps: int) -> None:
    """Write events to a MIDI file."""
    try:
        import mido
    except ImportError:
        log.error("mido not installed. Run: pip install -r scripts/requirements.txt")
        sys.exit(1)

    ticks_per_beat = 480
    tempo = int(60_000_000 / bpm)  # microseconds per beat

    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)

    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
    track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))

    # Sort events by tick
    sorted_events = sorted(events, key=lambda e: e["tick"])

    last_tick = 0
    for ev in sorted_events:
        delta = ev["tick"] - last_tick
        track.append(mido.Message("note_on", channel=9, note=ev["note"],
                                  velocity=ev["velocity"], time=delta))
        track.append(mido.Message("note_off", channel=9, note=ev["note"],
                                  velocity=0, time=10))
        last_tick = ev["tick"] + 10

    # End of track: pad to full pattern length
    pattern_end_tick = steps * (ticks_per_beat // 4)
    remaining = max(0, pattern_end_tick - last_tick)
    track.append(mido.MetaMessage("end_of_track", time=remaining))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(output_path))
    log.info("MIDI written: %s (%d events)", output_path, len(sorted_events))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate MIDI sequences for the IRON STATIC rig."
    )
    parser.add_argument("--concept", default="heavy 4/4 groove",
                        help="Describe the pattern concept")
    parser.add_argument("--bpm", type=float, default=120.0, help="BPM (default: 120)")
    parser.add_argument("--key", default="Em", help="Key/scale (e.g. Em, Am, F#m, E Phrygian)")
    parser.add_argument("--steps", type=int, default=16,
                        help="Number of steps in the pattern (default: 16)")
    parser.add_argument("--instrument", default="digitakt",
                        choices=["digitakt", "rev2", "take5", "minibrute2s"],
                        help="Target instrument")
    parser.add_argument("--output", default=None,
                        help="Output .mid file path (default: midi/patterns/<concept>.mid)")
    args = parser.parse_args()

    concept_slug = args.concept.lower().replace(" ", "_")[:40]
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path(f"midi/patterns/{concept_slug}_{args.instrument}.mid")

    log.info("Generating: '%s' at %g BPM, key %s, %d steps → %s",
             args.concept, args.bpm, args.key, args.steps, output_path)

    events = generate_drum_pattern(args.concept, args.steps, args.bpm)
    write_midi(events, output_path, args.bpm, args.steps)
    print(f"Done: {output_path}")


if __name__ == "__main__":
    main()
