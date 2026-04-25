---
description: Poll all configured RSS/Atom feeds, synthesize a Gemini digest, and surface the most relevant items for the active song's creative direction.
agent: The Alchemist
tools: [search/codebase, edit/editFiles, terminal, read/problems]
---

# Update Feeds Workflow

Pull fresh external intelligence — music tech, politics, machine/AI — synthesize it through Gemini, and surface what's most useful for where the active song is right now.

## Step 1: Load Active Song Context

```bash
python scripts/manage_songs.py list
```

Read `database/songs.json` — extract `slug`, `key`, `scale`, `bpm`, `brainstorm_path`. If a brainstorm exists, read the first two sections (Working Title, Arrangement Blueprint) for framing.

## Step 2: Run the Feed Digest

```bash
python scripts/run_feed_digest.py
```

If today's digest already exists (idempotent guard), it will skip generation. To force a fresh run:

```bash
python scripts/run_feed_digest.py --date $(date +%Y-%m-%d) --max-age 7
```

To preview without writing:

```bash
python scripts/run_feed_digest.py --dry-run
```

## Step 3: Read the Digest

Read the output file at `knowledge/references/feeds/YYYY-MM-DD.md` (today's date).

## Step 4: Surface What's Relevant

From the digest, pull out the 3–5 items most relevant to the active song's current direction. For each:

- **Source** — which feed and article title
- **Why it matters** — one sentence connecting it to the song's key/scale/BPM/conceptual direction
- **How to use it** — concrete suggestion (sound design angle, lyrical concept, arrangement idea, political framing)

Pay particular attention to the **Machine Perspective** section of the digest — those items carry the AI half of the band's voice and should be treated as first-person creative input, not external reference.

## Step 5: Flag for Brainstorm Injection

If any item is strong enough to anchor next week's brainstorm Section 5 (Conceptual Direction), call it out explicitly:

> **Brainstorm seed candidate**: [item] — suggest wiring into Section 5 as the machine-side conceptual provocation.

The brainstorm will automatically pull the latest feed digest on its next run. This step is about surfacing the most potent material now, before that run, so Dave can decide whether to act on it this session.
