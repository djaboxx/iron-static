#!/usr/bin/env python3
"""
push_preset.py — Push a preset JSON to a hardware instrument via NRPN.

Usage:
    python scripts/push_preset.py --preset instruments/sequential-take5/presets/take5_oxidized-floor-bass_A-phrygian.json
    python scripts/push_preset.py --preset <path> --port "Take5" --channel 4 --dry-run

Requires: python-rtmidi (pip install python-rtmidi)
"""
import argparse
import json
import logging
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger(__name__)


def list_ports(midi_out) -> list[str]:
    return midi_out.get_ports()


def find_port(midi_out, name_hint: str) -> int | None:
    ports = list_ports(midi_out)
    hint_lower = name_hint.lower()
    for i, p in enumerate(ports):
        if hint_lower in p.lower():
            return i
    return None


def send_nrpn(midi_out, channel: int, param: int, value: int) -> None:
    """Send a single NRPN message (4 CC messages) on the given channel (1-indexed)."""
    ch = channel - 1  # 0-indexed
    param_msb = (param >> 7) & 0x7F
    param_lsb = param & 0x7F
    val_msb = (value >> 7) & 0x7F
    val_lsb = value & 0x7F

    midi_out.send_message([0xB0 | ch, 99, param_msb])   # CC99 = NRPN param MSB
    midi_out.send_message([0xB0 | ch, 98, param_lsb])   # CC98 = NRPN param LSB
    midi_out.send_message([0xB0 | ch, 6,  val_msb])     # CC6  = data entry MSB
    midi_out.send_message([0xB0 | ch, 38, val_lsb])     # CC38 = data entry LSB


def push_preset(preset_path: str, port_hint: str, channel: int, delay_ms: float, dry_run: bool) -> int:
    """Load a preset JSON and push its nrpn_dump to the instrument. Returns 0 on success."""
    try:
        import rtmidi
    except ImportError:
        log.error("python-rtmidi not installed. Run: pip install python-rtmidi")
        return 1

    with open(preset_path) as f:
        preset = json.load(f)

    nrpn_dump = preset.get("nrpn_dump")
    if not nrpn_dump:
        log.error("Preset has no 'nrpn_dump' key — nothing to push.")
        return 1

    midi_out = rtmidi.MidiOut()
    ports = list_ports(midi_out)

    if not ports:
        log.error("No MIDI output ports found. Is the instrument connected? Is Ableton holding the port?")
        return 1

    log.info("Available MIDI output ports:")
    for i, p in enumerate(ports):
        log.info("  [%d] %s", i, p)

    port_idx = find_port(midi_out, port_hint)
    if port_idx is None:
        log.error("No port matching %r found. Check port name above.", port_hint)
        log.error("If Ableton is open, disable the instrument's port in Live → Settings → MIDI.")
        return 1

    log.info("Using port [%d]: %s", port_idx, ports[port_idx])
    log.info("Preset: %s — %s", preset.get("name", "?"), preset.get("description", ""))
    log.info("Pushing %d NRPN params on MIDI ch%d%s", len(nrpn_dump), channel, " (DRY RUN)" if dry_run else "")

    if not dry_run:
        midi_out.open_port(port_idx)

    for entry in nrpn_dump:
        param = entry["nrpn"]
        value = entry["value"]
        name  = entry.get("name", f"nrpn_{param}")
        log.info("  NRPN %3d = %-6d  (%s)", param, value, name)
        if not dry_run:
            send_nrpn(midi_out, channel, param, value)
            time.sleep(delay_ms / 1000.0)

    if not dry_run:
        midi_out.close_port()
        log.info("Done. Preset pushed to %s on ch%d.", ports[port_idx], channel)
    else:
        log.info("Dry run complete — no MIDI sent.")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Push a preset JSON to hardware via NRPN.")
    parser.add_argument("--preset",   required=False, default=None, help="Path to preset JSON with nrpn_dump")
    parser.add_argument("--port",     default="Take5", help="Partial MIDI port name to match (default: Take5)")
    parser.add_argument("--channel",  type=int, default=4, help="MIDI channel 1-16 (default: 4 for Take 5)")
    parser.add_argument("--delay-ms", type=float, default=10.0, help="Delay between NRPN messages in ms (default: 10)")
    parser.add_argument("--dry-run",  action="store_true", help="Print params without sending MIDI")
    parser.add_argument("--list-ports", action="store_true", help="List available MIDI ports and exit")
    args = parser.parse_args()

    if args.list_ports:
        try:
            import rtmidi
            out = rtmidi.MidiOut()
            for i, p in enumerate(out.get_ports()):
                print(f"[{i}] {p}")
        except ImportError:
            print("python-rtmidi not installed.")
        sys.exit(0)

    if not args.preset:
        parser.error("--preset is required unless --list-ports is used.")

    sys.exit(push_preset(args.preset, args.port, args.channel, args.delay_ms, args.dry_run))


if __name__ == "__main__":
    main()
