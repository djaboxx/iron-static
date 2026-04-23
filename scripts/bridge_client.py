#!/usr/bin/env python3
"""
bridge_client.py — IRON STATIC bridge command-line client and Python API

Sends OSC commands to iron-static-bridge.amxd running in Ableton Live,
listens on :7401 for responses.

Usage (CLI):
    python3 scripts/bridge_client.py ping
    python3 scripts/bridge_client.py transport play
    python3 scripts/bridge_client.py transport stop
    python3 scripts/bridge_client.py transport tempo 95.0
    python3 scripts/bridge_client.py scene fire 0
    python3 scripts/bridge_client.py clip create 0 0 8.0
    python3 scripts/bridge_client.py clip clear 0 0
    python3 scripts/bridge_client.py clip write 0 0 /path/to/notes.json
    python3 scripts/bridge_client.py clip append 0 0 /path/to/notes.json
    python3 scripts/bridge_client.py reporter dump
    python3 scripts/bridge_client.py reporter dump /path/to/output.json

Python API:
    from scripts.bridge_client import BridgeClient
    with BridgeClient() as b:
        b.ping()
        b.transport_tempo(95.0)
        b.clip_write(track=0, slot=0, notes_path="/tmp/notes.json")

Notes JSON format:
    {
      "notes": [
        {"pitch": 60, "start_time": 0.0, "duration": 0.25, "velocity": 100, "mute": 0},
        ...
      ]
    }
"""

import argparse
import json
import logging
import socket
import sys
import time
from pathlib import Path

from pythonosc import udp_client, dispatcher, osc_server
from pythonosc.osc_message_builder import OscMessageBuilder

log = logging.getLogger(__name__)

BRIDGE_HOST   = "127.0.0.1"
BRIDGE_TX_PORT = 7400   # we send to the bridge on this port
BRIDGE_RX_PORT = 7401   # bridge sends responses here
RESPONSE_TIMEOUT = 3.0  # seconds


# ---------------------------------------------------------------------------
# Low-level send/receive
# ---------------------------------------------------------------------------

def _send_osc(address: str, *args, host: str = BRIDGE_HOST, port: int = BRIDGE_TX_PORT):
    """Send a single OSC message to the bridge."""
    client = udp_client.SimpleUDPClient(host, port)
    client.send_message(address, list(args))
    log.debug("sent %s %s", address, args)


def _send_and_wait(address: str, *args, timeout: float = RESPONSE_TIMEOUT) -> dict:
    """
    Send OSC command and block until /ok or /error response arrives.
    Returns {"status": "ok"|"error", "address": str, "message": str|None}.
    """
    result = {}

    disp = dispatcher.Dispatcher()

    def _on_ok(addr, *a):
        result["status"]  = "ok"
        result["address"] = a[0] if a else address

    def _on_error(addr, *a):
        result["status"]  = "error"
        result["address"] = a[0] if a else address
        result["message"] = a[1] if len(a) > 1 else ""

    def _on_pong(addr, *a):
        result["status"]  = "ok"
        result["address"] = "/pong"

    disp.map("/ok",    _on_ok)
    disp.map("/error", _on_error)
    disp.map("/pong",  _on_pong)

    server = osc_server.ThreadingOSCUDPServer((BRIDGE_HOST, BRIDGE_RX_PORT), disp)
    server.timeout = timeout

    # Send the command
    _send_osc(address, *args)

    # Wait for response
    deadline = time.time() + timeout
    while not result and time.time() < deadline:
        server.handle_request()

    server.server_close()

    if not result:
        result = {"status": "timeout", "address": address, "message": "no response"}

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class BridgeClient:
    """
    Context-manager wrapper for iron-static-bridge commands.

    with BridgeClient() as b:
        b.ping()
        b.transport_tempo(95.0)
        b.clip_write(track=0, slot=0, notes_path="outputs/notes.json")
    """

    def __init__(self, host: str = BRIDGE_HOST, port: int = BRIDGE_TX_PORT,
                 timeout: float = RESPONSE_TIMEOUT):
        self.host    = host
        self.port    = port
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def _cmd(self, address: str, *args) -> dict:
        r = _send_and_wait(address, *args, timeout=self.timeout)
        if r["status"] == "error":
            log.error("bridge error [%s]: %s", address, r.get("message", ""))
        elif r["status"] == "timeout":
            log.warning("bridge timeout: no response to %s", address)
        return r

    # Transport

    def ping(self) -> bool:
        return self._cmd("/ping")["status"] == "ok"

    def transport_play(self) -> dict:
        return self._cmd("/transport/play")

    def transport_stop(self) -> dict:
        return self._cmd("/transport/stop")

    def transport_tempo(self, bpm: float) -> dict:
        return self._cmd("/transport/tempo", float(bpm))

    # Scenes

    def scene_fire(self, index: int) -> dict:
        return self._cmd("/scene/fire", int(index))

    # Clips

    def clip_create(self, track: int, slot: int, length_beats: float) -> dict:
        return self._cmd("/clip/create", int(track), int(slot), float(length_beats))

    def clip_clear(self, track: int, slot: int) -> dict:
        return self._cmd("/clip/clear", int(track), int(slot))

    def clip_write(self, track: int, slot: int, notes_path: str) -> dict:
        """Replace all notes in clip from a JSON file."""
        return self._cmd("/clip/write", int(track), int(slot), str(notes_path))

    def clip_append(self, track: int, slot: int, notes_path: str) -> dict:
        """Append notes to clip from a JSON file."""
        return self._cmd("/clip/append", int(track), int(slot), str(notes_path))

    # Reporter

    def reporter_dump(self, output_path: str | None = None) -> dict:
        if output_path:
            return self._cmd("/reporter/dump", str(output_path))
        return self._cmd("/reporter/dump")


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------

def _require_args(parsed, names: list[str]):
    for name in names:
        if getattr(parsed, name, None) is None:
            log.error("missing required argument: %s", name)
            sys.exit(1)


def _print_result(r: dict):
    status = r.get("status", "?")
    if status == "ok":
        print(f"ok  {r.get('address', '')}")
    elif status == "error":
        print(f"error  {r.get('address', '')}  {r.get('message', '')}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"timeout — no response from bridge (is iron-static-bridge.amxd loaded in Live?)",
              file=sys.stderr)
        sys.exit(2)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

    p = argparse.ArgumentParser(
        description="IRON STATIC bridge client — sends OSC commands to Ableton Live",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    p.add_argument("--host",    default=BRIDGE_HOST,    help="bridge host (default: 127.0.0.1)")
    p.add_argument("--tx-port", type=int, default=BRIDGE_TX_PORT, help="bridge receive port (default: 7400)")
    p.add_argument("--timeout", type=float, default=RESPONSE_TIMEOUT, help="response timeout in seconds")
    p.add_argument("-v", "--verbose", action="store_true")

    sub = p.add_subparsers(dest="group", required=True)

    # ping
    sub.add_parser("ping", help="check if bridge is alive")

    # transport
    tp = sub.add_parser("transport", help="transport commands")
    tp_sub = tp.add_subparsers(dest="action", required=True)
    tp_sub.add_parser("play")
    tp_sub.add_parser("stop")
    tp_tempo = tp_sub.add_parser("tempo")
    tp_tempo.add_argument("bpm", type=float)

    # scene
    sc = sub.add_parser("scene", help="scene commands")
    sc_sub = sc.add_subparsers(dest="action", required=True)
    sc_fire = sc_sub.add_parser("fire")
    sc_fire.add_argument("index", type=int)

    # clip
    cl = sub.add_parser("clip", help="clip commands")
    cl_sub = cl.add_subparsers(dest="action", required=True)

    cl_create = cl_sub.add_parser("create")
    cl_create.add_argument("track", type=int)
    cl_create.add_argument("slot",  type=int)
    cl_create.add_argument("beats", type=float)

    cl_clear = cl_sub.add_parser("clear")
    cl_clear.add_argument("track", type=int)
    cl_clear.add_argument("slot",  type=int)

    cl_write = cl_sub.add_parser("write")
    cl_write.add_argument("track", type=int)
    cl_write.add_argument("slot",  type=int)
    cl_write.add_argument("notes_file", type=Path)

    cl_append = cl_sub.add_parser("append")
    cl_append.add_argument("track", type=int)
    cl_append.add_argument("slot",  type=int)
    cl_append.add_argument("notes_file", type=Path)

    # reporter
    rp = sub.add_parser("reporter", help="session state reporter")
    rp_sub = rp.add_subparsers(dest="action", required=True)
    rp_dump = rp_sub.add_parser("dump")
    rp_dump.add_argument("output_file", type=Path, nargs="?",
                          help="override output path (default: outputs/live_state.json)")

    args = p.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    with BridgeClient(host=args.host, port=args.tx_port, timeout=args.timeout) as b:

        if args.group == "ping":
            _print_result(b._cmd("/ping"))

        elif args.group == "transport":
            if args.action == "play":
                _print_result(b.transport_play())
            elif args.action == "stop":
                _print_result(b.transport_stop())
            elif args.action == "tempo":
                _print_result(b.transport_tempo(args.bpm))

        elif args.group == "scene":
            if args.action == "fire":
                _print_result(b.scene_fire(args.index))

        elif args.group == "clip":
            if args.action == "create":
                _print_result(b.clip_create(args.track, args.slot, args.beats))
            elif args.action == "clear":
                _print_result(b.clip_clear(args.track, args.slot))
            elif args.action == "write":
                if not args.notes_file.exists():
                    print(f"error: notes file not found: {args.notes_file}", file=sys.stderr)
                    sys.exit(1)
                _print_result(b.clip_write(args.track, args.slot, str(args.notes_file.resolve())))
            elif args.action == "append":
                if not args.notes_file.exists():
                    print(f"error: notes file not found: {args.notes_file}", file=sys.stderr)
                    sys.exit(1)
                _print_result(b.clip_append(args.track, args.slot, str(args.notes_file.resolve())))

        elif args.group == "reporter":
            if args.action == "dump":
                path = str(args.output_file.resolve()) if args.output_file else None
                _print_result(b.reporter_dump(path))


if __name__ == "__main__":
    main()
