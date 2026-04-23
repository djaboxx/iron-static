#!/usr/bin/env python3
"""
run_audio_intake.py — Audio file intake processor for IRON STATIC.

Scans audio/recordings/raw/ for new audio files not yet logged in the intake manifest,
runs BPM + key detection (via librosa if available), calls Gemini for rig-specific
suggestions, and writes results to:

  outputs/audio_analysis/<filename>.json    — per-file analysis JSON
  outputs/audio_intake_manifest.json        — tracks all processed files
  knowledge/recordings/YYYY-MM-DD.md        — human-readable session log

If no new files are found, exits cleanly without writing anything.

Usage:
    python scripts/run_audio_intake.py
    python scripts/run_audio_intake.py --no-llm
    python scripts/run_audio_intake.py --date 2026-05-01
    python scripts/run_audio_intake.py --scan-stems    # also scan audio/recordings/stems/
"""
import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "audio" / "recordings" / "raw"
STEMS_DIR = REPO_ROOT / "audio" / "recordings" / "stems"
ANALYSIS_DIR = REPO_ROOT / "outputs" / "audio_analysis"
MANIFEST_PATH = REPO_ROOT / "outputs" / "audio_intake_manifest.json"
OUT_DIR = REPO_ROOT / "knowledge" / "recordings"

AUDIO_EXTENSIONS = {".wav", ".aif", ".aiff", ".mp3", ".flac", ".ogg", ".m4a"}

INTAKE_PROMPT_TEMPLATE = """\
You are IRON STATIC's Copilot analyzing a newly recorded audio file.
IRON STATIC is an electronic metal duo — heavy, weird, electronic, intentional.

The rig:
- Elektron Digitakt MK1: drum machine + sampler + MIDI sequencer
- Sequential Rev2: 16-voice polyphonic analog (bi-timbral, Curtis filter), MIDI ch 2/3
- Sequential Take 5: 5-voice compact poly analog, MIDI ch 4
- Moog Subharmonicon: polyrhythmic semi-modular drone (2 VCOs + 4 subharmonic oscs), MIDI ch 5
- Moog DFAM: analog percussion (8-step sequencer, Moog ladder filter), MIDI ch 6
- Arturia Minibrute 2S: patchable mono synth + step sequencer (Steiner-Parker, Brute Factor), MIDI ch 7
- Arturia Pigments: software poly (Wavetable/Analog/Sample engines, 4 Macros), MIDI ch 8

Audio file: {filename}
File path: {filepath}

Analysis results:
{analysis_block}

Write a concise intake report for this audio file with exactly these three sections:

## What This Is
2–3 sentences. Describe the audio: is it a drum loop, a synth riff, a bass line, an ambient texture,
a full mix? What is its energy and character? Describe the frequency content in plain terms.
Reference the detected key and BPM if available and whether they seem reliable.

## How It Fits IRON STATIC
2 sentences. Does this clip work as-is in an IRON STATIC track? Does it need treatment
(distortion, gating, resampling into Digitakt)? Where would it sit in an arrangement?

## Rig Suggestions
3 specific, actionable suggestions for working this file into the rig.
Name the instrument. Name the technique. Be concrete.
Example: "Sample it into Digitakt track 3 — trim to 1 bar, apply sample start parameter lock
on step 5 to catch the snare transient on the off-beat."

Keep the entire response under 300 words.
"""


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text())
        except json.JSONDecodeError:
            log.warning("Manifest JSON corrupt — starting fresh")
    return {"processed": {}}


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))


def scan_audio_files(include_stems: bool = False) -> list[Path]:
    """Return all audio files in raw/ (and optionally stems/)."""
    dirs = [RAW_DIR]
    if include_stems:
        dirs.append(STEMS_DIR)
    found = []
    for d in dirs:
        if d.exists():
            for ext in AUDIO_EXTENSIONS:
                found.extend(d.rglob(f"*{ext}"))
    return sorted(found)


def analyze_file(filepath: Path) -> dict:
    """Run BPM + key + spectral analysis. Returns partial results if librosa unavailable."""
    result: dict = {
        "file": str(filepath.relative_to(REPO_ROOT)),
        "filename": filepath.name,
        "size_bytes": filepath.stat().st_size,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        import librosa
        import numpy as np

        log.info("Running librosa analysis on %s…", filepath.name)
        y, sr = librosa.load(str(filepath), mono=True, sr=None)
        duration = librosa.get_duration(y=y, sr=sr)
        result["duration_seconds"] = round(duration, 2)
        result["sample_rate"] = sr

        # BPM
        try:
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            tempo_val = float(tempo.item() if hasattr(tempo, "item") else tempo)
            result["bpm"] = round(tempo_val, 1)
            result["beat_count"] = int(len(beats))
        except Exception as e:
            log.debug("BPM detection failed: %s", e)

        # Key (chroma-based heuristic)
        try:
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            chroma_mean = chroma.mean(axis=1)
            pitch_classes = ["C", "C#", "D", "D#", "E", "F",
                             "F#", "G", "G#", "A", "A#", "B"]
            dominant = int(np.argmax(chroma_mean))
            maj_tpl = np.array([1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1], dtype=float)
            min_tpl = np.array([1, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0], dtype=float)
            maj_corr = float(np.dot(chroma_mean, np.roll(maj_tpl, dominant)))
            min_corr = float(np.dot(chroma_mean, np.roll(min_tpl, dominant)))
            mode = "major" if maj_corr > min_corr else "minor"
            result["key"] = pitch_classes[dominant]
            result["mode"] = mode
            result["key_display"] = f"{pitch_classes[dominant]} {mode}"
        except Exception as e:
            log.debug("Key detection failed: %s", e)

        # Spectral summary
        try:
            spectral_centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
            fft = np.abs(np.fft.rfft(y))
            freqs = np.fft.rfftfreq(len(y), d=1.0 / sr)
            total_power = float(np.sum(fft ** 2)) or 1.0

            def _band_pct(lo, hi) -> float:
                mask = (freqs >= lo) & (freqs < hi)
                return round(100.0 * float(np.sum(fft[mask] ** 2)) / total_power, 1)

            result["spectrum"] = {
                "sub_20_80hz_pct": _band_pct(20, 80),
                "bass_80_250hz_pct": _band_pct(80, 250),
                "low_mid_250_800hz_pct": _band_pct(250, 800),
                "mid_800_4khz_pct": _band_pct(800, 4000),
                "high_4khz_plus_pct": _band_pct(4000, sr / 2),
                "spectral_centroid_hz": round(spectral_centroid, 1),
            }
        except Exception as e:
            log.debug("Spectral analysis failed: %s", e)

    except ImportError:
        log.warning("librosa not installed — skipping acoustic analysis for %s", filepath.name)
        result["analysis_skipped"] = "librosa not available"

    return result


def format_analysis_block(analysis: dict) -> str:
    """Turn analysis dict into a readable text block for the LLM prompt."""
    lines = []
    if analysis.get("duration_seconds"):
        lines.append(f"- Duration: {analysis['duration_seconds']:.1f}s")
    if analysis.get("sample_rate"):
        lines.append(f"- Sample rate: {analysis['sample_rate']} Hz")
    if analysis.get("bpm"):
        lines.append(f"- Detected BPM: {analysis['bpm']}")
    if analysis.get("key_display"):
        lines.append(f"- Detected key: {analysis['key_display']}")
    if "spectrum" in analysis:
        sp = analysis["spectrum"]
        lines.append(
            f"- Spectral centroid: {sp.get('spectral_centroid_hz', '?')} Hz\n"
            f"  Sub (20–80 Hz): {sp.get('sub_20_80hz_pct', '?')}%  |  "
            f"Bass (80–250 Hz): {sp.get('bass_80_250hz_pct', '?')}%  |  "
            f"Low-mid (250–800 Hz): {sp.get('low_mid_250_800hz_pct', '?')}%  |  "
            f"Mid (800 Hz–4 kHz): {sp.get('mid_800_4khz_pct', '?')}%  |  "
            f"High (4 kHz+): {sp.get('high_4khz_plus_pct', '?')}%"
        )
    if analysis.get("analysis_skipped"):
        lines.append(f"- Analysis skipped: {analysis['analysis_skipped']}")
    return "\n".join(lines) if lines else "(no acoustic data available)"


def generate_llm_notes(filepath: Path, analysis: dict) -> str:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from llm_utils import complete  # noqa: PLC0415

    prompt = INTAKE_PROMPT_TEMPLATE.format(
        filename=filepath.name,
        filepath=str(filepath.relative_to(REPO_ROOT)),
        analysis_block=format_analysis_block(analysis),
    )
    return complete(prompt, model_tier="fast")


def generate_no_llm_notes(filepath: Path, analysis: dict) -> str:
    return (
        f"## What This Is\n*(stub — run without --no-llm for real analysis)*\n\n"
        f"## How It Fits IRON STATIC\n*(stub)*\n\n"
        f"## Rig Suggestions\n*(stub)*\n"
    )


def build_recording_doc(today: str, results: list[dict]) -> str:
    """Build the knowledge/recordings/YYYY-MM-DD.md document."""
    lines = [f"# IRON STATIC — Audio Intake ({today})", ""]
    lines.append(f"{len(results)} new file(s) processed.\n")

    for r in results:
        analysis = r["analysis"]
        notes = r["notes"]
        lines += [
            f"---",
            f"",
            f"## {analysis['filename']}",
            f"",
            f"**Path:** `{analysis['file']}`",
        ]
        if analysis.get("duration_seconds"):
            lines.append(f"**Duration:** {analysis['duration_seconds']:.1f}s")
        if analysis.get("bpm"):
            lines.append(f"**BPM:** {analysis['bpm']}")
        if analysis.get("key_display"):
            lines.append(f"**Key:** {analysis['key_display']}")
        lines += ["", notes.strip(), ""]

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Process new audio files into IRON STATIC knowledge base")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM call, write stubs")
    parser.add_argument("--date", default=None, help="Override date string (YYYY-MM-DD)")
    parser.add_argument("--scan-stems", action="store_true", help="Also scan audio/recordings/stems/")
    args = parser.parse_args()

    today = args.date or date.today().isoformat()

    manifest = load_manifest()
    processed_keys = set(manifest["processed"].keys())

    audio_files = scan_audio_files(include_stems=args.scan_stems)
    new_files = [f for f in audio_files if str(f.relative_to(REPO_ROOT)) not in processed_keys]

    if not new_files:
        log.info("No new audio files found — nothing to process.")
        sys.exit(0)

    log.info("Found %d new audio file(s) to process", len(new_files))

    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for filepath in new_files:
        log.info("Processing: %s", filepath.name)

        analysis = analyze_file(filepath)
        analysis_out = ANALYSIS_DIR / f"{filepath.stem}.json"
        analysis_out.write_text(json.dumps(analysis, indent=2))
        log.info("  → wrote %s", analysis_out.relative_to(REPO_ROOT))

        if args.no_llm:
            notes = generate_no_llm_notes(filepath, analysis)
        else:
            try:
                notes = generate_llm_notes(filepath, analysis)
            except Exception as e:
                log.warning("LLM call failed for %s: %s — using stub", filepath.name, e)
                notes = generate_no_llm_notes(filepath, analysis)

        results.append({"analysis": analysis, "notes": notes})

        # Update manifest
        rel_key = str(filepath.relative_to(REPO_ROOT))
        manifest["processed"][rel_key] = {
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "date_tag": today,
            "bpm": analysis.get("bpm"),
            "key": analysis.get("key_display"),
        }

    # Write recording doc
    doc_path = OUT_DIR / f"{today}.md"
    # If doc already exists for today, append rather than overwrite
    if doc_path.exists():
        existing = doc_path.read_text()
        extra = build_recording_doc(today + " (batch 2)", results)
        doc_path.write_text(existing.rstrip() + "\n\n" + extra)
        log.info("Appended to existing recording doc: %s", doc_path.relative_to(REPO_ROOT))
    else:
        doc_path.write_text(build_recording_doc(today, results))
        log.info("Wrote %s", doc_path.relative_to(REPO_ROOT))

    save_manifest(manifest)
    log.info("Manifest updated: %d total processed files", len(manifest["processed"]))


if __name__ == "__main__":
    main()
