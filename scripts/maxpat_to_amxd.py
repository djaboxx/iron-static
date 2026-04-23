#!/usr/bin/env python3
"""
maxpat_to_amxd.py — Convert a Max .maxpat file to an Ableton .amxd file

The .amxd format is a binary wrapper around the same JSON content as .maxpat:

  [ampf][version=4 LE32][aaaa][meta][meta_len LE32][meta_bytes]
  [ptch][json_len+1 LE32][json_bytes][0x00]

The JSON content is identical between .maxpat and .amxd.

Usage:
    python3 scripts/maxpat_to_amxd.py ableton/m4l/my-device.maxpat
    # writes ableton/m4l/my-device.amxd

    python3 scripts/maxpat_to_amxd.py ableton/m4l/my-device.maxpat --out /path/to/output.amxd

    # Build all .maxpat files in ableton/m4l/ that don't already have a matching .amxd:
    python3 scripts/maxpat_to_amxd.py --all
"""

import argparse
import logging
import struct
import sys
from pathlib import Path

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
M4L_DIR   = REPO_ROOT / "ableton" / "m4l"

# Binary header constants
MAGIC        = b"ampf"
FORMAT_VER   = struct.pack("<I", 4)
TAG_AAAA     = b"aaaa"
TAG_META     = b"meta"
META_PAYLOAD = struct.pack("<I", 4) + b"\x00\x00\x00\x00"   # len=4, 4 null bytes
TAG_PTCH     = b"ptch"


def build_amxd_bytes(json_bytes: bytes) -> bytes:
    """Wrap raw JSON bytes in the .amxd binary container."""
    # ptch length includes the null terminator
    ptch_len = len(json_bytes) + 1
    header = (
        MAGIC
        + FORMAT_VER
        + TAG_AAAA
        + TAG_META
        + META_PAYLOAD
        + TAG_PTCH
        + struct.pack("<I", ptch_len)
    )
    return header + json_bytes + b"\x00"


def convert(src: Path, dst: Path) -> None:
    json_bytes = src.read_bytes()
    # Validate it parses as JSON
    import json
    try:
        json.loads(json_bytes)
    except Exception as e:
        log.error("Invalid JSON in %s: %s", src, e)
        sys.exit(1)

    amxd_bytes = build_amxd_bytes(json_bytes)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(amxd_bytes)
    log.info("wrote %s (%d bytes)", dst, len(amxd_bytes))
    print(f"  {src.name}  →  {dst}")


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    p = argparse.ArgumentParser(description="Convert .maxpat to .amxd")
    p.add_argument("src", nargs="?", type=Path,
                   help="Source .maxpat file")
    p.add_argument("--out", type=Path,
                   help="Output .amxd path (default: same dir, .amxd extension)")
    p.add_argument("--all", action="store_true",
                   help=f"Convert all .maxpat files under {M4L_DIR} that lack a matching .amxd")
    args = p.parse_args()

    if args.all:
        targets = list(M4L_DIR.rglob("*.maxpat"))
        if not targets:
            print("No .maxpat files found.")
            return
        for src in sorted(targets):
            dst = src.with_suffix(".amxd")
            if dst.exists():
                print(f"  skip (already exists): {dst.name}")
                continue
            convert(src, dst)
    elif args.src:
        if not args.src.exists():
            log.error("File not found: %s", args.src)
            sys.exit(1)
        dst = args.out or args.src.with_suffix(".amxd")
        convert(args.src, dst)
    else:
        p.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
