---
description: Build an Instrument Rack on a specified track — checks Ableton is running, builds the rack from a chain spec, then fires a status check. Auto-removes existing non-rack instruments on the track before building.
agent: The Sound Designer
tools: [terminal, search/codebase, edit/editFiles, read/problems]
argument-hint: "track name (e.g. DFAM, Pigments, Take5)"
---

# Build-Rack Workflow

Build a named Instrument Rack on the specified track with pre-configured chains. Removes any bare non-rack instruments first. Pushes to Ableton immediately — no file-only outputs.

## Step 1: Load Skills

Load both skill files before proceeding:
- [ableton-launch SKILL](./../skills/ableton-launch/SKILL.md)
- [ableton-push SKILL](./../skills/ableton-push/SKILL.md)

## Step 2: Load Context

Read active song and confirm target track:
- [database/songs.json](../../database/songs.json) — confirm active song key/scale/BPM
- Run `status` to confirm Live is running and identify the target track index:
  ```bash
  /Users/darnold/venv/bin/python3 scripts/ableton_push.py status
  ```

## Step 3: Confirm Ableton Is Running

```bash
pgrep -x "Live" > /dev/null && echo "running" || echo "not running"
```

If not running:
```bash
open -a "Ableton Live 12 Suite"
# Wait ~15s then check bridge
/Users/darnold/venv/bin/python3 scripts/ableton_push.py status
```

If the bridge isn't responding after Live is open: in Ableton → Settings → Link/Tempo/MIDI → Control Surface → deselect then reselect **IronStatic**.

## Step 4: Build the Rack

```bash
/Users/darnold/venv/bin/python3 scripts/ableton_push.py build-rack \
  --track "${input:track:DFAM}" \
  --rack-name "${input:track:DFAM} Rack" \
  --chains '${input:chains:[{"name":"Hit","device":"Collision"},{"name":"Tone","device":"Collision"},{"name":"Noise","device":"Collision"}]}'
```

**`build-rack` behavior:**
- If an Instrument Rack already exists on the track → adds the specified chains to it
- If non-rack instruments exist (e.g. a bare Collision) → **auto-deletes them** then inserts the Instrument Rack
- Only works with native Ableton devices (Live 12.3+). For VST/AU use `insert-device` into a pre-existing rack manually.

### Predefined rack specs for Iron Static:

**DFAM** — three Collision voices routed to a Chain Selector for step-sequenced percussion:
```json
[
  {"name": "Hit",   "device": "Collision"},
  {"name": "Tone",  "device": "Collision"},
  {"name": "Noise", "device": "Collision"}
]
```

**Pigments Layered** — soft + hard layers for bi-timbral use:
```json
[
  {"name": "Body",  "device": "Operator"},
  {"name": "Air",   "device": "Wavetable"}
]
```

**Percussion Rack** — typical 4-voice drum utility rack:
```json
[
  {"name": "Kick",  "device": "Collision"},
  {"name": "Snare", "device": "Collision"},
  {"name": "HH",    "device": "Collision"},
  {"name": "Perc",  "device": "Collision"}
]
```

## Step 5: Verify

Confirm the rack was built:
```bash
/Users/darnold/venv/bin/python3 scripts/ableton_push.py get-devices --track "${input:track:DFAM}"
```

Expected output for DFAM:
```
[0] DFAM Rack (InstrumentGroupDevice) N params
  chain[0] Hit   → Collision
  chain[1] Tone  → Collision
  chain[2] Noise → Collision
```

## Step 6: Hand Off (optional)

After confirming the rack is built:

- **If designing sounds for the chains** → hand off to **The Sound Designer** with: "Design a ${input:track:DFAM} chain for chain [N] in the context of the active song"
- **If wiring Chain Selector automation** → hand off to **The Live Engineer** with: "Wire Chain Selector automation on DFAM Rack chains Hit/Tone/Noise using MIDI from Digitakt ch6"
- **If evaluating the structure** → hand off to **The Critic** with: "Evaluate the DFAM Rack layout for rust-protocol"

## Notes

- `delete-device` is also available for manual cleanup:
  ```bash
  /Users/darnold/venv/bin/python3 scripts/ableton_push.py delete-device --track "DFAM" --device 0
  ```
- Chain Selector range auto-configures as 0–127 per chain (0-42=Hit, 43-85=Tone, 86-127=Noise for 3 chains)
- DFAM MIDI channel is 6 per the Iron Static default allocation
