#!/usr/bin/env python3
"""
audio_to_midi.py — Audio-to-MIDI transcription for IRON STATIC.

Converts audio files to MIDI sequences using Basic Pitch (Spotify).
Optionally separates a full mix into stems first using Demucs.

Usage:
    python scripts/audio_to_midi.py audio/recordings/raw/my_bass.aif
    python scripts/audio_to_midi.py audio/recordings/raw/full_mix.wav --stems
    python scripts/audio_to_midi.py audio/recordings/raw/full_mix.wav --stems --stem-type bass
    python scripts/audio_to_midi.py path/to/file.wav --output midi/sequences/
"""

import argparse
import logging
import re
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

# MIDI channel routing suggestions by stem type
STEM_CHANNEL_MAP = {
    "bass":   {"instrument": "Minibrute 2S or Subharmonicon", "channel": "7 or 5"},
    "drums":  {"instrument": "Digitakt (trigger source) or DFAM", "channel": "6"},
    "other":  {"instrument": "Rev2 Layer A or Take 5", "channel": "2 or 4"},
    "vocals": {"instrument": "Rev2 Layer B (process heavily)", "channel": "3"},
}


def slugify(name: str) -> str:
    """Convert a filename stem to a safe slug."""
    name = name.lower()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s_]+", "-", name).strip("-")
    return name


def transcribe_to_midi(audio_path: Path, output_dir: Path, stem_type: str = "unknown") -> Path:
    """
    Run Basic Pitch transcription on an audio file and save the MIDI output.
    Returns the path to the output .mid file.
    """
    try:
        from basic_pitch.inference import predict
        from basic_pitch import ICASSP_2022_MODEL_PATH
    except ImportError:
        log.error("basic-pitch not installed. Run: pip install basic-pitch")
        sys.exit(1)

    log.info("Transcribing: %s", audio_path.name)
    model_output, midi_data, note_events = predict(str(audio_path))

    slug = slugify(audio_path.stem)
    out_name = f"{slug}_{stem_type}_v1.mid"
    out_path = output_dir / out_name

    output_dir.mkdir(parents=True, exist_ok=True)
    midi_data.write(str(out_path))
    log.info("MIDI written: %s", out_path)
    return out_path


def separate_stems(audio_path: Path, stems_dir: Path) -> dict[str, Path]:
    """
    Run Demucs stem separation on a full mix.
    Returns a dict of {stem_type: path_to_stem_wav}.
    """
    try:
        import torch  # noqa: F401 — validate demucs deps present
    except ImportError:
        log.error("demucs requires PyTorch. Run: pip install demucs")
        sys.exit(1)

    log.info("Running Demucs stem separation on: %s", audio_path.name)
    result = subprocess.run(
        [sys.executable, "-m", "demucs", str(audio_path), "-o", str(stems_dir), "--mp3"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        log.error("Demucs failed:\n%s", result.stderr)
        sys.exit(1)

    # Demucs outputs to: stems_dir/htdemucs/<track_name>/{drums,bass,other,vocals}.mp3
    track_name = audio_path.stem
    stem_dir = stems_dir / "htdemucs" / track_name
    if not stem_dir.exists():
        # fallback: some demucs versions omit the model name subdir
        stem_dir = stems_dir / track_name

    stems = {}
    for stem_file in stem_dir.glob("*.mp3"):
        stems[stem_file.stem] = stem_file
    for stem_file in stem_dir.glob("*.wav"):
        stems[stem_file.stem] = stem_file

    if not stems:
        log.error("Demucs ran but no stem files found in: %s", stem_dir)
        sys.exit(1)

    log.info("Stems separated: %s", list(stems.keys()))
    return stems


def print_routing_suggestions(midi_paths: list[tuple[str, Path]]) -> None:
    """Print IRON STATIC rig routing suggestions for each MIDI file."""
    print("\n--- MIDI ASSIGNMENT SUGGESTIONS ---")
    for stem_type, midi_path in midi_paths:
        mapping = STEM_CHANNEL_MAP.get(stem_type, {
            "instrument": "Rev2 Layer A (ch 2) — review and reroute",
            "channel": "2"
        })
        print(f"  {midi_path.name}")
        print(f"    → Instrument : {mapping['instrument']}")
        print(f"    → MIDI ch    : {mapping['channel']}")
        print(f"    → File       : {midi_path}")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert audio to MIDI sequences for the IRON STATIC rig."
    )
    parser.add_argument("file", help="Path to audio file (WAV, AIF, AIFF, MP3, FLAC)")
    parser.add_argument(
        "--stems",
        action="store_true",
        help="Separate the audio into stems (drums/bass/other) using Demucs before transcription"
    )
    parser.add_argument(
        "--stem-type",
        choices=["bass", "drums", "other", "vocals", "all"],
        default="all",
        help="Which stem to transcribe after separation (default: all). Ignored without --stems."
    )
    parser.add_argument(
        "--output",
        default="midi/sequences",
        help="Output directory for .mid files (default: midi/sequences)"
    )
    parser.add_argument(
        "--stems-dir",
        default="audio/recordings/stems",
        help="Directory to write Demucs stem files (default: audio/recordings/stems)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress info logs"
    )
    args = parser.parse_args()

    if args.quiet:
        logging.disable(logging.INFO)

    audio_path = Path(args.file)
    if not audio_path.exists():
        log.error("File not found: %s", audio_path)
        sys.exit(1)

    output_dir = Path(args.output)
    midi_outputs: list[tuple[str, Path]] = []

    if args.stems:
        stems_dir = Path(args.stems_dir)
        stems = separate_stems(audio_path, stems_dir)

        for stem_type, stem_path in stems.items():
            if args.stem_type != "all" and stem_type != args.stem_type:
                continue
            midi_path = transcribe_to_midi(stem_path, output_dir, stem_type=stem_type)
            midi_outputs.append((stem_type, midi_path))
    else:
        # Treat the file as a single stem — infer type from filename if possible
        name_lower = audio_path.stem.lower()
        inferred_type = "unknown"
        for key in STEM_CHANNEL_MAP:
            if key in name_lower:
                inferred_type = key
                break

        midi_path = transcribe_to_midi(audio_path, output_dir, stem_type=inferred_type)
        midi_outputs.append((inferred_type, midi_path))

    print_routing_suggestions(midi_outputs)


if __name__ == "__main__":
    main()
