#!/usr/bin/env python3
"""
bridge_client.py -- IRON STATIC bridge client

Talks to the IronStatic Remote Script (TCP/JSON, port 9877) running inside Live.

Usage (CLI):
    python3 scripts/bridge_client.py ping
    python3 scripts/bridge_client.py info
    python3 scripts/bridge_client.py transport play
    python3 scripts/bridge_client.py transport stop
    python3 scripts/bridge_client.py transport tempo 95.0
    python3 scripts/bridge_client.py clip create 0 0 8.0
    python3 scripts/bridge_client.py clip clear 0 0
    python3 scripts/bridge_client.py clip write 0 0 /path/to/notes.json
    python3 scripts/bridge_client.py clip fire 0 0
    python3 scripts/bridge_client.py reporter dump

Python API:
    from scripts.bridge_client import BridgeClient
    with BridgeClient() as b:
        b.ping()
        b.transport_tempo(95.0)
        b.clip_write(track=0, slot=0, notes_path="/tmp/notes.json")

Protocol: TCP localhost:9877 -- one JSON object per connection.
  Send:    {"type": "cmd_name", "params": {...}}
  Receive: {"status": "success"|"error", "result": {...}}
"""

import argparse
import json
import logging
import socket
import sys
from pathlib import Path

log = logging.getLogger(__name__)

BRIDGE_HOST     = "127.0.0.1"
BRIDGE_PORT     = 9877
CONNECT_TIMEOUT = 5.0


def _call(cmd_type, params=None, host=BRIDGE_HOST, port=BRIDGE_PORT, timeout=CONNECT_TIMEOUT):
    """Open TCP connection, send one JSON command, read one JSON response."""
    payload = json.dumps({"type": cmd_type, "params": params or {}})
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(payload.encode("utf-8"))
        sock.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    return json.loads(b"".join(chunks).decode("utf-8"))


class BridgeClient:
    """Context-manager wrapper for IronStatic Remote Script commands."""

    def __init__(self, host=BRIDGE_HOST, port=BRIDGE_PORT, timeout=CONNECT_TIMEOUT):
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def _cmd(self, cmd_type, params=None):
        try:
            r = _call(cmd_type, params, host=self.host, port=self.port, timeout=self.timeout)
            if r.get("status") == "error":
                log.debug("bridge error [%s]: %s", cmd_type, r.get("message", ""))
            return r
        except ConnectionRefusedError:
            return {"status": "error",
                    "message": "connection refused -- is IronStatic selected as Control Surface in Live?"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def ping(self):
        return self._cmd("get_session_info").get("status") == "success"

    def get_session_info(self):
        return self._cmd("get_session_info")

    def transport_play(self):
        return self._cmd("start_playback")

    def transport_stop(self):
        return self._cmd("stop_playback")

    def transport_tempo(self, bpm):
        return self._cmd("set_tempo", {"tempo": float(bpm)})

    def clip_create(self, track, slot, length_beats):
        return self._cmd("create_clip", {
            "track_index": int(track), "clip_index": int(slot), "length": float(length_beats)})

    def clip_clear(self, track, slot):
        return self._cmd("clear_clip", {"track_index": int(track), "clip_index": int(slot)})

    def clip_write(self, track, slot, notes_path):
        p = Path(notes_path)
        if not p.exists():
            return {"status": "error", "message": f"notes file not found: {p}"}
        notes = json.loads(p.read_text()).get("notes", [])
        self.clip_clear(track, slot)
        return self._cmd("add_notes_to_clip", {
            "track_index": int(track), "clip_index": int(slot), "notes": notes})

    def clip_fire(self, track, slot):
        return self._cmd("fire_clip", {"track_index": int(track), "clip_index": int(slot)})

    def clip_stop(self, track, slot):
        return self._cmd("stop_clip", {"track_index": int(track), "clip_index": int(slot)})

    def clip_set_name(self, track, slot, name):
        return self._cmd("set_clip_name", {
            "track_index": int(track), "clip_index": int(slot), "name": name})

    def clip_notes(self, track, slot):
        return self._cmd("get_clip_notes", {"track_index": int(track), "clip_index": int(slot)})

    def clip_info(self, track, slot):
        return self._cmd("get_clip_info", {"track_index": int(track), "clip_index": int(slot)})

    def clip_find_by_name(self, name, track_name=None):
        params = {"name": name}
        if track_name:
            params["track_name"] = track_name
        return self._cmd("find_clip_by_name", params)

    def reporter_dump(self, output_path=None):
        r = self._cmd("get_session_info")
        if r.get("status") != "success":
            return r
        out = Path(output_path) if output_path else Path("outputs/live_state.json")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(r.get("result", {}), indent=2))
        return {"status": "success", "result": {"path": str(out)}}


def _print_result(r):
    if r.get("status") == "success":
        result = r.get("result", {})
        print(json.dumps(result, indent=2) if result else "ok")
    else:
        print(f"error: {r.get('message', 'unknown')}", file=sys.stderr)
        sys.exit(1)


def main():
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
    p = argparse.ArgumentParser(description="IRON STATIC bridge client")
    p.add_argument("--host",    default=BRIDGE_HOST)
    p.add_argument("--port",    type=int, default=BRIDGE_PORT)
    p.add_argument("--timeout", type=float, default=CONNECT_TIMEOUT)
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="group", required=True)

    sub.add_parser("ping")
    sub.add_parser("info")

    tp = sub.add_parser("transport")
    tp_sub = tp.add_subparsers(dest="action", required=True)
    tp_sub.add_parser("play")
    tp_sub.add_parser("stop")
    tp_sub.add_parser("tempo").add_argument("bpm", type=float)

    cl = sub.add_parser("clip")
    cl_sub = cl.add_subparsers(dest="action", required=True)
    for name, xargs in [("create", [("track",int),("slot",int),("beats",float)]),
                        ("clear",  [("track",int),("slot",int)]),
                        ("write",  [("track",int),("slot",int),("notes_file",Path)]),
                        ("fire",   [("track",int),("slot",int)]),
                        ("stop",   [("track",int),("slot",int)]),
                        ("notes",  [("track",int),("slot",int)]),
                        ("info",   [("track",int),("slot",int)])]:
        sp = cl_sub.add_parser(name)
        for a, t in xargs:
            sp.add_argument(a, type=t)
    sn = cl_sub.add_parser("set-name")
    sn.add_argument("track", type=int)
    sn.add_argument("slot",  type=int)
    sn.add_argument("name",  type=str)
    fn = cl_sub.add_parser("find")
    fn.add_argument("name", type=str)
    fn.add_argument("--on-track", default=None, metavar="TRACK_NAME")
    rp = sub.add_parser("reporter")
    rp_sub = rp.add_subparsers(dest="action", required=True)
    rp_sub.add_parser("dump").add_argument("output_file", type=Path, nargs="?")

    args = p.parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    with BridgeClient(host=args.host, port=args.port, timeout=args.timeout) as b:
        if args.group == "ping":
            ok = b.ping()
            print("ok -- Live is connected" if ok else "error -- no response")
            sys.exit(0 if ok else 1)
        elif args.group == "info":
            _print_result(b.get_session_info())
        elif args.group == "transport":
            if args.action == "play":    _print_result(b.transport_play())
            elif args.action == "stop":  _print_result(b.transport_stop())
            elif args.action == "tempo": _print_result(b.transport_tempo(args.bpm))
        elif args.group == "clip":
            if args.action == "create":   _print_result(b.clip_create(args.track, args.slot, args.beats))
            elif args.action == "clear":  _print_result(b.clip_clear(args.track, args.slot))
            elif args.action == "write":  _print_result(b.clip_write(args.track, args.slot, args.notes_file))
            elif args.action == "fire":   _print_result(b.clip_fire(args.track, args.slot))
            elif args.action == "stop":   _print_result(b.clip_stop(args.track, args.slot))
            elif args.action == "notes":    _print_result(b.clip_notes(args.track, args.slot))
            elif args.action == "info":     _print_result(b.clip_info(args.track, args.slot))
            elif args.action == "set-name": _print_result(b.clip_set_name(args.track, args.slot, args.name))
            elif args.action == "find":     _print_result(b.clip_find_by_name(args.name, getattr(args, "on_track", None)))
        elif args.group == "reporter":
            out = str(args.output_file) if getattr(args, "output_file", None) else None
            _print_result(b.reporter_dump(out))


if __name__ == "__main__":
    main()
