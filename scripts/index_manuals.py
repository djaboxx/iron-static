#!/usr/bin/env python3
"""
index_manuals.py — Extract and index text from all instrument manuals.

For each PDF in instruments/[slug]/manuals/, produces:
  [name].txt        — full extracted text (grep-friendly, one line per PDF line)
  [name].index.json — page-level JSON with detected section headings

This is idempotent: a manual is re-indexed only if the PDF is newer than its
existing .index.json, or if --force is passed.

Usage:
  python scripts/index_manuals.py                       # all instruments
  python scripts/index_manuals.py --instrument rev2     # one instrument
  python scripts/index_manuals.py --force               # always re-index
  python scripts/index_manuals.py --list                # list index status
"""

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

log = logging.getLogger("index_manuals")

REPO_ROOT = Path(__file__).parent.parent

INSTRUMENT_SLUGS = {
    "rev2":         "sequential-rev2",
    "take5":        "sequential-take5",
    "digitakt":     "elektron-digitakt-mk1",
    "dfam":         "moog-dfam",
    "subharmonicon":"moog-subharmonicon",
    "minibrute2s":  "arturia-minibrute-2s",
    "rytm":         "elektron-analog-rytm",
    "pigments":     "arturia-pigments",
}

# ---------------------------------------------------------------------------
# PDF extraction
# ---------------------------------------------------------------------------

def extract_text_pdftotext(pdf_path: Path) -> list[str] | None:
    """
    Use system pdftotext to extract text, one page per separator.
    Returns list of page strings (1-indexed: pages[0] = page 1).
    Returns None if pdftotext is not available.
    """
    if not shutil.which("pdftotext"):
        return None
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), "-"],
        capture_output=True, text=True, errors="replace"
    )
    if result.returncode != 0:
        log.warning("pdftotext error: %s", result.stderr[:200])
        return None
    # pdftotext separates pages with \f (form feed)
    pages = result.stdout.split("\f")
    # Drop trailing empty page added by pdftotext
    while pages and not pages[-1].strip():
        pages.pop()
    return pages


def extract_text_pypdf(pdf_path: Path) -> list[str] | None:
    """Fallback: use pypdf if pdftotext is not available."""
    try:
        import pypdf
    except ImportError:
        return None
    try:
        reader = pypdf.PdfReader(str(pdf_path))
        return [page.extract_text() or "" for page in reader.pages]
    except Exception as e:
        log.warning("pypdf error: %s", e)
        return None


def extract_pages(pdf_path: Path) -> list[str]:
    pages = extract_text_pdftotext(pdf_path)
    if pages is None:
        pages = extract_text_pypdf(pdf_path)
    if pages is None:
        log.error("No PDF extraction backend available. Install pdftotext (poppler) or pypdf.")
        sys.exit(1)
    return pages

# ---------------------------------------------------------------------------
# Section heading detection
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(
    r'^('
    r'(Chapter|Appendix|Section|Part)\s+\S+'       # Chapter/Appendix N
    r'|[A-Z][A-Za-z0-9 /\-]{2,50}'                 # Title case line
    r'|\d+\.\d*\s+[A-Z][A-Za-z].*'                 # 3.1 Heading
    r')\s*$'
)

_SKIP_RE = re.compile(
    r'^\d+$'                                        # bare page numbers
    r'|^[.\-_\s]+$'                                 # separator lines
    r'|^(www\.|http)'                               # URLs
)


def detect_sections(pages: list[str]) -> list[dict]:
    """
    Detect section headings across all pages.
    Returns list of {title, page, line_offset} dicts (page is 1-based).
    """
    sections = []
    seen_titles: set[str] = set()
    for page_num, page_text in enumerate(pages, start=1):
        for line in page_text.splitlines():
            stripped = line.strip()
            if not stripped or _SKIP_RE.search(stripped):
                continue
            if len(stripped) > 70:
                continue
            if _HEADING_RE.match(stripped):
                title = stripped
                if title not in seen_titles:
                    sections.append({"title": title, "page": page_num})
                    seen_titles.add(title)
    return sections

# ---------------------------------------------------------------------------
# Core indexer
# ---------------------------------------------------------------------------

def index_manual(pdf_path: Path, force: bool = False) -> dict:
    """
    Index a single PDF manual.
    Writes .txt and .index.json alongside the PDF.
    Returns the index dict.
    """
    txt_path   = pdf_path.with_suffix(".txt")
    index_path = pdf_path.with_suffix(".index.json")

    if not force and index_path.exists():
        pdf_mtime   = pdf_path.stat().st_mtime
        index_mtime = index_path.stat().st_mtime
        if index_mtime > pdf_mtime:
            log.info("  Already indexed (up to date): %s", pdf_path.name)
            return json.loads(index_path.read_text())

    log.info("  Indexing: %s", pdf_path.name)
    pages = extract_pages(pdf_path)
    sections = detect_sections(pages)

    # Write flat .txt (each page separated by a marker line)
    lines = []
    for i, page_text in enumerate(pages, start=1):
        lines.append(f"=== PAGE {i} ===")
        lines.append(page_text)
    txt_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("    Wrote %s (%d pages, %d chars)",
             txt_path.name, len(pages), txt_path.stat().st_size)

    # Write JSON index (without full page text to keep it light)
    index = {
        "manual":       pdf_path.name,
        "pdf_path":     str(pdf_path.relative_to(REPO_ROOT)),
        "txt_path":     str(txt_path.relative_to(REPO_ROOT)),
        "indexed_at":   datetime.now().isoformat(),
        "page_count":   len(pages),
        "sections":     sections,
    }
    index_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    log.info("    Wrote %s (%d sections detected)", index_path.name, len(sections))

    return index

# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_index(args):
    target = args.instrument
    total = 0

    for slug_key, folder_slug in INSTRUMENT_SLUGS.items():
        if target and slug_key != target:
            continue

        manual_dir = REPO_ROOT / "instruments" / folder_slug / "manuals"
        pdfs = sorted(manual_dir.glob("*.pdf"))
        if not pdfs:
            log.warning("No PDFs found for %s (%s)", slug_key, manual_dir)
            continue

        print(f"\n{folder_slug}")
        for pdf in pdfs:
            index = index_manual(pdf, force=args.force)
            total += 1

    print(f"\nDone. {total} manual(s) indexed.")
    print("Search tip: grep -n 'keyword' instruments/[slug]/manuals/[name].txt")


def cmd_list(_args):
    print(f"\n{'Instrument':<25} {'Manual':<45} {'Pages':>6}  {'Sections':>8}  Status")
    print("-" * 100)
    for slug_key, folder_slug in INSTRUMENT_SLUGS.items():
        manual_dir = REPO_ROOT / "instruments" / folder_slug / "manuals"
        pdfs = sorted(manual_dir.glob("*.pdf"))
        for pdf in pdfs:
            index_path = pdf.with_suffix(".index.json")
            if index_path.exists():
                idx = json.loads(index_path.read_text())
                status = "indexed"
                pages = idx.get("page_count", "?")
                nsec  = len(idx.get("sections", []))
            else:
                status = "NOT INDEXED"
                pages  = "?"
                nsec   = "?"
            print(f"{folder_slug:<25} {pdf.name:<45} {str(pages):>6}  {str(nsec):>8}  {status}")
    print()

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="Index IRON STATIC instrument manuals for fast text search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    idx = sub.add_parser("index", help="Index manuals (default command)")
    idx.add_argument("--instrument", choices=list(INSTRUMENT_SLUGS.keys()),
                     default=None, help="Index a single instrument (default: all)")
    idx.add_argument("--force", action="store_true",
                     help="Re-index even if already up to date")

    sub.add_parser("list", help="Show index status for all manuals")

    args = parser.parse_args()

    # Default to 'index' if no subcommand given
    if args.command is None:
        # Inject default subcommand args
        args.command    = "index"
        args.instrument = None
        args.force      = False

    if args.command == "index":
        cmd_index(args)
    elif args.command == "list":
        cmd_list(args)


if __name__ == "__main__":
    main()
