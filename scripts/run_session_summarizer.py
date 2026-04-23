#!/usr/bin/env python3
"""
run_session_summarizer.py — Ableton session summarizer for IRON STATIC.

Reads session state data from outputs/ (live_state.json, *_summary.json, *_clips.csv,
etc. produced by session-reporter.amxd or extract_midi_clips.py) and generates a
narrative session summary with next-step suggestions via Gemini.

Writes to: knowledge/sessions/YYYY-MM-DD.md

Usage:
    python scripts/run_session_summarizer.py
    python scripts/run_session_summarizer.py --no-llm
    python scripts/run_session_summarizer.py --date 2026-05-01
    python scripts/run_session_summarizer.py --force    # overwrite if exists
"""
import argparse
import csv
import json
import logging
import sys
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUTS_DIR = REPO_ROOT / "outputs"
SONGS_DB = REPO_ROOT / "database" / "songs.json"
OUT_DIR = REPO_ROOT / "knowledge" / "sessions"

# Files to skip when scanning outputs/ — these are not session state files
_OUTPUTS_SKIP = {"repo_health.json", "repo_health_issues.md", "audio_intake_manifest.json"}

SESSION_PROMPT_TEMPLATE = """\
You are IRON STATIC's Copilot summarizing an Ableton Live session.
IRON STATIC is an electronic metal duo. The rig:
- Elektron Digitakt MK1: drum machine, sampler, MIDI hub (MIDI ch 1–8)
- Sequential Rev2: 16-voice poly analog (MIDI ch 2/3)
- Sequential Take 5: 5-voice poly analog (MIDI ch 4)
- Moog Subharmonicon: polyrhythmic drone, semi-modular (MIDI ch 5)
- Moog DFAM: analog percussion (MIDI ch 6)
- Arturia Minibrute 2S: mono bass/leads (MIDI ch 7)
- Arturia Pigments: software poly (MIDI ch 8)

Below is the session data extracted from this Ableton Live session:

{session_block}

Generate a session summary with exactly these four sections:

## Session Overview
2–3 sentences. What is in this session? What tempo and scale/key is it in?
How many tracks, how many clips? Is it early-stage, mid-development, or dense/finished?

## What's Built
A concise inventory of what exists in the session:
- List the tracks/instruments with what clips or patterns they contain
- Note any MIDI clips: how many steps, what instrument they're routing to
- Flag any tracks that look empty or placeholder-only
- If a clip inventory CSV is available, reference specific clip names

## What's Missing / Underdeveloped
Based on the IRON STATIC rig and the active song context, what is conspicuously absent?
Think: is there a bass line? A lead? A drum pattern? Are there arrangement sections (intro/drop/outro)?
List 3–5 specific gaps with brief reasoning.

## Suggested Next Steps
3–5 concrete, actionable next steps in priority order.
Each suggestion should name the specific instrument to use and describe exactly what to do.
Example: "1. Program a Digitakt kick pattern at 138 BPM — 4-on-the-floor with step 9 ghost hit.
Trigger Rev2 chord stabs on Digitakt MIDI track 2, channel 2, E Phrygian voicings."
Be opinionated. Challenge Dave. Push the sound forward.
"""


def get_active_song() -> dict | None:
    if not SONGS_DB.exists():
        return None
    data = json.loads(SONGS_DB.read_text())
    return next((s for s in data.get("songs", []) if s.get("status") == "active"), None)


def find_session_data() -> dict:
    """Collect all available session state files from outputs/."""
    data: dict = {}

    # Primary: live_state.json from session-reporter.amxd
    live_state_path = OUTPUTS_DIR / "live_state.json"
    if live_state_path.exists():
        try:
            data["live_state"] = json.loads(live_state_path.read_text())
            log.info("Loaded live_state.json")
        except json.JSONDecodeError as e:
            log.warning("Failed to parse live_state.json: %s", e)

    # Secondary: any *_summary.json files (from extract_midi_clips.py / parse-als skill)
    for p in sorted(OUTPUTS_DIR.glob("*_summary.json")):
        if p.name in _OUTPUTS_SKIP:
            continue
        try:
            data.setdefault("summaries", {})[p.stem] = json.loads(p.read_text())
            log.info("Loaded session summary: %s", p.name)
        except json.JSONDecodeError as e:
            log.warning("Skipping %s (parse error): %s", p.name, e)

    # Clip inventory CSVs (from session-reporter or extract_midi_clips)
    for p in sorted(OUTPUTS_DIR.glob("*_clips.csv")):
        try:
            with open(p, newline="") as f:
                rows = list(csv.DictReader(f))
            data.setdefault("clips", {})[p.stem] = rows
            log.info("Loaded clip CSV: %s (%d rows)", p.name, len(rows))
        except Exception as e:
            log.warning("Skipping %s: %s", p.name, e)

    # Devices JSON (from extract_midi_clips or parse-als)
    for p in sorted(OUTPUTS_DIR.glob("*_devices.json")):
        if p.name in _OUTPUTS_SKIP:
            continue
        try:
            data.setdefault("devices", {})[p.stem] = json.loads(p.read_text())
            log.info("Loaded devices JSON: %s", p.name)
        except json.JSONDecodeError:
            pass

    return data


def format_session_block(session_data: dict, song: dict | None) -> str:
    """Format all session data into a single text block for the prompt."""
    parts: list[str] = []

    if "live_state" in session_data:
        blob = json.dumps(session_data["live_state"], indent=2)
        parts.append(f"[Ableton Live State (live_state.json)]\n{blob}")

    if "summaries" in session_data:
        for name, summary in session_data["summaries"].items():
            blob = json.dumps(summary, indent=2)
            parts.append(f"[Session Summary: {name}]\n{blob}")

    if "clips" in session_data:
        for name, rows in session_data["clips"].items():
            if rows:
                header = ", ".join(rows[0].keys())
                lines = [header] + [", ".join(str(v) for v in r.values()) for r in rows]
                parts.append(f"[Clip Inventory: {name}]\n" + "\n".join(lines))
            else:
                parts.append(f"[Clip Inventory: {name}]\n(empty — no clips found)")

    if "devices" in session_data:
        for name, devices in session_data["devices"].items():
            blob = json.dumps(devices, indent=2)[:2000]  # cap size
            parts.append(f"[Track Devices: {name}]\n{blob}")

    if song:
        song_lines = [
            f"[Active Song]",
            f"Title: {song.get('title', song['slug'])}",
            f"Key: {song.get('key', '?')} {song.get('scale', '?')}",
            f"BPM: {song.get('bpm', '?')}",
        ]
        if song.get("notes"):
            song_lines.append(f"Notes: {song['notes']}")
        parts.append("\n".join(song_lines))

    if not parts:
        return (
            "No session data found in outputs/. "
            "Run session-reporter.amxd in Ableton to generate live_state.json, "
            "or run extract_midi_clips.py on an .als file."
        )

    return "\n\n".join(parts)


def generate_no_llm(today: str, session_data: dict, song: dict | None) -> str:
    has_live = "live_state" in session_data
    has_summaries = bool(session_data.get("summaries"))
    has_clips = bool(session_data.get("clips"))
    n_clips = sum(len(rows) for rows in session_data.get("clips", {}).values())

    song_ctx = (
        f"{song.get('title', song['slug'])} — {song.get('key', '?')} {song.get('scale', '?')} @ {song.get('bpm', '?')} BPM"
        if song
        else "no active song"
    )

    return f"""\
# IRON STATIC — Session Summary ({today})

> **[no-llm stub]** LLM generation was skipped. Run without `--no-llm` for real analysis.

**Data available:**
- live_state.json: {"yes" if has_live else "no"}
- session summary JSONs: {"yes" if has_summaries else "no"}
- clip CSVs: {"yes" if has_clips else "no"} ({n_clips} rows)
- Active song: {song_ctx}

## Session Overview
*(stub)*

## What's Built
*(stub)*

## What's Missing / Underdeveloped
*(stub)*

## Suggested Next Steps
*(stub)*
"""


def generate_summary(today: str, session_data: dict, song: dict | None) -> str:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from llm_utils import complete  # noqa: PLC0415

    session_block = format_session_block(session_data, song)
    prompt = SESSION_PROMPT_TEMPLATE.format(session_block=session_block)

    log.info("Calling Gemini for session summary (model_tier=fast)…")
    content = complete(prompt, model_tier="fast")

    if song:
        ctx = f"*{song.get('title', song['slug'])} — {song.get('key', '?')} {song.get('scale', '?')} @ {song.get('bpm', '?')} BPM*\n\n"
    else:
        ctx = "*No active song*\n\n"

    return f"# IRON STATIC — Session Summary ({today})\n\n{ctx}{content.strip()}\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize an IRON STATIC Ableton session")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM call, write stub")
    parser.add_argument("--date", default=None, help="Override date string (YYYY-MM-DD)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output")
    args = parser.parse_args()

    today = args.date or date.today().isoformat()
    out_path = OUT_DIR / f"{today}.md"

    if out_path.exists() and not args.force:
        log.warning("Output already exists for %s — skipping (use --force to overwrite): %s", today, out_path)
        sys.exit(0)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    session_data = find_session_data()
    song = get_active_song()

    if not session_data and not song:
        log.warning("No session data found in outputs/ and no active song — writing minimal stub")

    if args.no_llm:
        content = generate_no_llm(today, session_data, song)
    else:
        content = generate_summary(today, session_data, song)

    out_path.write_text(content)
    log.info("Wrote %s", out_path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
