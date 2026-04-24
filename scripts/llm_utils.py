#!/usr/bin/env python3
"""
llm_utils.py — LLM routing utility for IRON STATIC automated workflows.

Routes to Gemini (primary for scheduled work). GitHub Copilot is reserved
for interactive VS Code sessions — this module is for scripts and CI only.

Usage:
    from llm_utils import complete

    response = complete(
        prompt="...",
        model_tier="fast",   # "fast" → gemini-2.0-flash, "pro" → gemini-2.5-pro
        context_files=["knowledge/band-lore/manifesto.md"],
    )
"""
import logging
import os
from pathlib import Path

log = logging.getLogger(__name__)

_MODEL_MAP = {
    "fast": os.environ.get("GEMINI_MODEL_FAST", "gemini-2.0-flash"),
    "pro": os.environ.get("GEMINI_MODEL_PRO", "gemini-2.5-pro"),
}

# Repo root — two levels up from this script
_REPO_ROOT = Path(__file__).resolve().parent.parent


def complete(
    prompt: str,
    model_tier: str = "fast",
    context_files: list[str] | None = None,
) -> str:
    """Send a prompt to Gemini. Returns response text.

    Args:
        prompt: The prompt to send.
        model_tier: "fast" (gemini-2.0-flash) or "pro" (gemini-2.5-pro).
        context_files: Repo-relative paths to prepend as context blocks.

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

    full_prompt = _prepend_context(prompt, context_files or [])

    log.info("Calling Gemini model=%s prompt_chars=%d", model_name, len(full_prompt))
    response = client.models.generate_content(model=model_name, contents=full_prompt)
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
