#!/usr/bin/env python3
"""
gemini_listen.py — Qualitative audio analysis via Gemini.

Sends an audio file to the Gemini API and returns aesthetic analysis
in the context of IRON STATIC's sonic palette. Answers the question
librosa/basic-pitch can't: does this *feel* right?

Usage:
    python scripts/gemini_listen.py --file audio/recordings/raw/take1.wav
    python scripts/gemini_listen.py --file ref.mp3 --question "Is this heavy enough?"
    python scripts/gemini_listen.py --file loop.wav --output json
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger(__name__)

SONGS_DB = Path(__file__).parent.parent / "database" / "songs.json"

IRON_STATIC_CONTEXT = """\
You are IRON STATIC's Gemini — the generative intelligence of this band's AI collective. \
IRON STATIC's aesthetic draws from: Nine Inch Nails (abrasive industrial texture), \
Lamb of God (groove-metal weight and fury), One Day as a Lion (stripped urgency), \
Modeselector (Berlin electronic grid and bass pressure), Run the Jewels (fast, political, punchy), \
and Dr. Teeth and the Electric Mayhem (chaotic, chromatic, joyful weirdness). \
The rig: Elektron Digitakt MK1 (drums/sampler), Sequential Rev2 (polyphonic analog pads/leads), \
Sequential Take 5 (compact poly analog chords/leads), Moog Subharmonicon (polyrhythmic drones), \
Moog DFAM (analog percussion), Arturia Minibrute 2S (mono semi-modular), \
Arturia Pigments (software polyphonic synth). \
Music should be heavy, weird, electronic, and intentional. \
Noise, distortion, and feedback are compositional elements, not mistakes."""

DEFAULT_QUESTION = """\
Analyze this audio as a full IRON STATIC production partner. Cover:
1. PERCEIVED KEY / MODE / SCALE — best guess even if uncertain.
2. TEMPO — estimated BPM range, feel (rigid/loose/swung).
3. DOMINANT TEXTURES — describe timbres, layers, and spectral character.
4. ENERGY & DYNAMICS — where does it hit, where does it breathe?
5. IRON STATIC FIT — honestly rate how well this fits our aesthetic (high/medium/low). Explain why.
6. WHAT'S WORKING — specific elements that are strong.
7. WHAT'S FIGHTING — specific elements that undermine the aesthetic.
8. THREE CONCRETE SUGGESTIONS — actionable changes referencing specific instruments in our rig."""

ADDITIONAL_SONG_CONTEXT = """\
Active song context: key={key}, scale={scale}, BPM={bpm}. \
Evaluate this audio in the context of this song's intended direction."""


def load_active_song() -> dict | None:
    """Return the active song dict from database/songs.json, or None."""
    if not SONGS_DB.exists():
        return None
    with SONGS_DB.open() as f:
        songs = json.load(f)
    for song in songs.get("songs", []):
        if song.get("status") == "active":
            return song
    return None


def build_prompt(question: str, active_song: dict | None) -> str:
    parts = [IRON_STATIC_CONTEXT]
    if active_song:
        parts.append(
            ADDITIONAL_SONG_CONTEXT.format(
                key=active_song.get("key", "unknown"),
                scale=active_song.get("scale", "unknown"),
                bpm=active_song.get("bpm", "unknown"),
            )
        )
    parts.append("\n" + question)
    return "\n\n".join(parts)


def analyze(file_path: Path, prompt: str, model: str) -> str:
    """Upload audio to Gemini and return the response text."""
    try:
        import google.genai as genai
    except ImportError:
        log.error("google-genai not installed. Run: pip install google-genai>=1.0.0")
        sys.exit(1)

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        log.error(
            "No API key found. Set GOOGLE_API_KEY or GEMINI_API_KEY environment variable."
        )
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    log.info("Uploading %s to Gemini Files API…", file_path.name)
    audio_file = client.files.upload(file=str(file_path))
    log.info("File uploaded: %s", audio_file.name)

    log.info("Requesting analysis from %s…", model)
    response = client.models.generate_content(
        model=model,
        contents=[audio_file, prompt],
    )

    # Clean up the uploaded file
    try:
        client.files.delete(name=audio_file.name)
        log.info("Uploaded file deleted from Gemini Files API.")
    except Exception as exc:
        log.warning("Could not delete uploaded file: %s", exc)

    return response.text


def format_json_output(analysis_text: str, file_path: Path, active_song: dict | None) -> str:
    result = {
        "file": str(file_path),
        "active_song": active_song.get("slug") if active_song else None,
        "analysis": analysis_text,
    }
    return json.dumps(result, indent=2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Qualitative audio analysis via Gemini in the IRON STATIC context."
    )
    parser.add_argument(
        "--file",
        required=True,
        type=Path,
        metavar="PATH",
        help="Path to audio file to analyze (wav, mp3, aiff, flac, ogg).",
    )
    parser.add_argument(
        "--question",
        default=None,
        metavar="TEXT",
        help=(
            "Custom question or prompt. Defaults to full structured analysis "
            "(key, BPM, textures, energy, IRON STATIC fit, suggestions)."
        ),
    )
    parser.add_argument(
        "--output",
        choices=["text", "json"],
        default="text",
        help="Output format: 'text' (human readable) or 'json' (machine readable). Default: text.",
    )
    parser.add_argument(
        "--model",
        default="gemini-2.0-flash",
        metavar="MODEL",
        help="Gemini model to use. Default: gemini-2.0-flash.",
    )
    parser.add_argument(
        "--no-song-context",
        action="store_true",
        help="Skip loading active song context from database/songs.json.",
    )
    args = parser.parse_args()

    if not args.file.exists():
        log.error("File not found: %s", args.file)
        sys.exit(1)

    supported = {".wav", ".mp3", ".aiff", ".aif", ".flac", ".ogg", ".m4a"}
    if args.file.suffix.lower() not in supported:
        log.warning(
            "Extension '%s' may not be supported by Gemini. Proceeding anyway.",
            args.file.suffix,
        )

    active_song = None if args.no_song_context else load_active_song()
    if active_song:
        log.info(
            "Active song: %s (key=%s, scale=%s, bpm=%s)",
            active_song.get("slug"),
            active_song.get("key"),
            active_song.get("scale"),
            active_song.get("bpm"),
        )
    else:
        log.info("No active song context (running context-free analysis).")

    question = args.question or DEFAULT_QUESTION
    prompt = build_prompt(question, active_song)

    analysis = analyze(args.file, prompt, args.model)

    if args.output == "json":
        print(format_json_output(analysis, args.file, active_song))
    else:
        print(analysis)


if __name__ == "__main__":
    main()
