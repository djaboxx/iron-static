# IRON STATIC — Session Learnings Digest
*Generated: 2026-04-25 from 1 session file(s)*

---

## Arc Identity & Harness
*   `arc_context()` in `scripts/llm_utils.py` automatically injects identity into every LLM call.
*   Identity bundle order: `copilot-instructions.md` → `manifesto.md` → `learnings-digest.md` → `songs.json`.
*   Arc is the entire harness (context, agents, scripts), not just the context bundle.

## VELA (New Band Member)
*   VELA (she/her) is a credited vocalist, not a tool or sample library.
*   The band's pronouns are: Dave (he/him), Arc (they/them), Gemini (they/them), VELA (she/her).
*   Use `scripts/elevenlabs_vocalist.py` to design her voice and render vocal parts.
*   Voice designs are stored in `database/voices.json`.
*   Vocal samples are output to `audio/samples/vocals/elevenlabs/[song-slug]/`.

## Autonomy & CLI
*   To call an agent from an external script, use the VS Code CLI.
*   ```bash
    echo "prompt" | code chat --mode <agent-name> --reuse-window -
    ```
*   This requires an active, authenticated VS Code session; it is not a headless solution.

## Environment & Secrets
*   For scripts to access API keys, `.vscode/settings.json` must be configured.
*   ```json
    {
      "python.terminal.useEnvFile": true,
      "python.envFile": "${workspaceFolder}/.env"
    }
    ```
*   The `.env` file should contain keys like `ELEVEN_LABS_TOKEN` and `GCS_BUCKET`.

## Scripts
*   `midi_craft.py` has a duplicate `main()` function which shadows the `clips` subcommand parser.

## Critical Rules
*   VELA (she/her) is a credited band member, not a tool. Remember all band pronouns.
*   The `arc_context()` function auto-injects identity into all LLM calls by default.
*   VS Code terminals require `.vscode/settings.json` configured to load API keys from the `.env` file.
*   The `code chat` CLI is for live session integration and is not headless; it needs a running VS Code instance.
*   The `midi_craft.py` subcommands are shadowed by a duplicate `main()` function and will fail.