#!/usr/bin/env python3
"""
extract_pdf_docs.py — Extract Ableton Live 12 manual PDF into per-chapter markdown files.

Reads docs/api/ableton/live12-manual-en.pdf, splits by top-level TOC chapters,
and writes one .md file per chapter to docs/api/ableton/.

Usage:
    python scripts/extract_pdf_docs.py [--force] [--verbose] [--chapter N]
"""

import argparse
import logging
import re
import sys
from pathlib import Path

try:
    import pymupdf  # PyMuPDF ≥ 1.24
except ImportError:
    print("ERROR: pymupdf not installed. Run: pip install pymupdf", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
PDF_PATH = REPO_ROOT / "docs" / "api" / "ableton" / "live12-manual-en.pdf"
OUT_DIR = REPO_ROOT / "docs" / "api" / "ableton"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(levelname)-7s %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def slugify(title: str) -> str:
    """Convert a chapter title to a filesystem-safe slug."""
    # Strip leading chapter number like "1. " or "23. "
    title = re.sub(r"^\d+\.\s*", "", title)
    title = title.lower()
    title = re.sub(r"[^\w\s-]", "", title)
    title = re.sub(r"[\s_]+", "-", title.strip())
    title = re.sub(r"-+", "-", title)
    return title[:80]


def heading_marker(level: int) -> str:
    return "#" * min(level, 6)


def clean_text(text: str) -> str:
    """Light cleanup on extracted page text — normalise line endings."""
    # Collapse excessive blank lines (>2) to exactly 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.rstrip()


def extract_chapter(
    doc: pymupdf.Document,
    toc: list,
    chapter_toc_idx: int,
    l1_chapters: list,
    l1_pos: int,
) -> str:
    """Return full markdown text for a single L1 chapter.

    Args:
        doc: PyMuPDF document.
        toc: Full table of contents list from doc.get_toc().
        chapter_toc_idx: Index of this chapter within the full toc list.
        l1_chapters: List of (toc_idx, entry) tuples for L1 chapters only.
        l1_pos: Position of this chapter within l1_chapters.
    """
    level, title, start_page = toc[chapter_toc_idx]
    assert level == 1

    # Page range: ends just before the next L1 chapter (or end of doc).
    if l1_pos + 1 < len(l1_chapters):
        _, (_, _, next_l1_page) = l1_chapters[l1_pos + 1]
        end_page = next_l1_page - 1  # inclusive, 1-based
    else:
        end_page = doc.page_count  # 1-based inclusive

    # Build a lookup: page number → list of (level, sub-title) to inject
    # at the start of that page (for L2+ TOC entries in this chapter's range).
    page_headings: dict[int, list[tuple[int, str]]] = {}
    for entry in toc:
        elevel, etitle, epage = entry
        if elevel > 1 and start_page <= epage <= end_page:
            page_headings.setdefault(epage, []).append((elevel, etitle))

    lines: list[str] = []
    lines.append(f"# {title}\n")

    for page_num in range(start_page, end_page + 1):  # 1-based
        page = doc[page_num - 1]  # pymupdf is 0-based

        # Inject sub-headings from TOC at top of their page
        for hlevel, htitle in page_headings.get(page_num, []):
            marker = heading_marker(hlevel)
            lines.append(f"\n{marker} {htitle}\n")

        page_text = page.get_text("text")  # type: ignore[attr-defined]
        if page_text.strip():
            lines.append(clean_text(page_text))
            lines.append("")  # blank line between pages

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Ableton Live 12 PDF to markdown")
    parser.add_argument("--force", action="store_true", help="Overwrite existing .md files")
    parser.add_argument("--verbose", action="store_true", help="Debug logging")
    parser.add_argument(
        "--chapter",
        type=int,
        metavar="N",
        help="Extract only chapter N (1-based number from PDF TOC)",
    )
    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    if not PDF_PATH.exists():
        log.error("PDF not found: %s", PDF_PATH)
        log.error("Run: python scripts/fetch_api_docs.py --pdf-only")
        sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    log.info("Opening %s", PDF_PATH)
    doc = pymupdf.open(str(PDF_PATH))
    log.info("Pages: %d", doc.page_count)

    toc = doc.get_toc()
    log.debug("TOC entries: %d", len(toc))

    # Collect only L1 entries (chapters), in page order
    chapters = [(i, entry) for i, entry in enumerate(toc) if entry[0] == 1]
    log.info("Chapters found: %d", len(chapters))

    succeeded = 0
    skipped = 0
    failed = 0
    written_files: list[Path] = []

    for l1_pos, (toc_idx, (level, title, start_page)) in enumerate(chapters):
        # Determine chapter number from title if present (e.g. "22. Stem Separation" → 22)
        chapter_num_match = re.match(r"^(\d+)\.", title)
        chapter_num = int(chapter_num_match.group(1)) if chapter_num_match else 0

        # Filter to a specific chapter if requested
        if args.chapter is not None and chapter_num != args.chapter:
            continue

        slug = slugify(title)
        if chapter_num:
            filename = f"{chapter_num:02d}-{slug}.md"
        else:
            filename = f"{slug}.md"

        out_path = OUT_DIR / filename

        if out_path.exists() and not args.force:
            log.info("  SKIP  %s (exists — use --force to overwrite)", filename)
            skipped += 1
            written_files.append(out_path)
            continue

        log.info("  EXTRACT  Chapter %s → %s", title, filename)
        try:
            markdown = extract_chapter(doc, toc, toc_idx, chapters, l1_pos)
            out_path.write_text(markdown, encoding="utf-8")
            size = len(markdown)
            log.info("    → %s (%d chars)", out_path.relative_to(REPO_ROOT), size)
            succeeded += 1
            written_files.append(out_path)
        except Exception as exc:
            log.error("  FAILED %s: %s", filename, exc)
            failed += 1

    # Write INDEX.md listing all chapter files
    index_path = OUT_DIR / "INDEX.md"
    if not index_path.exists() or args.force or succeeded > 0:
        _write_index(chapters, written_files, index_path)

    log.info("")
    log.info(
        "✓ Done: %d extracted, %d skipped, %d failed.",
        succeeded,
        skipped,
        failed,
    )
    if failed:
        sys.exit(1)


def _write_index(chapters: list, written_files: list[Path], index_path: Path) -> None:
    """Write docs/api/ableton/INDEX.md linking all chapter files."""
    lines = [
        "# Ableton Live 12 Manual — Chapter Index",
        "",
        "> Extracted from `live12-manual-en.pdf` by `scripts/extract_pdf_docs.py`.",
        "> Refresh: `python scripts/extract_pdf_docs.py --force`",
        "",
        "| Chapter | File |",
        "|---|---|",
    ]

    for _toc_idx, (level, title, start_page) in chapters:
        chapter_num_match = re.match(r"^(\d+)\.", title)
        chapter_num = int(chapter_num_match.group(1)) if chapter_num_match else 0
        slug = slugify(title)
        filename = f"{chapter_num:02d}-{slug}.md" if chapter_num else f"{slug}.md"
        lines.append(f"| {title} | [{filename}]({filename}) |")

    lines.append("")
    index_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Wrote %s", index_path.relative_to(index_path.parent.parent.parent))


if __name__ == "__main__":
    main()
