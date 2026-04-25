#!/usr/bin/env python3
"""discover_devices.py — Index all Ableton device presets (.adg) into a searchable JSON library.

Scans Live's Core Library, installed Packs, and User Library for .adg files.
Extracts device type, name, and category from each preset.
Outputs database/device_library.json for use by build_session.py and generate_als.py.

Usage:
    python scripts/discover_devices.py              # (re)build index
    python scripts/discover_devices.py --rebuild    # force rebuild
    python scripts/discover_devices.py --search "wavetable"
    python scripts/discover_devices.py --list-types
    python scripts/discover_devices.py --list-categories
"""

import argparse
import gzip
import json
import logging
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
OUTPUT = REPO_ROOT / "database" / "device_library.json"

SCAN_ROOTS = [
    Path("/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Core Library"),
    Path.home() / "Music" / "Ableton" / "Packs",
    Path.home() / "Music" / "Ableton" / "User Library",
]


def _source_label(adg_path: Path) -> str:
    s = str(adg_path)
    if "App-Resources" in s:
        return "core"
    if "User Library" in s:
        return "user"
    return "pack"


def _parse_adg(adg_path: Path) -> dict | None:
    """Extract metadata from a single .adg file.

    ADG structure:
        <Ableton>
          <GroupDevicePreset>
            <Device>
              <{DeviceTag} Id="0">...</{DeviceTag}>
            </Device>
            ...
          </GroupDevicePreset>
        </Ableton>
    """
    try:
        xml_bytes = gzip.open(adg_path).read()
        root = ET.fromstring(xml_bytes)
        gp = root.find("GroupDevicePreset")
        if gp is None:
            return None
        dev_wrapper = gp.find("Device")
        if dev_wrapper is None:
            return None
        device = next(iter(dev_wrapper), None)
        if device is None:
            return None

        device_tag = device.tag
        name_elem = device.find(".//UserName")
        preset_name = name_elem.get("Value", "").strip() if name_elem is not None else ""
        if not preset_name:
            preset_name = adg_path.stem

        return {
            "name": preset_name,
            "file": adg_path.stem,
            "device_type": device_tag,
            "category": adg_path.parent.name,
            "source": _source_label(adg_path),
            "path": str(adg_path),
        }
    except Exception as exc:
        logging.debug("Skipping %s: %s", adg_path, exc)
        return None


def build_index(verbose: bool = False) -> list[dict]:
    entries = []
    for root_dir in SCAN_ROOTS:
        if not root_dir.exists():
            logging.debug("Skipping missing directory: %s", root_dir)
            continue
        for adg_path in sorted(root_dir.rglob("*.adg")):
            entry = _parse_adg(adg_path)
            if entry:
                entries.append(entry)
                if verbose:
                    logging.debug("  [%s] %s / %s", entry["source"], entry["device_type"], entry["name"])
    logging.info("Indexed %d device presets", len(entries))
    return entries


def search(entries: list[dict], query: str) -> list[dict]:
    q = query.lower()
    return [
        e for e in entries
        if q in e["name"].lower()
        or q in e["file"].lower()
        or q in e["device_type"].lower()
        or q in e["category"].lower()
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index Ableton device presets (.adg) into database/device_library.json.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild even if index exists")
    parser.add_argument("--search", metavar="QUERY", help="Search the index (fuzzy name/type/category)")
    parser.add_argument("--list-types", action="store_true", help="List all device_type values by count")
    parser.add_argument("--list-categories", action="store_true", help="List all category values by count")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    needs_build = args.rebuild or not OUTPUT.exists()
    # Also rebuild if any of the query flags are set without an existing index
    if (args.list_types or args.list_categories or args.search) and not OUTPUT.exists():
        needs_build = True

    if needs_build:
        logging.info("Scanning %d root directories for .adg files...", len(SCAN_ROOTS))
        entries = build_index(args.verbose)
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(json.dumps(entries, indent=2))
        logging.info("Written: %s  (%d entries)", OUTPUT, len(entries))
    else:
        logging.info("Loading existing index from %s  (use --rebuild to refresh)", OUTPUT)
        entries = json.loads(OUTPUT.read_text())
        logging.info("Loaded %d entries", len(entries))

    if args.list_types:
        print("\nDevice types:")
        for dtype, count in Counter(e["device_type"] for e in entries).most_common():
            print(f"  {dtype:<45} {count}")
        return

    if args.list_categories:
        print("\nCategories:")
        for cat, count in Counter(e["category"] for e in entries).most_common(30):
            print(f"  {cat:<40} {count}")
        return

    if args.search:
        matches = search(entries, args.search)
        for m in sorted(matches, key=lambda e: e["name"])[:40]:
            print(f"  [{m['source']:4}] {m['device_type']:<40} {m['name']}")
            print(f"         {m['path']}")
        if not matches:
            print("  (no matches)")
        else:
            print(f"\n{len(matches)} match(es)")
        return

    # Default: just print a summary
    by_source = Counter(e["source"] for e in entries)
    by_type = Counter(e["device_type"] for e in entries)
    print(f"\nDevice library: {len(entries)} presets")
    print(f"  By source: {dict(by_source)}")
    print(f"  Top types: {dict(by_type.most_common(5))}")
    print(f"\nUse --search, --list-types, or --list-categories for details.")


if __name__ == "__main__":
    main()
