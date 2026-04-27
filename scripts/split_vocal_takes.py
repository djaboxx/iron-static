#!/usr/bin/env python3
from __future__ import annotations
"""
split_vocal_takes.py — Split a single vocal recording into individual training takes.

Detects silence gaps between phrases and exports each segment as a separate WAV file.
Use this when a vocalist records all phrases in one continuous file.

Usage:
    python scripts/split_vocal_takes.py <input_file>
    python scripts/split_vocal_takes.py <input_file> --out-dir instruments/vela/takes
    python scripts/split_vocal_takes.py <input_file> --min-silence 1.5 --silence-thresh -40
    python scripts/split_vocal_takes.py <input_file> --dry-run   # preview splits without saving

Output: instruments/vela/takes/take_01.wav, take_02.wav, ...
"""

import argparse
import logging
import sys
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

DEFAULT_OUT_DIR = Path("instruments/vela/takes")
DEFAULT_MIN_SILENCE_SEC = 1.5   # minimum silence gap to treat as a phrase boundary
DEFAULT_SILENCE_THRESH_DB = -40  # dB threshold below which audio is considered silence
DEFAULT_PAD_SEC = 0.1            # seconds of silence to leave at start/end of each take
MIN_TAKE_SEC = 2.0               # discard segments shorter than this (likely noise/artifacts)


def rms_to_db(rms: np.ndarray) -> np.ndarray:
    return 20 * np.log10(np.maximum(rms, 1e-10))


def detect_speech_regions(
    y: np.ndarray,
    sr: int,
    silence_thresh_db: float,
    min_silence_sec: float,
    pad_sec: float,
) -> list[tuple[int, int]]:
    """Return list of (start_sample, end_sample) for each speech region."""
    frame_length = 2048
    hop_length = 512

    rms = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
    db = rms_to_db(rms)
    is_speech = db > silence_thresh_db

    min_silence_frames = int(min_silence_sec * sr / hop_length)
    pad_frames = int(pad_sec * sr / hop_length)

    regions: list[tuple[int, int]] = []
    in_speech = False
    start_frame = 0
    silence_count = 0

    for i, speech in enumerate(is_speech):
        if speech:
            if not in_speech:
                start_frame = max(0, i - pad_frames)
                in_speech = True
            silence_count = 0
        else:
            if in_speech:
                silence_count += 1
                if silence_count >= min_silence_frames:
                    end_frame = min(len(is_speech) - 1, i - silence_count + pad_frames)
                    regions.append((
                        librosa.frames_to_samples(start_frame, hop_length=hop_length),
                        librosa.frames_to_samples(end_frame, hop_length=hop_length),
                    ))
                    in_speech = False
                    silence_count = 0

    if in_speech:
        end_frame = len(is_speech) - 1
        regions.append((
            librosa.frames_to_samples(start_frame, hop_length=hop_length),
            min(len(y), librosa.frames_to_samples(end_frame, hop_length=hop_length)),
        ))

    return regions


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Split a vocal recording into individual training takes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", help="Input audio file (wav, m4a, mp3, aiff, etc.)")
    parser.add_argument(
        "--out-dir", default=str(DEFAULT_OUT_DIR),
        help=f"Output directory (default: {DEFAULT_OUT_DIR})",
    )
    parser.add_argument(
        "--min-silence", type=float, default=DEFAULT_MIN_SILENCE_SEC,
        help=f"Minimum silence gap in seconds to split on (default: {DEFAULT_MIN_SILENCE_SEC})",
    )
    parser.add_argument(
        "--silence-thresh", type=float, default=DEFAULT_SILENCE_THRESH_DB,
        help=f"Silence threshold in dB (default: {DEFAULT_SILENCE_THRESH_DB})",
    )
    parser.add_argument(
        "--pad", type=float, default=DEFAULT_PAD_SEC,
        help=f"Silence padding to keep around each take in seconds (default: {DEFAULT_PAD_SEC})",
    )
    parser.add_argument(
        "--prefix", default="take",
        help="Output filename prefix (default: 'take' → take_01.wav, take_02.wav...)",
    )
    parser.add_argument(
        "--start-index", type=int, default=1,
        help="Starting number for output filenames (default: 1 → take_01.wav). "
             "Use this to append to an existing set without overwriting.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Preview detected splits without writing any files",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        log.error("File not found: %s", input_path)
        sys.exit(1)

    log.info("Loading: %s", input_path)
    y, sr = librosa.load(str(input_path), sr=None, mono=True)
    duration = len(y) / sr
    log.info("Duration: %.1fs | Sample rate: %dHz", duration, sr)

    log.info(
        "Detecting phrases (silence threshold: %ddB, min gap: %.1fs)...",
        args.silence_thresh, args.min_silence,
    )
    regions = detect_speech_regions(
        y, sr,
        silence_thresh_db=args.silence_thresh,
        min_silence_sec=args.min_silence,
        pad_sec=args.pad,
    )

    # Filter out segments that are too short
    regions = [
        (s, e) for s, e in regions
        if (e - s) / sr >= MIN_TAKE_SEC
    ]

    if not regions:
        log.error(
            "No speech regions found. Try lowering --silence-thresh (current: %ddB) "
            "or --min-silence (current: %.1fs).",
            args.silence_thresh, args.min_silence,
        )
        sys.exit(1)

    log.info("Found %d takes:", len(regions))
    for i, (s, e) in enumerate(regions, 1):
        log.info("  Take %02d: %.2fs – %.2fs (%.1fs)", i, s / sr, e / sr, (e - s) / sr)

    if args.dry_run:
        log.info("Dry run — no files written.")
        return

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for i, (start, end) in enumerate(regions, args.start_index):
        segment = y[start:end]
        out_path = out_dir / f"{args.prefix}_{i:02d}.wav"
        sf.write(str(out_path), segment, sr, subtype="PCM_24")
        log.info("  Saved: %s (%.1fs)", out_path, len(segment) / sr)

    log.info("Done. %d takes in: %s", len(regions), out_dir)
    log.info("Review takes, delete any bad ones, then run LoRA training via: http://localhost:7860")


if __name__ == "__main__":
    main()
