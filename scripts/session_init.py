#!/usr/bin/env python3
"""
session_init.py — Monday morning session initialization for IRON STATIC.

Scans connected MIDI devices, reports rig status vs database/instruments.json,
and wires up the Ableton Live session for the active song.

Subcommands:
    scan              Scan MIDI ports and report rig status
    setup             Scan rig + setup Ableton session (calls ableton_push.py setup-rig)
    add-instrument    Add a single instrument track to the current Ableton session
    midi-map          Print the full MIDI channel map

Options (scan):
    --json            Machine-readable JSON output (used by session_context hook)

Options (setup):
    --song SLUG       Override active song slug (default: active song from songs.json)

Options (add-instrument):
    --slug SLUG       Instrument slug (e.g. take5, rev2, dfam)
    --track-name NAME Override default Ableton track name

Usage:
    python scripts/session_init.py scan
    python scripts/session_init.py scan --json
    python scripts/session_init.py setup
    python scripts/session_init.py setup --song rust-protocol
    python scripts/session_init.py add-instrument --slug take5
    python scripts/session_init.py midi-map
"""

import argparse
import json
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
DB_INSTRUMENTS = REPO_ROOT / "database" / "instruments.json"
DB_SONGS = REPO_ROOT / "database" / "songs.json"
TEMPLATES_DIR = REPO_ROOT / "ableton" / "templates"
ABLETON_PUSH = REPO_ROOT / "scripts" / "ableton_push.py"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_instruments() -> list:
    return json.loads(DB_INSTRUMENTS.read_text())["instruments"]


def load_active_song() -> dict | None:
    if not DB_SONGS.exists():
        return None
    songs = json.loads(DB_SONGS.read_text()).get("songs", [])
    return next((s for s in songs if s.get("status") == "active"), None)


# ---------------------------------------------------------------------------
# MIDI scanning
# ---------------------------------------------------------------------------

def scan_midi_ports() -> tuple[list, list]:
    """Return (input_ports, output_ports). Gracefully handles missing rtmidi."""
    try:
        import rtmidi  # type: ignore
        mid_in = rtmidi.MidiIn()
        mid_out = rtmidi.MidiOut()
        ins = mid_in.get_ports()
        outs = mid_out.get_ports()
        del mid_in, mid_out
        return ins, outs
    except ImportError:
        log.warning("python-rtmidi not installed — cannot scan MIDI ports")
        return [], []


def match_port(instrument: dict, input_ports: list, output_ports: list) -> str | None:
    """Return the first matched MIDI port name string, or None."""
    patterns = instrument.get("midi_port_patterns", [])
    if not patterns:
        return None
    # Deduplicated, ordered union of in + out ports
    seen: set = set()
    all_ports = []
    for p in input_ports + output_ports:
        if p not in seen:
            seen.add(p)
            all_ports.append(p)
    for port in all_ports:
        for pat in patterns:
            if pat.lower() in port.lower():
                return port
    return None


def build_rig_status(instruments: list, input_ports: list, output_ports: list) -> list:
    results = []
    for inst in instruments:
        midi_usb = inst.get("midi_usb", True)
        if not midi_usb:
            status = "no_usb_midi"
            port = None
        else:
            port = match_port(inst, input_ports, output_ports)
            status = "online" if port else "offline"
        results.append({
            "slug": inst["slug"],
            "name": inst["name"],
            "status": status,
            "port": port,
            "midi_channels": inst.get("midi_channels", {}),
            "ableton_track_name": inst.get("ableton_track_name"),
            "ableton_track_names": inst.get("ableton_track_names"),
        })
    return results


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_scan(args) -> None:
    instruments = load_instruments()
    in_ports, out_ports = scan_midi_ports()
    rig = build_rig_status(instruments, in_ports, out_ports)

    if getattr(args, "json", False):
        print(json.dumps({
            "rig_status": rig,
            "all_input_ports": in_ports,
            "all_output_ports": out_ports,
        }, indent=2))
        return

    online = [r for r in rig if r["status"] == "online"]
    offline = [r for r in rig if r["status"] == "offline"]
    no_usb = [r for r in rig if r["status"] == "no_usb_midi"]

    def ch_str(midi_channels: dict) -> str:
        return "  ".join(f"{k}={v}" for k, v in midi_channels.items())

    W = 70
    print()
    print("  " + "─" * W)
    print(f"  {'IRON STATIC — RIG STATUS':^{W}}")
    print("  " + "─" * W)

    for r in online:
        port_label = f"[{r['port']}]" if r["port"] else ""
        print(f"  ✓  {r['name']:<30}  ch: {ch_str(r['midi_channels']):<18}  {port_label}")

    if offline:
        print("  " + "·" * W)
        for r in offline:
            print(f"  ✗  {r['name']:<30}  ch: {ch_str(r['midi_channels']):<18}  NOT DETECTED")

    if no_usb:
        print("  " + "·" * W)
        for r in no_usb:
            print(f"  ~  {r['name']:<30}  ch: {ch_str(r['midi_channels']):<18}  DIN-only (no USB MIDI)")

    print("  " + "─" * W)
    usb_count = len(online) + len(offline)
    print(f"  {len(online)}/{usb_count} USB instruments online")

    # Flag unrecognised ports (not in instruments.json)
    unknown_in = [
        p for p in in_ports
        if not any(
            any(pat.lower() in p.lower() for pat in inst.get("midi_port_patterns", []))
            for inst in instruments
        )
    ]
    if unknown_in:
        print()
        print("  Unrecognised MIDI input ports (not in database/instruments.json):")
        for p in unknown_in:
            print(f"    • {p}")
    print()


def cmd_setup(args) -> None:
    # Show rig status first
    class _ScanArgs:
        json = False
    cmd_scan(_ScanArgs())

    active_song = load_active_song()
    song_slug = getattr(args, "song", None) or (active_song["slug"] if active_song else None)

    if not song_slug:
        log.error(
            "No active song found. Run: python scripts/manage_songs.py activate --slug <slug>"
        )
        sys.exit(1)

    template = TEMPLATES_DIR / f"{song_slug}.hcl"
    if not template.exists():
        template = TEMPLATES_DIR / "iron-static-default.hcl"
        log.warning("No template for '%s' — falling back to iron-static-default.hcl", song_slug)

    log.info("Wiring Ableton session for '%s' from %s", song_slug, template.name)
    result = subprocess.run([
        sys.executable, str(ABLETON_PUSH),
        "setup-rig", "--template", str(template),
    ])
    sys.exit(result.returncode)


def cmd_add_instrument(args) -> None:
    instruments = load_instruments()
    inst = next((i for i in instruments if i["slug"] == args.slug), None)
    if inst is None:
        log.error(
            "Unknown instrument slug '%s'. Known slugs: %s",
            args.slug,
            ", ".join(i["slug"] for i in instruments),
        )
        sys.exit(1)

    track_name = args.track_name or inst.get("ableton_track_name") or inst["name"]

    # Pick the first/primary MIDI channel value
    midi_channels = inst.get("midi_channels", {})
    midi_channel = next(iter(midi_channels.values()), 1) if midi_channels else 1

    log.info(
        "Adding track '%s' (MIDI ch %d) to the current Ableton session",
        track_name, midi_channel,
    )
    result = subprocess.run([
        sys.executable, str(ABLETON_PUSH),
        "create-track",
        "--name", track_name,
        "--midi-channel", str(midi_channel),
    ])
    sys.exit(result.returncode)


def cmd_midi_map(args) -> None:
    instruments = load_instruments()
    in_ports, out_ports = scan_midi_ports()
    rig = build_rig_status(instruments, in_ports, out_ports)

    print()
    print(f"  {'Instrument':<30}  {'Channel(s)':<24}  {'Ableton Track':<18}  Status")
    print(f"  {'─'*29}  {'─'*23}  {'─'*17}  {'─'*12}")

    for r in rig:
        ch = "  ".join(f"{k}={v}" for k, v in r["midi_channels"].items())
        # Show primary track name (or both if multi-layer)
        names = r.get("ableton_track_names") or (
            [r["ableton_track_name"]] if r["ableton_track_name"] else ["—"]
        )
        track_label = ", ".join(str(n) for n in names if n)
        icons = {"online": "✓ online", "offline": "✗ offline", "no_usb_midi": "~ DIN-only"}
        status = icons.get(r["status"], r["status"])
        print(f"  {r['name']:<30}  {ch:<24}  {track_label:<18}  {status}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="IRON STATIC session initialization — Monday morning startup"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # scan
    p_scan = sub.add_parser("scan", help="Scan MIDI ports and report rig status")
    p_scan.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    p_scan.set_defaults(func=cmd_scan)

    # setup
    p_setup = sub.add_parser(
        "setup",
        help="Scan rig + wire up Ableton session for the active song",
    )
    p_setup.add_argument(
        "--song", metavar="SLUG",
        help="Override active song slug (default: read from database/songs.json)",
    )
    p_setup.set_defaults(func=cmd_setup)

    # add-instrument
    p_add = sub.add_parser(
        "add-instrument",
        help="Add a single instrument track to the current Ableton session",
    )
    p_add.add_argument(
        "--slug", required=True,
        help="Instrument slug (e.g. take5, rev2, dfam, minibrute2s)",
    )
    p_add.add_argument(
        "--track-name", metavar="NAME",
        help="Override the default Ableton track name",
    )
    p_add.set_defaults(func=cmd_add_instrument)

    # midi-map
    p_map = sub.add_parser("midi-map", help="Print the full MIDI channel map with live status")
    p_map.set_defaults(func=cmd_midi_map)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
