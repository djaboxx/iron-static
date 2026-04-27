#!/usr/bin/env python3
"""
refresh_lom_docs.py — Keep docs/lom-api-ref.md current with cycling74.com documentation.

Fetches the Live API Overview and LOM object reference pages from docs.cycling74.com,
detects changes against the previously cached content, and updates the version/date
header in docs/lom-api-ref.md. Saves raw page cache to database/lom_cache/ for diff tracking.

Usage:
  python scripts/refresh_lom_docs.py                    # check + update
  python scripts/refresh_lom_docs.py --dry-run          # show diff, don't write
  python scripts/refresh_lom_docs.py --force            # update even if no change detected
  python scripts/refresh_lom_docs.py --output <path>    # write to alternate file

Exit codes:
  0 — success (no changes detected or updates applied)
  1 — error (network failure, parse error)
  2 — changes detected but --dry-run was set (use in CI to flag doc drift)
"""
import argparse
import hashlib
import json
import logging
import re
import sys
import urllib.request
import urllib.error
from datetime import date, datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
DOCS_PATH = REPO_ROOT / "docs" / "lom-api-ref.md"
CACHE_DIR = REPO_ROOT / "database" / "lom_cache"
CHANGELOG_PATH = REPO_ROOT / "database" / "lom_cache" / "changelog.jsonl"

# Pages to track. Each entry: (slug, url, section_header_in_doc)
LOM_PAGES = [
    ("overview", "https://docs.cycling74.com/userguide/m4l/live_api_overview/", "Live API Overview"),
    ("lom-index", "https://docs.cycling74.com/apiref/lom/", "LOM Index"),
    ("song", "https://docs.cycling74.com/apiref/lom/song/", "Song"),
    ("track", "https://docs.cycling74.com/apiref/lom/track/", "Track"),
    ("device", "https://docs.cycling74.com/apiref/lom/device/", "Device"),
    ("rackdevice", "https://docs.cycling74.com/apiref/lom/rackdevice/", "RackDevice"),
    ("chain", "https://docs.cycling74.com/apiref/lom/chain/", "Chain"),
    ("clip", "https://docs.cycling74.com/apiref/lom/clip/", "Clip"),
    ("clipslot", "https://docs.cycling74.com/apiref/lom/clipslot/", "ClipSlot"),
    ("scene", "https://docs.cycling74.com/apiref/lom/scene/", "Scene"),
    ("deviceparameter", "https://docs.cycling74.com/apiref/lom/deviceparameter/", "DeviceParameter"),
    ("mixerdevice", "https://docs.cycling74.com/apiref/lom/mixerdevice/", "MixerDevice"),
    ("application", "https://docs.cycling74.com/apiref/lom/application/", "Application"),
    ("liveapi-js", "https://docs.cycling74.com/apiref/js/liveapi/", "LiveAPI JS"),
]

HEADERS = {
    "User-Agent": "IRON-STATIC-refresh-lom-docs/1.0 (https://github.com/djaboxx/iron-static)",
    "Accept": "text/html,application/xhtml+xml",
}

# Regex to match the "Last refreshed" line in the doc header
REFRESH_DATE_RE = re.compile(
    r"(>\s*Last refreshed:\s*)[\d\-]+(\s*—\s*maintained by `scripts/refresh_lom_docs\.py`)"
)
VERSION_LINE_RE = re.compile(r"(>\s*Ableton Live version:\s*\*\*)([\d\.]+)(\*\*)")


def _fetch(url: str) -> str:
    """Fetch a URL and return the body text. Raises on HTTP error."""
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            charset = "utf-8"
            ct = resp.headers.get_content_charset()
            if ct:
                charset = ct
            return raw.decode(charset, errors="replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code} fetching {url}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error fetching {url}: {exc.reason}") from exc


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _strip_html(html: str) -> str:
    """Very lightweight HTML → plain text strip (no external deps)."""
    # Remove script/style blocks
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Replace block elements with newlines
    text = re.sub(r"<(br|p|div|h[1-6]|li|tr|th|td)[^>]*>", "\n", text, flags=re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode common HTML entities
    for entity, char in [
        ("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
        ("&quot;", '"'), ("&#39;", "'"), ("&nbsp;", " "),
    ]:
        text = text.replace(entity, char)
    # Collapse whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def load_cache() -> dict:
    """Load the hash cache from disk. Returns {slug: {hash, fetched_at}}."""
    cache_file = CACHE_DIR / "hashes.json"
    if cache_file.exists():
        try:
            return json.loads(cache_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            log.warning("Cache file corrupt — starting fresh.")
    return {}


def save_cache(cache: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / "hashes.json").write_text(
        json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8"
    )


def save_raw(slug: str, content: str) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / f"{slug}.txt").write_text(content, encoding="utf-8")


def append_changelog(entry: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with CHANGELOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def check_pages(dry_run: bool, force: bool) -> tuple[bool, list[str]]:
    """
    Fetch all pages, compare hashes to cache.
    Returns (any_changed: bool, changed_slugs: list[str]).
    """
    cache = load_cache()
    changed: list[str] = []
    now_iso = datetime.now(timezone.utc).isoformat()

    for slug, url, _ in LOM_PAGES:
        log.info("Fetching %s (%s)", slug, url)
        try:
            html = _fetch(url)
        except RuntimeError as exc:
            log.error("  SKIP — %s", exc)
            continue

        text = _strip_html(html)
        new_hash = _sha256(text)
        old = cache.get(slug, {})
        old_hash = old.get("hash", "")

        if new_hash != old_hash or force:
            if old_hash:
                log.info("  CHANGED — %s", slug)
                changed.append(slug)
                append_changelog({
                    "event": "changed",
                    "slug": slug,
                    "url": url,
                    "old_hash": old_hash,
                    "new_hash": new_hash,
                    "detected_at": now_iso,
                })
            else:
                log.info("  NEW — %s", slug)
                changed.append(slug)
                append_changelog({
                    "event": "first_fetch",
                    "slug": slug,
                    "url": url,
                    "hash": new_hash,
                    "fetched_at": now_iso,
                })

            if not dry_run:
                save_raw(slug, text)
                cache[slug] = {"hash": new_hash, "fetched_at": now_iso, "url": url}
        else:
            log.info("  unchanged — %s", slug)
            # Always update the fetched_at timestamp
            cache[slug]["fetched_at"] = now_iso

    if not dry_run:
        save_cache(cache)

    return bool(changed), changed


def update_doc_header(doc_path: Path, changed_slugs: list[str], dry_run: bool) -> str:
    """
    Update the 'Last refreshed' line in the doc.
    Returns the updated content (does not write to disk in dry_run mode).
    """
    content = doc_path.read_text(encoding="utf-8")
    today = date.today().isoformat()

    new_content = REFRESH_DATE_RE.sub(
        lambda m: f"{m.group(1)}{today}{m.group(2)}",
        content,
        count=1,
    )

    if new_content == content:
        log.warning("Could not find 'Last refreshed' line in %s — header not updated.", doc_path)

    if changed_slugs:
        note = f"\n> **Drift detected {today}**: pages changed: {', '.join(changed_slugs)}. Review and update manually.\n"
        # Insert after the header block (after the last `>` line at the top)
        new_content = re.sub(
            r"((?:^>.*\n)+)",
            lambda m: m.group(0) + note if "Drift detected" not in m.group(0) else m.group(0),
            new_content,
            count=1,
            flags=re.MULTILINE,
        )

    if not dry_run:
        doc_path.write_text(new_content, encoding="utf-8")
        log.info("Updated header in %s", doc_path)

    return new_content


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fetch cycling74.com LOM docs and update docs/lom-api-ref.md header."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Check for changes but do not write anything to disk. Exit code 2 if drift found.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-cache all pages even if hashes match (use after wiping cache).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DOCS_PATH,
        help=f"Path to lom-api-ref.md (default: {DOCS_PATH})",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show per-page status.",
    )
    args = parser.parse_args(argv)

    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(levelname)s  %(message)s")

    log.info("Checking %d LOM documentation pages…", len(LOM_PAGES))

    any_changed, changed_slugs = check_pages(dry_run=args.dry_run, force=args.force)

    if any_changed or args.force:
        log.info("Pages changed: %s", changed_slugs or "(force flag)")
        update_doc_header(args.output, changed_slugs, dry_run=args.dry_run)

        if changed_slugs:
            print("\n⚠️  Documentation drift detected. Changed pages:")
            for slug in changed_slugs:
                url = next(u for s, u, _ in LOM_PAGES if s == slug)
                print(f"   {slug}  {url}")
            print(f"\nReview the diffs in {CACHE_DIR}/ and update docs/lom-api-ref.md manually.")
            if args.dry_run:
                return 2
    else:
        log.info("All pages unchanged — no update needed.")

    print(f"\n✓ LOM docs check complete. Cache: {CACHE_DIR}/hashes.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
