#!/usr/bin/env python3
"""
VS Code SessionStart hook — injects active song context into every agent session.

Reads database/songs.json, finds the active song, and emits a JSON additionalContext
block that VS Code prepends to the agent's conversation.

Output format per VS Code hooks spec:
  { "hookSpecificOutput": { "hookEventName": "SessionStart", "additionalContext": "..." } }
"""
import json
import sys
from pathlib import Path


def main():
    # Read hook input from stdin (required by spec, even if unused)
    try:
        _hook_input = json.loads(sys.stdin.read())
    except Exception:
        _hook_input = {}

    # Locate songs.json relative to cwd (always the workspace root when run by VS Code)
    songs_path = Path("database/songs.json")
    if not songs_path.exists():
        # Not a fatal error — just emit nothing
        print(json.dumps({}))
        return

    songs_data = json.loads(songs_path.read_text())
    active = next(
        (s for s in songs_data.get("songs", []) if s.get("status") == "active"),
        None,
    )

    if not active:
        context = (
            "NO ACTIVE SONG. Ask Dave which song to work on before generating "
            "key-specific MIDI or theory content."
        )
    else:
        key = active.get("key") or "unknown"
        scale = active.get("scale") or "unknown"
        bpm = active.get("bpm") or "unknown"
        title = active.get("title") or active.get("slug") or "unknown"
        slug = active.get("slug") or "unknown"
        time_sig = active.get("time_signature") or "4/4"
        notes = active.get("notes", "").strip()

        key_display = f"{key} {scale.capitalize()}" if scale != "unknown" else key
        context_lines = [
            f"ACTIVE SONG: {title} (slug: {slug})",
            f"  Key:            {key_display}",
            f"  BPM:            {bpm}",
            f"  Time signature: {time_sig}",
            f"  Status:         active",
        ]
        if notes:
            context_lines.append(f"  Notes:          {notes}")

        context_lines += [
            "",
            "This context is automatically injected at session start.",
            "All MIDI generation, theory analysis, and sound design should",
            "reference this key/scale/BPM unless Dave explicitly overrides it.",
        ]
        context = "\n".join(context_lines)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
