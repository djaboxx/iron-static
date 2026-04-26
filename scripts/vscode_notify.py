#!/usr/bin/env python3
"""
vscode_notify.py — push notifications and status updates into VS Code
via the IRON STATIC VS Code Bridge extension (port 9880).

Usage:
    python scripts/vscode_notify.py notify "Brainstorm complete" --level info
    python scripts/vscode_notify.py status "Brainstorm done" --color green
    python scripts/vscode_notify.py progress --id my-task --title "GCS Push" --percent 50
    python scripts/vscode_notify.py progress --id my-task --title "GCS Push" --done
    python scripts/vscode_notify.py open /path/to/file.py --line 42
    python scripts/vscode_notify.py health

Can also be imported and used as a library:
    from scripts.vscode_notify import notify, status, open_file
"""

import argparse
import json
import logging
import sys
import urllib.request
import urllib.error

log = logging.getLogger(__name__)

BRIDGE_PORT = 9880
BASE_URL = f"http://127.0.0.1:{BRIDGE_PORT}"


def _post(endpoint: str, payload: dict) -> dict:
    """POST JSON to the VS Code bridge. Returns parsed response or raises."""
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE_URL}{endpoint}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        log.warning("VS Code bridge unreachable (%s) — skipping notification", e)
        return {"ok": False, "error": str(e)}


def health() -> dict:
    """Check if the VS Code bridge is running."""
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health", timeout=3) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        return {"ok": False, "error": str(e)}


def notify(
    message: str,
    level: str = "info",
    actions: list[str] | None = None,
) -> dict:
    """Show a VS Code notification."""
    return _post("/notify", {"message": message, "level": level, "actions": actions or []})


def status(
    text: str,
    tooltip: str | None = None,
    color: str | None = None,
) -> dict:
    """Update the IRON STATIC status bar item in VS Code."""
    payload: dict = {"text": text}
    if tooltip:
        payload["tooltip"] = tooltip
    if color:
        payload["color"] = color
    return _post("/status", payload)


def progress(
    task_id: str,
    title: str,
    percent: int | None = None,
    done: bool = False,
    message: str | None = None,
) -> dict:
    """Create or update a progress notification in VS Code."""
    payload: dict = {"id": task_id, "title": title, "done": done}
    if percent is not None:
        payload["percent"] = percent
    if message:
        payload["message"] = message
    return _post("/progress", payload)


def open_file(path: str, line: int | None = None) -> dict:
    """Open a file in VS Code, optionally at a specific line."""
    payload: dict = {"path": path}
    if line is not None:
        payload["line"] = line
    return _post("/open", payload)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(
        description="Push notifications into VS Code via the IRON STATIC Bridge extension."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # health
    sub.add_parser("health", help="Check if the VS Code bridge is running.")

    # notify
    p_notify = sub.add_parser("notify", help="Show a VS Code notification.")
    p_notify.add_argument("message")
    p_notify.add_argument("--level", choices=["info", "warn", "error"], default="info")
    p_notify.add_argument("--actions", nargs="*", default=[])

    # status
    p_status = sub.add_parser("status", help="Update the VS Code status bar.")
    p_status.add_argument("text")
    p_status.add_argument("--tooltip")
    p_status.add_argument("--color", choices=["green", "yellow", "red", "blue"])

    # progress
    p_progress = sub.add_parser("progress", help="Show/update a progress notification.")
    p_progress.add_argument("--id", required=True)
    p_progress.add_argument("--title", required=True)
    p_progress.add_argument("--percent", type=int)
    p_progress.add_argument("--done", action="store_true")
    p_progress.add_argument("--message")

    # open
    p_open = sub.add_parser("open", help="Open a file in VS Code.")
    p_open.add_argument("path")
    p_open.add_argument("--line", type=int)

    args = parser.parse_args()

    if args.cmd == "health":
        result = health()
    elif args.cmd == "notify":
        result = notify(args.message, args.level, args.actions)
    elif args.cmd == "status":
        result = status(args.text, args.tooltip, args.color)
    elif args.cmd == "progress":
        result = progress(args.id, args.title, args.percent, args.done, args.message)
    elif args.cmd == "open":
        result = open_file(args.path, args.line)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("ok") else 1)


if __name__ == "__main__":
    main()
