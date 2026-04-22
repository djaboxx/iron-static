#!/usr/bin/env python3
"""
midi_control.py — Send real-time MIDI parameter changes to IRON STATIC instruments.

Sends NRPN (Non-Registered Parameter Number) messages to change synth parameters
live without touching the hardware. The Rev2 uses NRPNs as its preferred method —
they cover the full parameter range (values up to 255+) unlike CCs (max 127).

Usage:
  python scripts/midi_control.py list-ports

  # Set a single parameter by name
  python scripts/midi_control.py set --instrument rev2 --param "Filter Cutoff" --value 80

  # Set a single parameter by NRPN index
  python scripts/midi_control.py set --instrument rev2 --nrpn 15 --value 80

  # Nudge a parameter up/down (relative, +/-)
  python scripts/midi_control.py set --instrument rev2 --param "Filter Resonance" --value +10

  # List all known parameters for an instrument
  python scripts/midi_control.py params --instrument rev2

  # List parameters filtered by keyword
  python scripts/midi_control.py params --instrument rev2 --filter filter

  # Interactive mode: type param=value pairs continuously
  python scripts/midi_control.py interactive --instrument rev2
"""

import argparse
import json
import logging
import sys
import time
from pathlib import Path

log = logging.getLogger("midi_control")

REPO_ROOT = Path(__file__).parent.parent
PARAM_MAP_DIR = REPO_ROOT / "database" / "midi_params"

# Default MIDI port per instrument key (fuzzy-matched at runtime)
DEFAULT_PORTS = {
    "rev2":         "Rev2",
    "take5":        "Take 5",
    "digitakt":     "Digitakt",
    "minibrute2s":  "MiniBrute",
    "subharmonicon": None,
    "dfam":         None,
}

# Default MIDI channel per instrument (1-based, per copilot-instructions)
DEFAULT_CHANNELS = {
    "rev2":         2,   # Layer A
    "take5":        4,
    "digitakt":     1,
    "subharmonicon": 5,
    "dfam":         6,
    "minibrute2s":  7,
}

# ---------------------------------------------------------------------------
# Port resolution
# ---------------------------------------------------------------------------

def resolve_output_port(name: str) -> str:
    import mido
    available = mido.get_output_names()
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
    print(f"\nERROR: No MIDI output port matching '{name}'.")
    print("Available output ports:")
    for p in available:
        print(f"  {p}")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Param map loader
# ---------------------------------------------------------------------------

_param_cache: dict[str, dict] = {}

def load_params(instrument_key: str) -> dict:
    """Load param map as {name_lower: entry_dict} + {str(nrpn_a): entry_dict}."""
    if instrument_key in _param_cache:
        return _param_cache[instrument_key]
    path = PARAM_MAP_DIR / f"{instrument_key}.json"
    if not path.exists():
        log.warning("No param map for '%s' at %s", instrument_key, path)
        _param_cache[instrument_key] = {}
        return {}
    data = json.loads(path.read_text())
    params = data.get("params", {})
    # Build lookup by both lowercased name and NRPN index string
    by_name = {}
    by_index = {}
    for idx_str, entry in params.items():
        by_name[entry["name"].lower()] = entry
        by_index[idx_str] = entry
    _param_cache[instrument_key] = {"by_name": by_name, "by_index": by_index, "raw": params}
    return _param_cache[instrument_key]


def find_param(instrument_key: str, name_or_index: str) -> dict | None:
    """Find a parameter by exact name, partial name, or NRPN index string."""
    maps = load_params(instrument_key)
    if not maps:
        return None

    # Exact NRPN index
    if name_or_index.isdigit():
        return maps["by_index"].get(name_or_index)

    # Exact name (case-insensitive)
    lower = name_or_index.lower()
    if lower in maps["by_name"]:
        return maps["by_name"][lower]

    # Partial match
    hits = [(k, v) for k, v in maps["by_name"].items() if lower in k]
    if len(hits) == 1:
        return hits[0][1]
    if len(hits) > 1:
        print(f"Ambiguous parameter '{name_or_index}'. Matches:")
        for k, v in hits:
            print(f"  [{v['nrpn_a']:3d}] {v['name']}")
        sys.exit(1)

    return None

# ---------------------------------------------------------------------------
# NRPN send
# ---------------------------------------------------------------------------

def send_nrpn(port, channel: int, nrpn_number: int, value: int):
    """
    Send a 4-message NRPN sequence to set a parameter value.
    channel: 1-based MIDI channel
    nrpn_number: the NRPN parameter number (Layer A for Rev2)
    value: the parameter value
    """
    import mido
    ch = channel - 1  # mido uses 0-based channels
    nrpn_msb = (nrpn_number >> 7) & 0x7F
    nrpn_lsb = nrpn_number & 0x7F
    val_msb   = (value >> 7) & 0x7F
    val_lsb   = value & 0x7F

    messages = [
        mido.Message("control_change", channel=ch, control=99, value=nrpn_msb),  # NRPN MSB
        mido.Message("control_change", channel=ch, control=98, value=nrpn_lsb),  # NRPN LSB
        mido.Message("control_change", channel=ch, control=6,  value=val_msb),   # Data Entry MSB
        mido.Message("control_change", channel=ch, control=38, value=val_lsb),   # Data Entry LSB
    ]
    for msg in messages:
        port.send(msg)
    log.debug("NRPN %d = %d (ch %d)", nrpn_number, value, channel)

# ---------------------------------------------------------------------------
# Value resolver
# ---------------------------------------------------------------------------

def resolve_value(value_str: str, current: int | None, param: dict | None) -> int:
    """
    Resolve a value string. Supports:
      - Plain integer: "80"
      - Relative: "+10", "-5"
    Clamps to valid range if param has value_range.
    """
    value_str = value_str.strip()
    if value_str.startswith("+") or value_str.startswith("-"):
        delta = int(value_str)
        base = current if current is not None else 64
        value = base + delta
    else:
        value = int(value_str)

    # Clamp to valid range
    if param and param.get("value_range"):
        vrange = param["value_range"]
        parts = vrange.split("-")
        if len(parts) == 2:
            try:
                lo, hi = int(parts[0]), int(parts[1])
                value = max(lo, min(hi, value))
            except ValueError:
                pass
    return max(0, min(16383, value))  # NRPN max is 14-bit

# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_list_ports(_args):
    import mido
    print("\nMIDI Output ports:")
    for name in mido.get_output_names():
        print(f"  {name}")
    print()


def cmd_params(args):
    instrument = args.instrument
    maps = load_params(instrument)
    if not maps:
        print(f"No parameter map found for '{instrument}'.")
        print(f"Expected: database/midi_params/{instrument}.json")
        print("Use the instrument-onboard skill to build it.")
        return

    filt = args.filter.lower() if args.filter else None
    print(f"\n{instrument.upper()} parameters:")
    print(f"  {'NRPN':>6}  {'Name':<35}  {'Range':<12}  NRPN-B")
    print(f"  {'-'*6}  {'-'*35}  {'-'*12}  ------")
    for idx_str, entry in sorted(maps["raw"].items(), key=lambda x: int(x[0])):
        if filt and filt not in entry["name"].lower():
            continue
        nrpn_b = entry.get("nrpn_b") or "—"
        print(f"  {entry['nrpn_a']:>6}  {entry['name']:<35}  {entry['value_range']:<12}  {nrpn_b}")
    print()


def cmd_set(args):
    try:
        import mido
    except ImportError:
        log.error("mido not installed.")
        sys.exit(1)

    instrument = args.instrument
    channel = args.channel or DEFAULT_CHANNELS.get(instrument, 1)
    port_hint = args.port or DEFAULT_PORTS.get(instrument, instrument)

    if port_hint is None:
        log.error("%s has no default MIDI port. Specify --port.", instrument)
        sys.exit(1)

    port_name = resolve_output_port(port_hint)

    # Resolve parameter
    if args.nrpn is not None:
        nrpn_number = args.nrpn
        param = find_param(instrument, str(nrpn_number))
        param_label = f"NRPN {nrpn_number}"
    elif args.param:
        param = find_param(instrument, args.param)
        if param is None:
            print(f"Parameter '{args.param}' not found for {instrument}.")
            print(f"Run: python scripts/midi_control.py params --instrument {instrument}")
            sys.exit(1)
        nrpn_number = param["nrpn_a"]
        param_label = param["name"]
    else:
        log.error("Specify --param or --nrpn")
        sys.exit(1)

    value = resolve_value(args.value, None, param)

    print(f"\nSending to '{port_name}' ch{channel}: {param_label} = {value}")
    if param:
        print(f"  NRPN {nrpn_number}, range {param.get('value_range', '?')}")

    with mido.open_output(port_name) as port:
        send_nrpn(port, channel, nrpn_number, value)

    print("Done.")


def cmd_interactive(args):
    try:
        import mido
    except ImportError:
        log.error("mido not installed.")
        sys.exit(1)

    instrument = args.instrument
    channel = args.channel or DEFAULT_CHANNELS.get(instrument, 1)
    port_hint = args.port or DEFAULT_PORTS.get(instrument, instrument)

    if port_hint is None:
        log.error("%s has no default MIDI port. Specify --port.", instrument)
        sys.exit(1)

    port_name = resolve_output_port(port_hint)
    maps = load_params(instrument)

    print(f"\nInteractive MIDI control — {instrument.upper()} on '{port_name}' ch{channel}")
    print("Enter: <param name or NRPN index> = <value>  (e.g. 'Filter Cutoff = 80')")
    print("Prefix value with + or - for relative change (e.g. 'Filter Cutoff = +10')")
    print("Type 'list' to show all parameters, 'quit' to exit.\n")

    last_values: dict[int, int] = {}

    with mido.open_output(port_name) as port:
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nDone.")
                break

            if not line:
                continue
            if line.lower() in ("quit", "exit", "q"):
                break
            if line.lower() == "list":
                cmd_params(args)
                continue

            if "=" not in line:
                print("  Format: <param> = <value>")
                continue

            name_part, val_part = line.split("=", 1)
            name_part = name_part.strip()
            val_part  = val_part.strip()

            if name_part.isdigit():
                nrpn_number = int(name_part)
                param = find_param(instrument, name_part)
                param_label = f"NRPN {nrpn_number}"
            else:
                param = find_param(instrument, name_part)
                if param is None:
                    print(f"  Unknown parameter '{name_part}'. Try 'list' or a partial name.")
                    continue
                nrpn_number = param["nrpn_a"]
                param_label = param["name"]

            try:
                value = resolve_value(val_part, last_values.get(nrpn_number), param)
            except ValueError:
                print(f"  Bad value: '{val_part}'")
                continue

            send_nrpn(port, channel, nrpn_number, value)
            last_values[nrpn_number] = value
            vrange = param.get("value_range", "?") if param else "?"
            print(f"  {param_label} [{nrpn_number}] = {value}  (range {vrange})")

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="IRON STATIC real-time MIDI parameter control",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-ports", help="List available MIDI output ports")

    # params
    prms = sub.add_parser("params", help="List parameters for an instrument")
    prms.add_argument("--instrument", required=True, choices=list(DEFAULT_CHANNELS.keys()))
    prms.add_argument("--filter", default=None, help="Filter params by keyword")

    # set
    s = sub.add_parser("set", help="Set a single parameter via NRPN")
    s.add_argument("--instrument", required=True, choices=list(DEFAULT_CHANNELS.keys()))
    s.add_argument("--param",   default=None, help="Parameter name (partial match ok)")
    s.add_argument("--nrpn",    type=int, default=None, help="Raw NRPN number")
    s.add_argument("--value",   required=True, help="Value, or +N/-N for relative change")
    s.add_argument("--channel", type=int, default=None, help="MIDI channel (default from rig config)")
    s.add_argument("--port",    default=None, help="MIDI output port (default auto-detected)")

    # interactive
    i = sub.add_parser("interactive", help="Interactive parameter editor")
    i.add_argument("--instrument", required=True, choices=list(DEFAULT_CHANNELS.keys()))
    i.add_argument("--channel", type=int, default=None)
    i.add_argument("--port",    default=None)
    i.add_argument("--filter",  default=None)  # shared with params for reuse in cmd_params

    args = parser.parse_args()
    dispatch = {
        "list-ports":   cmd_list_ports,
        "params":       cmd_params,
        "set":          cmd_set,
        "interactive":  cmd_interactive,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
