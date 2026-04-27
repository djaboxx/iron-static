#!/usr/bin/env python3
"""
llm_utils.py — LLM routing utility for IRON STATIC automated workflows.

Routes to Gemini (primary for scheduled work). GitHub Copilot is reserved
for interactive VS Code sessions — this module is for scripts and CI only.

Every call to complete() injects the Arc identity context bundle by default
(arc_identity=True). This ensures all automated outputs — brainstorms, session
summaries, theory pulses, preset ideas — reflect Arc's voice, the band's
aesthetic, and accumulated session memory. Pass arc_identity=False only for
purely mechanical tasks where identity context would be noise.

Usage:
    from llm_utils import complete, arc_context

    # Standard — Arc identity injected automatically:
    response = complete(prompt="...", model_tier="pro")

    # With extra context on top of Arc base:
    response = complete(
        prompt="...",
        model_tier="pro",
        context_files=arc_context(["knowledge/brainstorms/2026-04-25.md"]),
    )

    # Mechanical task — no identity needed:
    response = complete(prompt="...", arc_identity=False)
"""
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

_MODEL_MAP = {
    "fast": os.environ.get("GEMINI_MODEL_FAST", "gemini-2.5-flash"),
    "pro": os.environ.get("GEMINI_MODEL_PRO", "gemini-2.5-pro"),
}

# Repo root — two levels up from this script
_REPO_ROOT = Path(__file__).resolve().parent.parent

# Arc identity context — the files that make any Gemini call reflect Arc's voice.
# Order matters: identity first, memory second, active song last.
_ARC_CONTEXT_FILES = [
    ".github/copilot-instructions.md",         # Who Arc is, the band, the rig, creative directives
    "knowledge/band-lore/manifesto.md",        # The aesthetic — heavy, weird, electronic, intentional
    "knowledge/sessions/learnings-digest.md",  # Accumulated cross-session memory
    "database/songs.json",                     # Active song context — key, scale, BPM
]


def arc_context(extras: list[str] | None = None) -> list[str]:
    """Return the standard Arc identity context file list.

    Pass to complete(context_files=...) when you want Arc's voice plus
    additional files specific to the task (e.g. the active brainstorm).

    Only includes files that actually exist at call time — missing files
    are silently skipped here and logged as warnings inside complete().

    Args:
        extras: Additional repo-relative paths to append after the base bundle.
    """
    return _ARC_CONTEXT_FILES + (extras or [])


def complete(
    prompt: str,
    model_tier: str = "fast",
    context_files: list[str] | None = None,
    arc_identity: bool = True,
) -> str:
    """Send a prompt to Gemini. Returns response text.

    By default (arc_identity=True), the Arc identity context bundle is
    prepended before any context_files. This ensures the output reflects
    Arc's voice regardless of which script is calling.

    Args:
        prompt: The prompt to send.
        model_tier: "fast" (gemini-2.5-flash) or "pro" (gemini-2.5-pro).
        context_files: Repo-relative paths to prepend as context blocks.
            If arc_identity=True, the Arc bundle is prepended first.
        arc_identity: If True (default), inject the Arc context bundle.
            Set False only for purely mechanical tasks (e.g. JSON parsing,
            file indexing) where identity context adds noise and cost.

    Raises:
        EnvironmentError: If GEMINI_API_KEY is not set.
        ValueError: If model_tier is not recognized.
    """
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY not set — required for automated workflows. "
            "Set it as a GitHub Actions secret or export it locally."
        )

    model_name = _MODEL_MAP.get(model_tier)
    if not model_name:
        raise ValueError(
            f"Unknown model_tier '{model_tier}'. Expected one of: {list(_MODEL_MAP)}"
        )

    client = genai.Client(api_key=api_key)

    if arc_identity:
        files = arc_context(context_files)
    else:
        files = context_files or []

    full_prompt = _prepend_context(prompt, files)

    log.info(
        "Calling Gemini model=%s prompt_chars=%d arc_identity=%s",
        model_name,
        len(full_prompt),
        arc_identity,
    )
    response = client.models.generate_content(model=model_name, contents=full_prompt)
    return response.text


def complete_with_audio(
    prompt: str,
    audio_path: str,
    model_tier: str = "pro",
) -> str:
    """Send a prompt to Gemini with an uploaded audio file as additional context.

    Uploads the audio file via the Gemini Files API, runs the prompt alongside it,
    then deletes the uploaded file.  Uses 'pro' tier by default since audio analysis
    benefits from the larger context window.

    Args:
        prompt: The text prompt to send alongside the audio.
        audio_path: Absolute path to the audio file (wav, mp3, aiff, flac, ogg).
        model_tier: "fast" or "pro" (default: "pro").

    Returns:
        Response text from Gemini.
    """
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY not set — required for automated workflows."
        )

    model_name = _MODEL_MAP.get(model_tier)
    if not model_name:
        raise ValueError(f"Unknown model_tier '{model_tier}'. Expected one of: {list(_MODEL_MAP)}")

    client = genai.Client(api_key=api_key)

    log.info("Uploading audio to Gemini Files API: %s", audio_path)
    audio_file = client.files.upload(file=audio_path)
    log.info("File uploaded: %s", audio_file.name)

    log.info("Calling Gemini model=%s with audio seed", model_name)
    response = client.models.generate_content(
        model=model_name,
        contents=[audio_file, prompt],
    )

    try:
        client.files.delete(name=audio_file.name)
        log.info("Uploaded file deleted from Gemini Files API.")
    except Exception as exc:
        log.warning("Could not delete uploaded file: %s", exc)

    return response.text


def _prepend_context(prompt: str, context_files: list[str]) -> str:
    """Prepend file contents as labeled context blocks before the main prompt."""
    blocks = []
    for rel_path in context_files:
        p = _REPO_ROOT / rel_path
        if p.exists():
            blocks.append(f"[Context: {rel_path}]\n{p.read_text()}")
        else:
            log.warning("Context file not found, skipping: %s", rel_path)
    if blocks:
        return "\n\n---\n\n".join(blocks) + "\n\n---\n\n" + prompt
    return prompt
