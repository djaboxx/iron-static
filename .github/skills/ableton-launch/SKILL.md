---
name: ableton-launch
description: Check whether Ableton Live is running and open it if not. Always run this before any ableton-push commands.
argument-hint: "[optional: version=10|12 (default: 12)]"
user-invocable: true
disable-model-invocation: false
---

# Skill: ableton-launch

## What This Skill Does

Ensures Ableton Live is running before any session or bridge work begins.
- Checks for a running `Live` process
- Opens the correct version if not running
- Waits briefly for it to be ready

## When to Use

- Any time the user asks to open, launch, or start Ableton
- Before running any `ableton-push` commands (setup-rig, push-midi, fire, etc.)
- At the start of a session when it's unclear if Live is open

## Installed Versions (this machine)

| Version | App Name |
|---|---|
| 12 (default) | `Ableton Live 12 Suite` |
| 10 | `Ableton Live 10 Suite` |

## Procedure

### Step 1 — Check if already running
```bash
pgrep -x "Live" > /dev/null && echo "running" || echo "not running"
```

### Step 2 — Open if not running
```bash
# Default (Live 12)
open -a "Ableton Live 12 Suite"

# Specific version
open -a "Ableton Live 10 Suite"
```

### Step 3 — Confirm
```bash
pgrep -x "Live" > /dev/null && echo "already_running" || echo "launched"
```

> After launching, wait ~10–15 seconds before running `ableton_push.py` commands —
> Live takes time to load and register the IronStatic Remote Script.

## Notes

- If the IronStatic Remote Script is installed, it will activate automatically when Live loads
- Run `python scripts/ableton_push.py status` to confirm the Remote Script bridge is ready
- Do not run both AbletonMCP and IronStatic Remote Scripts simultaneously — both use port 9877
