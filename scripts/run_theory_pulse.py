#!/usr/bin/env python3
"""
run_theory_pulse.py — Weekly music theory pulse generator for IRON STATIC.

Reads the active song's key, scale, and BPM from database/songs.json and
generates a focused, hardware-actionable theory document, written to:
    knowledge/music-theory/pulse/YYYY-MM-DD.md

Usage:
    python scripts/run_theory_pulse.py
    python scripts/run_theory_pulse.py --no-llm
    python scripts/run_theory_pulse.py --date 2026-05-01
"""
import argparse
import json
import logging
import math
import sys
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
SONGS_DB = REPO_ROOT / "database" / "songs.json"
SCALES_REF = REPO_ROOT / "knowledge" / "music-theory" / "scales-and-modes.md"
OUT_DIR = REPO_ROOT / "knowledge" / "music-theory" / "pulse"

THEORY_PROMPT_TEMPLATE = """\
You are IRON STATIC's Copilot generating the weekly music theory pulse.
This is a focused, practical theory document — not music school theory, but
hardware-actionable knowledge for an electronic metal duo using:
- Elektron Digitakt MK1 (drum machine + MIDI sequencer, 16-step patterns)
- Sequential Rev2 (16-voice polyphonic analog, Curtis filter)
- Sequential Take 5 (5-voice polyphonic analog)
- Moog Subharmonicon (2 VCOs + 4 subharmonic oscillators, 4 independent sequencers)
- Moog DFAM (8-step analog percussion sequencer)
- Arturia Minibrute 2S (mono synth + 2×8 step sequencer, Steiner-Parker filter)
- Arturia Pigments (software poly, Wavetable + Analog + Sample engines)

{scales_block}

Active song context:
{song_block}

Generate a weekly theory pulse document with exactly these six sections.
Be specific. Name notes. Give exact millisecond values. Reference instrument names.

## 1. Scale Map
The complete note set for {key} {scale} across the whole rig.
List all 7 notes (or 8 with octave) by name. Then show:
- Which notes form the strongest bass foundation (Digitakt bass track, Minibrute 2S)
- Which notes are safe melody notes on the Subharmonicon's sequencer
- The tension note(s) that create maximum dissonance against the root
- Recommended lowest MIDI note (octave placement) for each instrument

## 2. Tension & Resolution Moves
Three specific harmonic tension/resolution techniques for {key} {scale}:
For each: name the move, describe which instruments play what, and give exact MIDI notes.
Example format: "The ♭II lift: Rev2 plays F major voicing [F2 A2 C3] over E bass on Minibrute 2S; tension resolves by dropping back to E minor tonic."

## 3. Rhythm Grid
At {bpm} BPM, the complete timing grid:
- Quarter note: X ms
- 8th note: X ms
- 16th note: X ms
- 32nd note: X ms
- Dotted 8th: X ms (common for syncopation)
- Triplet 8th: X ms
- Digitakt steps per beat (16-step = 4 steps per quarter note at 4/4)
- Which Digitakt step length values (1/8, 1/16, etc.) align to this BPM

## 4. Chord Vocabulary
5 chords that work in {key} {scale} with voicing suggestions.
For each chord: name, notes, Rev2 voicing (MIDI note numbers), Take 5 voicing, and function
(tonic, subdominant, dominant, color, etc.).
Include at least one cluster voicing and one power-chord-equivalent for maximum weight.

## 5. Modulation Targets
Two keys/modes to pivot to for contrast sections:
For each: the target key/mode, the pivot note they share with {key} {scale},
how to execute the modulation smoothly (which instrument leads, what the transition sounds like),
and what emotional shift this creates.

## 6. LFO Sync Reference
At {bpm} BPM, LFO rates in Hz for key sync divisions:
- 1 bar (4/4): X Hz
- Half note: X Hz
- Quarter note: X Hz
- 8th note: X Hz
- Dotted quarter: X Hz
- Triplet quarter: X Hz
Formatted as a lookup table. Note which values map well to Digitakt LFO multiplier settings
and Minibrute 2S LFO Rate knob positions (low/mid/high range guidance).
"""


def get_active_song() -> dict | None:
    if not SONGS_DB.exists():
        return None
    data = json.loads(SONGS_DB.read_text())
    for song in data.get("songs", []):
        if song.get("status") == "active":
            return song
    return None


def compute_timing_grid(bpm: float) -> dict:
    """Pre-compute timing values so we can also include them in the stub."""
    beat_ms = 60000.0 / bpm
    return {
        "quarter_ms": beat_ms,
        "eighth_ms": beat_ms / 2,
        "sixteenth_ms": beat_ms / 4,
        "thirtysecond_ms": beat_ms / 8,
        "dotted_eighth_ms": beat_ms * 0.75,
        "triplet_eighth_ms": beat_ms / 3,
        "bar_hz": 1 / (beat_ms * 4 / 1000),
        "half_hz": 1 / (beat_ms * 2 / 1000),
        "quarter_hz": 1 / (beat_ms / 1000),
        "eighth_hz": 1 / (beat_ms / 2 / 1000),
    }


def build_scales_block() -> str:
    if SCALES_REF.exists():
        return f"[Scale Reference]\n{SCALES_REF.read_text()}\n\n"
    return ""


def generate_no_llm(today: str, song: dict | None, grid: dict) -> str:
    if song:
        ctx = f"{song.get('key', '?')} {song.get('scale', '?')} @ {song.get('bpm', '?')} BPM"
    else:
        ctx = "no active song"
    lines = [
        f"# IRON STATIC — Theory Pulse ({today})",
        "",
        f"> **[no-llm stub]** Context: {ctx}. Run without `--no-llm` for real content.",
        "",
    ]
    if song and song.get("bpm"):
        lines += [
            "## Pre-computed Timing Grid",
            f"- Quarter note: {grid['quarter_ms']:.1f} ms",
            f"- 8th note: {grid['eighth_ms']:.1f} ms",
            f"- 16th note: {grid['sixteenth_ms']:.1f} ms",
            f"- 32nd note: {grid['thirtysecond_ms']:.1f} ms",
            f"- Dotted 8th: {grid['dotted_eighth_ms']:.1f} ms",
            f"- Triplet 8th: {grid['triplet_eighth_ms']:.1f} ms",
            "",
        ]
    lines += [
        "## 1. Scale Map",
        "*(stub)*",
        "",
        "## 2. Tension & Resolution Moves",
        "*(stub)*",
        "",
        "## 3. Rhythm Grid",
        "*(stub — see timing grid above)*",
        "",
        "## 4. Chord Vocabulary",
        "*(stub)*",
        "",
        "## 5. Modulation Targets",
        "*(stub)*",
        "",
        "## 6. LFO Sync Reference",
        "*(stub)*",
    ]
    return "\n".join(lines) + "\n"


def generate_theory_pulse(today: str, song: dict | None) -> str:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from llm_utils import complete  # noqa: PLC0415

    key = song.get("key", "E") if song else "E"
    scale = song.get("scale", "minor") if song else "minor"
    bpm = song.get("bpm", 120) if song else 120

    song_block = (
        f"Title: {song.get('title', song['slug'])}\n"
        f"Key: {key}\nScale: {scale}\nBPM: {bpm}\n"
        f"Time signature: {song.get('time_signature', '4/4')}\n"
        if song
        else "No active song — use E minor @ 140 BPM as a working context.\n"
    )

    prompt = THEORY_PROMPT_TEMPLATE.format(
        scales_block=build_scales_block(),
        song_block=song_block,
        key=key,
        scale=scale,
        bpm=bpm,
    )

    log.info("Calling Gemini for theory pulse (model_tier=fast)…")
    content = complete(prompt, model_tier="fast")

    ctx_line = (
        f"*{key} {scale} @ {bpm} BPM*\n\n"
        if song
        else "*No active song — theoretical context only*\n\n"
    )
    return f"# IRON STATIC — Theory Pulse ({today})\n\n{ctx_line}{content.strip()}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly IRON STATIC theory pulse")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM call, write stub")
    parser.add_argument("--date", default=None, help="Override date string (YYYY-MM-DD)")
    args = parser.parse_args()

    today = args.date or date.today().isoformat()
    out_path = OUT_DIR / f"{today}.md"

    if out_path.exists():
        log.warning("Output already exists for %s — skipping: %s", today, out_path)
        sys.exit(0)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    song = get_active_song()
    if not song:
        log.warning("No active song in songs.json — theory pulse will use generic context")

    if args.no_llm:
        bpm = float(song["bpm"]) if song and song.get("bpm") else 120.0
        grid = compute_timing_grid(bpm)
        content = generate_no_llm(today, song, grid)
    else:
        content = generate_theory_pulse(today, song)

    out_path.write_text(content)
    log.info("Wrote %s", out_path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
