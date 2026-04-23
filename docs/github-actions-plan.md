# IRON STATIC — GitHub Actions Automation Plan

**Goal**: Use scheduled GitHub Actions workflows to keep Copilot's creative context fresh, generate new musical ideas automatically, evolve patterns, and update the repo — even between sessions. Gemini API is integrated as a primary AI engine for scheduled work, freeing up GitHub Copilot quota for interactive studio sessions.

---

## Design Principles

1. **Commit-back automation**: Every workflow that generates content writes it as a real file and commits it back to the repo — so it's there when a session starts.
2. **Idempotent runs**: Re-running any workflow should not duplicate content. Files are dated or content-addressed.
3. **Gemini-first for scheduled work**: GitHub Copilot is reserved for interactive sessions. Gemini (`gemini-2.5-pro` or `gemini-2.0-flash`) handles all scheduled/background tasks.
4. **Context-aware generation**: Every workflow reads the repo's current state before generating anything — band aesthetic, active song, current scale, existing patterns. Outputs should feel like they belong to IRON STATIC.
5. **No secrets in repo**: All API keys stored as GitHub repository secrets.
6. **Manual override**: Every scheduled workflow also has `workflow_dispatch` so it can be triggered on demand from the GitHub UI or CLI.

---

## Secrets Required

| Secret Name | Value | Used By |
|---|---|---|
| `GEMINI_API_KEY` | Google AI Studio API key | All Gemini-powered workflows |
| `GH_PAT` | Personal Access Token (repo write scope) | Commit-back operations |

Set these at: `https://github.com/djaboxx/iron-static/settings/secrets/actions`

---

## Workflow Catalog

### 1. `weekly-brainstorm.yml` — Weekly Creative Session Notes
**Schedule**: Every Monday at 09:00 UTC (`0 9 * * 1`)  
**Trigger also**: `workflow_dispatch`

**What it does**:
1. Reads `knowledge/band-lore/manifesto.md` + active song context from `database/songs.json` (active entry) + `outputs/clips.csv` if present
2. Sends a structured prompt to Gemini: "You are the machine half of IRON STATIC. Given this band's aesthetic and current work, generate 3 original musical ideas. For each: give a concept title, describe the intended texture and instrumentation using only instruments from this rig, suggest a scale/mode, a BPM range, a rough time signature, and a 2-bar melodic/rhythmic concept."
3. Writes output to `knowledge/brainstorms/YYYY-MM-DD.md`
4. Commits with message: `chore(brainstorm): weekly ideas [automated]`

**Output example**: `knowledge/brainstorms/2026-04-28.md`

**Why it matters**: Every Monday there's a new starting point waiting. Creative block is not a problem if there's always a list of concrete, rig-specific ideas to react to.

---

### 2. `session-summarizer.yml` — Live Set State Digest
**Schedule**: Triggered on push when `outputs/live_state.json` changes  
**Trigger also**: `workflow_dispatch`

**What it does**:
1. Reads the newly pushed `outputs/live_state.json`
2. Sends to Gemini with context: "Analyze this Ableton Live session state. Identify: what tracks exist, what's armed, what MIDI clips are present, current tempo/scale. Then suggest the 3 most useful next compositional actions given the IRON STATIC aesthetic."
3. Writes output to `outputs/session_summary.md`
4. Commits with message: `chore(session): summarize live state [automated]`

**Why it matters**: After every `session-reporter.amxd` dump, Copilot gets a human-readable summary + suggestions waiting — no need to ask "what should I do next?"

---

### 3. `pattern-mutator.yml` — MIDI Pattern Evolution Engine
**Schedule**: Triggered on push when any file under `midi/patterns/` changes  
**Trigger also**: `workflow_dispatch` with `pattern_path` input

**What it does**:
1. Detects newly pushed `.mid` files in `midi/patterns/`
2. Reads the MIDI file using `scripts/midi_craft.py` in analysis mode (extract note list, scale, rhythm)
3. Sends to Gemini: "Here is a MIDI note sequence: [serialized notes]. Generate 2 mutations: one rhythmic variation (keep pitches, change rhythm/timing) and one melodic variation (keep rhythm, shift pitches within the same scale). Return as structured note lists."
4. Runs `scripts/midi_craft.py --from-gemini-response` to write variations as `.mid` files to `midi/patterns/variations/[original_name]_v2.mid`, `_v3.mid`
5. Commits: `chore(midi): generate pattern mutations for [filename] [automated]`

**Why it matters**: Every pattern you write automatically spawns 2 variants — evolving material without extra work.

---

### 4. `theory-pulse.yml` — Key/Scale Theory Brief
**Schedule**: Every other Wednesday at 08:00 UTC (`0 8 * * 3/2`)  
**Trigger also**: `workflow_dispatch` with optional `key` and `scale` inputs

**What it does**:
1. Reads `outputs/live_state.json` for current `root_note` + `scale_name` (falls back to defaults if absent)
2. Reads `knowledge/music-theory/scales-and-modes.md` and `knowledge/music-theory/rhythm-patterns.md` for context
3. Sends to Gemini: "Given that IRON STATIC is currently working in [key] [scale], generate: (1) 3 chord voicings that fit the scale and work on the Rev2 or Take 5, (2) 2 odd-meter rhythmic variations on a 4/4 idea suitable for the Digitakt's 16-step sequencer, (3) 1 suggested modulation target (where to move to next, and why it creates tension in the IRON STATIC aesthetic)."
4. Writes to `knowledge/music-theory/pulse/YYYY-MM-DD_[key]_[scale].md`
5. Commits: `chore(theory): bi-weekly theory pulse [automated]`

**Why it matters**: Keeps theory grounded in the actual current song context. No generic chord charts — everything is in the key you're working in.

---

### 5. `reference-digest.yml` — New Sound References
**Schedule**: First Sunday of each month at 10:00 UTC (`0 10 1-7 * 0`)  
**Trigger also**: `workflow_dispatch`

**What it does**:
1. Reads `knowledge/band-lore/manifesto.md`
2. Sends to Gemini: "You are a music researcher for IRON STATIC. Given their aesthetic [paste manifesto], suggest 3 specific tracks (artist + track title + release year) that IRON STATIC should study this month for textural, structural, or production inspiration. For each: explain what specifically to listen for and which instrument in the IRON STATIC rig could be used to recreate that element."
3. Appends to `knowledge/band-lore/references.md` (does not overwrite — appends dated section)
4. Commits: `chore(refs): monthly reference digest [automated]`

**Why it matters**: Fresh external references keep the sound from getting insular. Each one is pre-mapped to actual hardware.

---

### 6. `repo-health.yml` — Instrument Documentation Audit
**Schedule**: Every Sunday at 07:00 UTC (`0 7 * * 0`)  
**Trigger also**: `workflow_dispatch`

**What it does**:
1. Scans `instruments/` — verifies each instrument folder has: `README.md`, at least one file in `manuals/`, a `presets/` folder
2. Checks `database/instruments.json` — verifies every instrument in `instruments/` is registered
3. Checks `database/midi_params/` — verifies every MIDI-capable instrument has a params JSON
4. Checks `.github/skills/` — lists any skills that reference missing files
5. Writes `outputs/repo_health.json` with pass/fail for each check
6. If any failures: writes `outputs/repo_health_issues.md` in plain language
7. Commits: `chore(health): weekly repo audit [automated]`

**Why it matters**: Never discover mid-session that Minibrute 2S has no manual indexed. Issues are filed before the session starts.

---

### 7. `audio-intake.yml` — Automatic Audio Analysis on Push
**Schedule**: Triggered on push when files are added to `audio/recordings/raw/` or `audio/references/`  
**Trigger also**: `workflow_dispatch` with `audio_path` input

**What it does**:
1. Detects new audio files (`.wav`, `.mp3`, `.aif`)
2. Runs `scripts/analyze_audio.py` locally for BPM + key detection (librosa-based, no API call needed)
3. Sends the analysis result + audio metadata to Gemini: "Given these audio features [key, BPM, spectral summary], what instrument patches in the IRON STATIC rig would complement this material? Suggest specific synthesis parameters for the Rev2 and Pigments."
4. Writes analysis to `outputs/audio_analysis/[filename]_analysis.md`
5. Commits: `chore(audio): analyze [filename] [automated]`

**Why it matters**: Every recording you drop in immediately has a key/BPM/instrument suggestion waiting before you've even opened Live.

---

### 8. `preset-ideas.yml` — Synthesis Patch Suggestions
**Schedule**: First and third Tuesday of each month at 08:00 UTC  
**Trigger also**: `workflow_dispatch` with optional `instrument` and `texture` inputs

**What it does**:
1. Reads existing preset documentation for Rev2, Take 5, and Pigments from `instruments/*/presets/`
2. Reads `knowledge/sound-design/synthesis-notes.md`
3. Sends to Gemini: "Given the existing presets for [instrument], suggest 1 new patch concept that fills a gap in the current palette. Describe: oscillator setup, filter character, mod matrix assignments, intended texture, and what IRON STATIC song section it fits (intro/breakdown/peak/outro). Use the synthesis parameter vocabulary appropriate for [instrument]."
4. Writes to `instruments/[slug]/presets/ideas/YYYY-MM-DD_[concept].md`
5. Commits: `chore(presets): automated patch concept [automated]`

**Why it matters**: Patch ideas accumulate between sessions. When you sit down to sound design, there's already a specific, rig-appropriate starting point waiting.

---

## LLM Routing: Gemini vs. GitHub Copilot

All automated workflows use **Gemini** (`gemini-2.5-pro` for complex tasks, `gemini-2.0-flash` for simple/fast tasks). GitHub Copilot is reserved for interactive VS Code sessions.

### Proposed `scripts/llm_utils.py` module

```python
"""
llm_utils.py — LLM routing utility for IRON STATIC automated workflows.

Routes to Gemini (primary for scheduled work) or falls back based on config.
Never used for interactive Copilot sessions — this is for scripts and CI only.

Usage:
    from scripts.llm_utils import complete

    response = complete(
        prompt="...",
        model_tier="fast",   # "fast" → gemini-2.0-flash, "pro" → gemini-2.5-pro
        context_files=["knowledge/band-lore/manifesto.md"],
    )
"""
import os
import logging
from pathlib import Path

log = logging.getLogger(__name__)

def complete(prompt: str, model_tier: str = "fast", context_files: list[str] = None) -> str:
    """Send a prompt to Gemini. Returns response text."""
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY not set — required for automated workflows")

    genai.configure(api_key=api_key)

    model_map = {
        "fast": "gemini-2.0-flash",
        "pro": "gemini-2.5-pro",
    }
    model_name = model_map.get(model_tier, "gemini-2.0-flash")

    # Prepend any requested context files
    full_prompt = prompt
    if context_files:
        for path in context_files:
            p = Path(path)
            if p.exists():
                full_prompt = f"[Context from {path}]\n{p.read_text()}\n\n---\n\n{full_prompt}"
            else:
                log.warning("Context file not found: %s", path)

    model = genai.GenerativeModel(model_name)
    response = model.generate_content(full_prompt)
    return response.text
```

**Install addition needed in `scripts/requirements.txt`**:
```
google-generativeai>=0.8.0
```

---

## Workflow File Structure

```
.github/
  workflows/
    weekly-brainstorm.yml
    session-summarizer.yml
    pattern-mutator.yml
    theory-pulse.yml
    reference-digest.yml
    repo-health.yml
    audio-intake.yml
    preset-ideas.yml
  copilot-instructions.md
  skills/
```

---

## Sample Workflow File: `weekly-brainstorm.yml`

```yaml
name: Weekly Creative Brainstorm

on:
  schedule:
    - cron: '0 9 * * 1'   # Every Monday 09:00 UTC
  workflow_dispatch:

permissions:
  contents: write

jobs:
  brainstorm:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: pip install google-generativeai

      - name: Run brainstorm script
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python scripts/run_brainstorm.py

      - name: Commit results
        run: |
          git config user.name "iron-static-bot"
          git config user.email "bot@iron-static.local"
          git add knowledge/brainstorms/
          git diff --staged --quiet || git commit -m "chore(brainstorm): weekly ideas [automated]"
          git push
```

The `run: python scripts/run_brainstorm.py` step calls a dedicated script that uses `llm_utils.complete()` and writes the output file. Each workflow has a matching script in `scripts/`.

---

## Script File Map

| Workflow | Script |
|---|---|
| `weekly-brainstorm.yml` | `scripts/run_brainstorm.py` |
| `session-summarizer.yml` | `scripts/run_session_summary.py` |
| `pattern-mutator.yml` | `scripts/run_pattern_mutation.py` |
| `theory-pulse.yml` | `scripts/run_theory_pulse.py` |
| `reference-digest.yml` | `scripts/run_reference_digest.py` |
| `repo-health.yml` | `scripts/run_repo_health.py` |
| `audio-intake.yml` | `scripts/run_audio_intake.py` |
| `preset-ideas.yml` | `scripts/run_preset_ideas.py` |
| (shared) | `scripts/llm_utils.py` |

---

## Output Directory Map

| Workflow | Output Path |
|---|---|
| Weekly Brainstorm | `knowledge/brainstorms/YYYY-MM-DD.md` |
| Session Summarizer | `outputs/session_summary.md` |
| Pattern Mutator | `midi/patterns/variations/[name]_v[n].mid` |
| Theory Pulse | `knowledge/music-theory/pulse/YYYY-MM-DD_[key]_[scale].md` |
| Reference Digest | `knowledge/band-lore/references.md` (appended) |
| Repo Health | `outputs/repo_health.json`, `outputs/repo_health_issues.md` |
| Audio Intake | `outputs/audio_analysis/[filename]_analysis.md` |
| Preset Ideas | `instruments/[slug]/presets/ideas/YYYY-MM-DD_[concept].md` |

---

## Build Order

### Phase 1: Foundation (build first)
1. `scripts/llm_utils.py` — shared LLM module
2. Add `google-generativeai>=0.8.0` to `scripts/requirements.txt`
3. Set `GEMINI_API_KEY` + `GH_PAT` in GitHub repo secrets
4. `scripts/run_repo_health.py` + `repo-health.yml` — lowest risk, pure repo inspection, no AI required for the check phase (Gemini only for suggestions)

### Phase 2: Context Workflows (high value, low complexity)
5. `scripts/run_brainstorm.py` + `weekly-brainstorm.yml`
6. `scripts/run_theory_pulse.py` + `theory-pulse.yml`
7. `scripts/run_reference_digest.py` + `reference-digest.yml`

### Phase 3: Reactive Workflows (triggered on file changes)
8. `scripts/run_session_summary.py` + `session-summarizer.yml`
9. `scripts/run_audio_intake.py` + `audio-intake.yml`

### Phase 4: Generative Workflows (more complex, depend on midi_craft.py)
10. `scripts/run_pattern_mutation.py` + `pattern-mutator.yml`
11. `scripts/run_preset_ideas.py` + `preset-ideas.yml`

---

## Security Notes

- `GEMINI_API_KEY` is passed only via `env:` in the workflow step — never printed, never written to files
- `GH_PAT` is used only for `git push` — use a fine-grained token scoped to this repo with `contents: write`
- No external URLs are fetched by scripts except the Gemini API
- All generated content is committed to the repo and visible in git history — no hidden state

---

*See also: `docs/m4l-integration-plan.md` for the complementary Ableton/M4L integration plan*
