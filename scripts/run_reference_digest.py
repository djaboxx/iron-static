#!/usr/bin/env python3
"""
run_reference_digest.py — Weekly reference track digest generator for IRON STATIC.

Calls Gemini (gemini-2.5-pro) to curate 5 reference tracks with production analysis,
written to:
    knowledge/references/YYYY-MM-DD.md

Usage:
    python scripts/run_reference_digest.py
    python scripts/run_reference_digest.py --no-llm
    python scripts/run_reference_digest.py --date 2026-05-01
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
MIXING_NOTES = REPO_ROOT / "knowledge" / "production" / "mixing-notes.md"
OUT_DIR = REPO_ROOT / "knowledge" / "references"

DIGEST_PROMPT_TEMPLATE = """\
You are IRON STATIC's Copilot generating the weekly reference digest.
IRON STATIC is an electronic metal duo making heavy, weird, intentional music.

Core influences for calibration:
- Nine Inch Nails — industrial texture, abrasive electronics, programmed drums + live rage
- Lamb of God — groove-metal weight and precision, locked rhythm section, guitar chug
- One Day as a Lion (Zack de la Rocha + Jon Theodore) — two-member urgency, political voice, minimal but explosive
- Modeselector — Berlin electronic bass pressure, grid-locked rhythm, dub influence
- Run The Jewels — punchy, fast, political, two voices in counterpoint
- Dr. Teeth and the Electric Mayhem — chaotic, chromatic, joyful weirdness, anything goes

The rig (for instrument parallel suggestions):
- Digitakt MK1: drum machine + sampler
- Sequential Rev2: polyphonic analog (pads, chords, modulated leads)
- Sequential Take 5: compact poly (punchy chords, tight leads)
- Moog Subharmonicon: polyrhythmic drone, sub bass, evolving pitch sequences
- Moog DFAM: analog percussion (kick, clap, tom, noise hits)
- Arturia Minibrute 2S: mono bass, acid lines, noise textures
- Arturia Pigments: software poly (evolving pads, wavetable leads, sample layers)

{manifesto_block}
{mixing_block}
{song_block}
Generate a weekly reference digest with exactly 5 tracks. Each track should come from a
different angle: rhythm/groove, bass/low end, texture/noise, synth design, and arrangement.
Do NOT repeat artists across the five entries.

Choose tracks that are SPECIFIC and REAL — artist name, track title, album, year.
Do not invent tracks. If uncertain of a track title, use the album name.

For each track use exactly this format:

---

### [N]. Artist — "Track Title" (*Album*, Year)

**Why it's relevant:**
2–3 sentences connecting this track to IRON STATIC's sound, an active song direction (if any),
or a specific technique Dave should study right now. Be direct. Name what's happening sonically.

**Production element to steal:**
One specific, concrete technique Dave can reverse-engineer. Include signal chain hints if possible.
Example: "The kick has no sustain but massive low-end transient — it's likely heavily compressed
with a very fast attack+release, high-passed above 30Hz. Study the ratio and the room it sits in."

**Instrument parallel:**
Which IRON STATIC instrument(s) could achieve a similar sound, and how.
Name the instrument and give at least one concrete control/parameter hint.

---

After all 5 tracks, add a brief section:

## This Week's Focus
One sentence: the single most important production lesson to take from this week's digest.
"""


def get_active_song() -> dict | None:
    if not SONGS_DB.exists():
        return None
    data = json.loads(SONGS_DB.read_text())
    for song in data.get("songs", []):
        if song.get("status") == "active":
            return song
    return None


def build_song_block(song: dict | None) -> str:
    if not song:
        return "Active song: none — curate broadly across the IRON STATIC aesthetic.\n\n"
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


def build_mixing_block() -> str:
    if MIXING_NOTES.exists():
        text = MIXING_NOTES.read_text()
        # Don't send the whole file if it's huge — cap at 3000 chars
        if len(text) > 3000:
            text = text[:3000] + "\n[…truncated]"
        return f"[Current Mixing Notes]\n{text}\n\n"
    return ""


def generate_no_llm(today: str) -> str:
    return f"""\
# IRON STATIC — Reference Digest ({today})

> **[no-llm stub]** LLM generation was skipped. Run without `--no-llm` to generate real content.

---

### 1. *Artist* — "Track" (*Album*, Year)
*(stub)*

### 2. *Artist* — "Track" (*Album*, Year)
*(stub)*

### 3. *Artist* — "Track" (*Album*, Year)
*(stub)*

### 4. *Artist* — "Track" (*Album*, Year)
*(stub)*

### 5. *Artist* — "Track" (*Album*, Year)
*(stub)*

## This Week's Focus
*(stub)*
"""


def generate_digest(today: str, song: dict | None) -> str:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from llm_utils import complete  # noqa: PLC0415

    prompt = DIGEST_PROMPT_TEMPLATE.format(
        manifesto_block=build_manifesto_block(),
        mixing_block=build_mixing_block(),
        song_block=build_song_block(song),
    )

    log.info("Calling Gemini for reference digest (model_tier=pro)…")
    content = complete(prompt, model_tier="pro")

    if song:
        ctx = f"*Song context: {song.get('title', song['slug'])} — {song.get('key', '?')} {song.get('scale', '?')} @ {song.get('bpm', '?')} BPM*\n\n"
    else:
        ctx = "*No active song — general IRON STATIC aesthetic focus*\n\n"

    return f"# IRON STATIC — Reference Digest ({today})\n\n{ctx}{content.strip()}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly IRON STATIC reference digest")
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

    if args.no_llm:
        content = generate_no_llm(today)
    else:
        content = generate_digest(today, song)

    out_path.write_text(content)
    log.info("Wrote %s", out_path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
