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

---

# Session Learnings — 2026-04-25 (Part 3)

*Active song: Ignition Point — E phrygian @ 116 BPM*
*Checkpoint: end-of-day*

## What We Figured Out

- **`iron_static` is now an installable Python package** — `pyproject.toml` at repo root, `pip install -e .` in the venv. Import as `from iron_static.notify import event, notify, status`. Installed CLI: `iron-static-notify <subcommand>`. `scripts/vscode_notify.py` reduced to a thin re-export shim for backwards compat.

- **`setuptools.backends.legacy:build` is not available in the venv's older setuptools** — correct backend is `setuptools.build_meta`. Always use that for new `pyproject.toml` files in this repo.

- **VS Code bridge extension (port 9880) now has a `/event` endpoint** — POSTs `{source, type, message, data?}` to queue structured events for Arc. Queue is drained by the `ironStatic_getEvents` LM Tool. Status bar badges with `$(bell) N` when events are pending.

- **LM Tool registration requires both `vscode.lm.registerTool()` in `extension.ts` AND a `contributes.languageModelTools` entry in `package.json`** — skipping the `package.json` declaration means VS Code won't surface the tool to the model. Both are now present.

- **Extension changes require `npm run build` + window reload to take effect** — the bridge server runs inside the extension host; `out/extension.js` is the compiled output loaded at activation. `iron-static-notify event` returning 404 is always a "stale binary" symptom — reload window, not reinstall.

- **Stream Deck profile wired to `com.iron-static.bridge` plugin** — all 8 keypad buttons and 4 encoder dials now use bridge plugin action UUIDs (`com.iron-static.bridge.run-script` / `com.iron-static.bridge.dial-info`), not `.command` file openers. Profile generated by `scripts/streamdeck/generate_profile.py`.

- **Stream Deck plugin compiles to `bin/plugin.js` via rollup** — source is TypeScript at `streamdeck/plugin/src/`. After any source change: `npm run build` in `streamdeck/plugin/`, then `streamdeck restart com.iron-static.bridge` or reinstall. Plugin UUID: `com.iron-static.bridge`.

- **Stream Deck status server (port 9879)** — `POST /dial {label, value}` to update encoder touchscreen from Python. `POST /status` for keypad labels. `GET /health`. Separate from the VS Code bridge (port 9880).

- **`/event` → status bar badge pattern** — when a script pushes an event, the VS Code status bar shows `$(radio-tower) IS :9880 $(bell) N`. Ask Arc to "check events" or Arc can proactively call `ironStatic_getEvents` to drain the queue. Badge clears after drain.

## What Failed and Why

- **`setuptools.backends.legacy:build` in pyproject.toml** → `BackendUnavailable: Cannot import 'setuptools.backends.legacy'` — the venv has setuptools ~68 but the legacy backend path changed in later versions. Fix: use `setuptools.build_meta` always.

- **`multi_replace_string_in_file` with replacements not as a proper JSON array** → tool error "must be array" — the replacements parameter must be a JSON array even for a single replacement. Had to fall back to sequential `replace_string_in_file` calls.

- **`iron-static-notify event` returning 404 before window reload** — the bridge was running from the pre-`/event` compiled binary. The endpoint existed in source but not in `out/extension.js`. Reload window fixes this, not package reinstall.

## Decisions Made

| Decision | Reasoning |
|---|---|
| `iron_static/` package at repo root, not inside `scripts/` | Makes imports clean (`from iron_static.notify import ...`) without sys.path hacks; `scripts/` stays as CLI entry points |
| `scripts/vscode_notify.py` kept as a shim | Shell scripts and shortcuts that invoke it directly continue to work; the real code is in the package |
| `/event` endpoint separate from `/notify` | `/notify` is fire-and-forget UI toast; `/event` is structured data for Arc's LM tool queue — different consumers, different semantics |
| LM Tool queue max 100 events, FIFO eviction | Prevents unbounded growth if nobody reads the queue for a long time |

## Correct Configurations / Commands

```bash
# Install the iron_static package in editable mode
pip install -e .

# Verify package import
python -c "from iron_static.notify import notify, event, health; print('OK')"

# CLI health check
iron-static-notify health

# Push an event into Arc's queue
iron-static-notify event "Brainstorm complete" --source run_brainstorm --type done

# Same from Python
from iron_static.notify import event
event("run_brainstorm", "Brainstorm complete", type="done", data={"file": "knowledge/brainstorms/2026-04-25.md"})

# Rebuild VS Code extension after source changes
cd vscode-extension/iron-static-bridge && npm run build
# Then: Cmd+Shift+P → Developer: Reload Window

# Rebuild Stream Deck plugin after source changes
cd streamdeck/plugin && npm run build
streamdeck restart com.iron-static.bridge
```

```
# pyproject.toml build-system block (correct)
[build-system]
requires = ["setuptools>=42"]
build-backend = "setuptools.build_meta"
```

## Open Questions

- [ ] VELA `vela_vocalist.py render` still exits 1 — ACE-Step server may not be fully initialized; check `/tmp/acestep-api.log` health response includes `"models_initialized": true` before rendering
- [ ] `midi_craft.py` duplicate `main()` — second one shadows `clips` subcommand (carried over from prior session)
- [ ] `code chat --mode` identifier format — "The Sound Designer" vs "the-sound-designer" not yet verified
- [ ] Verify `vars.GCS_BUCKET` set in GitHub Actions: `gh variable list`
- [ ] MCP Actions in Stream Deck Preferences → General → enable MCP Actions (not yet done)
- [ ] Stream Deck marketplace plugins to install: Ableton lite, GitHub Utilities, VSCode Runner

## Next Session Priority

Reload the VS Code window to activate the `/event` endpoint, then smoke-test the full loop: `iron-static-notify event "test" --source cli --type info` → status bar badges → ask Arc to call `ironStatic_getEvents` → queue drains → badge clears.


---

# Session Learnings — 2026-04-25 (Part 3 — VELA ACE-Step API)

*Active song: Ignition Point — E phrygian @ 116.0 BPM*
*Checkpoint: 21:45*

## What We Figured Out

- **ACE-Step `/query_result` uses `task_id_list`, not `task_ids`** — the field name in the POST body is `task_id_list` (a list or JSON-encoded string). Sending `task_ids` returns an empty `data: []` with no error.
- **`data` is a list, not a dict keyed by task_id** — each item is `{"task_id": ..., "result": "<JSON string>", "status": int}`. The old script tried `result.get("data", {}).get(task_id, {})` which crashed with `AttributeError: 'list' object has no attribute 'get'`.
- **`result` field is a JSON-encoded string, not a parsed object** — must call `json.loads(item["result"])` to get the list of audio file items.
- **Status codes**: `0`=running/queued, `1`=succeeded, `2`=failed. There is no status `3` (cancelled was wrong).
- **Audio `file` key is a local absolute path** — ACE-Step stores generated audio locally and returns the path in `item["file"]`. Use `shutil.copy2()` to copy it. The old code looked for `audio_url` or `path` keys that don't exist.
- **ACE-Step uses lazy model loading** — `models_initialized: false` in `/health` does NOT mean it's still starting. The server is ready; models load on first request. Polling health for `models_initialized: true` will loop forever.
- **ACE-Step startup fails if `VIRTUAL_ENV` is set to a different venv path** — the `start_api_server_macos.sh` script uses `uv` and conflicts with an active `VIRTUAL_ENV`. Must `unset VIRTUAL_ENV` before starting.
- **ACE-Step API server location**: `~/tools/ACE-Step-1.5`. Start command: `unset VIRTUAL_ENV && cd ~/tools/ACE-Step-1.5 && nohup bash start_api_server_macos.sh > /tmp/acestep-api.log 2>&1 &`

## What Failed and Why

- `python scripts/vela_vocalist.py render` → `AttributeError: 'list' object has no attribute 'get'` → wrong field name (`task_ids` vs `task_id_list`) + wrong response parsing (list not dict)
- Polling `models_initialized: true` in health check → infinite loop → ACE-Step lazy-loads, health never returns `true` until a request triggers model init
- `nohup ./start_api_server_macos.sh > /tmp/acestep-api.log 2>&1 &` in a zsh terminal with `VIRTUAL_ENV` set → `Fatal Python error: init_sys_streams: can't initialize sys standard streams` → uv sees conflicting venv

## Decisions Made

| Decision | Reasoning |
|---|---|
| Copy audio via `shutil.copy2()` (local path) not HTTP | ACE-Step runs on same machine; `file` field is always a local abs path; copying is faster and avoids temp dir access restrictions |
| Use `unset VIRTUAL_ENV` before starting ACE-Step | Prevents uv from inheriting a conflicting venv that causes Python stream init failure |
| No readiness poll for `models_initialized` | Field stays `false` until first request (lazy load). Server is ready as soon as it accepts HTTP connections. |

## Correct Configurations / Commands

```bash
# Start ACE-Step API server (lazy-loads models on first request)
unset VIRTUAL_ENV && cd ~/tools/ACE-Step-1.5 && nohup bash start_api_server_macos.sh > /tmp/acestep-api.log 2>&1 &

# Wait for server to accept connections (not models_initialized — that stays false until first request)
until curl -s http://127.0.0.1:8001/health | grep -q '"status":"ok"'; do sleep 2; done

# Generate VELA training takes (3 variations, 20s each)
cd /Users/darnold/git/iron-static && python scripts/vela_vocalist.py render \
  --lyrics "Ignition. The system knows." --batch-size 3 --duration 20

# query_result correct call (task_id_list, not task_ids)
curl -s http://127.0.0.1:8001/query_result -X POST -H "Content-Type: application/json" \
  -d '{"task_id_list": ["<task_id>"]}'
```

## Open Questions

- [ ] First successful render hasn't run yet — need to confirm `file` path and copy logic work end-to-end
- [ ] Does ACE-Step persist task records across server restarts, or are task IDs lost on shutdown?
- [ ] LoRA training via Gradio UI (`localhost:7860`) — is Gradio also running, or does it need a separate launch?
- [ ] How many takes will be good enough to start LoRA training? README says 8–10 but minimum quality threshold is unclear

## Next Session Priority

Start ACE-Step server (with `unset VIRTUAL_ENV`), run `python scripts/vela_vocalist.py render --lyrics "Ignition. The system knows." --batch-size 3 --duration 20`, confirm files land in `audio/samples/vocals/vela/ignition-point/`, then generate 2–3 more phrases to reach 8+ takes for LoRA training.
