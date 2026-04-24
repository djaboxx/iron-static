#!/usr/bin/env python3
"""
ableton_push.py — Iron Static → Ableton Live bridge.

Talks to the IronStatic Remote Script over TCP (port 9877).
Session templates are defined in HCL; see ableton/templates/.

Usage:
    # Build the rig from an HCL template
    python scripts/ableton_push.py setup-rig --template ableton/templates/iron-static-default.hcl

    # Push a MIDI file into a specific track/clip
    python scripts/ableton_push.py push-midi --file midi/sequences/my_bass_v1.mid \\
        --track Rev2-A --clip 0

    # Fire a clip
    python scripts/ableton_push.py fire --track Digitakt --clip 0

    # Set tempo
    python scripts/ableton_push.py set-tempo --bpm 140

    # Show current session state
    python scripts/ableton_push.py status
"""

import argparse
import json
import logging
import socket
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

HOST = "localhost"
PORT = 9877


# ---------------------------------------------------------------------------
# HCL parsing
# ---------------------------------------------------------------------------

def load_hcl(path: Path) -> dict:
    """
    Parse an HCL template file and return a normalised rig definition dict.

    Returns:
        {
            "tempo": float,
            "time_signature": [int, int],
            "tracks": [
                {"name": str, "midi_channel": int, "color": int,
                 "clips": [{"index": int, "length": float, "name": str}]}
            ]
        }
    """
    try:
        import hcl2
    except ImportError:
        log.error("python-hcl2 not installed. Run: pip install python-hcl2")
        sys.exit(1)

    with path.open("r", encoding="utf-8") as f:
        raw = hcl2.load(f)

    rig = {
        "tempo": 120.0,
        "time_signature": [4, 4],
        "tracks": [],
    }

    # Parse session block
    for session_block in raw.get("session", []):
        if "tempo" in session_block:
            rig["tempo"] = float(session_block["tempo"])
        if "time_signature" in session_block:
            rig["time_signature"] = list(session_block["time_signature"])

    # Parse track blocks — hcl2 returns [{track_name: {attrs}}]
    for track_entry in raw.get("track", []):
        for track_name_raw, track_attrs in track_entry.items():
            # hcl2 preserves block-label quotes: '"Digitakt"' → 'Digitakt'
            track_name = track_name_raw.strip('"')
            # hcl2 may wrap single-block attrs in a list
            if isinstance(track_attrs, list):
                track_attrs = track_attrs[0]

            clips = []
            for clip_entry in track_attrs.get("clips", []):
                # hcl2 returns list attributes as Python lists of dicts
                if isinstance(clip_entry, dict):
                    clips.append({
                        "index": int(clip_entry.get("index", 0)),
                        "length": float(clip_entry.get("length", 4.0)),
                        "name": str(clip_entry.get("name", "clip")).strip('"'),
                    })

            # Parse color — HCL passes hex literals as ints
            color = track_attrs.get("color", None)
            if color is not None:
                color = int(color)

            rig["tracks"].append({
                "name": track_name,
                "midi_channel": int(track_attrs.get("midi_channel", 1)),
                "color": color,
                "clips": clips,
            })

    return rig


# ---------------------------------------------------------------------------
# Ableton socket client
# ---------------------------------------------------------------------------

class AbletonClient:

    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port

    def send(self, command_type: str, params: dict = None) -> dict:
        """Send a command to the IronStatic remote script and return the response."""
        payload = json.dumps({"type": command_type, "params": params or {}})
        try:
            with socket.create_connection((self.host, self.port), timeout=20.0) as sock:
                sock.sendall(payload.encode("utf-8"))
                # Read response (may arrive in chunks)
                chunks = []
                while True:
                    chunk = sock.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    try:
                        return json.loads(b"".join(chunks).decode("utf-8"))
                    except ValueError:
                        continue  # incomplete JSON, keep reading
        except ConnectionRefusedError:
            log.error(
                "Could not connect to Ableton on %s:%d — "
                "is IronStatic Remote Script loaded and Ableton running?",
                self.host, self.port
            )
            sys.exit(1)
        except socket.timeout:
            log.error("Timed out waiting for Ableton response")
            sys.exit(1)

    def require_success(self, response: dict) -> dict:
        if response.get("status") != "success":
            log.error("Ableton returned error: %s", response.get("message", "unknown"))
            sys.exit(1)
        return response["result"]


# ---------------------------------------------------------------------------
# MIDI file → note list converter
# ---------------------------------------------------------------------------

def midi_file_to_notes(midi_path: Path) -> list[dict]:
    """
    Read a .mid file and return a flat list of note dicts suitable for
    the add_notes_to_clip command.

    Notes are taken from the first non-empty track in the file.
    Timing is converted from ticks to beats.
    """
    try:
        import mido
    except ImportError:
        log.error("mido not installed. Run: pip install mido")
        sys.exit(1)

    mid = mido.MidiFile(str(midi_path))
    ticks_per_beat = mid.ticks_per_beat
    notes = []

    for track in mid.tracks:
        active: dict[int, dict] = {}
        current_tick = 0

        for msg in track:
            current_tick += msg.time
            beat = current_tick / ticks_per_beat

            if msg.type == "note_on" and msg.velocity > 0:
                active[msg.note] = {"start": beat, "velocity": msg.velocity}
            elif msg.type == "note_off" or (msg.type == "note_on" and msg.velocity == 0):
                if msg.note in active:
                    start = active.pop(msg.note)
                    notes.append({
                        "pitch": msg.note,
                        "start_time": round(start["start"], 4),
                        "duration": round(beat - start["start"], 4),
                        "velocity": start["velocity"],
                        "mute": False,
                    })

        if notes:
            break  # use first populated track

    return notes


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------

def cmd_setup_rig(args, client: AbletonClient) -> None:
    template_path = Path(args.template)
    if not template_path.exists():
        log.error("Template not found: %s", template_path)
        sys.exit(1)

    log.info("Parsing template: %s", template_path)
    rig = load_hcl(template_path)

    log.info(
        "Setting up rig: %d tracks, %.1f BPM, %d/%d",
        len(rig["tracks"]), rig["tempo"],
        rig["time_signature"][0], rig["time_signature"][1]
    )

    result = client.require_success(client.send("setup_rig", rig))
    print("\n--- RIG CONFIGURED ---")
    print("Tempo : {:.1f} BPM".format(result.get("tempo", "?")))
    print("Tracks: {}".format(result.get("tracks_configured", "?")))
    for t in result.get("tracks", []):
        print("  [{index}] {name}  (MIDI ch {midi_channel})".format(**t))


def cmd_push_midi(args, client: AbletonClient) -> None:
    midi_path = Path(args.file)
    if not midi_path.exists():
        log.error("MIDI file not found: %s", midi_path)
        sys.exit(1)

    # Resolve track index from name or integer
    track_index = _resolve_track_index(args.track, client)
    clip_index = int(args.clip)

    notes = midi_file_to_notes(midi_path)
    if not notes:
        log.error("No notes found in MIDI file: %s", midi_path)
        sys.exit(1)

    log.info("Pushing %d notes → track %d clip %d", len(notes), track_index, clip_index)
    result = client.require_success(
        client.send("add_notes_to_clip", {
            "track_index": track_index,
            "clip_index": clip_index,
            "notes": notes,
        })
    )
    print("Pushed {} notes into track {} clip {}".format(
        result.get("note_count", "?"), track_index, clip_index))


def cmd_fire(args, client: AbletonClient) -> None:
    track_index = _resolve_track_index(args.track, client)
    client.require_success(client.send("fire_clip", {
        "track_index": track_index,
        "clip_index": int(args.clip),
    }))
    print("Fired: track {} clip {}".format(track_index, args.clip))


def cmd_stop(args, client: AbletonClient) -> None:
    track_index = _resolve_track_index(args.track, client)
    client.require_success(client.send("stop_clip", {
        "track_index": track_index,
        "clip_index": int(args.clip),
    }))
    print("Stopped: track {} clip {}".format(track_index, args.clip))


def cmd_set_tempo(args, client: AbletonClient) -> None:
    result = client.require_success(client.send("set_tempo", {"tempo": float(args.bpm)}))
    print("Tempo set to {:.1f} BPM".format(result.get("tempo", args.bpm)))


def cmd_status(args, client: AbletonClient) -> None:
    result = client.require_success(client.send("get_session_info"))
    print("\n--- ABLETON SESSION ---")
    print("Tempo : {:.1f} BPM".format(result.get("tempo", "?")))
    print("Time  : {}/{}".format(
        result.get("signature_numerator", "?"),
        result.get("signature_denominator", "?")))
    print("Tracks: {}".format(result.get("track_count", "?")))
    for t in result.get("tracks", []):
        kind = "MIDI" if t.get("is_midi") else "AUDIO"
        flags = []
        if t.get("mute"):
            flags.append("muted")
        if t.get("arm"):
            flags.append("armed")
        flag_str = "  [{}]".format(", ".join(flags)) if flags else ""
        print("  [{index}] {name}  ({kind}){flags}".format(
            kind=kind, flags=flag_str, **t))


def cmd_create_track(args, client: AbletonClient) -> None:
    params = {
        "name": args.name,
        "midi_channel": int(args.midi_channel),
    }
    if args.color is not None:
        params["color"] = int(args.color)
    result = client.require_success(client.send("create_track", params))
    print("Created track [{index}] {name}  (MIDI ch {midi_channel})".format(**result))


def cmd_get_devices(args, client: AbletonClient) -> None:
    track_index = _resolve_track_index(args.track, client)
    result = client.require_success(client.send("get_track_devices", {
        "track_index": track_index,
    }))
    print("\n--- DEVICES on track: {} ---".format(result.get("track_name", track_index)))
    for d in result.get("devices", []):
        chains = "  ({} chains)".format(d["num_chains"]) if d.get("can_have_chains") else ""
        print("  [{index}] {name}  ({class_name})  {num_parameters} params{chains}".format(
            chains=chains, **d))


def cmd_get_params(args, client: AbletonClient) -> None:
    track_index = _resolve_track_index(args.track, client)
    params = {"track_index": track_index, "device_index": int(args.device)}
    if args.chain is not None:
        parts = args.chain.split(".")
        params["chain_index"] = int(parts[0])
        if len(parts) > 1:
            params["chain_device_index"] = int(parts[1])
    result = client.require_success(client.send("get_device_params", params))
    print("\n--- PARAMS: {} ({}) ---".format(
        result.get("device_name"), result.get("class_name")))
    for p in result.get("parameters", []):
        print("  [{index}] {name:<30} = {value:.4f}  (range {min:.2f}–{max:.2f})".format(**p))


def cmd_inspect_drum_rack(args, client: AbletonClient) -> None:
    track_index = _resolve_track_index(args.track, client)
    result = client.require_success(client.send("inspect_drum_rack", {
        "track_index": track_index,
        "device_index": int(args.device),
    }))
    print("\n--- DRUM RACK: {} ({}) — {} chains ---".format(
        result.get("device_name"), result.get("class_name"), result.get("num_chains")))
    NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]
    for pad in result.get("pads", []):
        note = pad.get("receiving_note")
        if note is not None:
            note_name = "{}{}".format(NOTE_NAMES[note % 12], (note // 12) - 2)
        else:
            note_name = "?"
        sample = pad.get("sample_path") or "(empty)"
        print("  chain {:>2}  note {:>3} {:4}  {:20}  {}".format(
            pad["chain_index"], note or 0, note_name, pad["name"][:20], sample))



def cmd_set_param(args, client: AbletonClient) -> None:
    track_index = _resolve_track_index(args.track, client)
    params = {
        "track_index": track_index,
        "device_index": int(args.device),
        "value": float(args.value),
    }
    if args.chain is not None:
        parts = args.chain.split(".")
        params["chain_index"] = int(parts[0])
        if len(parts) > 1:
            params["chain_device_index"] = int(parts[1])
    # param_name takes priority over param_index
    try:
        params["param_index"] = int(args.param)
    except ValueError:
        params["param_name"] = args.param
    result = client.require_success(client.send("set_device_param", params))
    print("Set [{device_name}] {param_name} = {value:.4f}".format(**result))


def cmd_fire_scene(args, client: AbletonClient) -> None:
    result = client.require_success(client.send("fire_scene", {
        "scene_index": int(args.index),
    }))
    print("Fired scene {}".format(result.get("scene_index")))


def cmd_create_scene(args, client: AbletonClient) -> None:
    params = {}
    if args.name:
        params["name"] = args.name
    if args.index is not None:
        params["index"] = int(args.index)
    result = client.require_success(client.send("create_scene", params))
    print("Created scene [{scene_index}] {name}".format(**result))


def cmd_insert_device(args, client: AbletonClient) -> None:
    track_index = _resolve_track_index(args.track, client)
    params = {
        "track_index": track_index,
        "device_name": args.device_name,
    }
    if args.target_index is not None:
        params["target_index"] = int(args.target_index)
    if args.chain is not None:
        params["chain_index"] = int(args.chain)
    result = client.require_success(client.send("insert_device", params))
    print("Inserted [{class_name}] '{device_name}' (device count: {device_count})".format(**result))


def cmd_insert_chain(args, client: AbletonClient) -> None:
    track_index = _resolve_track_index(args.track, client)
    params = {
        "track_index": track_index,
        "device_index": int(args.device),
    }
    if args.index is not None:
        params["index"] = int(args.index)
    if args.name:
        params["name"] = args.name
    result = client.require_success(client.send("insert_chain", params))
    print("Inserted chain [{chain_index}] '{chain_name}' into rack '{rack_name}' ({chain_count} chains total)".format(**result))


def cmd_build_rack(args, client: AbletonClient) -> None:
    import json as _json
    track_index = _resolve_track_index(args.track, client)
    params = {"track_index": track_index}
    if args.rack_name:
        params["rack_name"] = args.rack_name
    if args.chains:
        params["chains"] = _json.loads(args.chains)
    result = client.require_success(client.send("build_rack", params))
    print("Built rack '{}' on track '{}': {} chains created".format(
        result["rack_name"], result["track_name"], result["chains_created"]))
    for ch in result.get("chains", []):
        print("  [{chain_index}] {chain_name} — {device}".format(**ch))


def cmd_delete_device(args, client: AbletonClient) -> None:
    track_index = _resolve_track_index(args.track, client)
    params = {
        "track_index": track_index,
        "device_index": int(args.device),
    }
    if args.chain is not None:
        params["chain_index"] = int(args.chain)
    result = client.require_success(client.send("delete_device", params))
    print("Deleted '{}' from track '{}'".format(result.get("deleted"), result.get("track", args.track)))


def cmd_apply_preset(args, client: AbletonClient) -> None:
    """Read a preset JSON file and batch-push all parameters to a device.

    Preset format::

        {
          "name": "My Preset",
          "parameters": {"Param Name": value, ...},
          "chains": {
            "0": {"Res 1 Decay": 0.22, "Mallet Volume": 0.8},
            "1": {"Res 2 Tune": -24}
          }
        }

    Keys starting with "_" in chain dicts are metadata and are skipped.
    """
    with open(args.preset, "r", encoding="utf-8") as f:
        preset = json.load(f)

    track_index = _resolve_track_index(args.track, client)
    device_index = int(args.device)

    operations = []
    for param, value in preset.get("parameters", {}).items():
        operations.append({"param": param, "value": float(value)})
    for chain_str, chain_params in preset.get("chains", {}).items():
        chain_idx = int(chain_str)
        for param, value in chain_params.items():
            if param.startswith("_"):
                continue
            operations.append({
                "param": param,
                "value": float(value),
                "chain_index": chain_idx,
                "chain_device_index": 0,
            })

    if not operations:
        print("No parameters found in preset '{}'.".format(args.preset))
        return

    result = client.require_success(client.send("batch_set_device_params", {
        "track_index": track_index,
        "device_index": device_index,
        "operations": operations,
    }))
    preset_name = preset.get("name", Path(args.preset).stem)
    print("Applied {} parameters from '{}' to track '{}' device {}".format(
        result["applied"], preset_name, args.track, device_index))


def cmd_list_packs(args, client: AbletonClient) -> None:  # noqa: ARG001
    """List installed Ableton packs and optionally search for presets (.adg files)."""
    import glob as _glob
    import os
    import sqlite3

    packs_dir = os.path.expanduser("~/Music/Ableton/Packs")
    if not os.path.isdir(packs_dir):
        print("No packs directory found at", packs_dir)
        return

    packs = sorted(p for p in os.listdir(packs_dir) if os.path.isdir(os.path.join(packs_dir, p)))
    print("\n--- Installed Packs ({}) ---".format(len(packs)))
    for pack in packs:
        print("  {}".format(pack))

    if not args.search:
        print("\nTip: use --search <term> to find presets (e.g. --search 808)")
        return

    # Search the Live database for matching .adg preset names
    db_dir = os.path.expanduser("~/Library/Application Support/Ableton/Live Database")
    dbs = sorted(_glob.glob(os.path.join(db_dir, "Live-files-*.db")))
    if not dbs:
        print("Live database not found at", db_dir)
        return
    db_path = dbs[-1]  # most recent schema version

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT name FROM files WHERE name LIKE ? AND name LIKE '%.adg' ORDER BY name LIMIT 100",
        ("%{}%".format(args.search),),
    ).fetchall()
    conn.close()

    print("\n--- Presets matching '{}' ---".format(args.search))
    found_count = 0
    for (name,) in rows:
        matches = _glob.glob(os.path.join(packs_dir, "**", name), recursive=True)
        user_matches = _glob.glob(
            os.path.expanduser("~/Music/Ableton/User Library/**/{}".format(name)), recursive=True)
        all_matches = matches + user_matches
        if all_matches:
            for path in all_matches:
                rel = path.replace(packs_dir + os.sep, "").replace(
                    os.path.expanduser("~/Music/Ableton/") + os.sep, "[User] ")
                print("  {}".format(rel))
                found_count += 1
        else:
            print("  {} (indexed but not found on disk)".format(name))
    print("\n{} preset(s) found.".format(found_count))


def cmd_load_adg(args, client: AbletonClient) -> None:
    """Stage a local .adg file into the Live User Library, then load it onto a track.

    Copies the .adg to:
      ~/Music/Ableton/User Library/Presets/Instruments/Drum Rack/Iron Static/

    Then calls load-preset so Live's browser can find and load it — no dragging required.

    Example:
        python scripts/ableton_push.py load-adg \\
            --file ableton/racks/rust-protocol_corroded-v1.adg \\
            --track "Corroded Pads"
    """
    import shutil
    import os

    adg_path = Path(args.file)
    if not adg_path.exists():
        log.error("ADG file not found: %s", adg_path)
        sys.exit(1)

    user_lib = Path(os.path.expanduser(
        "~/Music/Ableton/User Library/Presets/Instruments/Drum Rack/Iron Static"
    ))
    user_lib.mkdir(parents=True, exist_ok=True)

    dest = user_lib / adg_path.name
    shutil.copy2(adg_path, dest)
    log.info("Staged '%s' → %s", adg_path.name, dest)

    # load-preset searches by name (with or without .adg extension)
    track_index = _resolve_track_index(args.track, client)
    preset_name = adg_path.stem  # strip .adg for the browser search
    result = client.require_success(client.send("load_preset", {
        "track_index": track_index,
        "preset_name": preset_name,
    }))
    print("Loaded '{}' onto track '{}'".format(result["loaded"], result["track"]))


def cmd_load_preset(args, client: AbletonClient) -> None:
    """Load a browser preset (.adg) onto a track by name — no dragging required.

    Searches Browser > Packs and User Library inside Live via the Remote Script.
    The track must already exist. Use --track to name an existing track, or pair
    with create-track to create it first.

    Example:
        python scripts/ableton_push.py load-preset \\
            --track "808 Drums" --preset "808 Depth Charger Kit"
    """
    track_index = _resolve_track_index(args.track, client)
    result = client.require_success(client.send("load_preset", {
        "track_index": track_index,
        "preset_name": args.preset,
    }))
    print("Loaded '{}' onto track '{}'".format(result["loaded"], result["track"]))


def cmd_create_clip(args, client: AbletonClient) -> None:
    """Create an empty MIDI clip in a track's clip slot.

    Must be called before push-midi when the slot is empty.
    Length is in beats (e.g. 8.0 = 2 bars at 4/4, 32.0 = 8 bars).

    Example:
        python scripts/ableton_push.py create-clip --track DFAM --clip 0 --length 32
        python scripts/ableton_push.py create-clip --track "808 Drums" --clip 0 --length 32
    """
    track_index = _resolve_track_index(args.track, client)
    result = client.require_success(client.send("create_clip", {
        "track_index": track_index,
        "clip_index": int(args.clip),
        "length": float(args.length),
    }))
    print("Created clip in track '{}' slot {} ({} beats)".format(
        args.track, args.clip, result.get("length", args.length)))


def cmd_set_clip_name(args, client: AbletonClient) -> None:
    """Name a clip in a track's clip slot.

    Example:
        python scripts/ableton_push.py set-clip-name \\
            --track DFAM --clip 0 --name "rust-protocol groove v1"
    """
    track_index = _resolve_track_index(args.track, client)
    result = client.require_success(client.send("set_clip_name", {
        "track_index": track_index,
        "clip_index": int(args.clip),
        "name": args.name,
    }))
    print("Renamed clip to '{}'".format(result.get("name", args.name)))


def _resolve_track_index(track_arg: str, client: AbletonClient) -> int:
    """Accept either an integer index or a track name string."""
    try:
        return int(track_arg)
    except ValueError:
        pass
    # Look up by name
    result = client.require_success(client.send("get_session_info"))
    for t in result.get("tracks", []):
        if t["name"].lower() == track_arg.lower():
            return t["index"]
    log.error("Track not found: %s", track_arg)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Iron Static → Ableton Live bridge (IronStatic Remote Script required)"
    )
    parser.add_argument("--host", default=HOST, help="Remote script host (default: localhost)")
    parser.add_argument("--port", type=int, default=PORT, help="Remote script port (default: 9877)")
    parser.add_argument("--quiet", "-q", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    # setup-rig
    p_rig = sub.add_parser("setup-rig", help="Build session from an HCL template")
    p_rig.add_argument("--template", required=True, help="Path to .hcl template file")

    # push-midi
    p_midi = sub.add_parser("push-midi", help="Push a .mid file into a clip")
    p_midi.add_argument("--file", required=True, help="Path to .mid file")
    p_midi.add_argument("--track", required=True, help="Track name or index")
    p_midi.add_argument("--clip", default="0", help="Clip slot index (default: 0)")

    # fire
    p_fire = sub.add_parser("fire", help="Fire a clip")
    p_fire.add_argument("--track", required=True)
    p_fire.add_argument("--clip", default="0")

    # stop
    p_stop = sub.add_parser("stop", help="Stop a clip")
    p_stop.add_argument("--track", required=True)
    p_stop.add_argument("--clip", default="0")

    # set-tempo
    p_tempo = sub.add_parser("set-tempo", help="Set session tempo")
    p_tempo.add_argument("--bpm", required=True, type=float)

    # status
    sub.add_parser("status", help="Show current session info")

    # create-track
    p_create = sub.add_parser("create-track", help="Append a new MIDI track to the session")
    p_create.add_argument("--name", required=True, help="Track name")
    p_create.add_argument("--midi-channel", type=int, default=1, help="MIDI channel (default: 1)")
    p_create.add_argument("--color", type=int, default=None, help="Track color as integer")

    # get-devices
    p_getdev = sub.add_parser("get-devices", help="List devices on a track")
    p_getdev.add_argument("--track", required=True, help="Track name or index")

    # get-params
    p_getparam = sub.add_parser("get-params", help="List parameters on a device")
    p_getparam.add_argument("--track", required=True, help="Track name or index")
    p_getparam.add_argument("--device", required=True, help="Device index")
    p_getparam.add_argument("--chain", default=None,
                            help="Chain navigation: chain_index or chain_index.device_index (e.g. 0 or 0.1)")

    # inspect-drum-rack
    p_idr = sub.add_parser("inspect-drum-rack",
                           help="List all pads in a DrumGroupDevice with sample paths")
    p_idr.add_argument("--track", required=True, help="Track name or index")
    p_idr.add_argument("--device", required=True, help="Device index (usually 0)")

    # set-param
    p_setparam = sub.add_parser("set-param", help="Set a device parameter value")
    p_setparam.add_argument("--track", required=True, help="Track name or index")
    p_setparam.add_argument("--device", required=True, help="Device index")
    p_setparam.add_argument("--param", required=True, help="Parameter name (e.g. 'Chain Selector') or index")
    p_setparam.add_argument("--value", required=True, help="Value to set")
    p_setparam.add_argument("--chain", default=None,
                            help="Chain navigation: chain_index or chain_index.device_index")

    # fire-scene
    p_fscene = sub.add_parser("fire-scene", help="Fire a scene by index")
    p_fscene.add_argument("--index", required=True, help="Scene index")

    # create-scene
    p_cscene = sub.add_parser("create-scene", help="Create a new scene")
    p_cscene.add_argument("--name", default=None, help="Scene name")
    p_cscene.add_argument("--index", type=int, default=None,
                          help="Insert position (-1 or omit to append)")

    # insert-device (Live 12.3)
    p_idev = sub.add_parser("insert-device", help="Insert a native Live device (Live 12.3+)")
    p_idev.add_argument("--track", required=True, help="Track name or index")
    p_idev.add_argument("--device-name", required=True,
                        help="Device name as shown in Live's UI (e.g. 'Collision', 'Instrument Rack')")
    p_idev.add_argument("--target-index", default=None, type=int,
                        help="Position in device chain (omit to append)")
    p_idev.add_argument("--chain", default=None, type=int,
                        help="If set, insert into this chain index of the first rack on the track")

    # insert-chain (Live 12.3)
    p_ichain = sub.add_parser("insert-chain", help="Insert a new chain into a Rack device (Live 12.3+)")
    p_ichain.add_argument("--track", required=True, help="Track name or index")
    p_ichain.add_argument("--device", required=True, type=int, help="Rack device index on the track")
    p_ichain.add_argument("--index", default=None, type=int, help="Chain position (omit to append)")
    p_ichain.add_argument("--name", default=None, help="Name for the new chain")

    # build-rack (Live 12.3)
    p_brack = sub.add_parser("build-rack", help="Create an Instrument Rack and populate chains (Live 12.3+)")
    p_brack.add_argument("--track", required=True, help="Track name or index")
    p_brack.add_argument("--rack-name", default=None, help="Name for the rack")
    p_brack.add_argument("--chains", default=None,
                         help='JSON array of chain specs: \'[{"name":"Hit","device":"Collision"}]\'')

    # delete-device
    p_deldev = sub.add_parser("delete-device", help="Delete a device from a track or rack chain")
    p_deldev.add_argument("--track", required=True, help="Track name or index")
    p_deldev.add_argument("--device", required=True, type=int, help="Device index to delete")
    p_deldev.add_argument("--chain", default=None, type=int,
                          help="If set, delete device index 0 from this chain of the rack")

    # apply-preset
    p_apreset = sub.add_parser(
        "apply-preset",
        help="Batch-push a preset JSON file to a device (one round-trip for all params)")
    p_apreset.add_argument("--track", required=True, help="Track name or index")
    p_apreset.add_argument("--device", required=True, type=int, help="Device index")
    p_apreset.add_argument("--preset", required=True,
                           help="Path to preset JSON file (instruments/<slug>/presets/<name>.json)")

    # list-packs
    p_lpacks = sub.add_parser(
        "list-packs",
        help="List installed Ableton packs and search for preset .adg files")
    p_lpacks.add_argument("--search", default=None,
                          help="Search term for preset .adg files (e.g. '808', 'Collision')")

    # load-preset
    p_lpreset = sub.add_parser(
        "load-preset",
        help="Load a browser preset (.adg) onto a track by name (no drag required)")
    p_lpreset.add_argument("--track", required=True, help="Track name or index")
    p_lpreset.add_argument("--preset", required=True,
                           help="Preset name as it appears in the browser (e.g. '808 Depth Charger Kit')")

    # load-adg: stage a local .adg into User Library then load it
    p_ladg = sub.add_parser(
        "load-adg",
        help="Copy a local .adg into the Live User Library and load it onto a track")
    p_ladg.add_argument("--file", required=True, help="Path to the .adg file (e.g. ableton/racks/foo.adg)")
    p_ladg.add_argument("--track", required=True, help="Track name or index to load onto")

    # create-clip
    p_cclip = sub.add_parser(
        "create-clip",
        help="Create an empty MIDI clip in a track slot (required before push-midi)")
    p_cclip.add_argument("--track", required=True, help="Track name or index")
    p_cclip.add_argument("--clip", default="0", help="Clip slot index (default: 0)")
    p_cclip.add_argument("--length", type=float, default=32.0,
                         help="Clip length in beats (default: 32.0 = 8 bars at 4/4)")

    # set-clip-name
    p_sclipname = sub.add_parser("set-clip-name", help="Name a clip in a track slot")
    p_sclipname.add_argument("--track", required=True, help="Track name or index")
    p_sclipname.add_argument("--clip", default="0", help="Clip slot index (default: 0)")
    p_sclipname.add_argument("--name", required=True, help="Clip name")

    args = parser.parse_args()

    if args.quiet:
        logging.disable(logging.INFO)

    client = AbletonClient(host=args.host, port=args.port)

    dispatch = {
        "setup-rig":     cmd_setup_rig,
        "push-midi":     cmd_push_midi,
        "fire":          cmd_fire,
        "stop":          cmd_stop,
        "set-tempo":     cmd_set_tempo,
        "status":        cmd_status,
        "create-track":  cmd_create_track,
        "get-devices":   cmd_get_devices,
        "get-params":       cmd_get_params,
        "inspect-drum-rack": cmd_inspect_drum_rack,
        "set-param":     cmd_set_param,
        "fire-scene":    cmd_fire_scene,
        "create-scene":  cmd_create_scene,
        "insert-device": cmd_insert_device,
        "insert-chain":  cmd_insert_chain,
        "build-rack":    cmd_build_rack,
        "delete-device": cmd_delete_device,
        "apply-preset":  cmd_apply_preset,
        "list-packs":    cmd_list_packs,
        "load-preset":   cmd_load_preset,
        "load-adg":      cmd_load_adg,
        "create-clip":   cmd_create_clip,
        "set-clip-name": cmd_set_clip_name,
    }
    # list-packs is purely local — no Live connection needed
    if args.command == "list-packs":
        cmd_list_packs(args, client=None)
        return
    dispatch[args.command](args, client)


if __name__ == "__main__":
    main()
