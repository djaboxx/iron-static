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


# Slugs for instruments that are always-offline (no USB MIDI, DIN-only).
# DFAM and Subharmonicon are never USB-connected on this rig.
_ALWAYS_OFFLINE_SLUGS = {"dfam", "subharmonicon"}


# ---------------------------------------------------------------------------
# Known instrument track specs (slug → list of track dicts)
#
# Port indices assume the standard IRON STATIC Ableton MIDI port ordering:
#   0 = Elektron Digitakt  (USB; also used for DIN-only gear via its DIN out)
#   1 = Sequential Rev2
#   2 = Sequential Take 5
#   3 = Arturia Minibrute 2S
#   4 = Elektron Analog Rytm  (when connected)
#
# Colors are decimal representations of 0xRRGGBB.
# ---------------------------------------------------------------------------

_SLUG_TRACKS: dict[str, list[dict]] = {
    "digitakt": [
        {
            "name": "Digitakt",
            "midi_channel": 1,
            "color": 16720384,           # 0xFF2200 red-orange
            "midi_out_port_index": 0,
            "midi_out_device_name": "Elektron Digitakt",
        }
    ],
    "rev2": [
        {
            "name": "Rev2-A",
            "midi_channel": 2,
            "color": 17663,              # 0x0044FF blue
            "midi_out_port_index": 1,
            "midi_out_device_name": "Sequential Rev2",
        },
        {
            "name": "Rev2-B",
            "midi_channel": 3,
            "color": 34047,              # 0x0088FF lighter blue
            "midi_out_port_index": 1,
            "midi_out_device_name": "Sequential Rev2",
        },
    ],
    "take5": [
        {
            "name": "Take5",
            "midi_channel": 4,
            "color": 10027263,           # 0x9900FF purple
            "midi_out_port_index": 2,
            "midi_out_device_name": "Sequential Take 5",
        }
    ],
    "subharmonicon": [
        {
            "name": "Subharmonicon",
            "midi_channel": 5,
            "color": 16744448,           # 0xFF8800 amber
            "midi_out_port_index": 0,
            "midi_out_device_name": "Elektron Digitakt",
            "_comment": "DIN-only — clocked via Digitakt MIDI out",
        }
    ],
    "dfam": [
        {
            "name": "DFAM",
            "midi_channel": 6,
            "color": 16728064,           # 0xFF4400 deep orange
            "midi_out_port_index": 0,
            "midi_out_device_name": "Elektron Digitakt",
            "_comment": "DIN-only — clocked via Digitakt MIDI out",
        }
    ],
    "minibrute2s": [
        {
            "name": "Minibrute2S",
            "midi_channel": 7,
            "color": 52292,              # 0x00CC44 green
            "midi_out_port_index": 3,
            "midi_out_device_name": "Arturia MiniBrute 2S",
        }
    ],
    "arturia-pigments": [
        {
            "name": "Pigments",
            "midi_channel": 8,
            "color": 16711935,           # 0xFF00FF magenta
            "_plugin": {
                "type": "vst3",
                "name": "Pigments",
                "uid": "41727475415649534B61743150726F63",
                "path": "/Library/Audio/Plug-Ins/VST3/Pigments.vst3",
                "manufacturer": "Arturia",
                "version": "5.0.3.5024",
                "sdk_version": "VST 3.7.5",
                "category": "Instrument|Synth",
            },
        }
    ],
    "analog-rytm": [
        {
            "name": "AnalogRytm",
            "midi_channel": 8,
            "color": 16744448,           # 0xFF8800 amber
            "midi_out_port_index": 4,
            "midi_out_device_name": "Elektron Analog Rytm",
        }
    ],
}

# Soft (in-box) substitutes for always-offline hardware.
_SOFT_TRACKS: dict[str, dict] = {
    "dfam": {
        "name": "DFAM-sub",
        "midi_channel": 6,
        "color": 16728064,
        "_device": {"type": "instrument", "name": "Collision"},
        "_comment": "DFAM substitute: Collision (membrane + mallet analog percussion)",
    },
    "subharmonicon": {
        "name": "SubH-sub",
        "midi_channel": 5,
        "color": 16744448,
        "_device": {"type": "instrument", "name": "Operator"},
        "_comment": "Subharmonicon substitute: Operator (FM drone, offset LFO polyrhythm)",
    },
}


def _should_use_soft_template(rig: list) -> bool:
    """Return True if all always-offline instruments are absent from the USB scan.

    Since DFAM and Subharmonicon have no USB MIDI, they are always 'no_usb_midi'
    and will never appear as online. This function returns True whenever that is
    the case — which is always — unless overridden by --no-soft.
    """
    for r in rig:
        if r["slug"] in _ALWAYS_OFFLINE_SLUGS and r["status"] == "online":
            # Somehow online (unexpected) — respect hardware, don't use soft template
            return False
    return True


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

    # Determine whether to prefer the soft (in-box) template.
    # Default: auto — use soft if DFAM/SubH are offline (they almost always are).
    # Override with --no-soft to force hardware template even when they're absent.
    use_soft = False
    if not getattr(args, "no_soft", False):
        instruments = load_instruments()
        in_ports, out_ports = scan_midi_ports()
        rig = build_rig_status(instruments, in_ports, out_ports)
        use_soft = _should_use_soft_template(rig)

    # Template resolution order:
    #   1. [song-slug]-soft.hcl   (if use_soft and file exists)
    #   2. [song-slug].hcl        (full hardware template)
    #   3. iron-static-default-soft.hcl  (generic soft fallback)
    #   4. iron-static-default.hcl       (generic hardware fallback)
    soft_template = TEMPLATES_DIR / f"{song_slug}-soft.hcl"
    hard_template = TEMPLATES_DIR / f"{song_slug}.hcl"
    default_soft  = TEMPLATES_DIR / "iron-static-default-soft.hcl"
    default_hard  = TEMPLATES_DIR / "iron-static-default.hcl"

    if use_soft and soft_template.exists():
        template = soft_template
        log.info("DFAM + Subharmonicon offline — using soft (in-box) template")
    elif hard_template.exists():
        template = hard_template
        if use_soft:
            log.warning(
                "No soft template for '%s' — using hardware template. "
                "Create ableton/templates/%s-soft.hcl to add in-box substitutes.",
                song_slug, song_slug,
            )
    elif use_soft and default_soft.exists():
        template = default_soft
        log.warning("No song template for '%s' — falling back to iron-static-default-soft.hcl", song_slug)
    else:
        template = default_hard
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
# HCL generator
# ---------------------------------------------------------------------------

def _make_clips(n: int, length: float = 4.0) -> list[dict]:
    """Generate n generic clip slot entries."""
    return [{"name": f"clip-{i}", "index": i, "length": length} for i in range(n)]


def _parse_raw_track(spec: str) -> dict:
    """
    Parse a raw track spec of the form NAME:CH or NAME:CH:COLOR.
    COLOR is a decimal or 0x-prefixed hex integer.
    """
    parts = spec.split(":")
    if len(parts) < 2:
        raise ValueError(
            f"Invalid --track spec '{spec}'. Expected NAME:CH or NAME:CH:COLOR"
        )
    name = parts[0].strip()
    try:
        ch = int(parts[1])
    except ValueError:
        raise ValueError(f"Invalid MIDI channel in track spec '{spec}'")
    color = None
    if len(parts) >= 3:
        color = int(parts[2].strip(), 0)  # handles decimal and 0x hex
    return {"name": name, "midi_channel": ch, "color": color}


def _render_hcl(
    session_name: str,
    tempo: float,
    time_sig: tuple[int, int],
    tracks: list[dict],
    file_slug: str | None = None,
) -> str:
    """Render a structured rig definition as an HCL template string."""
    slug = file_slug or session_name.lower().replace(" ", "-")
    lines: list[str] = []

    lines += [
        f"# Iron Static — {session_name} Session Template",
        f"# ableton/templates/{slug}.hcl",
        "#",
        "# Generated by: python scripts/session_init.py generate-hcl",
        "# Edit clip names, lengths, and routing as needed.",
        "#",
        "# Run with:",
        f"#   python scripts/ableton_push.py setup-rig --template ableton/templates/{slug}.hcl",
        "",
    ]

    ts_a, ts_b = time_sig
    lines += [
        "session {",
        f'  name           = "{session_name}"',
        f"  tempo          = {tempo:.1f}",
        f"  time_signature = [{ts_a}, {ts_b}]",
        "}",
        "",
    ]

    for idx, track in enumerate(tracks):
        comment  = track.get("_comment", "")
        name     = track["name"]
        ch       = track["midi_channel"]
        color    = track.get("color")
        port_idx = track.get("midi_out_port_index")
        port_nm  = track.get("midi_out_device_name")
        plugin   = track.get("_plugin")
        device   = track.get("_device")
        clips    = track.get("clips", [])

        label = f"Track {idx} — {name}"
        lines.append(f"# {label}" + (f" ({comment})" if comment else ""))
        lines.append(f'track "{name}" {{')
        lines.append(f"  midi_channel = {ch}")
        if port_idx is not None:
            lines.append(f"  midi_out_port_index  = {port_idx}")
        if port_nm:
            lines.append(f'  midi_out_device_name = "{port_nm}"')
        if color is not None:
            lines.append(f"  color = {color}")

        if plugin:
            lines.append("")
            lines.append("  plugin {")
            for k, v in plugin.items():
                lines.append(f'    {k:<14} = "{v}"')
            lines.append("  }")

        if device:
            lines.append("")
            lines.append("  device {")
            lines.append(f'    type = "{device["type"]}"')
            lines.append(f'    name = "{device["name"]}"')
            lines.append("  }")

        if clips:
            lines.append("")
            lines.append("  clips = [")
            for c in clips:
                lines.append(
                    f'    {{ name = "{c["name"]}", index = {c["index"]}, length = {c["length"]:.1f} }},'
                )
            lines.append("  ]")

        lines.append("}")
        lines.append("")

    return "\n".join(lines)


def cmd_generate_hcl(args) -> None:
    """Generate an HCL template from slug and/or raw track specs."""
    import tempfile

    instruments = load_instruments()
    all_slugs = [i["slug"] for i in instruments]
    use_soft = getattr(args, "soft", False)

    slugs_to_process: list[str]
    if getattr(args, "all", False):
        slugs_to_process = all_slugs
    else:
        slugs_to_process = list(getattr(args, "slug", []) or [])

    tracks: list[dict] = []

    for slug in slugs_to_process:
        if slug not in _SLUG_TRACKS:
            log.warning(
                "Unknown slug '%s' — skipping. Known: %s",
                slug, ", ".join(_SLUG_TRACKS),
            )
            continue
        if use_soft and slug in _SOFT_TRACKS:
            t = dict(_SOFT_TRACKS[slug])
            t["clips"] = _make_clips(args.clips, args.clip_length)
            tracks.append(t)
        else:
            for t_def in _SLUG_TRACKS[slug]:
                t = dict(t_def)
                t["clips"] = _make_clips(args.clips, args.clip_length)
                tracks.append(t)

    for spec in (getattr(args, "track", []) or []):
        try:
            t = _parse_raw_track(spec)
        except ValueError as exc:
            log.error("%s", exc)
            sys.exit(1)
        t["clips"] = _make_clips(args.clips, args.clip_length)
        tracks.append(t)

    if not tracks:
        log.error("No tracks specified. Use --slug SLUG, --track NAME:CH, or --all.")
        sys.exit(1)

    session_name = args.name
    try:
        ts_a, ts_b = (int(x) for x in args.time_sig.split("/"))
    except Exception:
        log.error(
            "Invalid time signature '%s'. Expected N/D format (e.g. 4/4, 7/8).",
            args.time_sig,
        )
        sys.exit(1)

    # Derive file slug from --out path stem or session name
    out_path = Path(args.out) if args.out else None
    file_slug = out_path.stem if out_path else session_name.lower().replace(" ", "-")

    hcl_text = _render_hcl(session_name, args.tempo, (ts_a, ts_b), tracks, file_slug)

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(hcl_text, encoding="utf-8")
        log.info("Template written to %s", out_path)
    else:
        print(hcl_text)

    if args.apply:
        # If no --out was given, write to a temp file for ableton_push.py
        if out_path:
            apply_path = out_path
            cleanup = False
        else:
            tmp = tempfile.NamedTemporaryFile(
                mode="w", suffix=".hcl", delete=False, encoding="utf-8"
            )
            tmp.write(hcl_text)
            tmp.close()
            apply_path = Path(tmp.name)
            cleanup = True
        log.info("Applying template to Ableton: %s", apply_path)
        result = subprocess.run([
            sys.executable, str(ABLETON_PUSH),
            "setup-rig", "--template", str(apply_path),
        ])
        if cleanup:
            apply_path.unlink(missing_ok=True)
        sys.exit(result.returncode)


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
    p_setup.add_argument(
        "--no-soft", action="store_true",
        help="Force hardware template even when DFAM/Subharmonicon are offline",
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

    # generate-hcl
    p_gen = sub.add_parser(
        "generate-hcl",
        help="Generate an HCL session template from instrument slugs or arbitrary tracks",
    )
    p_gen.add_argument(
        "--slug", action="append", metavar="SLUG",
        help="Instrument slug to include (repeatable). Run 'midi-map' to see known slugs.",
    )
    p_gen.add_argument(
        "--all", action="store_true",
        help="Include all instruments from database/instruments.json",
    )
    p_gen.add_argument(
        "--track", action="append", metavar="NAME:CH[:COLOR]",
        help="Arbitrary track: NAME:midi_channel[:color_int] (repeatable, not slug-based)",
    )
    p_gen.add_argument(
        "--soft", action="store_true",
        help="Substitute DFAM→Collision and Subharmonicon→Operator (in-box, no hardware needed)",
    )
    p_gen.add_argument(
        "--name", default="Iron Static Jam",
        help="Session name (default: 'Iron Static Jam')",
    )
    p_gen.add_argument(
        "--tempo", type=float, default=120.0,
        help="BPM (default: 120)",
    )
    p_gen.add_argument(
        "--time-sig", default="4/4", metavar="N/D",
        help="Time signature (default: 4/4)",
    )
    p_gen.add_argument(
        "--clips", type=int, default=2,
        help="Number of clip slots per track (default: 2)",
    )
    p_gen.add_argument(
        "--clip-length", type=float, default=4.0,
        help="Default clip length in bars (default: 4.0)",
    )
    p_gen.add_argument(
        "--out", metavar="PATH",
        help="Write HCL to this path (default: print to stdout)",
    )
    p_gen.add_argument(
        "--apply", action="store_true",
        help="Apply the generated template to the live Ableton session immediately",
    )
    p_gen.set_defaults(func=cmd_generate_hcl)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
