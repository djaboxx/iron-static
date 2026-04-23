#!/usr/bin/env python3
"""
sysex_capture.py — MIDI SysEx capture and preset cataloging for the IRON STATIC rig.

Subcommands:
  list-ports    List available MIDI input ports.
  capture       Open a MIDI port and save all incoming SysEx messages to raw .syx files.
  parse         Parse a raw .syx file and extract presets into JSON.
  catalog       Re-catalog all raw dumps for an instrument (runs parse on each).

Usage:
  python scripts/sysex_capture.py list-ports
  python scripts/sysex_capture.py capture --port "Rev2" --instrument rev2
  python scripts/sysex_capture.py capture --port "Digitakt MIDI" --instrument digitakt --timeout 60
  python scripts/sysex_capture.py parse --file instruments/sequential-rev2/presets/raw/dump_20260422_120000.syx --instrument rev2
  python scripts/sysex_capture.py catalog --instrument rev2

Output layout:
  instruments/[slug]/presets/raw/     -- raw .syx files (timestamped)
  instruments/[slug]/presets/         -- parsed JSON preset files
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
PARAM_MAP_DIR = REPO_ROOT / "database" / "midi_params"

_param_map_cache: dict[str, dict] = {}

def load_param_map(instrument_key: str) -> dict:
    """Load cached param map for an instrument from database/midi_params/[key].json."""
    if instrument_key in _param_map_cache:
        return _param_map_cache[instrument_key]
    path = PARAM_MAP_DIR / f"{instrument_key}.json"
    if path.exists():
        data = json.loads(path.read_text())
        _param_map_cache[instrument_key] = data.get("params", {})
    else:
        _param_map_cache[instrument_key] = {}
    return _param_map_cache[instrument_key]

log = logging.getLogger("sysex_capture")

# ---------------------------------------------------------------------------
# Instrument registry
# ---------------------------------------------------------------------------

INSTRUMENTS = {
    "rev2": {
        "name": "Sequential Prophet Rev2",
        "slug": "sequential-rev2",
        "mfr_id": (0x01,),
        # Sequential lets you set a global MIDI SysEx ID (0–15) which offsets this byte.
        # Default (ID=0) is 0x2E; ID=1 gives 0x2F, etc.  Accept the full range 0x2E–0x3D.
        "device_id_range": (0x2E, 0x3D),
        "can_parse": True,
        "parser": "sequential",
        # F0 01 [0x2E+sysex_id] <cmd> ... F7
        "commands": {
            0x02: "single_program_dump",
            0x03: "edit_buffer_dump",
            0x06: "all_programs_dump",
        },
        "name_offset": None,   # set after reading manual appendix; see NOTE below
        "name_length": 20,
        # Disambiguation: Rev2 dumps are large (bi-timbral, effects, sequencer)
        # Minimum expected unpacked bytes for a single program dump
        "min_unpacked_bytes": 1600,
    },
    "take5": {
        "name": "Sequential Take 5",
        "slug": "sequential-take5",
        "mfr_id": (0x01,),
        # Take 5 SysEx ID 0x2E (default).  Offset range 0x2E–0x3D same as Rev2
        # but disambiguated by dump size (Take 5 dumps are < 800 unpacked bytes).
        "device_id_range": (0x2E, 0x3D),
        "can_parse": True,
        "parser": "sequential",
        "commands": {
            0x02: "single_program_dump",
            0x03: "edit_buffer_dump",
        },
        "name_offset": None,
        "name_length": 20,
        "max_unpacked_bytes": 1599,   # anything larger is Rev2
    },
    "digitakt": {
        "name": "Elektron Digitakt MK1",
        "slug": "elektron-digitakt-mk1",
        "mfr_id": (0x00, 0x20, 0x3C),
        "can_parse": False,
        "parser": "raw",
        "note": "Elektron SysEx format is proprietary. Raw .syx is captured; use Elektron Transfer for full project restores.",
    },
    "rytm": {
        "name": "Elektron Analog Rytm",
        "slug": "elektron-analog-rytm",
        "mfr_id": (0x00, 0x20, 0x3C),
        "can_parse": False,
        "parser": "raw",
        "note": "Elektron SysEx format is proprietary. Capture raw .syx to presets/raw/ and use Elektron Transfer/Overbridge for restores.",
    },
    "minibrute2s": {
        "name": "Arturia MiniBrute 2S",
        "slug": "arturia-minibrute-2s",
        "mfr_id": (0x00, 0x20, 0x6B),
        "can_parse": False,
        "parser": "raw",
        "note": "MiniBrute 2S has minimal SysEx. Panel state is the primary documentation method.",
    },
    "subharmonicon": {
        "name": "Moog Subharmonicon",
        "slug": "moog-subharmonicon",
        "can_parse": False,
        "parser": "panel_state_only",
        "note": "Subharmonicon has no patch memory. Use the create-preset skill for panel-state documentation.",
    },
    "dfam": {
        "name": "Moog DFAM",
        "slug": "moog-dfam",
        "can_parse": False,
        "parser": "panel_state_only",
        "note": "DFAM has no patch memory. Use the create-preset skill for panel-state documentation.",
    },
    "pigments": {
        "name": "Arturia Pigments",
        "slug": "arturia-pigments",
        "can_parse": False,
        "parser": "software_synth",
        "note": "Software VST3/AU synth — no SysEx. MIDI CC assignments are per-preset via MIDI Learn. See database/midi_params/pigments.json for fixed and recommended assignments.",
        "fixed_ccs": {
            1: "Modulation Wheel",
            7: "Master Volume",
            11: "Expression",
            64: "Sustain",
            123: "All Notes Off",
        },
        "recommended_ccs": {
            20: "Macro 1 (M1)",
            21: "Macro 2 (M2)",
            22: "Macro 3 (M3)",
            23: "Macro 4 (M4)",
            74: "Filter 1 Cutoff",
            71: "Filter 1 Resonance",
            75: "Filter 2 Cutoff",
            76: "Filter 2 Resonance",
            73: "Amp Env Attack",
            72: "Amp Env Release",
        },
    },
}

# ---------------------------------------------------------------------------
# Sequential/DSI 7-bit packing helpers
# ---------------------------------------------------------------------------
# Sequential (DSI) packs 8-bit parameter data into MIDI-safe 7-bit form:
#   For each group of 7 data bytes, prepend 1 "high-bits" byte whose bits
#   0–6 are the MSBs of data bytes 0–6 respectively.
#   So every 8 MIDI bytes → 7 original bytes.
#
# NOTE: The exact byte layout and param-name offsets MUST be verified against
# the instrument's MIDI Implementation appendix in the downloaded manual at
# instruments/[slug]/manuals/. The algorithms here are correct for standard
# DSI packing but name_offset values require manual lookup.

def sequential_unpack(packed: bytes) -> bytes:
    """Unpack Sequential/DSI 7-bit encoded data to 8-bit bytes."""
    out = []
    i = 0
    while i + 7 < len(packed):
        hi_bits = packed[i]
        for j in range(7):
            byte = packed[i + 1 + j]
            if hi_bits & (1 << j):
                byte |= 0x80
            out.append(byte)
        i += 8
    return bytes(out)


def sequential_pack(data: bytes) -> bytes:
    """Pack 8-bit data bytes into Sequential/DSI 7-bit MIDI-safe form."""
    out = []
    i = 0
    while i < len(data):
        chunk = data[i:i + 7]
        hi = 0
        stripped = []
        for j, b in enumerate(chunk):
            if b & 0x80:
                hi |= (1 << j)
            stripped.append(b & 0x7F)
        out.append(hi)
        out.extend(stripped)
        if len(chunk) < 7:
            out.extend([0] * (7 - len(chunk)))
        i += 7
    return bytes(out)


def _extract_ascii_name(data: bytes, offset: int, length: int) -> str:
    """Extract a null-terminated ASCII name from unpacked parameter bytes."""
    if offset is None or offset + length > len(data):
        return ""
    raw = data[offset:offset + length]
    name = ""
    for b in raw:
        if b == 0:
            break
        if 0x20 <= b <= 0x7E:
            name += chr(b)
    return name.strip()


def _scan_for_name(data: bytes, length: int = 4) -> str:
    """
    Fallback: scan unpacked data for the best candidate preset name.
    Heuristic: find printable ASCII runs that look like names —
    at least `length` chars, not all the same character, not all digits,
    contains at least one letter.  Returns the first qualifying run.
    """
    run = ""
    for b in list(data) + [0]:  # sentinel to flush last run
        if 0x20 <= b <= 0x7E:
            run += chr(b)
        else:
            candidate = run.strip()
            run = ""
            if len(candidate) < length:
                continue
            # Reject runs of repeated identical characters (e.g. "<<<<<<")
            if len(set(candidate)) < 2:
                continue
            # Must contain at least one letter
            if not any(c.isalpha() for c in candidate):
                continue
            return candidate
    return "Unnamed"

# ---------------------------------------------------------------------------
# SysEx identification
# ---------------------------------------------------------------------------

def identify_sysex(data: tuple, payload_len: int = 0) -> dict | None:
    """
    Match raw SysEx data bytes (without F0/F7) to a known instrument.
    payload_len: total packed payload length for size-based disambiguation.
    Returns instrument info dict with matched 'command' key added, or None.
    """
    data = list(data)
    candidates = []
    for slug, info in INSTRUMENTS.items():
        if info.get("parser") == "panel_state_only":
            continue
        mfr = list(info.get("mfr_id", ()))
        if data[:len(mfr)] != mfr:
            continue
        offset = len(mfr)
        if len(mfr) == 1:
            if len(data) < offset + 2:
                continue
            dev_id = data[offset]
            cmd = data[offset + 1]
            # Single device_id match
            if "device_id" in info:
                if dev_id != info["device_id"]:
                    continue
            # Range-based match (e.g. Rev2/Take5 with configurable SysEx ID)
            elif "device_id_range" in info:
                lo, hi = info["device_id_range"]
                if not (lo <= dev_id <= hi):
                    continue
            else:
                continue
            cmd_name = info.get("commands", {}).get(cmd, f"cmd_0x{cmd:02X}")
            candidates.append({**info, "instrument_key": slug, "command_byte": cmd,
                                "command_name": cmd_name, "header_len": offset + 2})
        else:
            # 3-byte manufacturer: no further disambiguation
            candidates.append({**info, "instrument_key": slug, "command_byte": None,
                                "command_name": "raw", "header_len": offset})

    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]

    # Disambiguate by expected payload size
    # Estimate unpacked bytes from packed payload length: unpacked ≈ packed * 7/8
    est_unpacked = int(payload_len * 7 / 8)
    for c in candidates:
        min_u = c.get("min_unpacked_bytes", 0)
        max_u = c.get("max_unpacked_bytes", 999999)
        if min_u <= est_unpacked <= max_u:
            return c

    # Fall back to first candidate if disambiguation fails
    return candidates[0]

# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_sequential(sysex_data: tuple, info: dict, bank: int | None = None, prog: int | None = None) -> list[dict]:
    """
    Parse a Sequential/DSI SysEx dump into one or more preset dicts.
    Returns a list (single element for single-program dump, many for all-programs dump).
    """
    raw = list(sysex_data)
    header_len = info["header_len"]
    payload = bytes(raw[header_len:])
    unpacked = sequential_unpack(payload)

    name_offset = info.get("name_offset")
    name_length = info.get("name_length", 20)
    name = ""
    if name_offset is not None:
        name = _extract_ascii_name(unpacked, name_offset, name_length)
    if not name:
        name = _scan_for_name(unpacked, length=4) or "Unnamed"

    # Build named parameter dict if a param map exists for this instrument
    instrument_key = info["instrument_key"]
    param_map = load_param_map(instrument_key)   # {str(index): {name, value_range, ...}}
    if param_map:
        parameters = {}
        for idx, byte_val in enumerate(unpacked):
            entry = param_map.get(str(idx))
            param_name = entry["name"] if entry else f"param_{idx}"
            parameters[param_name] = {
                "index": idx,
                "value": byte_val,
                "value_range": entry["value_range"] if entry else None,
            }
    else:
        parameters = None

    preset = {
        "instrument": instrument_key,
        "command": info["command_name"],
        "bank": bank,
        "program": prog,
        "name": name,
        "unpacked_bytes": len(unpacked),
        "raw_hex": payload.hex(),
        "parameters": parameters if parameters is not None else list(unpacked),
        "captured_at": datetime.now().isoformat(),
        "parse_note": (
            "name_offset not yet set — name extracted by heuristic scan. "
            "See instruments/{}/manuals/ appendix for exact offsets.".format(info["slug"])
            if name_offset is None else ""
        ),
    }
    return [preset]


def parse_raw(sysex_data: tuple, info: dict) -> list[dict]:
    """Minimal parser: save raw bytes + identification only."""
    return [{
        "instrument": info["instrument_key"],
        "command": info.get("command_name", "raw"),
        "raw_hex": bytes(sysex_data).hex(),
        "byte_count": len(sysex_data),
        "captured_at": datetime.now().isoformat(),
        "note": info.get("note", ""),
    }]


def parse_sysex_message(msg_data: tuple) -> dict:
    """
    Top-level dispatcher: identify instrument and call the right parser.
    Returns a result dict with 'presets' list and metadata.
    """
    info = identify_sysex(msg_data, payload_len=len(msg_data))
    if info is None:
        return {
            "identified": False,
            "raw_hex": bytes(msg_data).hex(),
            "presets": [],
        }

    parser = info.get("parser", "raw")
    if parser == "sequential":
        presets = parse_sequential(msg_data, info)
    else:
        presets = parse_raw(msg_data, info)

    return {
        "identified": True,
        "instrument": info["instrument_key"],
        "instrument_name": info["name"],
        "command": info.get("command_name"),
        "presets": presets,
    }

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------


def preset_dir(slug: str) -> Path:
    return REPO_ROOT / "instruments" / slug / "presets"


def raw_dir(slug: str) -> Path:
    return preset_dir(slug) / "raw"


def save_raw_syx(data: tuple, slug: str, timestamp: str) -> Path:
    out = raw_dir(slug)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"dump_{timestamp}.syx"
    path.write_bytes(bytes([0xF0] + list(data) + [0xF7]))
    return path


def save_preset_json(preset: dict, slug: str, index: int = 0) -> Path:
    out = preset_dir(slug)
    out.mkdir(parents=True, exist_ok=True)
    ts = preset.get("captured_at", datetime.now().isoformat()).replace(":", "-").replace(".", "-")
    name_slug = preset.get("name", "unnamed").lower().replace(" ", "_")[:30]
    filename = f"{name_slug}_{ts[:10]}_{index:03d}.json"
    path = out / filename
    path.write_text(json.dumps(preset, indent=2))
    return path


def update_catalog(slug: str, presets: list[dict]) -> Path:
    catalog_path = preset_dir(slug) / "catalog.json"
    existing = []
    if catalog_path.exists():
        try:
            existing = json.loads(catalog_path.read_text())
        except Exception:
            existing = []
    existing.extend(presets)
    catalog_path.write_text(json.dumps(existing, indent=2))
    return catalog_path

# ---------------------------------------------------------------------------
# Port resolution (fuzzy matching)
# ---------------------------------------------------------------------------

def resolve_port(name: str, available: list[str]) -> str:
    """
    Resolve a user-supplied port name to an exact port string.
    Priority:
      1. Exact match
      2. Case-insensitive exact match
      3. Case-insensitive substring match (first hit wins)
    Exits with a helpful message if no match is found.
    """
    if name in available:
        return name
    lower = name.lower()
    for p in available:
        if p.lower() == lower:
            return p
    for p in available:
        if lower in p.lower():
            log.info("Resolved '%s' → '%s'", name, p)
            return p
    print(f"\nERROR: No MIDI input port matching '{name}'.")
    print("Available ports:")
    for p in available:
        print(f"  {p}")
    print("\nTo create a dedicated port, open Audio MIDI Setup → Window → Show MIDI Studio,")
    print("double-click 'IAC Driver', check 'Device is online', and add a port named 'iron-static'.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_list_ports(_args):
    try:
        import mido
    except ImportError:
        log.error("mido not installed. Run: pip install mido python-rtmidi")
        sys.exit(1)
    inputs = mido.get_input_names()
    outputs = mido.get_output_names()
    print("\nMIDI Input ports:")
    for name in inputs:
        print(f"  {name}")
    print("\nMIDI Output ports:")
    for name in outputs:
        print(f"  {name}")
    print()


def cmd_capture(args):
    try:
        import mido
    except ImportError:
        log.error("mido not installed. Run: pip install mido python-rtmidi")
        sys.exit(1)

    info = INSTRUMENTS.get(args.instrument)
    if info is None:
        log.error("Unknown instrument '%s'. Choices: %s", args.instrument, ", ".join(INSTRUMENTS))
        sys.exit(1)
    if info.get("parser") == "panel_state_only":
        log.error("%s has no SysEx memory. Use the create-preset skill for panel-state documentation.", info["name"])
        sys.exit(1)

    slug = info["slug"]
    port_name = resolve_port(args.port, mido.get_input_names())
    timeout = args.timeout

    print(f"\nListening for SysEx on '{port_name}' (instrument: {info['name']})...")
    print("Initiate a SysEx dump from the instrument now.")
    if timeout:
        print(f"Will stop automatically after {timeout}s of no messages.")
    else:
        print("Press Ctrl-C to stop.")
    print()

    messages_received = 0
    presets_saved = 0
    import signal, time

    deadline = (time.time() + timeout) if timeout else None

    try:
        with mido.open_input(port_name) as port:
            while True:
                if deadline and time.time() > deadline:
                    print(f"\nTimeout reached ({timeout}s). Done.")
                    break
                msg = port.receive(block=False)
                if msg is None:
                    time.sleep(0.01)
                    continue
                if msg.type != "sysex":
                    continue

                messages_received += 1
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                raw_path = save_raw_syx(msg.data, slug, ts)
                print(f"  Received SysEx ({len(msg.data)} bytes) → {raw_path.relative_to(REPO_ROOT)}")

                result = parse_sysex_message(msg.data)
                if result["identified"]:
                    for i, preset in enumerate(result["presets"]):
                        json_path = save_preset_json(preset, slug, i)
                        name = preset.get("name", "?")
                        print(f"    Parsed: '{name}' → {json_path.relative_to(REPO_ROOT)}")
                        presets_saved += 1
                    update_catalog(slug, result["presets"])
                else:
                    print(f"    Unrecognized SysEx header — raw bytes saved.")

                if deadline:
                    deadline = time.time() + timeout  # reset timer on each message

    except KeyboardInterrupt:
        print("\nCancelled.")
    except Exception as e:
        log.error("MIDI error: %s", e)
        sys.exit(1)

    print(f"\nTotal: {messages_received} messages, {presets_saved} presets saved.")
    if presets_saved > 0:
        catalog_path = preset_dir(slug) / "catalog.json"
        print(f"Catalog: {catalog_path.relative_to(REPO_ROOT)}")


def cmd_parse(args):
    syx_path = Path(args.file)
    if not syx_path.exists():
        log.error("File not found: %s", syx_path)
        sys.exit(1)

    info = INSTRUMENTS.get(args.instrument)
    if info is None:
        log.error("Unknown instrument '%s'", args.instrument)
        sys.exit(1)

    raw = syx_path.read_bytes()
    if raw[0] != 0xF0 or raw[-1] != 0xF7:
        log.error("File does not look like a valid SysEx dump (missing F0/F7 framing).")
        sys.exit(1)

    data = tuple(raw[1:-1])  # strip F0 and F7
    result = parse_sysex_message(data)
    slug = info["slug"]

    if not result["identified"]:
        print(f"WARNING: Could not identify instrument from SysEx header.")
        print(f"Raw bytes: {bytes(data[:16]).hex()}...")
    else:
        print(f"Instrument: {result['instrument_name']}")
        print(f"Command:    {result['command']}")

    for i, preset in enumerate(result["presets"]):
        json_path = save_preset_json(preset, slug, i)
        print(f"  Preset [{i}]: '{preset.get('name', '?')}' → {json_path.relative_to(REPO_ROOT)}")

    if result["presets"]:
        update_catalog(slug, result["presets"])
        print(f"Catalog updated: instruments/{slug}/presets/catalog.json")


def cmd_catalog(args):
    info = INSTRUMENTS.get(args.instrument)
    if info is None:
        log.error("Unknown instrument '%s'", args.instrument)
        sys.exit(1)

    slug = info["slug"]
    raw_path = raw_dir(slug)
    if not raw_path.exists():
        print(f"No raw dumps found at {raw_path.relative_to(REPO_ROOT)}")
        return

    syx_files = sorted(raw_path.glob("*.syx"))
    if not syx_files:
        print("No .syx files found.")
        return

    print(f"Re-cataloging {len(syx_files)} dump(s) for {info['name']}...")
    all_presets = []
    for syx_file in syx_files:
        raw = syx_file.read_bytes()
        if raw[0] != 0xF0 or raw[-1] != 0xF7:
            print(f"  SKIP {syx_file.name}: invalid framing")
            continue
        data = tuple(raw[1:-1])
        result = parse_sysex_message(data)
        for preset in result["presets"]:
            all_presets.append(preset)
            print(f"  {syx_file.name}: '{preset.get('name', '?')}'")

    if all_presets:
        catalog_path = preset_dir(slug) / "catalog.json"
        catalog_path.write_text(json.dumps(all_presets, indent=2))
        print(f"\nWrote {len(all_presets)} entries to {catalog_path.relative_to(REPO_ROOT)}")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="IRON STATIC SysEx capture and preset cataloging tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list-ports
    sub.add_parser("list-ports", help="List available MIDI input/output ports")

    # capture
    cap = sub.add_parser("capture", help="Listen on a MIDI port and save incoming SysEx")
    cap.add_argument("--port", required=True, help="MIDI input port name (from list-ports)")
    cap.add_argument("--instrument", required=True, choices=list(INSTRUMENTS.keys()),
                     help="Instrument to capture from")
    cap.add_argument("--timeout", type=float, default=None,
                     help="Seconds of inactivity before stopping (default: wait for Ctrl-C)")

    # parse
    prs = sub.add_parser("parse", help="Parse a raw .syx file into JSON presets")
    prs.add_argument("--file", required=True, help="Path to .syx file")
    prs.add_argument("--instrument", required=True, choices=list(INSTRUMENTS.keys()),
                     help="Instrument the dump came from")

    # catalog
    cat = sub.add_parser("catalog", help="Re-catalog all raw dumps for an instrument")
    cat.add_argument("--instrument", required=True, choices=list(INSTRUMENTS.keys()),
                     help="Instrument to catalog")

    args = parser.parse_args()
    dispatch = {
        "list-ports": cmd_list_ports,
        "capture":    cmd_capture,
        "parse":      cmd_parse,
        "catalog":    cmd_catalog,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
