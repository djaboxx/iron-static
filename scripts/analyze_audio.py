#!/usr/bin/env python3
"""
analyze_audio.py — Audio analysis script for IRON STATIC.

Analyzes an audio file for key, BPM, spectral character, and outputs
structured analysis data to stdout or a JSON file.

Usage:
    python scripts/analyze_audio.py path/to/file.wav
    python scripts/analyze_audio.py path/to/file.wav --focus bpm
    python scripts/analyze_audio.py path/to/file.wav --output analysis.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def analyze_key(y, sr) -> dict:
    """Estimate musical key using chroma features."""
    try:
        import librosa
        import numpy as np

        chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
        chroma_mean = chroma.mean(axis=1)
        pitch_classes = ["C", "C#", "D", "D#", "E", "F",
                         "F#", "G", "G#", "A", "A#", "B"]
        dominant = int(np.argmax(chroma_mean))

        # Simple major/minor heuristic: compare major and minor template correlation
        major_template = np.array([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1], dtype=float)
        minor_template = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0], dtype=float)

        rolled_major = np.roll(major_template, dominant)
        rolled_minor = np.roll(minor_template, dominant)
        maj_corr = float(np.dot(chroma_mean, rolled_major))
        min_corr = float(np.dot(chroma_mean, rolled_minor))

        mode = "major" if maj_corr > min_corr else "minor"
        mode_name = "Ionian" if mode == "major" else "Aeolian"

        return {
            "root": pitch_classes[dominant],
            "mode": mode,
            "scale": mode_name,
            "display": f"{pitch_classes[dominant]} {mode} ({mode_name})",
            "confidence": "heuristic"
        }
    except ImportError:
        log.warning("librosa not available — key detection skipped")
        return {"root": "unknown", "mode": "unknown", "display": "unavailable"}


def analyze_bpm(y, sr) -> dict:
    """Estimate BPM using onset strength."""
    try:
        import librosa

        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        return {
            "bpm": float(round(tempo, 1)),
            "beat_count": int(len(beats)),
            "confidence": "librosa_beat_track"
        }
    except ImportError:
        log.warning("librosa not available — BPM detection skipped")
        return {"bpm": "unknown"}


def analyze_spectrum(y, sr) -> dict:
    """Characterize spectral content across frequency bands."""
    try:
        import librosa
        import numpy as np

        # RMS energy in frequency bands
        stft = np.abs(librosa.stft(y))
        freqs = librosa.fft_frequencies(sr=sr)

        def band_energy(low_hz: float, high_hz: float) -> float:
            mask = (freqs >= low_hz) & (freqs < high_hz)
            return float(np.mean(stft[mask])) if mask.any() else 0.0

        sub = band_energy(20, 80)
        bass = band_energy(80, 250)
        low_mid = band_energy(250, 800)
        mid = band_energy(800, 4000)
        high = band_energy(4000, 16000)
        total = sub + bass + low_mid + mid + high or 1.0

        def describe(val: float, total: float) -> str:
            pct = val / total
            if pct > 0.35:
                return "dominant"
            elif pct > 0.20:
                return "present"
            elif pct > 0.08:
                return "light"
            return "minimal"

        spectral_centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))

        return {
            "sub_20_80hz": describe(sub, total),
            "bass_80_250hz": describe(bass, total),
            "low_mid_250_800hz": describe(low_mid, total),
            "mid_800_4000hz": describe(mid, total),
            "high_4000hz_plus": describe(high, total),
            "spectral_centroid_hz": round(spectral_centroid, 1)
        }
    except ImportError:
        log.warning("librosa not available — spectral analysis skipped")
        return {}


def rig_suggestions(key_info: dict, bpm_info: dict, spectrum: dict) -> list[str]:
    """Generate IRON STATIC rig-specific suggestions based on analysis."""
    suggestions = []
    root = key_info.get("root", "?")
    mode = key_info.get("mode", "?")
    bpm = bpm_info.get("bpm", "?")

    suggestions.append(
        f"Digitakt: Program a kick pattern at {bpm} BPM. "
        f"Set MIDI auto-channel to sequence Rev2 in {root} {mode}."
    )

    sub_level = spectrum.get("sub_20_80hz", "unknown")
    if sub_level in ("dominant", "present"):
        suggestions.append(
            "Subharmonicon: Sub is already present in source — "
            "use Subharmonicon sparingly or an octave up to avoid mud."
        )
    else:
        suggestions.append(
            f"Subharmonicon: Sub is light — tune VCO1 to {root} and use Sub1 division 2 "
            "for deep foundation under this material."
        )

    if mode == "minor":
        suggestions.append(
            f"Rev2: Program {root} natural minor (Aeolian) chords. "
            "Try a slow LP filter sweep on the pad for movement."
        )
    else:
        suggestions.append(
            f"Rev2: {root} major tonality — consider using Dorian for "
            "a darker, more IRON STATIC-appropriate palette."
        )

    high_level = spectrum.get("high_4000hz_plus", "unknown")
    if high_level in ("minimal", "light"):
        suggestions.append(
            "Minibrute 2S: High content is sparse — a Steiner-Parker HP lead "
            "would cut through without competing with the source."
        )

    return suggestions


def analyze_file(filepath: Path, focus: str) -> dict:
    """Main analysis entry point."""
    try:
        import librosa
        import soundfile as sf
    except ImportError as e:
        log.error("Missing dependency: %s. Run: pip install -r scripts/requirements.txt", e)
        sys.exit(1)

    log.info("Loading: %s", filepath)
    try:
        y, sr = librosa.load(str(filepath), mono=True, sr=None)
    except Exception as e:
        log.error("Could not load audio file: %s", e)
        sys.exit(1)

    duration = float(len(y) / sr)

    result: dict = {
        "file": str(filepath),
        "duration_seconds": round(duration, 2),
        "sample_rate": sr,
    }

    if focus in ("all", "key"):
        result["key"] = analyze_key(y, sr)
    if focus in ("all", "bpm"):
        result["bpm"] = analyze_bpm(y, sr)
    if focus in ("all", "spectrum"):
        result["spectrum"] = analyze_spectrum(y, sr)

    if focus == "all":
        result["rig_suggestions"] = rig_suggestions(
            result.get("key", {}),
            result.get("bpm", {}),
            result.get("spectrum", {})
        )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze an audio file for key, BPM, and spectral character (IRON STATIC rig)."
    )
    parser.add_argument("file", help="Path to audio file (WAV, AIFF, MP3, FLAC)")
    parser.add_argument(
        "--focus",
        choices=["all", "key", "bpm", "spectrum"],
        default="all",
        help="Which analysis to perform (default: all)"
    )
    parser.add_argument(
        "--output",
        help="Write JSON output to this file (default: print to stdout)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress info logs"
    )
    args = parser.parse_args()

    if args.quiet:
        logging.disable(logging.INFO)

    filepath = Path(args.file)
    if not filepath.exists():
        log.error("File not found: %s", filepath)
        sys.exit(1)

    result = analyze_file(filepath, args.focus)

    output_json = json.dumps(result, indent=2)
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(output_json)
        log.info("Analysis written to: %s", out_path)
    else:
        print(output_json)


if __name__ == "__main__":
    main()
