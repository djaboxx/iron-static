#!/usr/bin/env python3
"""
fetch_reference_midi.py — Download MIDI files for reference tracks named in the
brainstorm or reference digest, then feed them into pattern_learn.py.

Sources consulted (in order):
  1. bitmidi.com  — large freely indexed MIDI library
  2. Gemini search grounding  — fallback when bitmidi comes up empty

Writes downloaded .mid files to midi/patterns/references/raw/ and calls
pattern_learn.py learn-file --subdir references on each.

Usage:
    # Pull from the latest reference digest JSON sidecar automatically
    python scripts/fetch_reference_midi.py

    # Pull from a specific digest
    python scripts/fetch_reference_midi.py --digest knowledge/references/2026-04-24.json

    # Single ad-hoc track
    python scripts/fetch_reference_midi.py --artist "Nine Inch Nails" --title "March of the Pigs"

    # Dry run (resolve URLs but don't download or learn)
    python scripts/fetch_reference_midi.py --dry-run
"""

import argparse
import json
import logging
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = REPO_ROOT / "midi" / "patterns" / "references" / "raw"
REFERENCES_JSON_DIR = REPO_ROOT / "knowledge" / "references"

# bitmidi search URL — returns HTML with embedded MIDI links
BITMIDI_SEARCH = "https://bitmidi.com/search?q={query}"
BITMIDI_DOWNLOAD_BASE = "https://bitmidi.com/uploads/"

# User-Agent to avoid 403s from bitmidi (standard browser UA)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Rate limit between requests to be polite to the server
_RATE_LIMIT_SECS = 1.5


# ---------------------------------------------------------------------------
# bitmidi search
# ---------------------------------------------------------------------------

def _bitmidi_search(artist: str, title: str) -> str | None:
    """Search bitmidi.com and return the first .mid download URL, or None."""
    query = urllib.parse.quote_plus(f"{artist} {title}")
    search_url = BITMIDI_SEARCH.format(query=query)

    try:
        req = urllib.request.Request(search_url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log.debug("bitmidi search failed for '%s %s': %s", artist, title, e)
        return None

    # bitmidi pages link to MIDI detail pages like href="/artist-track-mid"
    # The actual file downloads are at /uploads/<hash>.mid
    # Strategy: find the first /uploads/ URL in the search results
    match = re.search(r'/uploads/[A-Za-z0-9_\-]+\.mid', html)
    if match:
        return f"https://bitmidi.com{match.group(0)}"

    # Fallback: find a detail page link and scrape it for the download URL
    slug_match = re.search(r'href="(/[a-z0-9\-]+-mid)"', html)
    if not slug_match:
        return None

    detail_url = f"https://bitmidi.com{slug_match.group(1)}"
    time.sleep(_RATE_LIMIT_SECS)
    try:
        req = urllib.request.Request(detail_url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            detail_html = resp.read().decode("utf-8", errors="replace")
        match = re.search(r'/uploads/[A-Za-z0-9_\-]+\.mid', detail_html)
        if match:
            return f"https://bitmidi.com{match.group(0)}"
    except Exception as e:
        log.debug("bitmidi detail scrape failed: %s", e)

    return None


# ---------------------------------------------------------------------------
# Gemini fallback search
# ---------------------------------------------------------------------------

def _gemini_search(artist: str, title: str) -> str | None:
    """Use Gemini to suggest a MIDI download URL when bitmidi comes up empty."""
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from llm_utils import complete  # noqa: PLC0415
    except ImportError:
        return None

    prompt = f"""\
You are a MIDI file researcher. I need to download a standard MIDI (.mid) file for:
  Artist: {artist}
  Track: {title}

Search your knowledge of free MIDI repositories (bitmidi.com, freemidi.org, midi.world,
classicalmidi.co.uk, and similar) and provide exactly ONE direct download URL for a .mid
file of this track. The URL must end in .mid.

If you cannot find a reliable URL, respond with: NONE

Respond with only the URL (or NONE). No explanation.
"""
    try:
        result = complete(prompt, model_tier="fast").strip()
        if result and result != "NONE" and result.endswith(".mid"):
            return result
    except Exception as e:
        log.debug("Gemini MIDI search failed: %s", e)

    return None


# ---------------------------------------------------------------------------
# Downloader
# ---------------------------------------------------------------------------

def download_midi(url: str, out_path: Path) -> bool:
    """Download a .mid file to out_path. Returns True on success."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()

        # Sanity check: valid MIDI files start with 'MThd' (0x4D546864)
        if not data[:4] == b"MThd":
            log.warning("Downloaded file does not look like MIDI (bad header): %s", url)
            return False

        out_path.write_bytes(data)
        log.info("Downloaded: %s  (%d bytes)", out_path.name, len(data))
        return True
    except Exception as e:
        log.warning("Download failed for %s: %s", url, e)
        return False


# ---------------------------------------------------------------------------
# Learn pipeline
# ---------------------------------------------------------------------------

def learn_file(mid_path: Path, tag: str, dry_run: bool = False) -> bool:
    """Call pattern_learn.py learn-file on a downloaded MIDI."""
    if dry_run:
        log.info("[dry-run] would learn: %s  tag=%s", mid_path, tag)
        return True

    cmd = [
        sys.executable,
        str(REPO_ROOT / "scripts" / "pattern_learn.py"),
        "learn-file",
        "--file", str(mid_path),
        "--tag", tag,
        "--subdir", "references",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.warning("pattern_learn failed for %s:\n%s", mid_path.name, result.stderr)
        return False
    print(f"  → {result.stdout.strip()}")
    return True


# ---------------------------------------------------------------------------
# Main fetch logic
# ---------------------------------------------------------------------------

def fetch_track(artist: str, title: str, search_terms: str | None = None,
                dry_run: bool = False) -> bool:
    """Find, download, and learn a single reference track. Returns True on success."""
    tag = f"{artist} - {title}"
    safe_name = re.sub(r'[^\w\-]', '_', tag)[:80]
    out_path = RAW_DIR / f"{safe_name}.mid"

    if out_path.exists():
        log.info("Already downloaded: %s — re-learning", out_path.name)
        return learn_file(out_path, tag, dry_run=dry_run)

    log.info("Searching for: %s — %s", artist, title)

    # Try bitmidi first
    url = _bitmidi_search(artist, title)
    time.sleep(_RATE_LIMIT_SECS)

    # Try Gemini fallback
    if not url:
        log.info("  bitmidi: not found — trying Gemini")
        url = _gemini_search(artist, title)

    # Also try with search_terms override if provided
    if not url and search_terms:
        parts = search_terms.split()
        url = _bitmidi_search(" ".join(parts[:2]), " ".join(parts[2:]))

    if not url:
        log.warning("  No MIDI found for: %s — %s", artist, title)
        return False

    log.info("  Found: %s", url)

    if dry_run:
        log.info("[dry-run] would download: %s", url)
        return True

    if not download_midi(url, out_path):
        return False

    time.sleep(_RATE_LIMIT_SECS)
    return learn_file(out_path, tag)


def load_digest_json(path: Path) -> list[dict]:
    """Load reference tracks from a digest JSON sidecar."""
    data = json.loads(path.read_text())
    return data.get("tracks", [])


def latest_digest_json() -> Path | None:
    """Find the most recent reference digest JSON."""
    jsons = sorted(REFERENCES_JSON_DIR.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json"),
                   reverse=True)
    return jsons[0] if jsons else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download and learn MIDI files for reference tracks")
    parser.add_argument("--digest", default=None, metavar="PATH",
                        help="Path to reference digest JSON (default: latest)")
    parser.add_argument("--artist", default=None,
                        help="Ad-hoc single track: artist name")
    parser.add_argument("--title", default=None,
                        help="Ad-hoc single track: track title")
    parser.add_argument("--dry-run", action="store_true",
                        help="Resolve URLs but do not download or learn")
    args = parser.parse_args()

    if args.artist and args.title:
        # Single ad-hoc track
        ok = fetch_track(args.artist, args.title, dry_run=args.dry_run)
        sys.exit(0 if ok else 1)

    # Load from digest
    if args.digest:
        digest_path = Path(args.digest)
    else:
        digest_path = latest_digest_json()

    if not digest_path or not digest_path.exists():
        log.error(
            "No reference digest JSON found. Run run_reference_digest.py first, "
            "or specify --digest path/to/digest.json"
        )
        sys.exit(1)

    tracks = load_digest_json(digest_path)
    if not tracks:
        log.error("No tracks found in %s", digest_path)
        sys.exit(1)

    log.info("Fetching MIDI for %d reference track(s) from %s", len(tracks), digest_path.name)

    success = 0
    for t in tracks:
        artist = t.get("artist", "")
        title = t.get("title", "")
        search_terms = t.get("search_terms", None)
        if not artist or not title:
            log.warning("Skipping incomplete entry: %s", t)
            continue
        ok = fetch_track(artist, title, search_terms=search_terms, dry_run=args.dry_run)
        if ok:
            success += 1
        time.sleep(_RATE_LIMIT_SECS)

    print(f"\n{success}/{len(tracks)} tracks fetched and learned.")


if __name__ == "__main__":
    main()
