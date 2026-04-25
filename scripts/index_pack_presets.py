#!/usr/bin/env python3
"""
index_pack_presets.py — Scan all installed Ableton packs and build a searchable
preset catalog at database/pack_presets.json.

Metadata extracted per preset:
  name         — UserName from the preset XML
  file         — absolute path to the .adg or .adv file
  file_type    — "adg" (Instrument/Effect Rack) or "adv" (device preset)
  pack         — pack display name (from LivePackName or folder)
  pack_id      — LivePackId (e.g. www.ableton.com/237)
  category     — folder path within pack (e.g. "Sounds > Synth Bass")
  devices      — list of Live device types found inside (Analog, Operator, etc.)
  description  — Annotation value (credits, macro hints, etc.)
  macros       — list of named macro knobs (when rack has labeled knobs)
  tags         — derived keyword tags for fast filtering (bass, pad, drum, etc.)

Usage:
  python scripts/index_pack_presets.py [--packs-dir PATH] [--out PATH]
  python scripts/index_pack_presets.py --query bass --tag industrial
  python scripts/index_pack_presets.py --list-packs
  python scripts/index_pack_presets.py --list-categories
"""
import argparse
import gzip
import json
import logging
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_PACKS_DIR = Path.home() / "Music" / "Ableton" / "Packs"
DEFAULT_OUT = Path(__file__).parent.parent / "database" / "pack_presets.json"

# ── Device type tag → friendly name ────────────────────────────────────────
DEVICE_MAP = {
    "OperatorDevice": "Operator",
    "AnalogDevice": "Analog",
    "CollisionDevice": "Collision",
    "DrumGroupDevice": "DrumRack",
    "InstrumentGroupDevice": "InstrumentRack",
    "SamplerDevice": "Sampler",
    "SimplerDevice": "Simpler",
    "MxDeviceInstrument": "MaxForLive",
    "PluginDevice": "Plugin",
    "PluginFourPresetDevice": "Plugin",
    "AudioEffectGroupDevice": "AudioEffectRack",
    "Compressor2": "Compressor",
}

# ── Tag inference rules (name/category/description keyword → tag) ───────────
# Each entry: (pattern, tag)  — pattern matched case-insensitively against
# the combined string: name + " " + category + " " + description
TAG_RULES = [
    # Function
    (r"\bbass\b",               "bass"),
    (r"\bsub\b",                "bass"),
    (r"\bhover|hoover\b",       "bass"),
    (r"\breese\b",              "bass"),
    (r"\bpad\b",                "pad"),
    (r"\bdrone\b",              "pad"),
    (r"\bambien",               "pad"),
    (r"\bevolv",                "pad"),
    (r"\blead\b",               "lead"),
    (r"\bstab\b",               "lead"),
    (r"\barp\b",                "arp"),
    (r"\bpluck\b",              "pluck"),
    (r"\bkeys?\b",              "keys"),
    (r"\bpiano\b",              "keys"),
    (r"\bchord\b",              "keys"),
    (r"\bstrin",                "strings"),
    (r"\borgan\b",              "organ"),
    (r"\bdrum\b",               "drum"),
    (r"\bkit\b",                "drum"),
    (r"\bkick\b",               "drum"),
    (r"\bsnare\b",              "drum"),
    (r"\bperc",                 "drum"),
    (r"\b808\b",                "808"),
    (r"\b909\b",                "909"),
    (r"\b707\b",                "707"),
    (r"\b606\b",                "606"),
    # Texture
    (r"\bnoise\b",              "noise"),
    (r"\bstatic\b",             "noise"),
    (r"\bfuzz\b",               "distortion"),
    (r"\bdirt\b",               "distortion"),
    (r"\bdriv",                 "distortion"),
    (r"\bdistort",              "distortion"),
    (r"\bcrunch\b",             "distortion"),
    (r"\bgrit\b",               "distortion"),
    (r"\bwobble\b",             "modulation"),
    (r"\bwobbl",                "modulation"),
    (r"\bmod(?:ulation)?\b",    "modulation"),
    (r"\bfilter\b",             "filter"),
    (r"\bwah\b",                "filter"),
    (r"\bverb\b",               "reverb"),
    (r"\breverb\b",             "reverb"),
    (r"\bdelay\b",              "delay"),
    (r"\becho\b",               "delay"),
    # Mood / IRON STATIC relevance
    (r"\bdark\b",               "dark"),
    (r"\bblack\b",              "dark"),
    (r"\bdeath\b",              "dark"),
    (r"\bshad",                 "dark"),
    (r"\bnight\b",              "dark"),
    (r"\bindustri",             "industrial"),
    (r"\bcorrod",               "industrial"),
    (r"\bmetal\b",              "metal"),
    (r"\bheavy\b",              "heavy"),
    (r"\baggressiv",            "heavy"),
    (r"\bviol",                 "heavy"),
    (r"\bsic\b",                "heavy"),
    (r"\bhard\b",               "heavy"),
    (r"\bpunch",                "heavy"),
    (r"\bwarm\b",               "warm"),
    (r"\bsoft\b",               "soft"),
    (r"\bspace\b",              "ambient"),
    (r"\batmosp",               "ambient"),
    (r"\bether",                "ambient"),
    (r"\bsky\b",                "ambient"),
    (r"\bcosmics?\b",           "ambient"),
    (r"\bghost\b",              "ambient"),
    (r"\bfm\b",                 "fm"),
    (r"\boperator\b",           "fm"),
    (r"\bsynthes",              "synth"),
    (r"\banalog\b",             "analog"),
    (r"\bvintage\b",            "analog"),
    (r"\bretro\b",              "analog"),
    (r"\bgranul",               "granular"),
    (r"\bsample\b",             "sampler"),
    (r"\bsimpler\b",            "sampler"),
]


def _derive_tags(name: str, category: str, description: str, devices: list) -> list:
    text = f"{name} {category} {description}".lower()
    tags = set()
    for pattern, tag in TAG_RULES:
        if re.search(pattern, text):
            tags.add(tag)
    # Also tag by device type
    for d in devices:
        if d in ("Operator", "Analog", "Sampler", "Simpler", "Collision", "MaxForLive"):
            tags.add(d.lower())
        if d == "DrumRack":
            tags.add("drum")
    return sorted(tags)


def _extract_metadata(path: Path) -> dict | None:
    """Parse a .adg or .adv file and return a metadata dict."""
    try:
        raw = gzip.open(path).read().decode("utf-8", errors="replace")
    except Exception:
        return None

    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return None

    # Name
    un = root.find(".//UserName")
    name = (un.get("Value", "") if un is not None else "").strip()
    if not name:
        name = path.stem

    # Description / annotation
    ann = root.find(".//Annotation")
    desc = (ann.get("Value", "") if ann is not None else "").strip()

    # Macro knob names (only the non-empty ones)
    macros = []
    for i in range(8):
        m = root.find(f".//MacroDisplayNames.{i}")
        if m is not None:
            v = m.find("./Manual")
            if v is not None:
                label = v.get("Value", "").strip()
                if label:
                    macros.append(label)

    # Device types present
    devices = []
    for tag, fname in DEVICE_MAP.items():
        if root.find(f".//{tag}") is not None and fname not in devices:
            devices.append(fname)

    # Pack metadata
    pack_id_el = root.find(".//LivePackId")
    pack_name_el = root.find(".//LivePackName")
    pack_id = pack_id_el.get("Value", "") if pack_id_el is not None else ""
    pack_name_xml = pack_name_el.get("Value", "") if pack_name_el is not None else ""

    # Category from folder path
    try:
        packs_idx = path.parts.index("Packs")
        pack_from_path = path.parts[packs_idx + 1]
        cat_parts = path.parts[packs_idx + 2 : -1]
        category = " > ".join(cat_parts) if cat_parts else ""
    except ValueError:
        pack_from_path = path.parent.name
        category = ""

    pack = pack_name_xml or pack_from_path

    tags = _derive_tags(name, category, desc, devices)

    return {
        "name": name,
        "file": str(path),
        "file_type": path.suffix.lstrip("."),
        "pack": pack,
        "pack_id": pack_id,
        "category": category,
        "devices": sorted(set(devices)),
        "description": desc,
        "macros": macros,
        "tags": tags,
    }


def build_index(packs_dir: Path, out_path: Path) -> list:
    """Scan all .adg/.adv files under packs_dir and write JSON catalog."""
    presets = []
    skipped = 0
    total = 0

    for ext in ("*.adg", "*.adv"):
        for f in sorted(packs_dir.rglob(ext)):
            total += 1
            meta = _extract_metadata(f)
            if meta:
                presets.append(meta)
            else:
                skipped += 1
                log.debug("Skipped: %s", f)

    presets.sort(key=lambda p: (p["pack"], p["category"], p["name"]))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump(presets, fh, indent=2)

    log.info("Indexed %d presets (%d skipped) → %s", len(presets), skipped, out_path)
    return presets


def cmd_build(args):
    presets = build_index(Path(args.packs_dir), Path(args.out))
    # Summary by pack
    by_pack: dict = {}
    for p in presets:
        by_pack.setdefault(p["pack"], 0)
        by_pack[p["pack"]] += 1
    print(f"\nIndexed {len(presets)} presets across {len(by_pack)} packs:\n")
    for pack, count in sorted(by_pack.items(), key=lambda x: -x[1]):
        print(f"  {count:4d}  {pack}")
    print(f"\nSaved → {args.out}")


def _load_index(path: Path) -> list:
    if not path.exists():
        raise FileNotFoundError(f"Index not found: {path} — run with no subcommand first")
    with open(path) as fh:
        return json.load(fh)


def cmd_query(args):
    presets = _load_index(Path(args.out))

    results = presets
    if args.query:
        q = args.query.lower()
        results = [p for p in results if q in p["name"].lower()
                   or q in p["description"].lower()
                   or q in p["category"].lower()
                   or q in p["pack"].lower()]
    if args.tag:
        for tag in args.tag:
            results = [p for p in results if tag.lower() in p["tags"]]
    if args.pack:
        pk = args.pack.lower()
        results = [p for p in results if pk in p["pack"].lower()]
    if args.device:
        dev = args.device.lower()
        results = [p for p in results if any(dev in d.lower() for d in p["devices"])]

    if not results:
        print("No results.")
        return

    for p in results:
        tags_str = ", ".join(p["tags"]) if p["tags"] else "-"
        macros_str = f"  macros: {', '.join(p['macros'])}" if p["macros"] else ""
        desc_str = f"  desc: {p['description'][:70]}" if p["description"] else ""
        print(f"\n{p['name']}")
        print(f"  {p['pack']}  |  {p['category']}  |  devices: {', '.join(p['devices'])}")
        print(f"  tags: {tags_str}")
        if macros_str:
            print(macros_str)
        if desc_str:
            print(desc_str)
        print(f"  file: {p['file']}")

    print(f"\n{len(results)} result(s)")


def cmd_list_packs(args):
    presets = _load_index(Path(args.out))
    by_pack: dict = {}
    for p in presets:
        by_pack.setdefault(p["pack"], {"count": 0, "categories": set()})
        by_pack[p["pack"]]["count"] += 1
        by_pack[p["pack"]]["categories"].add(p["category"])
    for pack, info in sorted(by_pack.items()):
        print(f"\n{pack} ({info['count']} presets)")
        for cat in sorted(info["categories"]):
            n = sum(1 for p in presets if p["pack"] == pack and p["category"] == cat)
            print(f"  {n:4d}  {cat}")


def cmd_list_categories(args):
    presets = _load_index(Path(args.out))
    cats: dict = {}
    for p in presets:
        key = f"{p['pack']} > {p['category']}"
        cats.setdefault(key, 0)
        cats[key] += 1
    for cat, count in sorted(cats.items()):
        print(f"{count:4d}  {cat}")


def cmd_list_tags(args):
    presets = _load_index(Path(args.out))
    tag_counts: dict = {}
    for p in presets:
        for t in p["tags"]:
            tag_counts[t] = tag_counts.get(t, 0) + 1
    for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
        print(f"{count:4d}  {tag}")


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Index and query Ableton pack presets"
    )
    parser.add_argument("--packs-dir", default=str(DEFAULT_PACKS_DIR),
                        help="Path to Ableton Packs folder")
    parser.add_argument("--out", default=str(DEFAULT_OUT),
                        help="Output JSON path (default: database/pack_presets.json)")

    sub = parser.add_subparsers(dest="cmd")

    # build (default)
    sub.add_parser("build", help="Scan packs and build index (default)")

    # query
    q = sub.add_parser("query", help="Search indexed presets")
    q.add_argument("query", nargs="?", default="", help="Text search (name/description/category)")
    q.add_argument("--tag", nargs="+", help="Filter by tag (e.g. --tag bass dark)")
    q.add_argument("--pack", help="Filter by pack name")
    q.add_argument("--device", help="Filter by device type (Analog, Operator, etc.)")

    sub.add_parser("list-packs", help="List packs and category counts")
    sub.add_parser("list-categories", help="List all categories with counts")
    sub.add_parser("list-tags", help="List all inferred tags with counts")

    args = parser.parse_args()

    dispatch = {
        None: cmd_build,
        "build": cmd_build,
        "query": cmd_query,
        "list-packs": cmd_list_packs,
        "list-categories": cmd_list_categories,
        "list-tags": cmd_list_tags,
    }
    dispatch[args.cmd](args)


if __name__ == "__main__":
    main()
