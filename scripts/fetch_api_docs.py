#!/usr/bin/env python3
"""
fetch_api_docs.py — Pull all Ableton Live / Max for Live API documentation verbatim.

Downloads:
  - All 45 LOM object pages from docs.cycling74.com/apiref/lom/
  - M4L user guide pages from docs.cycling74.com/userguide/m4l/
  - Max JS API reference from docs.cycling74.com/apiref/js/
  - Max object reference pages (live.path, live.object, live.observer, etc.)
  - Ableton Live 12 manual PDF from cdn-resources.ableton.com

Output structure:
  docs/api/
    INDEX.md                         table of contents for all downloaded docs
    ableton/
      live12-manual-en.pdf           Ableton Live 12 full reference manual (PDF)
    lom/                             Live Object Model — 45 object class pages
      index.md
      application.md
      song.md
      ... (all objects)
    m4l/                             Max for Live user guide
      live_api_overview.md
      live_api.md
    js/                              Max JavaScript API
      index.md
      liveapi.md
    max-objects/                     Max object reference pages
      live.path.md
      live.object.md
      live.observer.md
      live.remote~.md
      live.thisdevice.md

Usage:
  python scripts/fetch_api_docs.py               # download everything
  python scripts/fetch_api_docs.py --dry-run     # check URLs, don't write files
  python scripts/fetch_api_docs.py --force       # re-download even if file exists
  python scripts/fetch_api_docs.py --section lom # download only one section
  python scripts/fetch_api_docs.py --pdf-only    # download only the Ableton PDF
  python scripts/fetch_api_docs.py --no-pdf      # skip the large PDF download

Exit codes:
  0 — all pages downloaded successfully (or already up to date)
  1 — one or more pages failed (check logs)
"""
import argparse
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None  # type: ignore

try:
    import html2text as _html2text
except ImportError:
    _html2text = None  # type: ignore

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = REPO_ROOT / "docs" / "api"

BASE_C74 = "https://docs.cycling74.com"
FETCH_DELAY = 1.5  # seconds between requests — be polite to cycling74

HEADERS = {
    "User-Agent": "IRON-STATIC-fetch-api-docs/1.0 (https://github.com/djaboxx/iron-static)",
    "Accept": "text/html,application/xhtml+xml,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}

# ─── URL REGISTRY ─────────────────────────────────────────────────────────────
# Each entry: (filename_stem, path, display_title)

LOM_PAGES: list[tuple[str, str, str]] = [
    ("index",                    "/apiref/lom/",                           "LOM — Overview & Object List"),
    ("application",              "/apiref/lom/application/",               "Application"),
    ("application_view",         "/apiref/lom/application_view/",          "Application.View"),
    ("chain",                    "/apiref/lom/chain/",                     "Chain"),
    ("chainmixerdevice",         "/apiref/lom/chainmixerdevice/",          "ChainMixerDevice"),
    ("clip",                     "/apiref/lom/clip/",                      "Clip"),
    ("clip_view",                "/apiref/lom/clip_view/",                 "Clip.View"),
    ("clipslot",                 "/apiref/lom/clipslot/",                  "ClipSlot"),
    ("compressordevice",         "/apiref/lom/compressordevice/",          "CompressorDevice"),
    ("controlsurface",           "/apiref/lom/controlsurface/",            "ControlSurface"),
    ("cuepoint",                 "/apiref/lom/cuepoint/",                  "CuePoint"),
    ("device",                   "/apiref/lom/device/",                    "Device"),
    ("device_view",              "/apiref/lom/device_view/",               "Device.View"),
    ("deviceio",                 "/apiref/lom/deviceio/",                  "DeviceIO"),
    ("deviceparameter",          "/apiref/lom/deviceparameter/",           "DeviceParameter"),
    ("driftdevice",              "/apiref/lom/driftdevice/",               "DriftDevice"),
    ("drumcelldevice",           "/apiref/lom/drumcelldevice/",            "DrumCellDevice"),
    ("drumchain",                "/apiref/lom/drumchain/",                 "DrumChain"),
    ("drumpad",                  "/apiref/lom/drumpad/",                   "DrumPad"),
    ("eq8device",                "/apiref/lom/eq8device/",                 "Eq8Device"),
    ("eq8device_view",           "/apiref/lom/eq8device_view/",            "Eq8Device.View"),
    ("groove",                   "/apiref/lom/groove/",                    "Groove"),
    ("groovepool",               "/apiref/lom/groovepool/",                "GroovePool"),
    ("hybridreverbdevice",       "/apiref/lom/hybridreverbdevice/",        "HybridReverbDevice"),
    ("looperdevice",             "/apiref/lom/looperdevice/",              "LooperDevice"),
    ("maxdevice",                "/apiref/lom/maxdevice/",                 "MaxDevice"),
    ("melddevice",               "/apiref/lom/melddevice/",                "MeldDevice"),
    ("mixerdevice",              "/apiref/lom/mixerdevice/",               "MixerDevice"),
    ("plugindevice",             "/apiref/lom/plugindevice/",              "PluginDevice"),
    ("rackdevice",               "/apiref/lom/rackdevice/",                "RackDevice"),
    ("rackdevice_view",          "/apiref/lom/rackdevice_view/",           "RackDevice.View"),
    ("roardevice",               "/apiref/lom/roardevice/",                "RoarDevice"),
    ("sample",                   "/apiref/lom/sample/",                    "Sample"),
    ("scene",                    "/apiref/lom/scene/",                     "Scene"),
    ("shifterdevice",            "/apiref/lom/shifterdevice/",             "ShifterDevice"),
    ("simplerdevice",            "/apiref/lom/simplerdevice/",             "SimplerDevice"),
    ("simplerdevice_view",       "/apiref/lom/simplerdevice_view/",        "SimplerDevice.View"),
    ("song",                     "/apiref/lom/song/",                      "Song"),
    ("song_view",                "/apiref/lom/song_view/",                 "Song.View"),
    ("spectralresonatordevice",  "/apiref/lom/spectralresonatordevice/",   "SpectralResonatorDevice"),
    ("takelane",                 "/apiref/lom/takelane/",                  "TakeLane"),
    ("this_device",              "/apiref/lom/this_device/",               "this_device"),
    ("track",                    "/apiref/lom/track/",                     "Track"),
    ("track_view",               "/apiref/lom/track_view/",                "Track.View"),
    ("tuningsystem",             "/apiref/lom/tuningsystem/",              "TuningSystem"),
    ("wavetabledevice",          "/apiref/lom/wavetabledevice/",           "WavetableDevice"),
]

M4L_PAGES: list[tuple[str, str, str]] = [
    ("live_api_overview",        "/userguide/m4l/live_api_overview/",      "Live API Overview"),
    ("live_api",                 "/userguide/m4l/live_api/",               "Creating Devices that use the Live API"),
]

JS_PAGES: list[tuple[str, str, str]] = [
    ("index",                    "/apiref/js/",                            "Max JavaScript API — Index"),
    ("liveapi",                  "/apiref/js/liveapi/",                    "LiveAPI class"),
]

MAX_OBJECT_PAGES: list[tuple[str, str, str]] = [
    ("live.path",                "/reference/live.path/",                  "live.path"),
    ("live.object",              "/reference/live.object/",                "live.object"),
    ("live.observer",            "/reference/live.observer/",              "live.observer"),
    ("live.remote~",             "/reference/live.remote~/",               "live.remote~"),
    ("live.thisdevice",          "/reference/live.thisdevice/",            "live.thisdevice"),
    ("live.numbox",              "/reference/live.numbox/",                "live.numbox"),
    ("live.dial",                "/reference/live.dial/",                  "live.dial"),
    ("live.slider",              "/reference/live.slider/",                "live.slider"),
    ("live.menu",                "/reference/live.menu/",                  "live.menu"),
    ("live.text",                "/reference/live.text/",                  "live.text"),
]

# Ableton Live 12 manual PDF
ABLETON_PDF_URL = (
    "https://cdn-resources.ableton.com/resources/pdfs/live-manual/12/2026-03-20/live12-manual-en.pdf"
)
ABLETON_PDF_FILENAME = "live12-manual-en.pdf"

# Section map: section name → (subdir, page_list, base_url)
SECTIONS: dict[str, tuple[str, list[tuple[str, str, str]], str]] = {
    "lom":         ("lom",          LOM_PAGES,          BASE_C74),
    "m4l":         ("m4l",          M4L_PAGES,          BASE_C74),
    "js":          ("js",           JS_PAGES,           BASE_C74),
    "max-objects": ("max-objects",  MAX_OBJECT_PAGES,   BASE_C74),
}


# ─── HTTP HELPERS ─────────────────────────────────────────────────────────────

def _fetch_html(url: str) -> str:
    """Fetch a URL and return decoded HTML body. Raises RuntimeError on failure."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} — {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error — {url}: {exc.reason}") from exc


def _fetch_binary(url: str) -> bytes:
    """Fetch a URL and return raw bytes (for PDFs etc.)."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} — {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error — {url}: {exc.reason}") from exc


# ─── HTML → MARKDOWN CONVERSION ───────────────────────────────────────────────

def _extract_article_html(html: str, url: str) -> str:
    """
    Extract only the main article content from a cycling74.com page.
    Returns the inner HTML of the article element, or full body if not found.
    """
    if BeautifulSoup is None:
        log.warning("beautifulsoup4 not available — returning raw HTML")
        return html

    soup = BeautifulSoup(html, "html.parser")

    # cycling74 docs use a stable class "c74-article-content" on the article element
    article = soup.find("article", class_="c74-article-content")
    if article:
        # Remove copy-to-clipboard buttons (noise)
        for btn in article.find_all("button"):
            btn.decompose()
        return str(article)

    # Fallback: try <main> content
    main = soup.find("main")
    if main:
        log.debug("No c74-article-content found, falling back to <main> for %s", url)
        return str(main)

    log.warning("No article or main element found for %s — using full body", url)
    body = soup.find("body")
    return str(body) if body else html


def _html_to_markdown(html_fragment: str, source_url: str) -> str:
    """Convert an HTML fragment to clean markdown."""
    if _html2text is None:
        # Fallback: basic tag stripping if html2text not installed
        log.warning("html2text not available — falling back to basic text extraction")
        return _basic_strip(html_fragment)

    h = _html2text.HTML2Text()
    h.ignore_links = False
    h.body_width = 0           # no line wrapping
    h.protect_links = True
    h.unicode_snob = True
    h.wrap_links = False
    h.ignore_images = True     # skip image tags (src would be broken offline anyway)
    h.ignore_emphasis = False
    h.mark_code = True

    md = h.handle(html_fragment)

    # Prepend source URL as a comment for traceability
    header = f"> **Source**: {source_url}  \n> **Fetched**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}  \n\n"
    return header + md.strip() + "\n"


def _basic_strip(html: str) -> str:
    """Minimal HTML stripper — used only if html2text is unavailable."""
    import re
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<(br|p|div|h[1-6]|li|tr)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    for e, c in [("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " ")]:
        text = text.replace(e, c)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ─── DOWNLOAD LOGIC ───────────────────────────────────────────────────────────

def download_page(
    filename_stem: str,
    path: str,
    title: str,
    base_url: str,
    out_dir: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """
    Download one documentation page and save as markdown.
    Returns True on success, False on failure.
    """
    url = base_url + path
    out_file = out_dir / f"{filename_stem}.md"

    if out_file.exists() and not force:
        log.debug("  SKIP (exists) — %s", out_file.name)
        return True

    log.info("  GET %s", url)

    if dry_run:
        log.info("    [dry-run] would write %s", out_file)
        return True

    try:
        html = _fetch_html(url)
    except RuntimeError as exc:
        log.error("  FAIL — %s", exc)
        return False

    article_html = _extract_article_html(html, url)
    markdown = _html_to_markdown(article_html, url)

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file.write_text(markdown, encoding="utf-8")
    log.info("    → %s (%d chars)", out_file.relative_to(REPO_ROOT), len(markdown))
    return True


def download_pdf(
    url: str,
    filename: str,
    out_dir: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> bool:
    """Download the Ableton Live manual PDF."""
    out_file = out_dir / filename

    if out_file.exists() and not force:
        size_mb = out_file.stat().st_size / (1024 * 1024)
        log.info("  SKIP (exists, %.1f MB) — %s", size_mb, out_file.name)
        return True

    log.info("  GET %s (PDF — may take a moment…)", url)

    if dry_run:
        log.info("    [dry-run] would write %s", out_file)
        return True

    try:
        data = _fetch_binary(url)
    except RuntimeError as exc:
        log.error("  FAIL — %s", exc)
        return False

    out_dir.mkdir(parents=True, exist_ok=True)
    out_file.write_bytes(data)
    size_mb = len(data) / (1024 * 1024)
    log.info("    → %s (%.1f MB)", out_file.relative_to(REPO_ROOT), size_mb)
    return True


def download_section(
    section_name: str,
    subdir: str,
    pages: list[tuple[str, str, str]],
    base_url: str,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Download all pages in a section.
    Returns (success_count, fail_count).
    """
    out_dir = OUTPUT_DIR / subdir
    log.info("\n─── Section: %s → docs/api/%s/ (%d pages)", section_name, subdir, len(pages))

    success = 0
    failures = 0

    for i, (stem, path, title) in enumerate(pages):
        ok = download_page(stem, path, title, base_url, out_dir, force=force, dry_run=dry_run)
        if ok:
            success += 1
        else:
            failures += 1

        # Rate limit (skip delay after last item in section)
        if i < len(pages) - 1:
            time.sleep(FETCH_DELAY)

    return success, failures


def write_index(sections_results: dict[str, tuple[int, int]], dry_run: bool) -> None:
    """Write docs/api/INDEX.md with a table of contents."""
    lines = [
        "# IRON STATIC — Ableton + Max for Live API Documentation",
        "",
        f"> **Downloaded**: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}  ",
        f"> Run `python scripts/fetch_api_docs.py --force` to refresh all pages.",
        "",
        "Verbatim developer reference pulled from Cycling '74 and Ableton documentation.",
        "For the IRON STATIC rig context, see [docs/lom-api-ref.md](../lom-api-ref.md).",
        "",
        "---",
        "",
        "## Cycling '74 — Live Object Model (LOM)",
        "",
        "All LOM object classes for Live 12. Path: `docs/api/lom/`",
        "",
        "| File | Title | Source |",
        "|---|---|---|",
    ]

    for stem, path, title in LOM_PAGES:
        url = BASE_C74 + path
        lines.append(f"| [lom/{stem}.md](lom/{stem}.md) | {title} | [{url}]({url}) |")

    lines += [
        "",
        "---",
        "",
        "## Cycling '74 — Max for Live User Guide",
        "",
        "How-to guides for using the Live API from Max for Live devices. Path: `docs/api/m4l/`",
        "",
        "| File | Title | Source |",
        "|---|---|---|",
    ]
    for stem, path, title in M4L_PAGES:
        url = BASE_C74 + path
        lines.append(f"| [m4l/{stem}.md](m4l/{stem}.md) | {title} | [{url}]({url}) |")

    lines += [
        "",
        "---",
        "",
        "## Cycling '74 — Max JavaScript API",
        "",
        "LiveAPI JS class for scripting the LOM from `js` objects. Path: `docs/api/js/`",
        "",
        "| File | Title | Source |",
        "|---|---|---|",
    ]
    for stem, path, title in JS_PAGES:
        url = BASE_C74 + path
        lines.append(f"| [js/{stem}.md](js/{stem}.md) | {title} | [{url}]({url}) |")

    lines += [
        "",
        "---",
        "",
        "## Cycling '74 — Max Object Reference",
        "",
        "Reference pages for the Max objects that implement the Live API. Path: `docs/api/max-objects/`",
        "",
        "| File | Title | Source |",
        "|---|---|---|",
    ]
    # Deduplicate by stem (live.thisdevice appears twice in the list)
    seen_stems: set[str] = set()
    for stem, path, title in MAX_OBJECT_PAGES:
        if stem in seen_stems:
            continue
        seen_stems.add(stem)
        url = BASE_C74 + path
        lines.append(f"| [max-objects/{stem}.md](max-objects/{stem}.md) | {title} | [{url}]({url}) |")

    lines += [
        "",
        "---",
        "",
        "## Ableton — Live 12 Reference Manual",
        "",
        "The complete Ableton Live 12 user manual as a PDF. Path: `docs/api/ableton/`",
        "",
        "| File | Description | Source |",
        "|---|---|---|",
        f"| [ableton/{ABLETON_PDF_FILENAME}](ableton/{ABLETON_PDF_FILENAME}) | Ableton Live 12 Reference Manual (EN) | [{ABLETON_PDF_URL}]({ABLETON_PDF_URL}) |",
        "",
        "---",
        "",
        "## Download Status",
        "",
        "| Section | Downloaded | Failed |",
        "|---|---|---|",
    ]

    for section_name, (success, failures) in sections_results.items():
        lines.append(f"| {section_name} | {success} | {failures} |")

    lines.append("")
    content = "\n".join(lines)

    if not dry_run:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUT_DIR / "INDEX.md").write_text(content, encoding="utf-8")
        log.info("Wrote docs/api/INDEX.md")
    else:
        log.info("[dry-run] would write docs/api/INDEX.md")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download all Ableton + Max for Live API docs verbatim to docs/api/."
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Check URLs and report; do not write any files.")
    parser.add_argument("--force", action="store_true",
                        help="Re-download and overwrite files that already exist.")
    parser.add_argument("--section", choices=list(SECTIONS.keys()),
                        help="Download only one section (lom, m4l, js, max-objects).")
    parser.add_argument("--pdf-only", action="store_true",
                        help="Download only the Ableton Live 12 manual PDF.")
    parser.add_argument("--no-pdf", action="store_true",
                        help="Skip the Ableton manual PDF download.")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Verbose logging.")
    args = parser.parse_args(argv)

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s  %(message)s")

    # Verify dependencies
    if BeautifulSoup is None:
        log.error("beautifulsoup4 is required. Run: pip install beautifulsoup4")
        return 1
    if _html2text is None:
        log.warning("html2text not installed — output will be plain text. Run: pip install html2text")

    sections_results: dict[str, tuple[int, int]] = {}

    # ── PDF only mode ────────────────────────────────────────────────────────
    if args.pdf_only:
        ok = download_pdf(
            ABLETON_PDF_URL,
            ABLETON_PDF_FILENAME,
            OUTPUT_DIR / "ableton",
            force=args.force,
            dry_run=args.dry_run,
        )
        return 0 if ok else 1

    # ── HTML sections ────────────────────────────────────────────────────────
    sections_to_run = (
        {args.section: SECTIONS[args.section]} if args.section else SECTIONS
    )

    total_success = 0
    total_fail = 0

    for section_name, (subdir, pages, base_url) in sections_to_run.items():
        success, failures = download_section(
            section_name, subdir, pages, base_url,
            force=args.force, dry_run=args.dry_run,
        )
        sections_results[section_name] = (success, failures)
        total_success += success
        total_fail += failures
        time.sleep(FETCH_DELAY)  # pause between sections

    # ── PDF ──────────────────────────────────────────────────────────────────
    if not args.no_pdf and not args.section:
        log.info("\n─── Section: ableton-pdf → docs/api/ableton/")
        ok = download_pdf(
            ABLETON_PDF_URL,
            ABLETON_PDF_FILENAME,
            OUTPUT_DIR / "ableton",
            force=args.force,
            dry_run=args.dry_run,
        )
        sections_results["ableton-pdf"] = (1 if ok else 0, 0 if ok else 1)
        total_fail += 0 if ok else 1

    # ── INDEX ─────────────────────────────────────────────────────────────────
    write_index(sections_results, dry_run=args.dry_run)

    # ── Summary ──────────────────────────────────────────────────────────────
    total_pages = total_success + total_fail
    log.info("\n✓ Done: %d/%d pages succeeded.", total_success, total_pages)
    if total_fail:
        log.warning("  %d page(s) failed — check logs above.", total_fail)

    if args.dry_run:
        log.info("  (dry-run — no files written)")

    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
