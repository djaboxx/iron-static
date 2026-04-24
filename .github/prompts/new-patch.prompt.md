---
description: Start a new sound design session — design a patch for a specific instrument, push to hardware, then route to The Critic.
agent: The Sound Designer
tools: [codebase, editFiles, terminal, search]
argument-hint: "instrument name (e.g. take5, rev2, minibrute2s, pigments)"
---

# New Patch Workflow

Design a new preset for the instrument specified, push it to hardware, then hand off to The Critic for evaluation.

## Step 1: Load Context

Read the active song context:
- [database/songs.json](../../database/songs.json) — confirm key, scale, BPM
- [instruments/${input:instrument:take5}/presets/catalog.json](../../instruments/) — check what already exists before building something new

## Step 2: Design the Patch

Design a patch for **${input:instrument:take5}** that serves the active song's harmonic context. Follow the design philosophy in your instructions — sub weight first, dark filters, noise as instrument.

Document the patch as:
- `instruments/${input:instrument}/presets/[slug]_[name]_[key].json` with a full `nrpn_dump` array
- Add entry to `instruments/${input:instrument}/presets/catalog.json`

## Step 3: Push to Hardware

Push the preset using:
```bash
/Users/darnold/venv/bin/python3 scripts/push_preset.py \
  --preset instruments/${input:instrument}/presets/[new-preset].json \
  --port [PortName] --channel [channel]
```

Default MIDI channels: take5=4, rev2=2, minibrute2s=7, pigments=8

## Step 4: Hand Off

After confirming the push, use the **"Critique this sound"** handoff to route to The Critic.
