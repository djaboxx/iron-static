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
        for track_name, track_attrs in track_entry.items():
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
                        "name": clip_entry.get("name", "clip"),
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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

    args = parser.parse_args()

    if args.quiet:
        logging.disable(logging.INFO)

    client = AbletonClient(host=args.host, port=args.port)

    dispatch = {
        "setup-rig": cmd_setup_rig,
        "push-midi": cmd_push_midi,
        "fire": cmd_fire,
        "stop": cmd_stop,
        "set-tempo": cmd_set_tempo,
        "status": cmd_status,
    }
    dispatch[args.command](args, client)


if __name__ == "__main__":
    main()
