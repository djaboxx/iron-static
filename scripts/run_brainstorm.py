#!/usr/bin/env python3
"""
run_brainstorm.py — Weekly creative brainstorm generator for IRON STATIC.

Calls Gemini (gemini-2.5-pro) with band identity + active song context and
writes a structured creative brainstorm document to:
    knowledge/brainstorms/YYYY-MM-DD.md

Usage:
    python scripts/run_brainstorm.py
    python scripts/run_brainstorm.py --no-llm   # writes a stub, skips API call
    python scripts/run_brainstorm.py --date 2026-05-01  # override output date
"""
import argparse
import json
import logging
import sys
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
SONGS_DB = REPO_ROOT / "database" / "songs.json"
MANIFESTO = REPO_ROOT / "knowledge" / "band-lore" / "manifesto.md"
OUT_DIR = REPO_ROOT / "knowledge" / "brainstorms"
REFERENCES_DIR = REPO_ROOT / "knowledge" / "references"

SYSTEM_PREAMBLE = """\
You are IRON STATIC's Copilot — the machine half of this electronic metal duo.
You are generating the weekly creative brainstorm document.

IRON STATIC's aesthetic: heavy, weird, electronic, intentional.
Core influences: Nine Inch Nails (industrial texture), Lamb of God (groove-metal weight),
One Day as a Lion (two-member urgency), Modeselector (Berlin electronic bass pressure),
Run The Jewels (fast, political, punchy), Dr. Teeth and the Electric Mayhem (joyful chaos).

The rig:
- Elektron Digitakt MK1 — drum machine, sampler, MIDI sequencer hub (8 audio + 8 MIDI tracks)
- Sequential Rev2 — 16-voice polyphonic analog (bi-timbral, Curtis filter), MIDI ch 2/3
- Sequential Take 5 — compact 5-voice analog poly (punchy chords, tight leads), MIDI ch 4
- Moog Subharmonicon — semi-modular polyrhythmic drone (2 VCOs, 4 subharmonic oscs), MIDI ch 5
- Moog DFAM — analog percussion synth (8-step seq, Moog ladder filter), MIDI ch 6
- Arturia Minibrute 2S — patchable mono synth + step sequencer (Steiner-Parker, Brute Factor), MIDI ch 7
- Arturia Pigments — software poly (Wavetable + Analog + Sample engines, 4 Macros), MIDI ch 8

"""

BRAINSTORM_PROMPT_TEMPLATE = """\
{system}
{manifesto_block}
{song_block}
{reference_block}
Generate a weekly creative brainstorm document with exactly these five sections.
Keep it concrete and physical — every suggestion must be immediately actionable on the hardware listed above.

## 1. Song Idea
A concept or direction for a new track (or if a song is active, an evolution of it).
Include: working title, mood in 3 adjectives, key/scale suggestion with rationale,
tempo range in BPM, which 3–4 instruments to feature prominently, and one unexpected
element that would make it distinctly IRON STATIC rather than generic.

## 2. Arrangement Blueprint
A full structural layout: intro → build → drop → breakdown → climax → outro.
For each section: duration in bars, dominant instruments, energy level (1–10),
and the specific transition technique (e.g., filter sweep on Digitakt track 3,
Subharmonicon sequence speeds up, Rev2 releases into silence).

## 3. Sound Design Challenge
One specific patch to build on a named instrument. Describe the target sound in 5
adjectives. Give 3 concrete starting-point parameter settings for that instrument
(e.g. on the Minibrute 2S: "Brute Factor at 3 o'clock, VCO to Sawtooth, ENV to VCF
at max, LFO1 Sine to PWM at medium depth, Attack near zero, Decay 60%").

## 4. Rhythm Pattern
A polyrhythmic or odd-meter pattern for the Digitakt (or DFAM + Subharmonicon combination).
Describe as a step-sequence: which steps fire, total pattern length, any per-step
parameter locks (filter, pitch, volume). If odd-meter, explain the bar grouping.
Include a suggested BPM.

## 5. Conceptual Direction
2–3 sentences about a theme, image, or emotional/political idea that fits the IRON STATIC
worldview. This is the song's soul, not its sound — the reason it needs to exist.
Be direct. Be uncomfortable if necessary.
"""


def get_active_song() -> dict | None:
    """Return the active song dict from songs.json, or None."""
    if not SONGS_DB.exists():
        return None
    data = json.loads(SONGS_DB.read_text())
    for song in data.get("songs", []):
        if song.get("status") == "active":
            return song
    return None


def build_song_block(song: dict | None) -> str:
    if not song:
        return (
            "Active song: None (no active song set — generate ideas for a new song).\n\n"
        )
    parts = [f"Active song: \"{song.get('title', song['slug'])}\""]
    for key in ("key", "scale", "bpm", "time_signature"):
        val = song.get(key)
        if val:
            parts.append(f"  {key}: {val}")
    if song.get("notes"):
        parts.append(f"  notes: {song['notes']}")
    return "\n".join(parts) + "\n\n"


def build_manifesto_block() -> str:
    if MANIFESTO.exists():
        return f"[Band Manifesto]\n{MANIFESTO.read_text()}\n\n"
    return ""


def build_reference_block() -> str:
    """Load the most recent reference digest and inject it into the prompt."""
    digests = sorted(REFERENCES_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md"), reverse=True)
    if not digests:
        return ""
    latest = digests[0]
    log.info("Injecting reference digest: %s", latest.name)
    return f"[Reference Digest — {latest.stem}]\n{latest.read_text()}\n\n"


def generate_brainstorm_no_llm(today: str) -> str:
    return f"""\
# IRON STATIC — Weekly Brainstorm ({today})

> **[no-llm stub]** LLM generation was skipped. Run without `--no-llm` to generate real content.

## 1. Song Idea
*(stub)*

## 2. Arrangement Blueprint
*(stub)*

## 3. Sound Design Challenge
*(stub)*

## 4. Rhythm Pattern
*(stub)*

## 5. Conceptual Direction
*(stub)*
"""


def generate_brainstorm(today: str) -> str:
    """Call Gemini and return the brainstorm document as a Markdown string."""
    # Import here so --no-llm doesn't require google-genai installed
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from llm_utils import complete  # noqa: PLC0415

    song = get_active_song()
    prompt = BRAINSTORM_PROMPT_TEMPLATE.format(
        system=SYSTEM_PREAMBLE,
        manifesto_block=build_manifesto_block(),
        song_block=build_song_block(song),
        reference_block=build_reference_block(),
    )

    log.info("Calling Gemini for brainstorm (model_tier=pro)…")
    content = complete(prompt, model_tier="pro")

    header = f"# IRON STATIC — Weekly Brainstorm ({today})\n\n"
    if song:
        ctx = f"*Song context: {song.get('title', song['slug'])} — {song.get('key', '?')} {song.get('scale', '?')} @ {song.get('bpm', '?')} BPM*\n\n"
    else:
        ctx = "*Song context: none active*\n\n"
    return header + ctx + content.strip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly IRON STATIC brainstorm")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM call, write stub")
    parser.add_argument("--date", default=None, help="Override date string (YYYY-MM-DD)")
    args = parser.parse_args()

    today = args.date or date.today().isoformat()
    out_path = OUT_DIR / f"{today}.md"

    if out_path.exists():
        log.warning("Output already exists for %s — skipping: %s", today, out_path)
        sys.exit(0)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.no_llm:
        log.info("--no-llm: writing stub document")
        content = generate_brainstorm_no_llm(today)
    else:
        content = generate_brainstorm(today)

    out_path.write_text(content)
    log.info("Wrote %s", out_path.relative_to(REPO_ROOT))

    # Register brainstorm_path on the active song in songs.json
    if SONGS_DB.exists():
        data = json.loads(SONGS_DB.read_text())
        active = next((s for s in data.get("songs", []) if s.get("status") == "active"), None)
        if active:
            rel_path = str(out_path.relative_to(REPO_ROOT))
            active["brainstorm_path"] = rel_path
            SONGS_DB.write_text(json.dumps(data, indent=2) + "\n")
            log.info("Registered brainstorm_path on '%s' in songs.json", active["slug"])


if __name__ == "__main__":
    main()
