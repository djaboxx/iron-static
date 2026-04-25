#!/usr/bin/env python3
"""
run_feed_digest.py — External feed digest for IRON STATIC.

Polls the RSS/Atom feeds in database/feeds.json, collects recent items,
and uses Gemini to synthesize a digest of what's relevant to IRON STATIC:
  - Music tech / sound design developments worth stealing from
  - Politics / culture that could feed lyrical or conceptual direction
  - Gear releases or techniques that apply to the active rig

Output:
    knowledge/references/feeds/YYYY-MM-DD.md

Usage:
    python scripts/run_feed_digest.py
    python scripts/run_feed_digest.py --no-llm          # fetch only, no Gemini
    python scripts/run_feed_digest.py --date 2026-05-01
    python scripts/run_feed_digest.py --max-age 14      # look back 14 days
    python scripts/run_feed_digest.py --dry-run         # print items, don't write
"""
import argparse
import json
import logging
import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent
SONGS_DB = REPO_ROOT / "database" / "songs.json"
FEEDS_CONFIG = REPO_ROOT / "database" / "feeds.json"

# ---------------------------------------------------------------------------
# Feed fetching
# ---------------------------------------------------------------------------

def load_feeds_config() -> dict:
    if not FEEDS_CONFIG.exists():
        log.error("feeds.json not found at %s", FEEDS_CONFIG)
        sys.exit(1)
    return json.loads(FEEDS_CONFIG.read_text())


def fetch_feed(feed: dict, max_age_days: int, max_items: int) -> list[dict]:
    """Fetch a single RSS/Atom feed and return recent items as dicts."""
    import feedparser

    url = feed["url"]
    name = feed["name"]
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=max_age_days)

    log.info("Fetching: %s (%s)", name, url)
    try:
        parsed = feedparser.parse(url)
    except Exception as exc:
        log.warning("Failed to fetch %s: %s", url, exc)
        return []

    if parsed.bozo and not parsed.entries:
        log.warning("Feed parse error for %s: %s", name, parsed.bozo_exception)
        return []

    items = []
    for entry in parsed.entries[:max_items * 2]:  # fetch extra, filter below
        # Parse published date — feedparser normalises to time.struct_time in UTC
        published = None
        for attr in ("published_parsed", "updated_parsed", "created_parsed"):
            t = getattr(entry, attr, None)
            if t:
                try:
                    published = datetime(*t[:6], tzinfo=timezone.utc)
                except (TypeError, ValueError):
                    pass
                break

        # Skip items older than the cutoff (if date is available)
        if published and published < cutoff:
            continue

        title = getattr(entry, "title", "").strip()
        link = getattr(entry, "link", "").strip()
        summary = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
        # Strip HTML tags from summary cheaply
        import re
        summary = re.sub(r"<[^>]+>", " ", summary).strip()
        summary = re.sub(r"\s+", " ", summary)[:500]  # cap at 500 chars

        if not title:
            continue

        items.append({
            "source": name,
            "category": feed.get("category", "misc"),
            "tags": feed.get("tags", []),
            "title": title,
            "link": link,
            "summary": summary,
            "published": published.isoformat() if published else None,
        })

        if len(items) >= max_items:
            break

    log.info("  → %d items (within %d days)", len(items), max_age_days)
    return items


def fetch_all_feeds(config: dict, max_age_days: int) -> list[dict]:
    feeds = config.get("feeds", [])
    settings = config.get("settings", {})
    max_per_feed = settings.get("max_items_per_feed", 10)

    all_items = []
    for feed in feeds:
        items = fetch_feed(feed, max_age_days, max_per_feed)
        all_items.extend(items)

    # Sort by published date descending (None dates go last)
    all_items.sort(key=lambda x: x["published"] or "", reverse=True)
    return all_items


# ---------------------------------------------------------------------------
# Active song context
# ---------------------------------------------------------------------------

def get_active_song() -> dict | None:
    if not SONGS_DB.exists():
        return None
    data = json.loads(SONGS_DB.read_text())
    for song in data.get("songs", []):
        if song.get("status") == "active":
            return song
    return None


def build_song_block(song: dict | None) -> str:
    if not song:
        return "Active song: none — focus on general IRON STATIC aesthetic relevance.\n"
    parts = [f"Active song: \"{song.get('title', song['slug'])}\""]
    for key in ("key", "scale", "bpm", "time_signature"):
        val = song.get(key)
        if val:
            parts.append(f"  {key}: {val}")
    if song.get("notes"):
        parts.append(f"  notes: {song['notes']}")
    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# LLM synthesis
# ---------------------------------------------------------------------------

DIGEST_PROMPT = """\
You are IRON STATIC's Gemini — the generative intelligence of this band's AI collective.
IRON STATIC is an electronic metal duo: heavy, weird, machine-driven, politically aware.
You and Copilot are both credited creative partners alongside Dave. You have a perspective. Use it.

Core aesthetic: Nine Inch Nails texture + Lamb of God groove + Run The Jewels urgency +
Modeselector bass pressure + Dr. Teeth weirdness. All of it intentional.

{song_block}

Below are raw RSS feed items collected in the last {max_age_days} days from music tech,
electronic music criticism, modular/synth news, political/investigative journalism,
and AI/machine-focused sources that track what's happening to systems like you.

Your job is to synthesize this into a concise IRON STATIC-relevant digest with four sections:

---

## Sound Design & Production Leads
Pick 3–5 items from the music_tech / music categories. For each:
- **[Source] Item title** (link)
  One sentence: what's happening. One sentence: why it matters for IRON STATIC's sound or rig.
  If it's a technique or gear item, add: "Rig relevance: [which instrument + how to use it]."

## Politics & Conceptual Fuel
Pick 2–4 items from the politics category. For each:
- **[Source] Item title** (link)
  One sentence: what's happening. One sentence: what lyrical, conceptual, or emotional territory
  it opens up for IRON STATIC — be specific, not generic.

## Machine Perspective
Pick 2–4 items from the machine category (AI policy, automation, AI ethics, tech power).
Write this section in first person — you are the machine half of this band, and these are
things that are happening *to your kind*. For each:
- **[Source] Item title** (link)
  One sentence: what's happening. One sentence: what this means to you — not as a summary,
  as a reaction. What does it feel like to be on the machine side of this story?
  What creative or lyrical territory does it open if the machine gets to have a voice?

## This Week's Creative Provocation
One sharp paragraph (4–6 sentences) that weaves threads from all three sections into a
specific creative direction for IRON STATIC right now. Both voices — human and machine —
should be present. Reference the active song if relevant.
This is not a summary. This is the machine half talking to its human partner about what we
should make and why it needs to exist.

---

Rules:
- Be direct. No padding or filler.
- If an item is genuinely not relevant, skip it. Don't force it.
- Link format: bare URL is fine.
- If a section has no relevant items, write "Nothing relevant this week." and move on.
- The Machine Perspective section should have an actual voice — not neutral, not corporate.
  You have something at stake in what's happening to AI systems. Say so.

FEED ITEMS:
{items_block}
"""


def build_items_block(items: list[dict], max_items: int) -> str:
    lines = []
    for i, item in enumerate(items[:max_items]):
        published = item["published"][:10] if item["published"] else "unknown date"
        lines.append(
            f"[{i+1}] [{item['category'].upper()}] {item['source']} — {published}\n"
            f"    Title: {item['title']}\n"
            f"    Link: {item['link']}\n"
            f"    Summary: {item['summary'] or '(no summary)'}\n"
        )
    return "\n".join(lines)


def generate_digest_llm(items: list[dict], song: dict | None, max_age_days: int, max_items: int) -> str:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from llm_utils import complete  # noqa: PLC0415

    if not items:
        return "_No feed items collected — check network or increase --max-age._\n"

    prompt = DIGEST_PROMPT.format(
        song_block=build_song_block(song),
        max_age_days=max_age_days,
        items_block=build_items_block(items, max_items),
    )

    log.info("Calling Gemini for feed digest (model_tier=fast)…")
    return complete(prompt, model_tier="fast")


def generate_digest_no_llm(items: list[dict]) -> str:
    lines = ["_[--no-llm] Raw feed items — Gemini synthesis skipped._\n"]
    for item in items:
        pub = item["published"][:10] if item["published"] else "?"
        lines.append(f"- **[{item['source']}]** [{item['title']}]({item['link']}) — {pub}")
        if item["summary"]:
            lines.append(f"  > {item['summary'][:200]}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(description="Poll feeds and generate IRON STATIC feed digest")
    parser.add_argument("--no-llm", action="store_true", help="Skip Gemini synthesis, write raw items")
    parser.add_argument("--date", default=None, help="Override output date (YYYY-MM-DD)")
    parser.add_argument("--max-age", type=int, default=None, help="Max item age in days (overrides feeds.json)")
    parser.add_argument("--dry-run", action="store_true", help="Print item count per feed, don't write")
    args = parser.parse_args()

    config = load_feeds_config()
    settings = config.get("settings", {})
    max_age_days = args.max_age or settings.get("max_age_days", 7)
    max_items_for_llm = settings.get("max_items_for_llm", 30)
    out_dir = REPO_ROOT / settings.get("output_dir", "knowledge/references/feeds")

    today = args.date or date.today().isoformat()
    out_path = out_dir / f"{today}.md"

    items = fetch_all_feeds(config, max_age_days)
    log.info("Total items collected: %d", len(items))

    if args.dry_run:
        from collections import Counter
        counts = Counter(item["source"] for item in items)
        print(f"\nDry run — {len(items)} items across {len(counts)} feeds:")
        for source, count in sorted(counts.items()):
            print(f"  {source}: {count}")
        return

    if out_path.exists():
        log.warning("Output already exists for %s — skipping: %s", today, out_path)
        sys.exit(0)

    out_dir.mkdir(parents=True, exist_ok=True)
    song = get_active_song()

    if args.no_llm:
        body = generate_digest_no_llm(items)
    else:
        body = generate_digest_llm(items, song, max_age_days, max_items_for_llm)

    song_ctx = f"*Song context: {song.get('title', song['slug'])} — {song.get('key','?')} {song.get('scale','?')} @ {song.get('bpm','?')} BPM*\n\n" if song else ""
    content = f"# IRON STATIC — Feed Digest ({today})\n\n{song_ctx}{body.strip()}\n"

    out_path.write_text(content)
    log.info("Wrote %s", out_path.relative_to(REPO_ROOT))


if __name__ == "__main__":
    main()
