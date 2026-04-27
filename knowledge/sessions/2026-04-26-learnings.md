# Session Learnings — 2026-04-26

*Active song: Ignition Point — E phrygian @ 116 BPM*
*Checkpoint: first checkpoint this session*

---

## What We Figured Out

- **ACE-Step runs fully free on M3 Max.** 36GB unified memory exceeds the 20GB VRAM requirement. No GPU rental, no GCP compute cost needed for generation or training. This is permanent — GCP GPU is never needed unless we want to run headless batch jobs overnight away from the machine.

- **GCP project `happypathway-1522441039906` is essentially idle.** Current monthly cost: $0.00–$0.01. Two Cloud Run services (`roknsound-rental-inventory`, `smartprompt-api-us-central1`) both configured at `minInstances=0` — they scale to zero and show no recent request traffic. 7 Cloud Functions all `OFFLINE`. 11 GCS buckets totaling < 200MB. Billing account: `RoknSound (019564-DD4CE0-79E96C)`.

- **GCP cost comparison for ACE-Step (if we ever wanted cloud).** `g2-standard-4` (L4 24GB): $0.70/hr, ~$22/month at 8hr/session. `a2-highgpu-1g` (A100 40GB): $3.67/hr, ~$118/month. Local M3 Max wins by every metric.

- **`@the-ace-step` chat participant is now live.** The agent file, package.json entry, and chatParticipants.ts entry are all wired. The participant loads `.github/agents/the-ace-step.agent.md` as its system prompt, injecting active song context from `database/songs.json` per the existing participant pattern.

- **ACE-Step API key patterns (validated from docs):**
  - Submit: `POST /release_task` → returns `{"task_id": "..."}` immediately
  - Poll: `POST /query_result` with `{"task_id_list": ["..."]}` — check `status` field
  - Download: `GET /v1/audio?path=...` — but if path starts with `/tmp/`, use `shutil.copy2` directly (faster)
  - `thinking=true` enables the 5Hz LM for best quality — always use for IRON STATIC
  - `lora_name` field in `/release_task` payload activates a trained LoRA adapter for VELA

- **VELA LoRA training data format (3 files per example):**
  - `phrase_001.wav` — audio
  - `phrase_001.lyrics.txt` — plaintext lyrics
  - `phrase_001.json` — `{"caption": "...", "bpm": 116, "keyscale": "E phrygian", "timesignature": "4/4", "language": "en"}`
  - The `caption` field must match VELA's `character_tags` from `database/voices.json`

- **`vela_vocalist.py` `render` command still exits 1.** Needs the ACE-Step server running at `127.0.0.1:8001` to debug. Script itself is structurally correct — the failure is a connection error, not a code bug.

- **VS Code Chat Participant API pattern for IRON STATIC extension.** All participants share one handler pattern in `chatParticipants.ts`: load agent `.agent.md` → strip YAML frontmatter → prepend active song context → send to `claude-sonnet-4-5` via `vscode.lm.selectChatModels`. Adding a new participant = 3 changes: agent.md file, package.json entry, AGENTS array in chatParticipants.ts. Build: `node esbuild.mjs` from the extension dir.

---

## What Failed and Why

- **`gcloud run services describe <name>` without `--region` flag** → exits 1 with no output. Cloud Run is regional. Always specify `--region us-central1` or use `--format json` via `gcloud run services list --platform managed --format json` to get all regions at once.

- **`gcloud monitoring metrics list` for Cloud Run request counts** → returned empty. The query works but our services have zero traffic — no metrics to surface.

---

## Decisions Made

| Decision | Reasoning |
|---|---|
| ACE-Step training stays local (M3 Max only) | 36GB unified memory handles it fully; GCP GPU would cost $22–$118/month for zero benefit |
| `@the-ace-step` uses same chatParticipants.ts pattern as all other agents | Consistency — one handler loop, one system prompt pattern, same song context injection |
| VELA `lora_path` stays `null` in voices.json until training completes | Script reads `lora_path` from voices.json at runtime; null = style-guided generation, set = voice-cloned generation |
| `the-ace-step` agent owns BOTH music generation AND VELA rendering | They share the same API server, same polling pattern, same output conventions — one agent makes more sense than splitting |

---

## Correct Configurations / Commands

```bash
# Start ACE-Step API server (M3 Max)
unset VIRTUAL_ENV && cd ~/tools/ACE-Step-1.5 && nohup bash start_api_server_macos.sh > /tmp/acestep-api.log 2>&1 &

# Check server health
curl -s http://127.0.0.1:8001/health

# Generate via forge + ACE-Step
python scripts/gemini_forge.py --target "industrial kick with sub tail" --acestep --acestep-duration 30 --acestep-batch 2

# Render VELA vocal
python scripts/vela_vocalist.py render --song ignition-point --lyrics "Ignition. The system knows."

# Build the VS Code extension after changes
cd /Users/darnold/git/iron-static/vscode-extension/iron-static-bridge && node esbuild.mjs

# Get Cloud Run services with full resource detail (no region flag needed)
gcloud run services list --platform managed --project happypathway-1522441039906 --format json
```

---

## Open Questions

- [ ] `vela_vocalist.py render` exits 1 — needs ACE-Step server running to isolate exact error. Is it a connection refused, a payload issue, or the poll logic?
- [ ] VELA training dataset: do we have any clean vocal recordings ready to use as training examples? Need `.wav` + matching `.lyrics.txt` + `.json` per sample.
- [ ] `gcloud run services describe` for detailed min/max instance config — need `--region us-central1` confirmed to work.
- [ ] Should `the-ace-step` participant get disambiguation entries in package.json for auto-routing? (e.g. "generate audio", "render VELA", "train LoRA" → auto-routes to `@the-ace-step`)
- [ ] Terraform `variables.tf` / `secrets.tf` modified this session — what changed and does it need `terraform apply`?

---

## Next Session Priority

Start ACE-Step server, run `vela_vocalist.py health` to confirm connection, then debug `render` — this unblocks the entire VELA vocal pipeline.
