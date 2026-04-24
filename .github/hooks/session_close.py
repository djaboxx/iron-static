#!/usr/bin/env python3
"""
VS Code Stop hook — reminds about session summarizer at end of every agent session.

Emits a systemMessage (non-blocking) so it shows in chat without stopping the agent.
"""
import json
import sys


def main():
    try:
        hook_input = json.loads(sys.stdin.read())
    except Exception:
        hook_input = {}

    # Don't fire if we're already in a stop-hook continuation loop
    if hook_input.get("stop_hook_active"):
        print(json.dumps({}))
        return

    output = {
        "systemMessage": (
            "Session ended. "
            "Run `gh workflow run session-summarizer.yml` to commit session notes to knowledge/sessions/. "
            "Or use /session-close to evaluate and summarize this session."
        )
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
