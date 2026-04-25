#!/usr/bin/env python3
"""
compact_learnings.py — Distill all session learnings into a persistent digest.

Reads all knowledge/sessions/*-learnings.md files (all time, not just recent),
calls Gemini to synthesize them into a topic-organized digest, and writes to:
  knowledge/sessions/learnings-digest.md

The digest is meant to be read at the start of every session — it should be
short enough to absorb in 30 seconds and dense enough to prevent re-learning
things that were already figured out.

Usage:
    python scripts/compact_learnings.py
    python scripts/compact_learnings.py --no-llm     # print raw concat only, no Gemini
    python scripts/compact_learnings.py --force      # overwrite even if digest is fresh
    python scripts/compact_learnings.py --dry-run    # print output, don't write
"""
import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
SESSIONS_DIR = REPO_ROOT / "knowledge" / "sessions"
DIGEST_FILE = SESSIONS_DIR / "learnings-digest.md"

DIGEST_PROMPT = """\
You are IRON STATIC's Copilot, synthesizing all session learnings into a compact,
actionable reference digest. IRON STATIC is a heavy electronic duo (Nine Inch Nails
meets Lamb of God meets Modeselector) working in Ableton Live 12 Suite with hardware
synths (Digitakt, Rev2, Take 5, Subharmonicon, DFAM, Minibrute 2S, Arturia Pigments).

Below are all session learnings captured across multiple sessions, in raw checkpoint
format. Your job is to distill them into a compact digest organized by topic.

## Rules for the digest:
- Organize by TOPIC, not by date. Topics should be practical categories like:
  "Ableton Session Build", "ADG Preset Format", "Agent Wiring", "Scripts",
  "MIDI Routing", "Remote Script", "Instrument Notes", etc.
- Each entry should be ONE SENTENCE or a SHORT CODE BLOCK. No prose.
- Prioritize entries that prevented re-discovery or fixed a blocker.
- Include exact commands or code snippets where they prevent future debugging.
- Drop entries that are obvious, transient, or superseded by newer learnings.
- The entire digest must be scannable in 30 seconds. Ruthlessly cut redundancy.
- Format: `## [Topic]` with bullet points under each.
- End with a `## Critical Rules` section: the 5–7 things that must NEVER be forgotten.

## Raw session learnings (all sessions, all checkpoints):

{learnings_block}

Write the digest now. Start directly with the first ## heading. No preamble.
"""


def _collect_learnings() -> list[tuple[str, str]]:
    """Return list of (filename, content) for all *-learnings.md files, sorted by date."""
    files = sorted(SESSIONS_DIR.glob("*-learnings.md"))
    results = []
    for f in files:
        results.append((f.name, f.read_text()))
    return results


def _is_digest_fresh(max_age_hours: int = 12) -> bool:
    """Return True if the digest was written within max_age_hours and no new learnings."""
    if not DIGEST_FILE.exists():
        return False
    digest_mtime = datetime.fromtimestamp(DIGEST_FILE.stat().st_mtime)
    age_hours = (datetime.now() - digest_mtime).total_seconds() / 3600
    if age_hours > max_age_hours:
        return False
    # Check if any learnings file is newer than the digest
    for f in SESSIONS_DIR.glob("*-learnings.md"):
        if f.stat().st_mtime > DIGEST_FILE.stat().st_mtime:
            return False
    return True


def _build_no_llm_summary(learnings: list[tuple[str, str]]) -> str:
    """Produce a minimal digest without LLM: just extract bullet points from
    'What We Figured Out' sections across all files."""
    lines = [
        f"# IRON STATIC — Session Learnings Digest",
        f"*Generated: {date.today()} (no-llm mode — raw extraction)*",
        "",
        "---",
        "",
    ]
    for fname, content in learnings:
        section_date = fname.replace("-learnings.md", "")
        lines.append(f"## From {section_date}")
        in_figured_out = False
        for line in content.splitlines():
            if "## What We Figured Out" in line:
                in_figured_out = True
                continue
            if in_figured_out:
                if line.startswith("## "):
                    in_figured_out = False
                    continue
                if line.strip().startswith("- "):
                    lines.append(line)
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Distill session learnings into a compact digest.")
    parser.add_argument("--no-llm", action="store_true", help="Skip Gemini, extract bullets only.")
    parser.add_argument("--force", action="store_true", help="Overwrite even if digest is fresh.")
    parser.add_argument("--dry-run", action="store_true", help="Print output, don't write file.")
    args = parser.parse_args()

    learnings = _collect_learnings()
    if not learnings:
        log.warning("No *-learnings.md files found in %s. Nothing to compact.", SESSIONS_DIR)
        sys.exit(0)

    log.info("Found %d learnings file(s): %s", len(learnings), [f for f, _ in learnings])

    if not args.force and not args.dry_run and _is_digest_fresh():
        log.info("Digest is already fresh (no new learnings, written within 12h). Use --force to regenerate.")
        sys.exit(0)

    if args.no_llm:
        digest_text = _build_no_llm_summary(learnings)
    else:
        from llm_utils import complete

        learnings_block = "\n\n".join(
            f"=== {fname} ===\n{content}" for fname, content in learnings
        )
        prompt = DIGEST_PROMPT.format(learnings_block=learnings_block)
        log.info("Calling Gemini to synthesize %d char(s) of learnings...", len(learnings_block))
        raw = complete(prompt, model_tier="pro")

        digest_text = (
            f"# IRON STATIC — Session Learnings Digest\n"
            f"*Generated: {date.today()} from {len(learnings)} session file(s)*\n\n"
            f"---\n\n"
            + raw
        )

    if args.dry_run:
        print(digest_text)
        sys.exit(0)

    DIGEST_FILE.write_text(digest_text)
    log.info("Written: %s (%d chars)", DIGEST_FILE.relative_to(REPO_ROOT), len(digest_text))

    # Count bullets written (handles both - and * list markers)
    bullet_count = digest_text.count("\n- ") + digest_text.count("\n*   ")
    log.info("Digest contains ~%d bullet entries.", bullet_count)


if __name__ == "__main__":
    main()
