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

        # Brainstorm — extract working title and conceptual direction as session seed
        brainstorm_path = active.get("brainstorm_path")
        if brainstorm_path:
            bp = Path(brainstorm_path)
            if bp.exists():
                bs_text = bp.read_text()
                # Extract working title from "**Working Title:**" line in Section 1
                wt_line = next(
                    (l.strip() for l in bs_text.splitlines()
                     if "working title" in l.lower() and ":" in l),
                    None,
                )
                working_title = wt_line.split(":", 1)[-1].strip().strip('*" ') if wt_line else None
                # Extract conceptual direction — lines after "## 5. Conceptual Direction"
                concept_lines = []
                in_concept = False
                for line in bs_text.splitlines():
                    if line.strip().startswith("## 5"):
                        in_concept = True
                        continue
                    if in_concept:
                        if line.startswith("##"):
                            break
                        stripped = line.strip()
                        if stripped:
                            concept_lines.append(stripped)
                concept = " ".join(concept_lines[:3])  # first ~3 sentences

                context_lines.append("")
                context_lines.append(
                    f"ACTIVE BRAINSTORM: {bp.name}"
                    + (f" — Working Title: \"{working_title}\"" if working_title else "")
                )
                if concept:
                    context_lines.append(f"  Concept: {concept}")
                context_lines.append(
                    f"  Full brainstorm: {brainstorm_path}"
                )
                context_lines.append(
                    "  This brainstorm is the creative seed for this session. "
                    "Read it before proposing any arrangement, patch, or pattern work."
                )

        # MIDI rig scan — shows which instruments are physically connected
        try:
            import rtmidi  # type: ignore
            instruments_path = Path("database/instruments.json")
            if instruments_path.exists():
                instruments = json.loads(instruments_path.read_text())["instruments"]
                mid_in = rtmidi.MidiIn()
                mid_out = rtmidi.MidiOut()
                in_ports = mid_in.get_ports()
                out_ports = mid_out.get_ports()
                del mid_in, mid_out

                all_ports_set = set(in_ports + out_ports)
                online, offline, din_only = [], [], []
                for inst in instruments:
                    midi_usb = inst.get("midi_usb", True)
                    if not midi_usb:
                        din_only.append(inst["name"])
                        continue
                    patterns = inst.get("midi_port_patterns", [])
                    if not patterns:
                        continue
                    matched = next(
                        (p for p in all_ports_set
                         if any(pat.lower() in p.lower() for pat in patterns)),
                        None,
                    )
                    if matched:
                        online.append(inst["name"])
                    else:
                        offline.append(inst["name"])

                rig_lines = [
                    "",
                    f"MIDI RIG ({len(online)}/{len(online)+len(offline)} USB instruments online):",
                ]
                for n in online:
                    rig_lines.append(f"  ✓ {n}")
                for n in offline:
                    rig_lines.append(f"  ✗ {n}  (not detected — check USB)")
                for n in din_only:
                    rig_lines.append(f"  ~ {n}  (DIN-only)")
                context_lines += rig_lines
        except ImportError:
            pass  # rtmidi not installed; skip rig scan

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
