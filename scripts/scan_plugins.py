#!/usr/bin/env python3
"""
scan_plugins.py — Scan installed VST2, VST3, CLAP, and AU plugins on macOS.

Writes a structured JSON catalogue to database/plugins.json (or --output path).
Used by the ableton-push skill to populate return FX and channel FX chains.

Usage:
    python scripts/scan_plugins.py
    python scripts/scan_plugins.py --output database/plugins.json
    python scripts/scan_plugins.py --format table       # human-readable table
    python scripts/scan_plugins.py --filter instruments  # only instruments
    python scripts/scan_plugins.py --filter effects      # only effects
"""

import argparse
import json
import logging
import os
import plistlib
import sys
from pathlib import Path
from typing import Optional

log = logging.getLogger("scan_plugins")

# ---------------------------------------------------------------------------
# Standard macOS plugin search paths
# ---------------------------------------------------------------------------

SCAN_PATHS: dict[str, list[Path]] = {
    "VST3": [
        Path("/Library/Audio/Plug-Ins/VST3"),
        Path("~/Library/Audio/Plug-Ins/VST3").expanduser(),
    ],
    "VST2": [
        Path("/Library/Audio/Plug-Ins/VST"),
        Path("~/Library/Audio/Plug-Ins/VST").expanduser(),
    ],
    "CLAP": [
        Path("/Library/Audio/Plug-Ins/CLAP"),
        Path("~/Library/Audio/Plug-Ins/CLAP").expanduser(),
    ],
    "AU": [
        Path("/Library/Audio/Plug-Ins/Components"),
        Path("~/Library/Audio/Plug-Ins/Components").expanduser(),
    ],
}

# VST3 subcategory strings that indicate an instrument plugin
VST3_INSTRUMENT_CATEGORIES = {
    "instrument", "synth", "sampler", "drum", "generator",
}

# Known instruments by display name (substring match, lowercase)
KNOWN_INSTRUMENTS = {
    "kontakt", "reaktor", "komplete kontrol", "pigments", "analog lab",
    "labs", "serum", "massive", "fm8", "absynth", "zebra", "diva",
    "sylenth", "spire", "vstation", "arp 2600", "cs-80", "jup-8", "dx7",
    "prophet", "mini v", "modular v", "solina", "stage-73", "piano v",
    "b-3 v", "vocoder v", "cmi v", "cz v", "synclavier", "synthi v",
    "farfisa", "mellotron", "jun-6", "op-xa", "sem v", "buchla",
    "emulator ii", "wurli", "clavinet", "augmented", "arcade",
    "digitakt", "analog four", "analog rytm",
    "minitaur editor", "tr-808",
    "reason rack plugin",
    "dexed", "tal-noisemaker",
    "mariana", "endlesss",
    "uaudio_minimoog", "bbc symphony", "europa",
}

# Known effects by display name (substring match, lowercase)
# Listed for documentation — anything NOT an instrument defaults to effect
KNOWN_EFFECTS = {
    "fabfilter", "fabfilter pro-q", "fabfilter pro-mb", "fabfilter saturn",
    "soundtoys", "echoboy", "decapitator", "crystallizer", "little alter boy",
    "eventide", "blackhole", "mangledverb", "ultratap", "microshift",
    "waves", "waveshell",
    "meldaproduction",
    "acon digital",
    "universal audio", "uaudio",
    "supercharger", "rc-20", "serato sample",
    "rift feedback",
    "suhr pt100",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def read_vst3_plist(bundle: Path) -> Optional[dict]:
    """Read Contents/Info.plist from a .vst3 bundle. Return None on failure."""
    plist_path = bundle / "Contents" / "Info.plist"
    if not plist_path.exists():
        return None
    try:
        with plist_path.open("rb") as f:
            return plistlib.load(f)
    except Exception:
        return None


def classify_vst3(bundle: Path, plist: Optional[dict]) -> str:
    """Return 'instrument' or 'effect' for a VST3 plugin."""
    if plist:
        subcats = plist.get("VST3SubCategories", "")
        if isinstance(subcats, str):
            subcats_lower = subcats.lower()
            for cat in VST3_INSTRUMENT_CATEGORIES:
                if cat in subcats_lower:
                    return "instrument"
    name_lower = bundle.stem.lower()
    for kw in KNOWN_INSTRUMENTS:
        if kw in name_lower:
            return "instrument"
    return "effect"


def classify_generic(name: str) -> str:
    """Classify a plugin by name when no metadata is available."""
    name_lower = name.lower()
    for kw in KNOWN_INSTRUMENTS:
        if kw in name_lower:
            return "instrument"
    return "effect"


def vendor_from_path(plugin_path: Path, base_path: Path) -> Optional[str]:
    """
    If the plugin lives in a vendor subdirectory (e.g. /VST3/Soundtoys/EchoBoy.vst3),
    return that subdirectory name as the vendor.
    """
    try:
        rel = plugin_path.parent.relative_to(base_path)
        parts = rel.parts
        if parts:
            return parts[0]
    except ValueError:
        pass
    return None


def format_display_name(stem: str) -> str:
    """Strip common suffix noise from bundle stem names."""
    return stem.replace("-VI", "").replace(" (Mono)", "").strip()


# ---------------------------------------------------------------------------
# Scanners
# ---------------------------------------------------------------------------

def scan_vst3(base_dirs: list[Path]) -> list[dict]:
    plugins = []
    for base in base_dirs:
        if not base.exists():
            continue
        # Scan top-level and one level of vendor subdirs
        for entry in sorted(base.rglob("*.vst3")):
            if not entry.is_dir():
                continue
            plist = read_vst3_plist(entry)
            vendor = vendor_from_path(entry, base)

            # Prefer CFBundleName from plist, fall back to stem
            name = format_display_name(entry.stem)
            if plist:
                name = plist.get("CFBundleName", name)

            plugin_type = classify_vst3(entry, plist)

            plugins.append({
                "name": name,
                "format": "VST3",
                "type": plugin_type,
                "vendor": vendor,
                "path": str(entry),
            })
    return plugins


def scan_vst2(base_dirs: list[Path]) -> list[dict]:
    plugins = []
    for base in base_dirs:
        if not base.exists():
            continue
        for entry in sorted(base.rglob("*.vst")):
            if not entry.is_dir():
                continue
            vendor = vendor_from_path(entry, base)
            name = format_display_name(entry.stem)
            plugin_type = classify_generic(name)
            plugins.append({
                "name": name,
                "format": "VST2",
                "type": plugin_type,
                "vendor": vendor,
                "path": str(entry),
            })
    return plugins


def scan_clap(base_dirs: list[Path]) -> list[dict]:
    plugins = []
    for base in base_dirs:
        if not base.exists():
            continue
        for entry in sorted(base.rglob("*.clap")):
            vendor = vendor_from_path(entry, base)
            name = format_display_name(entry.stem)
            plugin_type = classify_generic(name)
            plugins.append({
                "name": name,
                "format": "CLAP",
                "type": plugin_type,
                "vendor": vendor,
                "path": str(entry),
            })
    return plugins


def scan_au(base_dirs: list[Path]) -> list[dict]:
    plugins = []
    for base in base_dirs:
        if not base.exists():
            continue
        for entry in sorted(base.rglob("*.component")):
            if not entry.is_dir():
                continue
            plist_path = entry / "Contents" / "Info.plist"
            name = format_display_name(entry.stem)
            vendor = vendor_from_path(entry, base)
            plugin_type = classify_generic(name)
            if plist_path.exists():
                try:
                    with plist_path.open("rb") as f:
                        pdata = plistlib.load(f)
                    name = pdata.get("CFBundleName", name)
                except Exception:
                    pass
            plugins.append({
                "name": name,
                "format": "AU",
                "type": plugin_type,
                "vendor": vendor,
                "path": str(entry),
            })
    return plugins


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def deduplicate(plugins: list[dict]) -> list[dict]:
    """
    When a plugin exists in both VST3 and VST2, prefer VST3.
    When it exists in VST3 and CLAP, prefer VST3 (but keep CLAP as alternate).
    Keyed on lowercased name.
    """
    FORMAT_PRIORITY = {"VST3": 0, "CLAP": 1, "VST2": 2, "AU": 3}
    seen: dict[str, dict] = {}
    for p in plugins:
        key = p["name"].lower()
        if key not in seen:
            seen[key] = p
        else:
            existing_prio = FORMAT_PRIORITY.get(seen[key]["format"], 99)
            new_prio = FORMAT_PRIORITY.get(p["format"], 99)
            if new_prio < existing_prio:
                seen[key] = p
    return sorted(seen.values(), key=lambda p: p["name"].lower())


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def print_table(plugins: list[dict], filter_type: Optional[str]) -> None:
    shown = [p for p in plugins if filter_type is None or p["type"] == filter_type]
    col = {
        "name": max(len(p["name"]) for p in shown) if shown else 10,
        "format": 5,
        "vendor": max((len(p.get("vendor") or "") for p in shown), default=8),
    }
    col["name"] = max(col["name"], 4)
    col["vendor"] = max(col["vendor"], 6)
    hdr = (
        f"{'Name':<{col['name']}}  {'Fmt':<{col['format']}}  "
        f"{'Type':<10}  {'Vendor':<{col['vendor']}}"
    )
    print(hdr)
    print("-" * len(hdr))
    instruments = [p for p in shown if p["type"] == "instrument"]
    effects = [p for p in shown if p["type"] == "effect"]
    for section, items in [("INSTRUMENTS", instruments), ("EFFECTS", effects)]:
        if not items:
            continue
        if filter_type is None:
            print(f"\n{section}")
            print("-" * len(hdr))
        for p in items:
            print(
                f"{p['name']:<{col['name']}}  {p['format']:<{col['format']}}  "
                f"{p['type']:<10}  {p.get('vendor') or '':<{col['vendor']}}"
            )
    print(f"\n{len(shown)} plugins listed ({len(instruments)} instruments, {len(effects)} effects)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Scan installed VST/VST3/CLAP/AU plugins and write a JSON catalogue."
    )
    parser.add_argument(
        "--output", "-o",
        default="database/plugins.json",
        help="Output JSON file path (default: database/plugins.json)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "table"],
        default="json",
        help="Output format: json (write file) or table (print to stdout)",
    )
    parser.add_argument(
        "--filter",
        choices=["instruments", "effects", "all"],
        default="all",
        help="Filter output to instruments, effects, or all",
    )
    parser.add_argument(
        "--no-dedupe",
        action="store_true",
        help="Include duplicate entries across formats (default: prefer VST3 over VST2)",
    )
    args = parser.parse_args()

    filter_type = None
    if args.filter == "instruments":
        filter_type = "instrument"
    elif args.filter == "effects":
        filter_type = "effect"

    log.info("Scanning VST3...")
    vst3 = scan_vst3(SCAN_PATHS["VST3"])
    log.info("Scanning VST2...")
    vst2 = scan_vst2(SCAN_PATHS["VST2"])
    log.info("Scanning CLAP...")
    clap = scan_clap(SCAN_PATHS["CLAP"])
    log.info("Scanning AU...")
    au = scan_au(SCAN_PATHS["AU"])

    all_plugins = vst3 + vst2 + clap + au
    if not args.no_dedupe:
        all_plugins = deduplicate(all_plugins)

    if args.filter != "all":
        filtered = [p for p in all_plugins if p["type"] == filter_type]
    else:
        filtered = all_plugins

    log.info(
        "Found %d plugins total (%d instruments, %d effects)",
        len(all_plugins),
        sum(1 for p in all_plugins if p["type"] == "instrument"),
        sum(1 for p in all_plugins if p["type"] == "effect"),
    )

    if args.format == "table":
        print_table(all_plugins, filter_type)
        return

    # JSON output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    catalogue = {
        "scan_date": __import__("datetime").date.today().isoformat(),
        "total": len(all_plugins),
        "instruments": [p for p in all_plugins if p["type"] == "instrument"],
        "effects": [p for p in all_plugins if p["type"] == "effect"],
    }

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(catalogue, f, indent=2)

    log.info("Wrote %s", output_path)


if __name__ == "__main__":
    main()
