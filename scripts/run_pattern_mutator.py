#!/usr/bin/env python3
"""
run_pattern_mutator.py — MIDI pattern mutation engine for IRON STATIC.

Scans midi/patterns/ for source .mid files, applies algorithmic mutations
(inversion, retrograde, rhythmic displacement, euclidean reshaping, velocity
humanization), calls Gemini for a creative mutation brief, and writes:

  midi/patterns/<source-slug>_mut_<variant>_<date>.mid  — mutated MIDI files
  knowledge/patterns/YYYY-MM-DD.md                      — session log with mutation notes

Only processes source files that end in a root name (not already _mut_ files).
Idempotent per date: skips if today's log already exists (use --force to overwrite).

Usage:
    python scripts/run_pattern_mutator.py
    python scripts/run_pattern_mutator.py --no-llm
    python scripts/run_pattern_mutator.py --date 2026-05-01
    python scripts/run_pattern_mutator.py --pattern kick_groove_v1.mid
    python scripts/run_pattern_mutator.py --force
"""
import argparse
import copy
import logging
import math
import random
import sys
from datetime import date
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
PATTERNS_DIR = REPO_ROOT / "midi" / "patterns"
OUT_DIR = REPO_ROOT / "knowledge" / "patterns"

MUTATION_PROMPT_TEMPLATE = """\
You are IRON STATIC's Copilot writing mutation notes for a MIDI pattern.
IRON STATIC aesthetic: heavy, weird, electronic, intentional. Favor odd meters,
polyrhythm, dissonance with purpose, and noise as an instrument.

Source pattern: {filename}
{analysis_block}

Three mutations were generated algorithmically:
1. **Retrograde** — the note sequence played backwards
2. **Displaced** — all note onsets shifted by +{displacement} steps ({displacement_pct:.0f}% of pattern length)
3. **Euclidean** — hit count redistributed using a Euclidean algorithm (E({hits},{steps}))

Write a brief creative brief (under 200 words total) covering:

### Mutation Context
One sentence on what the source pattern is doing rhythmically/melodically.

### Which Mutation to Use
Recommend one of the three mutations for the current IRON STATIC session. Name it.
Explain in 2 sentences why it works — rhythmically, harmonically, or texturally.

### How to Combine It
One concrete suggestion: which other instrument should run simultaneously,
and what MIDI channel / Digitakt track / parameter to pay attention to.
"""


# ---------------------------------------------------------------------------
# MIDI parsing helpers (mido-based)
# ---------------------------------------------------------------------------

def _require_mido():
    try:
        import mido
        return mido
    except ImportError:
        log.error("mido is required. Run: pip install mido")
        sys.exit(1)


def parse_pattern(mid_path: Path) -> dict:
    """Extract a flat list of note events from a MIDI file.

    Returns dict with: tempo_bpm, ticks_per_beat, steps_estimated, notes[].
    Each note: {tick, pitch, velocity, duration_ticks, channel}.
    """
    mido = _require_mido()
    mid = mido.MidiFile(str(mid_path))
    tpb = mid.ticks_per_beat

    tempo = 500000  # default 120 BPM
    notes_on: dict[tuple, dict] = {}
    events: list[dict] = []
    abs_tick = 0

    for track in mid.tracks:
        abs_tick = 0
        for msg in track:
            abs_tick += msg.time
            if msg.type == "set_tempo":
                tempo = msg.tempo
            elif msg.type == "note_on" and msg.velocity > 0:
                key = (msg.channel, msg.note)
                notes_on[key] = {"tick": abs_tick, "velocity": msg.velocity, "channel": msg.channel}
            elif msg.type in ("note_off",) or (msg.type == "note_on" and msg.velocity == 0):
                key = (msg.channel, msg.note)
                if key in notes_on:
                    on = notes_on.pop(key)
                    events.append({
                        "tick": on["tick"],
                        "pitch": msg.note,
                        "velocity": on["velocity"],
                        "duration_ticks": max(1, abs_tick - on["tick"]),
                        "channel": on["channel"],
                    })

    bpm = round(60_000_000 / tempo, 1)
    # Estimate steps: total length in 16th notes
    if events:
        last_tick = max(e["tick"] + e["duration_ticks"] for e in events)
        step_ticks = tpb // 4  # 16th note
        steps = max(16, round(last_tick / step_ticks))
    else:
        steps = 16

    return {
        "tempo_bpm": bpm,
        "ticks_per_beat": tpb,
        "steps_estimated": steps,
        "notes": sorted(events, key=lambda e: e["tick"]),
    }


def events_to_midi(events: list[dict], out_path: Path, tpb: int, bpm: float) -> None:
    """Write a list of note events to a MIDI file."""
    mido = _require_mido()
    tempo = int(60_000_000 / bpm)
    mid = mido.MidiFile(ticks_per_beat=tpb)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))

    # Flatten to (tick, type, channel, note, velocity)
    raw: list[tuple] = []
    for e in events:
        raw.append((e["tick"], "note_on", e["channel"], e["pitch"], e["velocity"]))
        raw.append((e["tick"] + e["duration_ticks"], "note_off", e["channel"], e["pitch"], 0))
    raw.sort(key=lambda x: x[0])

    last_tick = 0
    for tick, mtype, ch, note, vel in raw:
        delta = tick - last_tick
        if mtype == "note_on":
            track.append(mido.Message("note_on", channel=ch, note=note, velocity=vel, time=delta))
        else:
            track.append(mido.Message("note_off", channel=ch, note=note, velocity=vel, time=delta))
        last_tick = tick

    track.append(mido.MetaMessage("end_of_track", time=0))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(out_path))


# ---------------------------------------------------------------------------
# Mutation algorithms
# ---------------------------------------------------------------------------

def mutate_retrograde(notes: list[dict], total_ticks: int) -> list[dict]:
    """Reverse the note sequence in time."""
    result = []
    for n in notes:
        new_tick = total_ticks - n["tick"] - n["duration_ticks"]
        result.append({**n, "tick": max(0, new_tick)})
    return sorted(result, key=lambda e: e["tick"])


def mutate_displaced(notes: list[dict], total_ticks: int, shift_ticks: int) -> list[dict]:
    """Shift all note onsets forward by shift_ticks, wrapping around the pattern."""
    result = []
    for n in notes:
        new_tick = (n["tick"] + shift_ticks) % total_ticks
        result.append({**n, "tick": new_tick})
    return sorted(result, key=lambda e: e["tick"])


def mutate_euclidean(notes: list[dict], total_ticks: int, tpb: int) -> list[dict]:
    """Redistribute note onsets using a Euclidean pattern over the same number of steps."""
    step_ticks = tpb // 4  # 16th note
    steps = max(8, round(total_ticks / step_ticks))
    hits = max(1, len(notes))
    if hits > steps:
        hits = steps

    # Bjorklund's algorithm
    groups = [[1]] * hits + [[0]] * (steps - hits)
    while len(groups) > 1 and (len(groups) % hits) != 0:
        remainder = groups[len(groups) - (len(groups) % hits or hits):]
        groups = groups[:len(groups) - len(remainder)]
        groups = [a + b for a, b in zip(groups, remainder)] + groups[len(remainder):]
    flat: list[int] = []
    for g in groups:
        flat.extend(g)
    flat = flat[:steps]

    # New tick positions from Euclidean grid
    new_ticks = [i * step_ticks for i, v in enumerate(flat) if v]

    result = []
    for i, n in enumerate(notes):
        new_tick = new_ticks[i % len(new_ticks)]
        result.append({**n, "tick": new_tick})
    return sorted(result, key=lambda e: e["tick"])


def _total_ticks(notes: list[dict], tpb: int, steps: int) -> int:
    if notes:
        last = max(n["tick"] + n["duration_ticks"] for n in notes)
        step_ticks = tpb // 4
        # Round up to nearest bar (16 steps)
        bar_ticks = 16 * step_ticks
        return math.ceil(last / bar_ticks) * bar_ticks
    return steps * (tpb // 4)


# ---------------------------------------------------------------------------
# Analysis block for prompt
# ---------------------------------------------------------------------------

def format_analysis(parsed: dict) -> str:
    notes = parsed["notes"]
    lines = [
        f"- BPM: {parsed['tempo_bpm']}",
        f"- Estimated steps: {parsed['steps_estimated']}",
        f"- Note events: {len(notes)}",
    ]
    if notes:
        pitches = sorted(set(n["pitch"] for n in notes))
        pitch_names = ["C", "C#", "D", "D#", "E", "F",
                       "F#", "G", "G#", "A", "A#", "B"]
        named = [f"{pitch_names[p % 12]}{p // 12 - 1}" for p in pitches]
        lines.append(f"- Unique pitches: {', '.join(named)}")
        velocities = [n["velocity"] for n in notes]
        lines.append(f"- Velocity range: {min(velocities)}–{max(velocities)}")
        channels = sorted(set(n["channel"] for n in notes))
        lines.append(f"- MIDI channels: {channels}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# LLM brief
# ---------------------------------------------------------------------------

def generate_brief(filename: str, parsed: dict, shift_steps: int, no_llm: bool) -> str:
    steps = parsed["steps_estimated"]
    notes = parsed["notes"]
    pct = 100 * shift_steps / steps if steps else 25

    if no_llm:
        hits = max(1, len(notes))
        return (
            f"### Mutation Context\n*(stub — run without --no-llm for real notes)*\n\n"
            f"### Which Mutation to Use\n*(stub)*\n\n"
            f"### How to Combine It\n*(stub)*\n"
        )

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from llm_utils import complete  # noqa: PLC0415

    hits = max(1, len(notes))
    prompt = MUTATION_PROMPT_TEMPLATE.format(
        filename=filename,
        analysis_block=format_analysis(parsed),
        displacement=shift_steps,
        displacement_pct=pct,
        hits=hits,
        steps=steps,
    )
    log.info("Calling Gemini for mutation brief (model_tier=fast)…")
    return complete(prompt, model_tier="fast")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_pattern(mid_path: Path, today: str, no_llm: bool) -> dict:
    """Process a single source pattern. Returns result dict for the log."""
    log.info("Processing pattern: %s", mid_path.name)

    parsed = parse_pattern(mid_path)
    notes = parsed["notes"]
    tpb = parsed["ticks_per_beat"]
    bpm = parsed["tempo_bpm"]
    steps = parsed["steps_estimated"]
    total = _total_ticks(notes, tpb, steps)
    step_ticks = tpb // 4

    slug = mid_path.stem
    outputs: list[dict] = []

    # 1. Retrograde
    retro = mutate_retrograde(notes, total)
    retro_path = PATTERNS_DIR / f"{slug}_mut_retro_{today}.mid"
    events_to_midi(retro, retro_path, tpb, bpm)
    outputs.append({"name": "retrograde", "path": retro_path})
    log.info("  → wrote %s", retro_path.name)

    # 2. Displaced (shift by ~1/4 of pattern)
    shift_steps = max(1, steps // 4)
    shift_ticks = shift_steps * step_ticks
    displaced = mutate_displaced(notes, total, shift_ticks)
    displ_path = PATTERNS_DIR / f"{slug}_mut_displaced_{today}.mid"
    events_to_midi(displaced, displ_path, tpb, bpm)
    outputs.append({"name": "displaced", "path": displ_path})
    log.info("  → wrote %s", displ_path.name)

    # 3. Euclidean
    euclid = mutate_euclidean(notes, total, tpb)
    euclid_path = PATTERNS_DIR / f"{slug}_mut_euclidean_{today}.mid"
    events_to_midi(euclid, euclid_path, tpb, bpm)
    outputs.append({"name": "euclidean", "path": euclid_path})
    log.info("  → wrote %s", euclid_path.name)

    brief = generate_brief(mid_path.name, parsed, shift_steps, no_llm)

    return {
        "source": mid_path.name,
        "analysis": format_analysis(parsed),
        "outputs": outputs,
        "brief": brief,
    }


def build_doc(today: str, results: list[dict]) -> str:
    lines = [f"# IRON STATIC — Pattern Mutations ({today})", ""]
    lines.append(f"{len(results)} source pattern(s) processed.\n")

    for r in results:
        lines += [
            "---",
            "",
            f"## Source: `{r['source']}`",
            "",
            "**Analysis:**",
        ]
        for l in r["analysis"].splitlines():
            lines.append(f"  {l}")
        lines += [
            "",
            "**Mutations written:**",
        ]
        for o in r["outputs"]:
            rel = o["path"].relative_to(REPO_ROOT)
            lines.append(f"  - `{rel}` ({o['name']})")
        lines += ["", r["brief"].strip(), ""]

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Mutate MIDI patterns for IRON STATIC")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM call, write stubs")
    parser.add_argument("--date", default=None, help="Override date string (YYYY-MM-DD)")
    parser.add_argument("--pattern", default=None, metavar="FILENAME",
                        help="Process only this filename (relative to midi/patterns/)")
    parser.add_argument("--force", action="store_true", help="Overwrite existing log for today")
    args = parser.parse_args()

    today = args.date or date.today().isoformat()
    log_path = OUT_DIR / f"{today}.md"

    if log_path.exists() and not args.force:
        log.warning("Log already exists for %s — skipping (use --force to overwrite)", today)
        sys.exit(0)

    # Collect source patterns (skip already-mutated files)
    if args.pattern:
        candidates = [PATTERNS_DIR / args.pattern]
    else:
        candidates = [
            p for p in sorted(PATTERNS_DIR.glob("*.mid"))
            if "_mut_" not in p.stem
        ]

    if not candidates:
        log.info("No source patterns found in %s — nothing to do.", PATTERNS_DIR)
        sys.exit(0)

    # Check mido available before processing anything
    _require_mido()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for mid_path in candidates:
        if not mid_path.exists():
            log.warning("Pattern not found: %s", mid_path)
            continue
        try:
            result = process_pattern(mid_path, today, args.no_llm)
            results.append(result)
        except Exception as e:
            log.error("Failed to process %s: %s", mid_path.name, e)

    if not results:
        log.warning("No patterns were processed successfully.")
        sys.exit(0)

    log_path.write_text(build_doc(today, results))
    log.info("Wrote %s", log_path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
