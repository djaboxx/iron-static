---
name: analyze-ableton-logs
description: Read and analyze Ableton Live log files to diagnose Remote Script loading errors, crashes, MIDI issues, and plugin problems.
argument-hint: "[optional: filter=ironStatic|remotescript|error|crash|all (default: all)]"
user-invocable: true
disable-model-invocation: false
---

# Skill: analyze-ableton-logs

## What This Skill Does

Reads Ableton's `Log.txt` from the active version directory and surfaces:
1. IronStatic Remote Script loading status and errors
2. Any Remote Script errors (Python tracebacks)
3. MIDI device configuration messages
4. Crash or error events
5. Plugin load failures

## Log File Locations (this machine)

The active log is always in the **most recently modified** version directory:

```
~/Library/Preferences/Ableton/Live 12.2.5/Log.txt   ← active (Live 12 Suite)
~/Library/Preferences/Ableton/Live 12.2.5/User Remote Scripts/IronStatic/
```

To find the active log dynamically:
```bash
find ~/Library/Preferences/Ableton -name "Log.txt" -exec ls -lt {} + | head -3
```

## Procedure

### Step 1 — Find active log
```bash
find ~/Library/Preferences/Ableton -name "Log.txt" | xargs ls -lt | head -3
```

### Step 2 — Check IronStatic specifically
```bash
grep -i "ironStatic\|iron_static" ~/Library/Preferences/Ableton/Live\ 12.2.5/Log.txt
```

### Step 3 — Check all Remote Script activity
```bash
grep -i "remotescript\|controlsurface\|remote script" ~/Library/Preferences/Ableton/Live\ 12.2.5/Log.txt | tail -30
```

### Step 4 — Check for Python errors / tracebacks
```bash
grep -i "traceback\|error\|exception\|warning" ~/Library/Preferences/Ableton/Live\ 12.2.5/Log.txt | tail -30
```

### Step 5 — Full tail of recent log
```bash
tail -80 ~/Library/Preferences/Ableton/Live\ 12.2.5/Log.txt
```

## Common IronStatic Issues

| Symptom | Cause | Fix |
|---|---|---|
| Script not appearing in Control Surfaces | **Live 12.2+ ignores `User Remote Scripts`** — needs to be in the app bundle | Run `python scripts/deploy_remote_script.py` |
| Script in app bundle but not appearing | Missing `__init__.pyc` in folder root (not just `__pycache__/`) | Run deploy script — it handles pyc placement |
| Script appears but port 9877 fails | `grep -i "9877\|ironStatic" Log.txt` | Check for socket binding error |
| Python import error | `grep -i "traceback\|ImportError" Log.txt` | Check syntax/imports |
| Script crashes on command | `grep -i "error in client handler\|error processing" Log.txt` | Fix command handler |

## Success Indicators

When IronStatic loads correctly you'll see:
```
Python: INFO - IronStatic Remote Script initialized on port 9877
RemoteScriptMessage: IronStatic: listening on port 9877
```

## Script: Use run_in_terminal with the grep/tail commands above.
