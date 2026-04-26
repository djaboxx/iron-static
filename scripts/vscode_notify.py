#!/usr/bin/env python3
"""
vscode_notify.py — thin CLI wrapper around iron_static.notify.

Kept for backwards-compatibility with existing shell scripts and shortcuts.
For library imports, use:  from iron_static.notify import notify, event, status
For the installed CLI, use: iron-static-notify <subcommand>
"""
from iron_static.notify import (  # noqa: F401 — re-exported for backwards compat
    health,
    notify,
    status,
    progress,
    open_file,
    event,
    main,
)

if __name__ == "__main__":
    main()

