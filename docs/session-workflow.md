# IRON STATIC — Session Workflow

> The complete guide to how a session begins, how the brainstorm drives the week, and how the agent stack orchestrates creative work.

---

## Table of Contents

1. [Monday Morning: The Full Startup Sequence](#monday-morning-the-full-startup-sequence)
2. [The Brainstorm: Weekly Creative Seed](#the-brainstorm-weekly-creative-seed)
3. [Session Initialization Script](#session-initialization-script)
4. [The Agent Stack](#the-agent-stack)
5. [Song Lifecycle](#song-lifecycle)
6. [Session Context Hook](#session-context-hook)
7. [MIDI Channel Map](#midi-channel-map)

---

## Monday Morning: The Full Startup Sequence

This is the intended flow every time you sit down to work.

```
1. Generate or review the brainstorm
2. Scan the rig
3. Wire up Ableton
4. Open VS Code → session context fires automatically
5. Run /session-start → The Producer reads the brainstorm and proposes 3 actions
6. Pick one → Producer dispatches the right workflow
```

### Step-by-step

**1. Generate the week's brainstorm** (if you haven't already):
```bash
python scripts/run_brainstorm.py
```
This calls the Gemini API, writes `knowledge/brainstorms/YYYY-MM-DD.md`, and auto-registers `brainstorm_path` on the active song in `database/songs.json`.

If you want to manually point the active song at an existing brainstorm:
```bash
python scripts/manage_songs.py set-brainstorm --path knowledge/brainstorms/2026-04-24.md
```

**2. Scan the rig:**
```bash
python scripts/session_init.py scan
```
Reports which instruments are detected on USB MIDI and which are DIN-only.

**3. Wire up Ableton:**
```bash
python scripts/session_init.py setup
```
Runs the scan, then calls `ableton_push.py setup-rig` with the active song's HCL template (falls back to `iron-static-default.hcl` if none exists).

**4. Open VS Code.** The session context hook fires automatically when Copilot starts. You'll see:
- Active song (key, scale, BPM, status)
- Active brainstorm (working title + concept summary)
- MIDI rig status (which instruments are online)

**5. Run `/session-start` in Copilot chat.** The Producer reads the full brainstorm first, runs `song-review`, and presents exactly 3 prioritized actions tied to specific brainstorm sections.

**6. Pick an action.** The Producer dispatches the appropriate workflow.

---

## The Brainstorm: Weekly Creative Seed

The brainstorm is a Gemini-generated document that seeds the week's creative direction. It is the canonical creative reference — every agent reads it before proposing anything.

### File location
```
knowledge/brainstorms/YYYY-MM-DD.md
```

### Format (5 sections)

| Section | Content |
|---|---|
| **1. Song Idea** | Working title, mood, key, BPM, instruments, unexpected element |
| **2. Arrangement Blueprint** | Per-section breakdown: bars, instruments, energy level, transition |
| **3. Sound Design Challenge** | Target sound + 3 starting-point parameters for a named instrument |
| **4. Rhythm Pattern** | Step sequence or polyrhythm description, Digitakt-compatible |
| **5. Conceptual Direction** | 2–3 sentences on the theme, the soul of the idea |

### How it propagates

| Where | What it does |
|---|---|
| `database/songs.json` | `brainstorm_path` field on the active song points to the file |
| `session_context.py` hook | Extracts working title + concept, injects into every session at startup |
| `/session-start` prompt | Step 0: reads and surfaces all 5 sections as creative constraints |
| `The Producer` agent | Reads brainstorm before every workflow (`theory-to-hardware`, `patch-and-critique`, `song-review`) |
| `run_brainstorm.py` | Auto-registers `brainstorm_path` on the active song after generation |

### Generating a brainstorm
```bash
python scripts/run_brainstorm.py
```
Requires `GOOGLE_API_KEY` in your environment (Gemini API).

### Manually linking an existing brainstorm
```bash
python scripts/manage_songs.py set-brainstorm --path knowledge/brainstorms/2026-04-24.md
# For a specific song (not the active one):
python scripts/manage_songs.py set-brainstorm --slug my-song --path knowledge/brainstorms/2026-04-24.md
```

---

## Session Initialization Script

`scripts/session_init.py` — four subcommands for rig startup.

### `scan` — MIDI rig status

```bash
python scripts/session_init.py scan
python scripts/session_init.py scan --json   # machine-readable for the session hook
```

Reports:
- `✓` — instrument detected on USB MIDI
- `✗` — instrument not detected (check USB cable / power)
- `~` — DIN-only (no USB MIDI by design — Subharmonicon, DFAM, Pigments)

### `setup` — wire Ableton session

```bash
python scripts/session_init.py setup
python scripts/session_init.py setup --song rust-protocol   # override active song
```

1. Runs `scan`
2. Resolves the active song's HCL template (`ableton/templates/<slug>-rig.hcl` or `iron-static-default.hcl`)
3. Calls `ableton_push.py setup-rig` to configure the Live session

### `add-instrument` — append a track mid-session

```bash
python scripts/session_init.py add-instrument --slug take5
python scripts/session_init.py add-instrument --slug rev2 --track-name "Rev2-Lead"
```

Adds a MIDI track to the live Ableton session via the IronStatic Remote Script (`create_track` command). Uses `instruments.json` for MIDI channel and default track name.

### `midi-map` — print the channel allocation table

```bash
python scripts/session_init.py midi-map
```

Prints the full channel map with live connection status next to each instrument.

---

## The Agent Stack

Four specialized personas + one orchestrating meta-agent. Switch in VS Code's Chat agents dropdown.

### The Producer (`@the-producer`)

The entry point for every session. **Always start here.**

- Reads `brainstorm_path` and the brainstorm file first
- Runs agents sequentially and passes context between them
- Never skips The Critic

**Workflows:**

| Workflow | What it does |
|---|---|
| `theory-to-hardware` | Full chain: Theorist → Arranger → Sound Designer → Critic |
| `patch-and-critique [instrument]` | Focused loop: Sound Designer → Critic → Sound Designer (revise) |
| `song-review` | Arranger + Critic assess current state, Producer proposes next 3 actions |

**How to invoke:**
```
@the-producer theory-to-hardware
@the-producer patch-and-critique minibrute2s
@the-producer song-review
```

Or just run `/session-start` — the Producer does `song-review` automatically and presents options.

### The Arranger (`@the-arranger`)

Song structure, section design, and energy arc. Read-only. Measures everything against the brainstorm's arrangement blueprint.

### The Sound Designer (`@the-sound-designer`)

Presets, synthesis, MIDI generation, and hardware push. Full terminal access. Can push directly to instruments and trigger GitHub Actions workflows.

### The Theorist (`@the-theorist`)

Music theory grounded in the IRON STATIC rig and aesthetic. Scales, modes, chord vocabulary, rhythmic structures — always expressed in terms of physical instruments.

### The Critic (`@the-critic`)

Evaluation only. No knowledge of how things were made — only whether they work. Always the final step in any Producer workflow.

### `/session-start` prompt

The structured Monday morning entry point. Runs as The Producer:
1. **Step 0**: Read brainstorm in full, extract all 5 sections
2. **Step 1**: Dispatch Arranger + Critic for `song-review` against the brainstorm
3. **Step 2**: Present exactly 3 prioritized actions tied to brainstorm sections

---

## Song Lifecycle

Songs are tracked in `database/songs.json`. One song is `active` at a time — all agents use it for key/scale/BPM context.

```
in-progress → active → released → archived
```

```bash
# Add a new song
python scripts/manage_songs.py add --slug my-song --title "My Song" --key E --scale phrygian --bpm 138

# Activate a song (makes it the context for all agents)
python scripts/manage_songs.py activate --slug my-song

# List all songs
python scripts/manage_songs.py list

# Link a brainstorm
python scripts/manage_songs.py set-brainstorm --path knowledge/brainstorms/2026-04-24.md

# Mark released
python scripts/manage_songs.py release --slug my-song
```

---

## Session Context Hook

`.github/hooks/session_context.py` fires when Copilot initializes. It injects three blocks into every session's `additionalContext`:

**Active Song:**
```
ACTIVE SONG: Rust Protocol (slug: rust-protocol)
  Key:            A Phrygian
  BPM:            95.0
  Time signature: 4/4
  Status:         active
```

**Active Brainstorm:**
```
ACTIVE BRAINSTORM: 2026-04-24.md — Working Title: "Tetanus Pulse"
  Concept: [first 3 sentences of Section 5]
  Full brainstorm: knowledge/brainstorms/2026-04-24.md
  This brainstorm is the creative seed for this session. Read it before
  proposing any arrangement, patch, or pattern work.
```

**MIDI Rig:**
```
MIDI RIG (4/5 USB instruments online):
  ✓ Elektron Digitakt MK1
  ✓ Sequential Rev2
  ✗ Sequential Take 5  (not detected — check USB)
  ✓ Arturia Minibrute 2S
  ~ Moog Subharmonicon  (DIN-only)
  ~ Moog DFAM  (DIN-only)
  ~ Arturia Pigments  (software)
```

This context is available to Copilot without any manual input from Dave.

---

## MIDI Channel Map

Default allocation — reflects `database/instruments.json`.

| Channel | Instrument | Notes |
|---|---|---|
| 1 | Elektron Digitakt MK1 | Auto-channel (pattern send) |
| 2 | Sequential Rev2 — Layer A | |
| 3 | Sequential Rev2 — Layer B | |
| 4 | Sequential Take 5 | |
| 5 | Moog Subharmonicon | DIN via Digitakt MIDI out |
| 6 | Moog DFAM | DIN via Digitakt MIDI out |
| 7 | Arturia Minibrute 2S | |
| 8 | Arturia Pigments | Software |
| 9–15 | Reserved | Future instruments / soft synths |
| 16 | Global clock / transport | |
