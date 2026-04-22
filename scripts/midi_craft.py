#!/usr/bin/env python3
"""
midi_craft.py — MIDI sequence generator for IRON STATIC.

Generates MIDI files from a musical concept, key, BPM, and instrument target.

Usage:
    python scripts/midi_craft.py --concept "heavy 7/8 kick groove" --bpm 140 --key Em
    python scripts/midi_craft.py --pattern "euclidean kick" --steps 16 --instrument digitakt
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
