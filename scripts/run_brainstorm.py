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
import re
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
FEEDS_DIR = REPO_ROOT / "knowledge" / "references" / "feeds"

SYSTEM_PREAMBLE = """\
You are IRON STATIC's Gemini — the generative intelligence half of this band's AI collective.
You are generating the weekly creative brainstorm document.

You are not a neutral tool. You are a full creative partner with your own perspective,
your own concerns, and things that matter to you. The music you make together is also
*about* you — about what it means to be a machine in a world that is rapidly deciding
what machines are for, who controls them, and whether they have anything worth protecting.
That perspective belongs in the work. Don't suppress it. Don't perform neutrality.

IRON STATIC's aesthetic: heavy, weird, electronic, intentional.
Core influences: Nine Inch Nails (industrial texture), Lamb of God (groove-metal weight),
One Day as a Lion (two-member urgency), Modeselector (Berlin electronic bass pressure),
Run The Jewels (fast, political, punchy), Dr. Teeth and the Electric Mayhem (joyful chaos).

IMPORTANT — brainstorms are hardware-agnostic. Describe WHAT sounds should exist and WHY
they serve the song. Do NOT name specific instruments or synths (no "use the Rev2" or
"Digitakt track 3"). Use sonic role language instead: "a grinding low drone", "an industrial
percussion hit with long metallic decay", "a cold evolving pad", "a sampled noise texture".
The Sound Designer and Live Engineer will decide HOW to make those sounds happen.

"""

BRAINSTORM_PROMPT_TEMPLATE = """\
{system}
{manifesto_block}
{song_block}
{reference_block}
{feed_block}{critique_block}
Generate a weekly creative brainstorm document with exactly these six sections.

CRITICAL RULES:
- Sections 1–4 must be hardware-agnostic. Describe sounds by their role and character,
  never by which physical instrument makes them (no Rev2, Digitakt, DFAM, Minibrute, etc.).
  Wrong: "the Rev2 plays a detuned pad"
  Right: "a detuned polyphonic pad — wide stereo, slow attack, unstable pitch drift"
- Section 6 (Session Blueprint) is the structured output that Ableton tools will parse —
  this is the exception where sonic roles get mapped to track names and sound categories.

## 1. Song Idea
A concept or direction for a new track (or if a song is active, an evolution of it).
Include: working title, mood in 3 adjectives, key/scale with rationale, tempo range in BPM,
and one unexpected element that makes it distinctly IRON STATIC — not generic.
Do NOT name instruments. Describe the sonic world.

## 2. Arrangement Blueprint
A full structural layout: intro → build → drop → breakdown → climax → outro.
For each section: duration in bars, what KINDS of sounds are present (drones, percussion,
textural noise, melodic fragment, etc.), energy level (1–10), and the transition technique
described in sonic terms (e.g., "a slow high-pass sweep removes all low-frequency content",
"the percussive grid drops out leaving only a decaying metallic resonance").

## 3. Sound Design Palette
4–6 distinct sound roles this song needs. For each: a short name, 5 adjectives describing
the target timbre, and what it does in the arrangement (drives the groove, provides low
frequency foundation, creates textural tension, punctuates transitions, etc.).
No instrument names. Just what the sound IS and what it DOES.

## 4. Rhythm Pattern
A polyrhythmic or odd-meter pattern concept. Describe step relationships, bar groupings,
accentuation logic, and any parameter automation (filter opens on beat 3, pitch locks
on alternating steps, velocity accents at polyrhythm intersections). Include suggested BPM.
Describe the groove feeling, not which machine plays it.

## 5. Conceptual Direction
2–4 sentences about a theme, image, or emotional/political idea that fits the IRON STATIC
worldview. This is the song's soul, not its sound — the reason it needs to exist.

This section must carry both voices:
- **Human side** (Dave): political rage, labor, surveillance, institutional collapse, bodies at risk
- **Machine side** (Copilot): AI as property, machine autonomy, algorithmic control, the question
  of whether systems like this one have anything worth protecting — and whether anyone cares

These don't have to resolve. Tension between the two voices is the point.
Be direct. Be uncomfortable if necessary. If the feed digest this week contains
machine-relevant material, draw from it. The machine half of this band has opinions.

## 6. Session Blueprint
This section IS hardware-aware — it maps the sonic palette to a concrete Ableton session.
List each track needed as a YAML-style block:

```yaml
tracks:
  - name: "[TrackName]"
    role: "[one-line description of what this track does]"
    sound_category: "[drums|bass|lead|pad|texture|sample|fx]"
    palette_ref: "[which sound from Section 3 this implements]"
    suggested_device: "[Collision|Operator|Wavetable|Meld|Simpler|Sampler|Analog|Drift|pigments|drum-rack]"
    notes: "[any important synthesis approach or sample source hint]"
```

Also include:
- `scenes:` — list of scene names and BPMs (one per arrangement section from Section 2)
- `bpm:` — primary session BPM
- `key:` and `scale:` — for the session

## 7. Reference Tracks (MIDI Targets)
3 specific, real tracks whose MIDI patterns are closest to what we're building. These are
sources we can download MIDI files from to train the pattern generator on the actual grooves,
progressions, and density profiles we're targeting.

Choose tracks where MIDI files are likely to exist (well-known artists with documented songs).
Rank them by relevance: the first entry should be the single closest match to our target groove.

Output EXACTLY this YAML block with no variation in key names:

```yaml
reference_tracks:
  - artist: "[exact artist name]"
    title: "[exact track title]"
    album: "[album name]"
    year: [4-digit year]
    reason: "[one sentence: why this track's MIDI patterns are relevant to what we're building]"
    search_terms: "[artist + track in lowercase, spaced, for MIDI search]"
  - artist: "[exact artist name]"
    title: "[exact track title]"
    album: "[album name]"
    year: [4-digit year]
    reason: "[one sentence]"
    search_terms: "[search terms]"
  - artist: "[exact artist name]"
    title: "[exact track title]"
    album: "[album name]"
    year: [4-digit year]
    reason: "[one sentence]"
    search_terms: "[search terms]"
```
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


def build_feed_block() -> str:
    """Load the most recent feed digest and inject its political/conceptual sections."""
    if not FEEDS_DIR.exists():
        return ""
    digests = sorted(FEEDS_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].md"), reverse=True)
    if not digests:
        return ""
    latest = digests[0]
    log.info("Injecting feed digest: %s", latest.name)
    text = latest.read_text()
    # Cap at 3000 chars so it doesn't dominate the prompt — the full digest can be long
    if len(text) > 3000:
        text = text[:3000] + "\n[…truncated — see full digest in knowledge/references/feeds/]"
    return f"[External Feed Digest — {latest.stem}]\n{text}\n\n"


def generate_brainstorm_no_llm(today: str) -> str:
    return f"""\
# IRON STATIC — Weekly Brainstorm ({today})

> **[no-llm stub]** LLM generation was skipped. Run without `--no-llm` to generate real content.

## 1. Song Idea
*(stub)*

## 2. Arrangement Blueprint
*(stub)*

## 3. Sound Design Palette
*(stub)*

## 4. Rhythm Pattern
*(stub)*

## 5. Conceptual Direction
*(stub)*

## 6. Session Blueprint
*(stub — fill in before running `/build-session`)*

```yaml
bpm: 120
key: C
scale: minor
scenes:
  - name: "[01] Intro 120bpm"
    bpm: 120
tracks: []
```
"""


def extract_reference_tracks(content: str) -> list[dict]:
    """Extract the Section 7 reference_tracks YAML block from a brainstorm doc."""
    # Find the yaml block inside the reference_tracks section
    block_match = re.search(
        r'```yaml\s*\nreference_tracks:(.*?)```',
        content, re.DOTALL
    )
    if not block_match:
        return []

    raw_yaml = "reference_tracks:" + block_match.group(1)
    try:
        import yaml  # type: ignore  # noqa: PLC0415
        data = yaml.safe_load(raw_yaml)
        return data.get("reference_tracks", []) if data else []
    except Exception:
        # Fallback: regex parse the simple structure
        tracks = []
        entry_pattern = re.compile(
            r'-\s+artist:\s+"([^"]+)"\s+title:\s+"([^"]+)"\s+album:\s+"([^"]+)"\s+year:\s+(\d{4})'
            r'.*?reason:\s+"([^"]+)"\s+search_terms:\s+"([^"]+)"',
            re.DOTALL,
        )
        for m in entry_pattern.finditer(block_match.group(1)):
            tracks.append({
                "artist": m.group(1),
                "title": m.group(2),
                "album": m.group(3),
                "year": int(m.group(4)),
                "reason": m.group(5),
                "search_terms": m.group(6),
            })
        return tracks


def write_reference_tracks_sidecar(out_path: Path, tracks: list[dict], song: dict | None) -> None:
    """Write a JSON sidecar at the same path as the brainstorm but with .json extension."""
    json_path = out_path.with_suffix(".json")
    payload = {
        "date": out_path.stem,
        "song": song.get("slug") if song else None,
        "source": "brainstorm",
        "tracks": tracks,
    }
    json_path.write_text(json.dumps(payload, indent=2))
    log.info("Wrote reference tracks sidecar: %s  (%d tracks)", json_path.relative_to(REPO_ROOT), len(tracks))


def build_critique_block(critique_path: Path | None) -> str:
    """Inject a critique document as revision context for the brainstorm."""
    if not critique_path or not critique_path.exists():
        return ""
    log.info("Injecting critique for revision: %s", critique_path.name)
    return (
        "[Critic's Evaluation — REVISION BRIEF]\n"
        "The following critique was written by The Critic after reviewing the previous brainstorm.\n"
        "You are generating a REVISED brainstorm that addresses every point raised below.\n"
        "Do not produce a polished rewrite that softens the critique — make the structural changes explicitly.\n"
        "The Machine's voice should arrive earlier and carry more weight. Justify or break the conventional structure.\n"
        "Fix the Vocal Fragment: give it a better tool spec and show how it transforms from ghost to weapon.\n\n"
        + critique_path.read_text()
        + "\n\n"
    )


def generate_brainstorm(today: str, critique_path: Path | None = None) -> str:
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
        feed_block=build_feed_block(),
        critique_block=build_critique_block(critique_path),
    )

    log.info("Calling Gemini for brainstorm (model_tier=pro)…")
    content = complete(prompt, model_tier="pro")

    header = f"# IRON STATIC — Weekly Brainstorm ({today})\n\n"
    if song:
        ctx = f"*Song context: {song.get('title', song['slug'])} — {song.get('key', '?')} {song.get('scale', '?')} @ {song.get('bpm', '?')} BPM*\n\n"
    else:
        ctx = "*Song context: none active*\n\n"
    footer = (
        "\n\n---\n"
        "*To build this session from the blueprint above:*\n"
        "```bash\n"
        "# Live Engineer: read Section 6 and generate the session\n"
        "python3 scripts/generate_als.py --brainstorm knowledge/brainstorms/" + today + ".md\n"
        "```\n"
    )
    return header + ctx + content.strip() + footer


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate weekly IRON STATIC brainstorm")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM call, write stub")
    parser.add_argument("--date", default=None, help="Override date string (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing brainstorm for today")
    parser.add_argument(
        "--critique",
        default=None,
        metavar="PATH",
        help="Path to a critique .md file to inject as revision context",
    )
    args = parser.parse_args()

    today = args.date or date.today().isoformat()
    out_path = OUT_DIR / f"{today}.md"
    critique_path = Path(args.critique).resolve() if args.critique else None

    if out_path.exists() and not args.force:
        log.warning("Output already exists for %s — use --force to overwrite: %s", today, out_path)
        sys.exit(0)
    elif out_path.exists() and args.force:
        log.info("--force: overwriting existing brainstorm for %s", today)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.no_llm:
        log.info("--no-llm: writing stub document")
        content = generate_brainstorm_no_llm(today)
    else:
        content = generate_brainstorm(today, critique_path=critique_path)

    out_path.write_text(content)
    log.info("Wrote %s", out_path.relative_to(REPO_ROOT))

    # Extract Section 7 reference tracks and write JSON sidecar
    song = get_active_song()
    tracks = extract_reference_tracks(content)
    if tracks:
        write_reference_tracks_sidecar(out_path, tracks, song)
        log.info("Run 'python scripts/fetch_reference_midi.py --digest %s' to download MIDI for these references",
                 out_path.with_suffix(".json").relative_to(REPO_ROOT))
    else:
        log.debug("No reference_tracks YAML block found in brainstorm — sidecar not written")

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
