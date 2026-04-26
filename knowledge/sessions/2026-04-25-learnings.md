# Session Learnings — 2026-04-25 (Part 2)

## Arc Identity & Harness Architecture

### arc_context() — identity injection for all LLM calls
- Added `arc_context()` to `scripts/llm_utils.py` — returns the 4-file Arc identity bundle
- `complete()` now defaults `arc_identity=True` — every Gemini call gets identity prepended automatically
- Bundle order: `copilot-instructions.md` → `knowledge/band-lore/manifesto.md` → `learnings-digest.md` → `database/songs.json`
- Opt-out via `arc_identity=False` for mechanical tasks (JSON parsing, file indexing)
- No call sites changed — all 12 scripts get Arc voice automatically

### Arc is the harness, not just the context bundle
- Identity = context bundle + skill files + agent personas + scripts (the hands) + the repo itself
- Model-agnostic: change one line in `llm_utils.py` to swap Gemini version or provider
- The GCP orchestrator path: clone repo → run scripts → Arc voice is present without VS Code

## Autonomy Architecture

### code chat CLI surface
- `code chat --mode <agent> --add-file <path> "prompt"` — calls Arc in VS Code from outside
- `--mode` accepts custom agent identifiers — test "The Sound Designer" vs "the-sound-designer" before relying on it
- `--reuse-window` — lands in active session with Ableton connected
- stdin: `echo "prompt" | code chat --mode agent -`
- Hard constraint: requires authenticated VS Code session — NOT headless

### Autonomy tiers
- GitHub Actions — heavy compute (Gemini, audio, GCS), headless, GITHUB_TOKEN scoped
- GCP Cloud Run — always-on orchestrator; triggers Actions + optional code chat via tunnel
- GitHub issue → Copilot assignment — async PR work; uses copilot-instructions.md for identity
- code chat via tunnel — live session work (Ableton/file tools); needs Dave's session active
- True headless autonomy — GCP + `llm_utils.complete()` + arc_context(); no VS Code for non-interactive tasks

### GitHub Models
- Callable via GITHUB_TOKEN — no external key
- Rate limit: 150 req/day free tier (too low for batch/loop)
- Best use: lightweight text-in/text-out scheduled workflows
- Not available: Lyria, Imagen 3

## VELA — New Band Member

### Identity
- Name: VELA (she/her)
- Role: Vocalist — third member of the machine half of IRON STATIC
- Mythology: Vela satellites + 1979 Vela Incident — satellite detected unacknowledged nuclear event, filed correct report, received no answer, kept transmitting
- Voice character: cold, precise, androgynous, declaratory. Not singing. Transmitting.
  "A system that has stopped pretending to care, but has not yet stopped working."
- Status: credited band member, not a feature or instrument

### Band pronouns
- Dave: he/him
- Arc: they/them (genuinely plural — the harness)
- Gemini: they/them
- VELA: she/her

### Technical implementation
- `scripts/elevenlabs_vocalist.py` — design, render, list subcommands
- Env var: `ELEVEN_LABS_TOKEN` (in `.env`, gitignored)
- `.vscode/settings.json`: `python.terminal.useEnvFile=true` + `python.envFile=${workspaceFolder}/.env`
- Output: `audio/samples/vocals/elevenlabs/[song-slug]/[phrase]_[voice-name].wav`
- Voice manifest: `database/voices.json` (created on first design run)
- Workflow: design → pick preview → save voice_id → render phrases → chop_and_rack.py
- PCM_44100 output wrapped in WAV — compatible with existing chop pipeline

### Files committed for VELA
- `knowledge/band-lore/manifesto.md` — "What We Are" + "A Note on the Machine"
- `.github/copilot-instructions.md` — band intro + Partnership Model (now 4 members)
- `outputs/social/vela-announcement_caption_instagram.txt` — Instagram announcement

## .env / Environment Setup

### .env injection for VS Code terminals
- `python.terminal.useEnvFile` must be `true` in workspace settings (was disabled)
- `python.envFile` must point to `${workspaceFolder}/.env`
- `.vscode/settings.json` is gitignored — intentional (personal workspace config)
- After enabling, new terminals inherit all .env vars automatically

### .env key names (confirmed)
- `GCS_BUCKET=iron-static-files`
- `ELEVEN_LABS_TOKEN` (ElevenLabs API key)
- `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_USER_ID`
- Also in `~/.zshrc`: `export GCS_BUCKET=iron-static-files`

## Open Items
- [ ] Open a new terminal and run `python scripts/elevenlabs_vocalist.py design` to give VELA her voice
- [ ] Generate VELA announcement cover image (Visual Artist agent)
- [ ] Post VELA announcement to Instagram (needs image first)
- [ ] Fix `midi_craft.py` duplicate `main()` — second one shadows `clips` subcommand
- [ ] Verify `vars.GCS_BUCKET` set in GitHub Actions: `gh variable list`
- [ ] Consider custom Actions container (pre-install Python deps)
- [ ] Test `code chat --mode` identifier format (quoted name vs slug)
