#!/usr/bin/env python3
"""
run_preset_ideas.py — Instrument preset idea generator for IRON STATIC.

Reads the active song context, rig configuration, and existing preset catalog,
then calls Gemini (gemini-2.5-pro) to generate detailed sound design blueprints
for each instrument in the rig. Each blueprint includes synthesis approach,
specific parameter starting points, and IRON STATIC aesthetic notes.

Writes to: knowledge/sound-design/YYYY-MM-DD.md

Does NOT write actual preset JSON files — use the create-preset skill for that.

Usage:
    python scripts/run_preset_ideas.py
    python scripts/run_preset_ideas.py --no-llm
    python scripts/run_preset_ideas.py --date 2026-05-01
    python scripts/run_preset_ideas.py --instrument rev2  # single instrument focus
    python scripts/run_preset_ideas.py --force
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
INSTRUMENTS_DB = REPO_ROOT / "database" / "instruments.json"
MIDI_PARAMS_DIR = REPO_ROOT / "database" / "midi_params"
OUT_DIR = REPO_ROOT / "knowledge" / "sound-design"

# Instruments that use panel-state docs (no memory) vs MIDI-param presets
PANEL_STATE_INSTRUMENTS = {"subharmonicon", "dfam", "minibrute2s"}

# Instruments to generate ideas for (in order)
DEFAULT_INSTRUMENTS = [
    "digitakt",
    "rev2",
    "take5",
    "subharmonicon",
    "dfam",
    "minibrute2s",
    "pigments",
]

PRESET_IDEAS_PROMPT = """\
You are IRON STATIC's Copilot generating weekly sound design blueprints.
IRON STATIC aesthetic: heavy, weird, electronic, intentional.
Influences: Nine Inch Nails (industrial texture), Lamb of God (groove-metal weight),
Modeselector (Berlin electronic pressure), Run The Jewels (punchy urgency).

Active song context:
{song_block}

Existing preset catalog for this instrument (for reference — don't repeat, build on gaps):
{catalog_block}

MIDI parameter map (available controls):
{midi_params_block}

Instrument: **{instrument_name}** ({instrument_type})
Filter: {filter_type}
Role: {role}
MIDI channel: {midi_channel}
{patch_format_note}

Generate exactly **2 preset ideas** for this instrument. Each idea should be genuinely
distinct from what's in the existing catalog.

Use this format for each:

### Preset [N]: [Name] — [5-word mood]

**Concept:** 2 sentences. What does this sound do? What IRON STATIC context does it fill?

**Synthesis Approach:**
- Engine / oscillator setup (waveforms, tuning, unison if applicable)
- Filter starting point (cutoff, resonance, mode)
- Envelope character (ADSR ballpark — e.g. "instant attack, 80ms decay, dead sustain")
- Modulation (LFO target, depth, rate; or envelope routing)
- Effects (reverb/delay/distortion — brief)

**Parameter Starting Points:**
List 5–8 specific parameter values the user should dial in first. Use parameter names
from the MIDI map when available. For panel-state instruments (Subharmonicon, DFAM,
Minibrute 2S), use knob/section names from the instrument manual.

**IRON STATIC Usage:**
- When to reach for this sound (arrangement context)
- Digitakt integration hint (MIDI track, channel, key CCs to automate)
- One thing that makes it heavy or weird

---
"""

SINGLE_INSTRUMENT_PROMPT = """\
You are IRON STATIC's Copilot generating focused sound design ideas.
Active song: {song_block}

{instrument_block}

{prompt_body}
"""


def get_active_song() -> dict | None:
    if not SONGS_DB.exists():
        return None
    data = json.loads(SONGS_DB.read_text())
    return next((s for s in data.get("songs", []) if s.get("status") == "active"), None)


def build_song_block(song: dict | None) -> str:
    if not song:
        return "No active song — generate broadly across the IRON STATIC aesthetic.\n"
    lines = [
        f"Title: {song.get('title', song['slug'])}",
        f"Key: {song.get('key', '?')} {song.get('scale', '?')}",
        f"BPM: {song.get('bpm', '?')}",
    ]
    if song.get("notes"):
        lines.append(f"Notes: {song['notes']}")
    return "\n".join(lines)


def get_instrument_info(slug: str) -> dict | None:
    if not INSTRUMENTS_DB.exists():
        return None
    data = json.loads(INSTRUMENTS_DB.read_text())
    for inst in data.get("instruments", []):
        if inst["slug"] == slug:
            return inst
    return None


def get_preset_catalog(slug: str) -> str:
    presets_dir = REPO_ROOT / "instruments"
    # Find the folder matching this slug
    for folder in presets_dir.iterdir():
        if not folder.is_dir():
            continue
        # Match by slug fragment
        if slug in folder.name or folder.name.endswith(slug):
            catalog_path = folder / "presets" / "catalog.json"
            if catalog_path.exists():
                try:
                    data = json.loads(catalog_path.read_text())
                    # Summarize: just names + descriptions
                    if isinstance(data, list):
                        items = data
                    elif isinstance(data, dict):
                        items = data.get("presets", [data])
                    else:
                        return "(catalog format unrecognized)"
                    lines = []
                    for item in items[:10]:  # cap at 10
                        name = item.get("name", "?")
                        desc = item.get("description", "")[:120]
                        lines.append(f"- {name}: {desc}")
                    return "\n".join(lines) if lines else "(empty catalog)"
                except (json.JSONDecodeError, Exception):
                    return "(catalog parse error)"
            # If no catalog.json, list .json preset files
            preset_files = [p.stem for p in (folder / "presets").glob("*.json")
                           if p.stem != "catalog"]
            if preset_files:
                return "Preset files: " + ", ".join(preset_files)
    return "(no catalog found)"


def get_midi_params_summary(slug: str) -> str:
    params_path = MIDI_PARAMS_DIR / f"{slug}.json"
    if not params_path.exists():
        return "(no MIDI param map)"
    try:
        data = json.loads(params_path.read_text())
        params = data.get("params", {})
        lines = []
        for section, contents in list(params.items())[:6]:  # cap sections
            if isinstance(contents, dict):
                param_names = list(contents.keys())[:8]
                lines.append(f"  [{section}]: {', '.join(param_names)}")
        if data.get("iron_static_usage"):
            usage = data["iron_static_usage"]
            lines.append(f"  Role: {usage.get('primary_role', '')}")
            for k, v in usage.items():
                if k.startswith("key_ccs"):
                    lines.append(f"  Key CCs: {v}")
        return "\n".join(lines) if lines else "(param map present but empty)"
    except (json.JSONDecodeError, Exception):
        return "(param map parse error)"


def get_midi_channel_str(inst: dict) -> str:
    ch = inst.get("midi_channels", {})
    if not ch:
        return "unassigned"
    parts = [f"{k}={v}" for k, v in ch.items()]
    return ", ".join(parts)


def generate_ideas_for_instrument(slug: str, song: dict | None, no_llm: bool) -> str:
    inst = get_instrument_info(slug)
    if not inst:
        # Fallback for instruments not in DB (e.g. pigments)
        inst = {
            "slug": slug,
            "name": slug.title(),
            "type": "unknown",
            "role": "IRON STATIC instrument",
            "filter": "unknown",
            "midi_channels": {},
        }

    name = inst.get("name", slug)
    itype = inst.get("type", "unknown")
    role = inst.get("role", "")
    filt = inst.get("filter", "—")
    midi_ch = get_midi_channel_str(inst)
    patch_note = (
        "**Note: panel-state instrument (no patch memory) — document as knob positions.**"
        if slug in PANEL_STATE_INSTRUMENTS else ""
    )

    catalog = get_preset_catalog(slug)
    midi_params = get_midi_params_summary(slug)
    song_block = build_song_block(song)

    if no_llm:
        return (
            f"### Preset 1: [Name] — *stub*\n\n"
            f"*(stub — run without --no-llm)*\n\n"
            f"---\n\n"
            f"### Preset 2: [Name] — *stub*\n\n"
            f"*(stub)*\n"
        )

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from llm_utils import complete  # noqa: PLC0415

    prompt = PRESET_IDEAS_PROMPT.format(
        song_block=song_block,
        catalog_block=catalog,
        midi_params_block=midi_params,
        instrument_name=name,
        instrument_type=itype,
        filter_type=filt,
        role=role,
        midi_channel=midi_ch,
        patch_format_note=patch_note,
    )

    log.info("Calling Gemini for %s preset ideas (model_tier=pro)…", slug)
    return complete(prompt, model_tier="pro")


def build_doc(today: str, song: dict | None, sections: list[tuple[str, str]]) -> str:
    lines = [f"# IRON STATIC — Sound Design Ideas ({today})", ""]

    if song:
        lines.append(
            f"*Context: {song.get('title', song['slug'])} — "
            f"{song.get('key', '?')} {song.get('scale', '?')} @ {song.get('bpm', '?')} BPM*\n"
        )
    else:
        lines.append("*No active song — ideas are aesthetic-general.*\n")

    for slug, content in sections:
        inst = get_instrument_info(slug)
        label = inst.get("name", slug) if inst else slug
        lines += [
            "---",
            "",
            f"## {label}",
            "",
            content.strip(),
            "",
        ]

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate IRON STATIC preset ideas via Gemini")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM call, write stubs")
    parser.add_argument("--date", default=None, help="Override date string (YYYY-MM-DD)")
    parser.add_argument("--instrument", default=None,
                        help="Slug of single instrument to generate ideas for")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output for today")
    args = parser.parse_args()

    today = args.date or date.today().isoformat()
    out_path = OUT_DIR / f"{today}.md"

    if out_path.exists() and not args.force:
        log.warning("Output already exists for %s — skipping (use --force): %s", today, out_path)
        sys.exit(0)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    song = get_active_song()
    if not song:
        log.warning("No active song — ideas will be aesthetic-general")

    slugs = [args.instrument] if args.instrument else DEFAULT_INSTRUMENTS

    sections = []
    for slug in slugs:
        try:
            content = generate_ideas_for_instrument(slug, song, args.no_llm)
            sections.append((slug, content))
        except Exception as e:
            log.error("Failed to generate ideas for %s: %s", slug, e)
            sections.append((slug, f"*(error: {e})*"))

    out_path.write_text(build_doc(today, song, sections))
    log.info("Wrote %s", out_path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
