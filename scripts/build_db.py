#!/usr/bin/env python3
"""
build_db.py — Build and query the IRON STATIC unified SQLite database.

Database: database/iron_static.db  (gitignored — regenerated artifact)

Sources imported:
  1. Ableton Pack presets  → database/pack_presets.json (from index_pack_presets.py)
  2. Hardware presets      → instruments/*/presets/*.json and *.md
  3. Songs                 → database/songs.json
  4. MIDI patterns         → midi/sequences/*.mid
  5. Generated audio       → audio/generated/*.mp3 / *.wav (top-level only)
  6. Ableton use_count     → ~/Library/Application Support/Ableton/Live Database/

Usage:
  python scripts/build_db.py build
      --no-use-count    skip Ableton use_count cross-ref (faster)

  python scripts/build_db.py query [text]
      --tag TAG [TAG...]  filter by tags (AND logic)
      --source SOURCE    ableton_pack | hardware | software | ableton_builtin
      --category CAT     e.g. "Bass", "Pad", "Synth Lead", "Drums"
      --pack PACK        filter by pack name
      --device TYPE      filter by device type in rack
      --limit N          max results (default 25)
      --sort use_count   sort by use_count descending (default: name)

  python scripts/build_db.py stats
  python scripts/build_db.py songs
  python scripts/build_db.py audio [--song SLUG]
  python scripts/build_db.py midi  [--song SLUG]

  python scripts/build_db.py tag add    <name_fragment> <tag>
  python scripts/build_db.py tag remove <name_fragment> <tag>
  python scripts/build_db.py rate <name_fragment> <1-5>
  python scripts/build_db.py fav  <name_fragment>
"""

import argparse
import html
import json
import logging
import os
import re
import sqlite3
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

log = logging.getLogger("build_db")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = REPO_ROOT / "database" / "iron_static.db"
PACK_PRESETS_JSON = REPO_ROOT / "database" / "pack_presets.json"
SONGS_JSON = REPO_ROOT / "database" / "songs.json"
INSTRUMENTS_DIR = REPO_ROOT / "instruments"
MIDI_DIR = REPO_ROOT / "midi" / "sequences"
AUDIO_GENERATED_DIR = REPO_ROOT / "audio" / "generated"
ABLETON_DB_DIR = Path.home() / "Library/Application Support/Ableton/Live Database"

# Instrument slug lookup keyed on folder name
INSTRUMENT_FOLDER_TO_SLUG = {
    "elektron-digitakt-mk1": "digitakt",
    "sequential-rev2": "rev2",
    "sequential-take5": "take5",
    "moog-subharmonicon": "subharmonicon",
    "moog-dfam": "dfam",
    "arturia-minibrute-2s": "minibrute2s",
    "arturia-pigments": "pigments",
    "elektron-analog-rytm": "rytm",
}

# ---------------------------------------------------------------------------
# Pack URL map  (pack folder name → ableton.com slug)
# ---------------------------------------------------------------------------

PACK_URL_MAP: dict[str, str] = {
    "APC Step Sequencer by Mark Egloff": "apc-step-sequencer-by-mark-egloff",
    "Beat Tools": "beat-tools",
    "BeatSeeker by Andrew Robertson": "beatseeker-by-andrew-robertson",
    "Classic Synths by Katsuhiro Chiba": "classic-synths",
    "Connection Kit": "connection-kit",
    "Convolution Reverb": "convolution-reverb",
    "Drum Essentials": "drum-essentials",
    "M4L Big Three": "m4l-big-three",
    "M4L Granulator II": "m4l-granulator-ii",
    "MIDI Tools by Philip Meyer": "midi-tools",
    "Max for Live Essentials": "max-for-live-essentials",
    "Skitter and Step": "skitter-and-step",
}

# Genre and instrument tags for each pack (these are JavaScript-rendered on
# Ableton's site and cannot be extracted from static HTML, so they are hardcoded
# from manually fetched page content).
PACK_KNOWN_TAGS: dict[str, dict[str, list[str]]] = {
    "Beat Tools": {
        "genre_tags": ["RnB", "HipHop"],
        "instrument_tags": ["Synth", "Drums", "Loops"],
    },
    "Drum Essentials": {
        "genre_tags": [],
        "instrument_tags": ["Drums", "Loops"],
    },
    "Skitter and Step": {
        "genre_tags": ["Drum & Bass"],
        "instrument_tags": ["Synth", "Drums", "Loops"],
    },
    "Classic Synths by Katsuhiro Chiba": {
        "genre_tags": ["Electronica"],
        "instrument_tags": ["Synth", "Vintage"],
    },
    "Convolution Reverb": {
        "genre_tags": ["Sound Effects", "Experimental"],
        "instrument_tags": ["Device Presets"],
    },
    "Connection Kit": {
        "genre_tags": [],
        "instrument_tags": ["MIDI"],
    },
    "MIDI Tools by Philip Meyer": {
        "genre_tags": [],
        "instrument_tags": ["MIDI"],
    },
    "APC Step Sequencer by Mark Egloff": {
        "genre_tags": [],
        "instrument_tags": ["MIDI"],
    },
    "BeatSeeker by Andrew Robertson": {
        "genre_tags": [],
        "instrument_tags": ["MIDI"],
    },
}

# ---------------------------------------------------------------------------
# Pack catalog — available-but-not-installed packs with IRON STATIC relevance.
# Sourced from example_packs.json in the Ableton app bundle.
# Relevance: high = strong fit for the aesthetic, medium = useful/interesting,
#            low = marginal, no = off-brand (orchestral, latin, etc.)
# ---------------------------------------------------------------------------

PACK_CATALOG: list[dict] = [
    {
        "name": "Sound Objects Lite",
        "pack_unique_id": "www.ableton.com/30",
        "slug": "sound-objects",
        "install_mb": 612,
        "download_mb": 600,
        "relevance": "high",
        "relevance_reason": (
            "Sampled hardware-store objects: saw blades, metal pipes, ceramic tiles, metal sheets, "
            "metal rods — literally industrial noise source material. 359 presets. "
            "Highest priority install for IRON STATIC noise-as-instrument work."
        ),
    },
    {
        "name": "Drum Machines",
        "pack_unique_id": "www.ableton.com/1",
        "slug": "drum-machines",
        "install_mb": 420,
        "download_mb": 210,
        "relevance": "high",
        "relevance_reason": (
            "Classic drum machine samples (TR-808, TR-909, LM-1, etc.). 170 presets + 170 clips. "
            "Complements the Digitakt perfectly — clean digital references for the machines "
            "that defined industrial and electronic percussion."
        ),
    },
    {
        "name": "Digicussion 1",
        "pack_unique_id": "www.ableton.com/99",
        "slug": "digicussion-1",
        "install_mb": 157,
        "download_mb": 100,
        "relevance": "high",
        "relevance_reason": (
            "Synthetic electronic drums with experimental sound design focus. "
            "50 presets. Small download, directly on-brand for electronic/industrial percussion."
        ),
    },
    {
        "name": "Digicussion 2",
        "pack_unique_id": "www.ableton.com/100",
        "slug": "digicussion-2",
        "install_mb": 142,
        "download_mb": 90,
        "relevance": "high",
        "relevance_reason": (
            "Synthetic electronic drums vol.2. 50 presets. "
            "Install both Digicussion packs as a set — 100 synthesized drum presets total."
        ),
    },
    {
        "name": "Cyclic Waves",
        "pack_unique_id": "www.ableton.com/31",
        "slug": "cyclic-waves",
        "install_mb": 444,
        "download_mb": 330,
        "relevance": "high",
        "relevance_reason": (
            "Cycling '74 processed audio loops from Ron MacLeod — the Max/MSP people. "
            "143 clips of heavily processed, weird electronic material. "
            "Great source for Digitakt sampling and texture layering."
        ),
    },
    {
        "name": "Konkrete Breaks",
        "pack_unique_id": "www.ableton.com/102",
        "slug": "konkrete-breaks",
        "install_mb": 174,
        "download_mb": 110,
        "relevance": "medium",
        "relevance_reason": (
            "MIDI drum loops + Soniccouture's Konkrete Drums samples (musique concrete adjacent). "
            "101 Live Clips. MIDI format means patterns are reprogrammable on our gear. "
            "Industrial-adjacent rhythmic vocabulary."
        ),
    },
    {
        "name": "Retro Synths",
        "pack_unique_id": "www.ableton.com/60",
        "slug": "retro-synths",
        "install_mb": 3440,
        "download_mb": 2000,
        "relevance": "medium",
        "relevance_reason": (
            "4,000+ samples from classic synths including Minimoog, TB-303, Casio CZ. "
            "752 presets. The TB-303 acid and Minimoog bass content is directly usable. "
            "Large (3.4 GB) — install only if you want Sampler-based vintage synth textures."
        ),
    },
    {
        "name": "Loopmasters Mixtape",
        "pack_unique_id": "www.ableton.com/36",
        "slug": "loopmasters-mixtape",
        "install_mb": 3409,
        "download_mb": 2100,
        "relevance": "medium",
        "relevance_reason": (
            "Free. 2,289 clips from Puremagnetik, Soniccouture, Digable Planets, Coldcut. "
            "Includes found sounds and experimental material. Large (3.4 GB) but free. "
            "Cherry-pick for found-sound/experimental content."
        ),
    },
    {
        "name": "Designer Drums",
        "pack_unique_id": "www.ableton.com/32",
        "slug": "designer-drums",
        "install_mb": 30,
        "download_mb": 15,
        "relevance": "medium",
        "relevance_reason": (
            "265 synthesized drum presets from Live's built-in instruments. "
            "Tiny (30 MB). Quick win — no excuse not to have it."
        ),
    },
    {
        "name": "Unnatural Selection",
        "pack_unique_id": "www.ableton.com/37",
        "slug": "unnatural-selection",
        "install_mb": 207,
        "download_mb": 130,
        "relevance": "low",
        "relevance_reason": (
            "Generic multi-genre construction kits. 156 clips. "
            "Nothing specific to our aesthetic — might find one or two useful loops."
        ),
    },
    {
        "name": "Samplification",
        "pack_unique_id": "www.ableton.com/7",
        "slug": "samplification",
        "install_mb": 927,
        "download_mb": 700,
        "relevance": "low",
        "relevance_reason": (
            "Free Sampler showcase pack. 179 presets. Potentially interesting for "
            "discovering Sampler capabilities but content is unfocused genre-wise."
        ),
    },
    {
        "name": "Bomblastic",
        "pack_unique_id": "www.ableton.com/98",
        "slug": "bomblastic",
        "install_mb": 137,
        "download_mb": 85,
        "relevance": "low",
        "relevance_reason": (
            "Hip hop drum kit. 50 presets. Mostly covered by Drum Essentials and the DFAM."
        ),
    },
    {
        "name": "Vinyl Classics",
        "pack_unique_id": "www.ableton.com/33",
        "slug": "vinyl-classics",
        "install_mb": 869,
        "download_mb": 600,
        "relevance": "no",
        "relevance_reason": "Disco/dance 70s-90s loops. Wrong aesthetic entirely.",
    },
    {
        "name": "Grand Piano",
        "pack_unique_id": "www.ableton.com/91",
        "slug": "grand-piano",
        "install_mb": 1443,
        "download_mb": 900,
        "relevance": "no",
        "relevance_reason": "Acoustic piano. Off-brand for IRON STATIC.",
    },
    {
        "name": "Guitars and Bass",
        "pack_unique_id": "www.ableton.com/101",
        "slug": "guitars-and-bass",
        "install_mb": 1085,
        "download_mb": 700,
        "relevance": "no",
        "relevance_reason": "Live guitars and bass — we have hardware synths for bass. Off-brand.",
    },
    {
        "name": "Latin Percussion",
        "pack_unique_id": "www.ableton.com/35",
        "slug": "latin-percussion",
        "install_mb": 978,
        "download_mb": 620,
        "relevance": "no",
        "relevance_reason": "Latin percussion samples. Wrong aesthetic.",
    },
    {
        "name": "Orchestral Brass",
        "pack_unique_id": "www.ableton.com/3",
        "slug": "orchestral-brass",
        "install_mb": 2918,
        "download_mb": 1800,
        "relevance": "no",
        "relevance_reason": "Orchestral samples. Off-brand.",
    },
    {
        "name": "Orchestral Mallets",
        "pack_unique_id": "www.ableton.com/4",
        "slug": "orchestral-mallets",
        "install_mb": 2744,
        "download_mb": 1700,
        "relevance": "no",
        "relevance_reason": "Orchestral samples. Off-brand.",
    },
    {
        "name": "Orchestral Strings",
        "pack_unique_id": "www.ableton.com/5",
        "slug": "orchestral-strings",
        "install_mb": 4116,
        "download_mb": 2500,
        "relevance": "no",
        "relevance_reason": "Orchestral samples. Off-brand.",
    },
    {
        "name": "Orchestral Woodwinds",
        "pack_unique_id": "www.ableton.com/6",
        "slug": "orchestral-woodwinds",
        "install_mb": 7188,
        "download_mb": 4500,
        "relevance": "no",
        "relevance_reason": "Orchestral samples. Off-brand.",
    },
    {
        "name": "Session Drums Club",
        "pack_unique_id": "www.ableton.com/95",
        "slug": "session-drums-club",
        "install_mb": 4546,
        "download_mb": 2800,
        "relevance": "no",
        "relevance_reason": "Live acoustic drums, massive file size. Not our aesthetic.",
    },
    {
        "name": "Session Drums Multimic",
        "pack_unique_id": "www.ableton.com/22",
        "slug": "session-drums-multimic",
        "install_mb": 12574,
        "download_mb": 7800,
        "relevance": "no",
        "relevance_reason": "12.5 GB of acoustic drum samples. Completely off-brand and prohibitively large.",
    },
    {
        "name": "Session Drums Studio",
        "pack_unique_id": "www.ableton.com/94",
        "slug": "session-drums-studio",
        "install_mb": 6082,
        "download_mb": 3800,
        "relevance": "no",
        "relevance_reason": "Live acoustic drums. Not our aesthetic.",
    },
]

# Map pack preset category strings to Ableton vfolder group IDs
# group 1=Instruments, 2=Drum Racks, 3=Audio Samples, 5=Audio Effects
CATEGORY_TO_GROUP = {
    "Bass": 1, "Pad": 1, "Synth Lead": 1, "Ambient & Evolving": 1,
    "Synth Keys": 1, "Synth Misc": 1, "Synth Rhythmic": 1, "Vintage": 1,
    "Experimental": 1, "Cinematic": 1, "Guitar & Plucked": 1, "Voices": 1,
    "Piano & Keys": 1, "Effects": 1, "Exotic": 1, "Brass": 1, "Strings": 1,
    "Mallets": 1, "Orchestral": 1, "Winds": 1, "MPE Sounds": 1,
    "Drums": 2, "Hybrid": 2, "Synthesized": 2, "Acoustic": 2,
    "Kick": 3, "Snare": 3, "Hihat": 3, "Clap": 3, "Cymbal": 3, "Tom": 3,
    "Percussion": 3, "FX Hit": 3,
    "Reverb Presets": 5, "Ambience and Small Rooms": 5, "Made for Drums": 5,
    "Hall": 5, "Room": 5, "Distortion": 5, "Filter": 5,
}

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
CREATE TABLE IF NOT EXISTS presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    source TEXT NOT NULL,           -- ableton_pack | ableton_builtin | hardware | software
    pack TEXT,                      -- pack display name (for ableton_pack)
    pack_id TEXT,                   -- LivePackId URI
    instrument TEXT,                -- instrument slug (for hardware presets)
    file_path TEXT UNIQUE,          -- absolute filesystem path
    file_type TEXT,                 -- adg | adv | json | md | syx
    category TEXT,                  -- Ableton vfolder category or custom
    ableton_category_group INTEGER, -- 1=Instruments 2=DrumRacks 3=Audio 5=FX
    devices TEXT,                   -- JSON array of Ableton device type strings
    description TEXT,               -- annotation / notes text
    macros TEXT,                    -- JSON array of macro knob names
    author TEXT,
    use_count INTEGER DEFAULT 0,    -- times loaded from Ableton browser
    dave_rating INTEGER,            -- 1-5, manually set
    is_favourite INTEGER DEFAULT 0,
    indexed_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_used_at TEXT
);

CREATE TABLE IF NOT EXISTS preset_tags (
    preset_id INTEGER NOT NULL REFERENCES presets(id) ON DELETE CASCADE,
    tag TEXT NOT NULL,
    is_auto INTEGER DEFAULT 1,      -- 1=derived by indexer, 0=manually assigned
    PRIMARY KEY (preset_id, tag)
);

CREATE TABLE IF NOT EXISTS songs (
    slug TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT DEFAULT 'in-progress',
    key TEXT,
    scale TEXT,
    bpm REAL,
    time_signature TEXT,
    als_path TEXT,
    brainstorm_path TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS midi_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    song_slug TEXT REFERENCES songs(slug),
    file_path TEXT UNIQUE,
    instrument TEXT,                -- instrument slug inferred from filename
    key TEXT,                       -- inherited from song
    scale TEXT,                     -- inherited from song
    bpm REAL,                       -- inherited from song
    description TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS generated_audio (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL,
    file_path TEXT UNIQUE,
    song_slug TEXT REFERENCES songs(slug),
    target TEXT,                    -- descriptive target (from filename)
    model TEXT,
    is_stem INTEGER DEFAULT 0,      -- 1 if this is a demucs stem
    stem_type TEXT,                 -- bass | drums | other | vocals
    parent_filename TEXT,           -- source file for stems/slices
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS song_presets (
    song_slug TEXT NOT NULL REFERENCES songs(slug),
    preset_id INTEGER NOT NULL REFERENCES presets(id),
    track_name TEXT,
    notes TEXT,
    PRIMARY KEY (song_slug, preset_id)
);

CREATE TABLE IF NOT EXISTS packs (
    name TEXT PRIMARY KEY,           -- matches presets.pack / example_packs.json title
    slug TEXT,                        -- URL slug (e.g. drum-essentials)
    url TEXT,
    author TEXT,
    description TEXT,
    genre_tags TEXT,                  -- JSON array of genre tag strings
    instrument_tags TEXT,             -- JSON array of instrument tag strings
    sample_providers TEXT,            -- JSON array of provider names
    content_summary TEXT,             -- e.g. "142 Presets, 308 Live Clips"
    enriched_at TEXT,
    installed INTEGER DEFAULT 0,      -- 1 if pack is installed locally
    pack_unique_id TEXT,              -- e.g. "www.ableton.com/1" from example_packs.json
    download_mb INTEGER,              -- download size in MB
    install_mb INTEGER,               -- installed disk size in MB
    relevance TEXT,                   -- high/medium/low/no (IRON STATIC suitability)
    relevance_reason TEXT             -- one-line rationale
);

CREATE INDEX IF NOT EXISTS idx_presets_source   ON presets(source);
CREATE INDEX IF NOT EXISTS idx_presets_category ON presets(category);
CREATE INDEX IF NOT EXISTS idx_presets_pack     ON presets(pack);
CREATE INDEX IF NOT EXISTS idx_presets_inst     ON presets(instrument);
CREATE INDEX IF NOT EXISTS idx_presets_name     ON presets(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS idx_presets_rating   ON presets(dave_rating);
CREATE INDEX IF NOT EXISTS idx_presets_fav      ON presets(is_favourite);
CREATE INDEX IF NOT EXISTS idx_presets_use      ON presets(use_count DESC);
CREATE INDEX IF NOT EXISTS idx_tags_tag         ON preset_tags(tag);
CREATE INDEX IF NOT EXISTS idx_midi_song        ON midi_patterns(song_slug);
CREATE INDEX IF NOT EXISTS idx_audio_song       ON generated_audio(song_slug);
"""


# ---------------------------------------------------------------------------
# Tag inference (same logic as index_pack_presets.py, kept in sync)
# ---------------------------------------------------------------------------

TAG_RULES: list[tuple[list[str], str]] = [
    (["bass", "low end", "sub ", "floor bass", "reese", "808 bass", "mud"], "bass"),
    (["sub bass", "sub-bass", "subharmonic", "808 sub"], "sub"),
    (["pad ", " pad", "texture", "evolv", "drift", "cloud", "ether", "ambient", "atmos"], "pad"),
    (["drone", "sustain", "hold", "endless"], "drone"),
    (["lead", "solo", "melody", "melodic"], "lead"),
    (["stab", "pluck", "attack", "perc "], "stab"),
    (["key", "chord", "poly", "piano", "organ", "clav"], "keys"),
    (["drum", "kit", "snare", "kick", "hihat", "hat", "percussion", "clap", "tom"], "drum"),
    (["808", "606", "707", "909", "303", "tb-3", "tr-8", "cr-78"], "808"),
    (["noise", "static", "grain", "granul", "glitch", "artifact", "corrupt"], "noise"),
    (["dist", "fuzz", "grit", "crunch", "scorch", "destroy", "wreck", "absolute filth", "corrod"], "distortion"),
    (["modwheel", "aftertouch", "mod.", "modulation", "wobble", "lfo"], "modulation"),
    (["filter", "cutoff", "resonan", "sweep"], "filter"),
    (["reverb", "hall", "room", "convolution", "ambience"], "reverb"),
    (["delay", "echo", "repeat"], "delay"),
    (["dark", "shadow", "void", "abyss", "black", "dead", "death", "tomb"], "dark"),
    (["industrial", "machine", "factory", "metal-o", "robot", "mech", "rust"], "industrial"),
    (["metal", "heavy metal", "thrash", "doom"], "metal"),
    (["heavy", "massive", "brutal", "crush", "slam"], "heavy"),
    (["warm", "analog", "vintage", "classic", "retro", "mellow"], "warm"),
    (["cold", "ice", "freeze", "chill", "arctic", "crisp"], "cold"),
    (["ambient", "space", "vast", "wide", "sphere", "cosmic"], "ambient"),
    (["fm", "fm synthesis", "digital", "metallic tone", "fm bass", "fm pad"], "fm"),
    (["analog", "vcf", "vco", "vcа", "ladder", "moog", "arp ", "juno", "mini "], "analog"),
    (["wavetable", "wave table"], "wavetable"),
    (["granular", "grain delay", "grainbeam", "granularstretch"], "granular"),
    (["sampler", "sample", "simpler", "ableton drum"], "sampler"),
    (["choir", "voice", "vocal", "angel", "hymn", "sacred"], "vocal"),
    (["string", "cello", "violin", "viola", "orchestra"], "strings"),
    (["brass", "horn", "trumpet", "trombone"], "brass"),
    (["arp", "arpegg"], "arp"),
    (["gate", "gated", "trem"], "gated"),
    (["punchy", "punch", "tight", "snap", "smack"], "punchy"),
    (["soft", "gentle", "quiet", "whisper", "airy", "breathy"], "soft"),
]


def infer_tags(name: str, category: str, description: str) -> list[str]:
    text = f"{name} {category} {description}".lower()
    tags = []
    for keywords, tag in TAG_RULES:
        if any(kw in text for kw in keywords):
            tags.append(tag)
    return tags


# ---------------------------------------------------------------------------
# Import: Pack catalog (available but not necessarily installed)
# ---------------------------------------------------------------------------

EXAMPLE_PACKS_JSON = Path("/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/example_packs.json")


def import_pack_catalog(con: sqlite3.Connection) -> int:
    """Populate the packs table with the full available pack catalog from
    Ableton's example_packs.json, merged with our PACK_CATALOG relevance data.
    Marks installed packs (those already in packs table) vs. available.
    """
    cur = con.cursor()

    # Load Ableton's catalog
    if not EXAMPLE_PACKS_JSON.exists():
        log.warning("example_packs.json not found in Ableton app bundle")
        return 0

    catalog = json.loads(EXAMPLE_PACKS_JSON.read_text())
    # Get set of installed pack unique IDs (from presets table)
    installed_ids = {r[0] for r in cur.execute(
        "SELECT DISTINCT pack_id FROM presets WHERE pack_id IS NOT NULL"
    ).fetchall() if r[0]}
    # Also check which packs are already in the packs table (imported via presets)
    installed_names = {r[0] for r in cur.execute(
        "SELECT name FROM packs"
    ).fetchall()}

    # Build a lookup from our PACK_CATALOG
    catalog_meta = {p["name"]: p for p in PACK_CATALOG}

    done = 0
    for entry in catalog:
        name = entry["title"]
        uid = entry.get("pack_unique_id", "")
        slug_from_url = entry["url"].strip("/").split("/")[-1] if entry.get("url") else None
        dl_mb = entry.get("download_size", 0) // (1024 * 1024)
        inst_mb = entry.get("installation_size", 0) // (1024 * 1024)
        is_installed = int(uid in installed_ids or name in installed_names)

        meta = catalog_meta.get(name, {})
        relevance = meta.get("relevance", "unknown")
        reason = meta.get("relevance_reason", "")

        cur.execute(
            """INSERT OR IGNORE INTO packs (name, slug, pack_unique_id, download_mb, install_mb,
               installed, relevance, relevance_reason)
               VALUES (?,?,?,?,?,?,?,?)""",
            (name, slug_from_url, uid, dl_mb, inst_mb, is_installed, relevance, reason),
        )
        # Update catalog fields even if row already exists (from enrichment)
        cur.execute(
            """UPDATE packs SET pack_unique_id=?, download_mb=?, install_mb=?,
               installed=?, relevance=COALESCE(NULLIF(relevance,''),?),
               relevance_reason=COALESCE(NULLIF(relevance_reason,''),?)
               WHERE name=?""",
            (uid, dl_mb, inst_mb, is_installed, relevance, reason, name),
        )
        done += 1

    # Mark installed packs that ARE in our presets but not in Ableton's example_packs.json
    for name in installed_names:
        cur.execute(
            "UPDATE packs SET installed=1 WHERE name=? AND installed=0",
            (name,),
        )

    con.commit()
    return done


# ---------------------------------------------------------------------------
# Pack URL map  (pack folder name → ableton.com slug)
# ---------------------------------------------------------------------------

PACK_URL_MAP: dict[str, str] = {
    "APC Step Sequencer by Mark Egloff": "apc-step-sequencer-by-mark-egloff",
    "Beat Tools": "beat-tools",
    "BeatSeeker by Andrew Robertson": "beatseeker-by-andrew-robertson",
    "Classic Synths by Katsuhiro Chiba": "classic-synths",
    "Connection Kit": "connection-kit",
    "Convolution Reverb": "convolution-reverb",
    "Drum Essentials": "drum-essentials",
    "M4L Big Three": "m4l-big-three",
    "M4L Granulator II": "m4l-granulator-ii",
    "MIDI Tools by Philip Meyer": "midi-tools",
    "Max for Live Essentials": "max-for-live-essentials",
    "Skitter and Step": "skitter-and-step",
}

# ---------------------------------------------------------------------------

def scrape_pack_page(slug: str) -> dict | None:
    """Fetch an Ableton pack page and extract metadata. Returns None on failure."""
    url = f"https://www.ableton.com/en/packs/{slug}/"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; iron-static-indexer/1.0)"
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        log.warning(f"Pack page /{slug}/: HTTP {e.code}")
        return None
    except Exception as e:
        log.warning(f"Pack page /{slug}/: {e}")
        return None

    def strip_tags(s: str) -> str:
        return re.sub(r'<[^>]+>', ' ', s).strip()

    result: dict = {"url": url, "slug": slug}

    # Author: /en/packs/by/SLUG → display name
    author_m = re.search(r'/en/packs/by/[^"]+">([^<]+)</a>', raw)
    result["author"] = html.unescape(author_m.group(1)) if author_m else "Ableton"

    # Description: og:description meta tag (static HTML — present even without JS)
    og_m = (
        re.search(r'<meta[^>]+property="og:description"[^>]+content="([^"]+)"', raw)
        or re.search(r'<meta[^>]+name="description"[^>]+content="([^"]+)"', raw)
    )
    result["description"] = html.unescape(og_m.group(1)) if og_m else ""

    # Contents summary: <dt>Contents</dt> <dd>...</dd>
    contents_m = (
        re.search(r'<dt[^>]*>\s*Contents\s*</dt>\s*<dd[^>]*>(.*?)</dd>', raw, re.DOTALL)
        or re.search(r'Contents</strong>\s*</dt>\s*<dd[^>]*>(.*?)</dd>', raw, re.DOTALL)
        or re.search(r'Contents</strong>([^<]{3,150})', raw)
    )
    result["content_summary"] = strip_tags(contents_m.group(1)).strip() if contents_m else ""

    # Sample providers: "Samples provided by Name, Name, ..."
    prov_m = re.search(r'Samples provided by (.*?)(?:</p>|</li>|</dd>)', raw, re.DOTALL)
    if prov_m:
        prov_text = strip_tags(prov_m.group(1))
        result["sample_providers"] = [p.strip() for p in re.split(r',\s*(?:and\s+)?', prov_text) if p.strip()]
    else:
        result["sample_providers"] = []

    # NOTE: genre_tags and instrument_tags are JS-rendered — they come from
    # PACK_KNOWN_TAGS in import_packs(), NOT from this scraper.

    return result


# ---------------------------------------------------------------------------
# Import: Pack catalog (available but not necessarily installed)
# ---------------------------------------------------------------------------

EXAMPLE_PACKS_JSON = Path(
    "/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/example_packs.json"
)


def import_pack_catalog(con: sqlite3.Connection) -> int:
    """Populate the packs table with the full available pack catalog from
    Ableton's example_packs.json, merged with PACK_CATALOG relevance data.
    Marks installed vs. not-installed. Safe to re-run (upserts only).
    """
    cur = con.cursor()

    if not EXAMPLE_PACKS_JSON.exists():
        log.warning("example_packs.json not found in Ableton app bundle — skipping catalog import")
        return 0

    catalog = json.loads(EXAMPLE_PACKS_JSON.read_text())

    # Pack unique IDs of packs we have presets for → installed
    installed_ids = {
        r[0] for r in cur.execute(
            "SELECT DISTINCT pack_id FROM presets WHERE pack_id IS NOT NULL"
        ).fetchall() if r[0]
    }
    # Also by name (presets from non-example_packs sources, e.g. Beat Tools)
    installed_names = {
        r[0] for r in cur.execute("SELECT name FROM packs").fetchall()
    }

    catalog_meta = {p["name"]: p for p in PACK_CATALOG}

    done = 0
    for entry in catalog:
        name = entry["title"]
        uid = entry.get("pack_unique_id", "")
        url_slug = entry.get("url", "").strip("/").split("/")[-1] or None
        dl_mb = entry.get("download_size", 0) // (1024 * 1024)
        inst_mb = entry.get("installation_size", 0) // (1024 * 1024)
        is_installed = int(uid in installed_ids or name in installed_names)

        meta = catalog_meta.get(name, {})
        relevance = meta.get("relevance", "unknown")
        reason = meta.get("relevance_reason", "")

        cur.execute(
            """INSERT OR IGNORE INTO packs
               (name, slug, pack_unique_id, download_mb, install_mb, installed, relevance, relevance_reason)
               VALUES (?,?,?,?,?,?,?,?)""",
            (name, url_slug, uid, dl_mb, inst_mb, is_installed, relevance, reason),
        )
        # Update catalog fields without clobbering enrichment fields
        cur.execute(
            """UPDATE packs
               SET pack_unique_id = ?,
                   download_mb    = ?,
                   install_mb     = ?,
                   installed      = ?,
                   relevance      = CASE WHEN relevance IS NULL OR relevance = '' THEN ? ELSE relevance END,
                   relevance_reason = CASE WHEN relevance_reason IS NULL OR relevance_reason = '' THEN ? ELSE relevance_reason END
               WHERE name = ?""",
            (uid, dl_mb, inst_mb, is_installed, relevance, reason, name),
        )
        done += 1

    # Installed packs that aren't in example_packs.json (e.g. Beat Tools, Drum Essentials)
    cur.execute("UPDATE packs SET installed=1 WHERE name IN (SELECT DISTINCT pack FROM presets)")

    con.commit()
    return done


# ---------------------------------------------------------------------------
# Import: Pack metadata
# ---------------------------------------------------------------------------

def import_packs(con: sqlite3.Connection, pack_names: list[str], force: bool = False) -> int:
    """Populate the packs table by scraping Ableton pack pages and merging known
    tag data from PACK_KNOWN_TAGS. Only re-scrapes if not already enriched (or force=True)."""
    cur = con.cursor()
    done = 0
    for name in pack_names:
        slug = PACK_URL_MAP.get(name)
        known = PACK_KNOWN_TAGS.get(name, {})

        if not slug:
            log.debug(f"No URL slug for pack '{name}' — inserting stub with known tags only")
            cur.execute(
                "INSERT OR IGNORE INTO packs (name, slug) VALUES (?,?)",
                (name, None),
            )
            # Still apply known tags if we have them
            if known:
                cur.execute(
                    "UPDATE packs SET genre_tags=?, instrument_tags=?, enriched_at=datetime('now') WHERE name=?",
                    (json.dumps(known.get("genre_tags", [])),
                     json.dumps(known.get("instrument_tags", [])),
                     name),
                )
                done += 1
            continue

        # Skip if already enriched and not forced
        row = cur.execute(
            "SELECT enriched_at FROM packs WHERE name=?", (name,)
        ).fetchone()
        if row and row[0] and not force:
            log.debug(f"Pack '{name}' already enriched at {row[0]} — skipping")
            continue

        log.info(f"Scraping pack page: {slug}")
        data = scrape_pack_page(slug)
        if not data:
            # Page 404'd — stub with known tags only
            cur.execute(
                "INSERT OR IGNORE INTO packs (name, slug) VALUES (?,?)",
                (name, slug),
            )
            if known:
                cur.execute(
                    "UPDATE packs SET genre_tags=?, instrument_tags=?, enriched_at=datetime('now') WHERE name=?",
                    (json.dumps(known.get("genre_tags", [])),
                     json.dumps(known.get("instrument_tags", [])),
                     name),
                )
                done += 1
            continue

        # Merge scraped data with hardcoded known tags
        genre_tags = known.get("genre_tags", data.get("genre_tags", []))
        instrument_tags = known.get("instrument_tags", data.get("instrument_tags", []))

        cur.execute(
            """INSERT OR REPLACE INTO packs
               (name, slug, url, author, description, genre_tags, instrument_tags,
                sample_providers, content_summary, enriched_at)
               VALUES (?,?,?,?,?,?,?,?,?,datetime('now'))""",
            (
                name,
                slug,
                data["url"],
                data.get("author", ""),
                data.get("description", ""),
                json.dumps(genre_tags),
                json.dumps(instrument_tags),
                json.dumps(data.get("sample_providers", [])),
                data.get("content_summary", ""),
            ),
        )
        done += 1

    con.commit()
    return done


# ---------------------------------------------------------------------------
# Apply pack genre/instrument tags to presets
# ---------------------------------------------------------------------------

def apply_pack_tags_to_presets(con: sqlite3.Connection) -> int:
    """Inherit genre + instrument tags from the packs table into preset_tags.
    Tags are stored with is_auto=1 (derived). Safe to re-run (INSERT OR IGNORE)."""
    cur = con.cursor()
    applied = 0

    rows = cur.execute(
        "SELECT name, genre_tags, instrument_tags FROM packs WHERE genre_tags IS NOT NULL OR instrument_tags IS NOT NULL"
    ).fetchall()

    for pack_name, genre_json, inst_json in rows:
        tags: list[str] = []
        try:
            tags += json.loads(genre_json or "[]")
        except json.JSONDecodeError:
            pass
        try:
            tags += json.loads(inst_json or "[]")
        except json.JSONDecodeError:
            pass
        # Normalize: lowercase, collapse spaces to hyphens
        tags = [re.sub(r'\s+', '-', t.lower().strip()) for t in tags if t.strip()]
        if not tags:
            continue

        preset_ids = [r[0] for r in cur.execute(
            "SELECT id FROM presets WHERE pack = ?", (pack_name,)
        ).fetchall()]

        for pid in preset_ids:
            for tag in tags:
                cur.execute(
                    "INSERT OR IGNORE INTO preset_tags (preset_id, tag, is_auto) VALUES (?,?,1)",
                    (pid, tag),
                )
                applied += 1

    con.commit()
    return applied


# ---------------------------------------------------------------------------
# Ableton use_count cross-reference
# ---------------------------------------------------------------------------

def load_ableton_use_counts() -> dict[str, int]:
    """Return {filename_with_ext: use_count} from the most recent Ableton Live DB."""
    if not ABLETON_DB_DIR.exists():
        return {}
    # pick the newest db by modification time (skip plugins db)
    dbs = sorted(
        [p for p in ABLETON_DB_DIR.glob("Live-files-*.db")],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not dbs:
        return {}
    db_path = dbs[0]
    log.info(f"Cross-referencing use_count from {db_path.name}")
    try:
        con = sqlite3.connect(db_path)
        cur = con.cursor()
        rows = cur.execute(
            "SELECT name, SUM(use_count) FROM files WHERE name LIKE '%.adg' OR name LIKE '%.adv' GROUP BY name"
        ).fetchall()
        con.close()
        return {r[0]: r[1] for r in rows if r[1]}
    except Exception as e:
        log.warning(f"Could not read Ableton DB: {e}")
        return {}


# ---------------------------------------------------------------------------
# Import: Ableton Pack presets
# ---------------------------------------------------------------------------

def import_pack_presets(con: sqlite3.Connection, use_counts: dict[str, int]) -> int:
    if not PACK_PRESETS_JSON.exists():
        log.warning(f"pack_presets.json not found — run index_pack_presets.py build first")
        return 0

    data = json.loads(PACK_PRESETS_JSON.read_text())
    presets = data if isinstance(data, list) else data.get("presets", [])

    cur = con.cursor()
    inserted = 0
    for p in presets:
        name = p.get("name") or Path(p.get("file", "")).stem
        file_path = p.get("file", "")
        category_path = p.get("category", "")
        # last segment of category path is the leaf category
        category = category_path.split(">")[-1].strip() if category_path else ""
        devices_list = p.get("devices", [])
        devices_json = json.dumps(devices_list)
        macros_list = p.get("macros", [])
        macros_json = json.dumps([m for m in macros_list if m])
        description = p.get("description", "") or ""
        tags = p.get("tags", [])
        pack = p.get("pack", "")
        pack_id = p.get("pack_id", "")
        file_type = p.get("file_type", Path(file_path).suffix.lstrip("."))

        # Use_count from Ableton DB
        filename = Path(file_path).name if file_path else ""
        use_count = use_counts.get(filename, 0)

        ableton_group = CATEGORY_TO_GROUP.get(category, 1)

        try:
            cur.execute(
                """INSERT OR REPLACE INTO presets
                   (name, source, pack, pack_id, file_path, file_type,
                    category, ableton_category_group, devices, description, macros,
                    use_count)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (name, "ableton_pack", pack, pack_id, file_path, file_type,
                 category, ableton_group, devices_json, description.strip(), macros_json,
                 use_count),
            )
            preset_id = cur.lastrowid
            for tag in tags:
                cur.execute(
                    "INSERT OR IGNORE INTO preset_tags (preset_id, tag, is_auto) VALUES (?,?,1)",
                    (preset_id, tag),
                )
            inserted += 1
        except sqlite3.IntegrityError:
            pass

    con.commit()
    return inserted


# ---------------------------------------------------------------------------
# Import: Hardware presets
# ---------------------------------------------------------------------------

def import_hardware_presets(con: sqlite3.Connection) -> int:
    cur = con.cursor()
    inserted = 0

    for inst_dir in INSTRUMENTS_DIR.iterdir():
        if not inst_dir.is_dir():
            continue
        slug = INSTRUMENT_FOLDER_TO_SLUG.get(inst_dir.name)
        if not slug:
            continue
        presets_dir = inst_dir / "presets"
        if not presets_dir.exists():
            continue

        for f in presets_dir.iterdir():
            if f.suffix not in (".json", ".md", ".syx"):
                continue
            if f.name in ("catalog.json", "README.md"):
                continue

            name = f.stem
            file_type = f.suffix.lstrip(".")
            description = ""
            tags: list[str] = []
            category = "Hardware Preset"
            macros_json = "[]"
            devices_json = "[]"

            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text())
                    if isinstance(data, dict):
                        name = data.get("name", name)
                        description = data.get("description", data.get("notes", ""))
                        tags = data.get("tags", [])
                        category = data.get("category", category)
                except Exception:
                    pass
            elif f.suffix == ".md":
                # Read first non-heading line as description
                lines = [ln.strip() for ln in f.read_text().splitlines() if ln.strip()]
                if lines:
                    description = " ".join(l for l in lines[:3] if not l.startswith("#"))

            # Skip .md if a .json with same stem exists (avoid duplicates)
            if f.suffix == ".md" and (presets_dir / f"{f.stem}.json").exists():
                continue

            # Infer tags from name/description
            auto_tags = infer_tags(name, category, description)
            all_tags = list({*tags, *auto_tags})

            try:
                cur.execute(
                    """INSERT OR REPLACE INTO presets
                       (name, source, instrument, file_path, file_type,
                        category, devices, description, macros)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (name, "hardware", slug, str(f), file_type,
                     category, devices_json, description, macros_json),
                )
                preset_id = cur.lastrowid
                for tag in all_tags:
                    cur.execute(
                        "INSERT OR IGNORE INTO preset_tags (preset_id, tag, is_auto) VALUES (?,?,1)",
                        (preset_id, tag),
                    )
                inserted += 1
            except sqlite3.IntegrityError:
                pass

    con.commit()
    return inserted


# ---------------------------------------------------------------------------
# Import: Songs
# ---------------------------------------------------------------------------

def import_songs(con: sqlite3.Connection) -> int:
    if not SONGS_JSON.exists():
        return 0
    data = json.loads(SONGS_JSON.read_text())
    songs = data.get("songs", [])
    cur = con.cursor()
    inserted = 0
    for s in songs:
        try:
            cur.execute(
                """INSERT OR REPLACE INTO songs
                   (slug, title, status, key, scale, bpm, time_signature,
                    als_path, brainstorm_path, notes)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (s.get("slug"), s.get("title"), s.get("status", "in-progress"),
                 s.get("key"), s.get("scale"), s.get("bpm"), s.get("time_signature"),
                 s.get("als_path"), s.get("brainstorm_path"), s.get("notes", "")),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass
    con.commit()
    return inserted


# ---------------------------------------------------------------------------
# Import: MIDI patterns
# ---------------------------------------------------------------------------

# Convention: [song-slug]_[instrument]_[version].mid
_MIDI_RE = re.compile(r"^([a-z0-9-]+)_([a-z0-9]+)_v\d+\.mid$")

def import_midi_patterns(con: sqlite3.Connection) -> int:
    if not MIDI_DIR.exists():
        return 0
    cur = con.cursor()
    inserted = 0

    # Build song lookup for key/scale/bpm
    songs = {r[0]: r for r in cur.execute(
        "SELECT slug, key, scale, bpm FROM songs"
    ).fetchall()}

    for f in MIDI_DIR.glob("*.mid"):
        m = _MIDI_RE.match(f.name)
        song_slug = None
        instrument = None
        key = scale = bpm = None
        name = f.stem

        if m:
            song_slug = m.group(1)
            instrument = m.group(2)
            song = songs.get(song_slug)
            if song:
                _, key, scale, bpm = song

        try:
            cur.execute(
                """INSERT OR IGNORE INTO midi_patterns
                   (name, song_slug, file_path, instrument, key, scale, bpm)
                   VALUES (?,?,?,?,?,?,?)""",
                (name, song_slug, str(f), instrument, key, scale, bpm),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass

    con.commit()
    return inserted


# ---------------------------------------------------------------------------
# Import: Generated audio
# ---------------------------------------------------------------------------

# Convention: [song-slug]_[target-description]_[date].mp3
_AUDIO_RE = re.compile(r"^([a-z0-9-]+)_(.+)_(\d{4}-\d{2}-\d{2})\.(mp3|wav)$")

def import_generated_audio(con: sqlite3.Connection) -> int:
    if not AUDIO_GENERATED_DIR.exists():
        return 0
    cur = con.cursor()
    inserted = 0

    # Top-level source files (not slices/stems subdirs)
    for f in AUDIO_GENERATED_DIR.iterdir():
        if f.suffix not in (".mp3", ".wav"):
            continue
        m = _AUDIO_RE.match(f.name)
        song_slug = target = None
        if m:
            song_slug = m.group(1)
            target = m.group(2).replace("-", " ")

        try:
            cur.execute(
                """INSERT OR IGNORE INTO generated_audio
                   (filename, file_path, song_slug, target, is_stem)
                   VALUES (?,?,?,?,0)""",
                (f.name, str(f), song_slug, target),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            pass

    # Stems under stems/
    stems_dir = AUDIO_GENERATED_DIR / "stems"
    if stems_dir.exists():
        for stem_file in stems_dir.rglob("*.wav"):
            parent_dir = stem_file.parent
            parent_filename = parent_dir.name + ".mp3"  # best guess
            stem_type = stem_file.stem  # bass, drums, other, vocals

            # Infer song_slug from grandparent dir name
            song_slug = None
            gp = parent_dir.parent.name  # htdemucs_ft
            if gp.startswith("htdemucs"):
                gp2 = parent_dir.name  # rust-protocol_corroded-texture_2026-04-24
                m2 = re.match(r"^([a-z0-9-]+)_", gp2)
                if m2:
                    song_slug = m2.group(1)

            try:
                cur.execute(
                    """INSERT OR IGNORE INTO generated_audio
                       (filename, file_path, song_slug, is_stem, stem_type, parent_filename)
                       VALUES (?,?,?,1,?,?)""",
                    (stem_file.name, str(stem_file), song_slug, stem_type, parent_filename),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                pass

    con.commit()
    return inserted


# ---------------------------------------------------------------------------
# Build command
# ---------------------------------------------------------------------------

def cmd_build(args: argparse.Namespace) -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Optionally wipe and rebuild clean
    if DB_PATH.exists() and not args.incremental:
        DB_PATH.unlink()
        log.info("Dropped existing database for clean rebuild")

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript(SCHEMA)

    # Load Ableton use_count index
    use_counts: dict[str, int] = {}
    if not args.no_use_count:
        use_counts = load_ableton_use_counts()
        log.info(f"Loaded {len(use_counts)} use_count entries from Ableton DB")

    # Collect unique pack names before importing presets
    pack_names: list[str] = []
    if PACK_PRESETS_JSON.exists():
        raw_presets = json.loads(PACK_PRESETS_JSON.read_text())
        presets_list = raw_presets if isinstance(raw_presets, list) else raw_presets.get("presets", [])
        seen: set[str] = set()
        for p in presets_list:
            nm = p.get("pack", "")
            if nm and nm not in seen:
                pack_names.append(nm)
                seen.add(nm)

    print("Enriching pack metadata from ableton.com...", flush=True)
    if args.no_enrich:
        print("  skipped (--no-enrich)")
    else:
        ne = import_packs(con, pack_names, force=False)
        print(f"  {ne} packs newly scraped ({len(pack_names)} total)")

    print("Importing pack catalog (available packs + relevance)...", flush=True)
    nc = import_pack_catalog(con)
    print(f"  {nc} catalog entries")

    print("Importing pack presets...", flush=True)
    n = import_pack_presets(con, use_counts)
    print(f"  {n} pack presets")

    print("Applying pack tags to presets...", flush=True)
    na = apply_pack_tags_to_presets(con)
    print(f"  {na} tag assignments from pack metadata")

    print("Importing hardware presets...", flush=True)
    n = import_hardware_presets(con)
    print(f"  {n} hardware presets")

    print("Importing songs...", flush=True)
    n = import_songs(con)
    print(f"  {n} songs")

    print("Importing MIDI patterns...", flush=True)
    n = import_midi_patterns(con)
    print(f"  {n} MIDI patterns")

    print("Importing generated audio...", flush=True)
    n = import_generated_audio(con)
    print(f"  {n} audio files")

    # Summary
    cur = con.cursor()
    total_presets = cur.execute("SELECT COUNT(*) FROM presets").fetchone()[0]
    total_tags    = cur.execute("SELECT COUNT(DISTINCT tag) FROM preset_tags").fetchone()[0]
    db_size = DB_PATH.stat().st_size
    con.close()

    print(f"\nDatabase: {DB_PATH}")
    print(f"  {total_presets} presets  |  {total_tags} unique tags  |  {db_size // 1024} KB")


# ---------------------------------------------------------------------------
# Query command
# ---------------------------------------------------------------------------

def cmd_query(args: argparse.Namespace) -> None:
    if not DB_PATH.exists():
        print("Database not built yet. Run: python scripts/build_db.py build", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    conditions = []
    params: list = []

    # Full-text search on name + description
    if args.text:
        text = f"%{args.text}%"
        conditions.append("(p.name LIKE ? OR p.description LIKE ? OR p.category LIKE ?)")
        params.extend([text, text, text])

    if args.source:
        conditions.append("p.source = ?")
        params.append(args.source)

    if args.category:
        conditions.append("p.category LIKE ?")
        params.append(f"%{args.category}%")

    if args.pack:
        conditions.append("p.pack LIKE ?")
        params.append(f"%{args.pack}%")

    if args.device:
        conditions.append("p.devices LIKE ?")
        params.append(f"%{args.device}%")

    if args.instrument:
        conditions.append("p.instrument = ?")
        params.append(args.instrument)

    if args.favourite:
        conditions.append("p.is_favourite = 1")

    if args.min_rating:
        conditions.append("p.dave_rating >= ?")
        params.append(args.min_rating)

    if args.tag:
        # AND logic: preset must have ALL requested tags
        for tag in args.tag:
            conditions.append(
                "p.id IN (SELECT preset_id FROM preset_tags WHERE tag = ?)"
            )
            params.append(tag)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sort = "p.use_count DESC, p.name" if args.sort == "use_count" else "p.name COLLATE NOCASE"

    query = f"""
        SELECT p.id, p.name, p.source, p.pack, p.instrument, p.category,
               p.devices, p.description, p.file_path, p.use_count,
               p.dave_rating, p.is_favourite,
               GROUP_CONCAT(pt.tag, ',') AS tags
        FROM presets p
        LEFT JOIN preset_tags pt ON pt.preset_id = p.id
        {where}
        GROUP BY p.id
        ORDER BY {sort}
        LIMIT ?
    """
    params.append(args.limit)

    rows = cur.execute(query, params).fetchall()
    con.close()

    if not rows:
        print("No results.")
        return

    for row in rows:
        pid, name, source, pack, instrument, category, devices_j, desc, fpath, use_count, rating, fav, tags_str = row
        source_label = pack or instrument or source
        tags = sorted(tags_str.split(",")) if tags_str else []
        devices = json.loads(devices_j) if devices_j else []
        desc_short = (desc or "").replace("\n", " ").strip()[:80]

        stars = ("★" * (rating or 0)) + ("☆" * (5 - (rating or 0))) if rating else ""
        fav_mark = " ♥" if fav else ""
        use_str = f"  ×{use_count}" if use_count else ""

        print(f"\n{name}{fav_mark}{use_str}")
        print(f"  {source_label}  |  {category}  |  devices: {', '.join(devices)}")
        if stars:
            print(f"  {stars}")
        if tags:
            print(f"  tags: {', '.join(tags)}")
        if desc_short:
            print(f"  desc: {desc_short}")
        print(f"  file: {fpath}")

    print(f"\n{len(rows)} result(s)")


# ---------------------------------------------------------------------------
# Stats command
# ---------------------------------------------------------------------------

def cmd_stats(args: argparse.Namespace) -> None:
    if not DB_PATH.exists():
        print("Database not built yet.", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    total = cur.execute("SELECT COUNT(*) FROM presets").fetchone()[0]
    print(f"Total presets: {total}")

    print("\nBy source:")
    for src, cnt in cur.execute(
        "SELECT source, COUNT(*) FROM presets GROUP BY source ORDER BY 2 DESC"
    ).fetchall():
        print(f"  {src:20s} {cnt}")

    print("\nBy pack (top 15):")
    for pack, cnt in cur.execute(
        "SELECT pack, COUNT(*) FROM presets WHERE pack IS NOT NULL GROUP BY pack ORDER BY 2 DESC LIMIT 15"
    ).fetchall():
        print(f"  {(pack or '(none)'):35s} {cnt}")

    print("\nBy category (top 20):")
    for cat, cnt in cur.execute(
        "SELECT category, COUNT(*) FROM presets WHERE category IS NOT NULL GROUP BY category ORDER BY 2 DESC LIMIT 20"
    ).fetchall():
        print(f"  {(cat or '(none)'):30s} {cnt}")

    print("\nTop tags (top 30):")
    for tag, cnt in cur.execute(
        "SELECT tag, COUNT(*) FROM preset_tags GROUP BY tag ORDER BY 2 DESC LIMIT 30"
    ).fetchall():
        print(f"  {tag:20s} {cnt}")

    print("\nMost-used presets (top 10):")
    for name, pack, uc in cur.execute(
        "SELECT name, pack, use_count FROM presets WHERE use_count > 0 ORDER BY use_count DESC LIMIT 10"
    ).fetchall():
        print(f"  ×{uc:3d}  {name}  [{pack}]")

    print("\nSongs:")
    for slug, title, status, key, scale, bpm in cur.execute(
        "SELECT slug, title, status, key, scale, bpm FROM songs ORDER BY status, slug"
    ).fetchall():
        print(f"  [{status}]  {slug}  —  {title}  |  {key} {scale} {bpm} BPM")

    total_mid = cur.execute("SELECT COUNT(*) FROM midi_patterns").fetchone()[0]
    total_audio = cur.execute("SELECT COUNT(*) FROM generated_audio WHERE is_stem=0").fetchone()[0]
    total_stems = cur.execute("SELECT COUNT(*) FROM generated_audio WHERE is_stem=1").fetchone()[0]
    print(f"\nMIDI patterns: {total_mid}")
    print(f"Generated audio: {total_audio} files, {total_stems} stems")

    db_size = DB_PATH.stat().st_size
    print(f"\nDatabase size: {db_size // 1024} KB  ({DB_PATH})")
    con.close()


# ---------------------------------------------------------------------------
# Songs command
# ---------------------------------------------------------------------------

def cmd_songs(args: argparse.Namespace) -> None:
    if not DB_PATH.exists():
        print("Database not built yet.", file=sys.stderr)
        sys.exit(1)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    for slug, title, status, key, scale, bpm in cur.execute(
        "SELECT slug, title, status, key, scale, bpm FROM songs ORDER BY status, slug"
    ).fetchall():
        active_mark = " ← ACTIVE" if status == "active" else ""
        bpm_str = f"{bpm} BPM" if bpm else ""
        key_str = f"{key} {scale}" if key else ""
        print(f"[{status}] {slug}  —  {title}  {key_str}  {bpm_str}{active_mark}")
    con.close()


# ---------------------------------------------------------------------------
# Audio command
# ---------------------------------------------------------------------------

def cmd_audio(args: argparse.Namespace) -> None:
    if not DB_PATH.exists():
        print("Database not built yet.", file=sys.stderr)
        sys.exit(1)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    q = "SELECT filename, song_slug, target, is_stem, stem_type FROM generated_audio"
    p: list = []
    if args.song:
        q += " WHERE song_slug = ?"
        p.append(args.song)
    q += " ORDER BY song_slug, filename"
    for row in cur.execute(q, p).fetchall():
        fname, song, target, is_stem, stype = row
        kind = f"[stem:{stype}]" if is_stem else "[source]"
        print(f"  {kind:15s} {(song or '?'):30s} {fname}")
        if target and not is_stem:
            print(f"               target: {target}")
    con.close()


# ---------------------------------------------------------------------------
# MIDI command
# ---------------------------------------------------------------------------

def cmd_midi(args: argparse.Namespace) -> None:
    if not DB_PATH.exists():
        print("Database not built yet.", file=sys.stderr)
        sys.exit(1)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    q = "SELECT name, song_slug, instrument, key, scale, bpm FROM midi_patterns"
    p: list = []
    if args.song:
        q += " WHERE song_slug = ?"
        p.append(args.song)
    q += " ORDER BY song_slug, name"
    for row in cur.execute(q, p).fetchall():
        name, song, inst, key, scale, bpm = row
        print(f"  {name}  [{song}]  inst={inst}  {key} {scale} {bpm} BPM")
    con.close()


# ---------------------------------------------------------------------------
# Tag command
# ---------------------------------------------------------------------------

def _resolve_preset(cur: sqlite3.Cursor, name_fragment: str) -> int:
    rows = cur.execute(
        "SELECT id, name FROM presets WHERE name LIKE ? ORDER BY name LIMIT 5",
        (f"%{name_fragment}%",),
    ).fetchall()
    if not rows:
        print(f"No preset matching '{name_fragment}'", file=sys.stderr)
        sys.exit(1)
    if len(rows) > 1:
        print(f"Multiple matches for '{name_fragment}':", file=sys.stderr)
        for r in rows:
            print(f"  [{r[0]}] {r[1]}", file=sys.stderr)
        sys.exit(1)
    return rows[0][0]


def cmd_tag(args: argparse.Namespace) -> None:
    if not DB_PATH.exists():
        print("Database not built yet.", file=sys.stderr)
        sys.exit(1)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    preset_id = _resolve_preset(cur, args.name)

    if args.tag_action == "add":
        cur.execute(
            "INSERT OR REPLACE INTO preset_tags (preset_id, tag, is_auto) VALUES (?,?,0)",
            (preset_id, args.tag),
        )
        print(f"Added tag '{args.tag}' to preset {preset_id}")
    elif args.tag_action == "remove":
        cur.execute(
            "DELETE FROM preset_tags WHERE preset_id=? AND tag=?",
            (preset_id, args.tag),
        )
        print(f"Removed tag '{args.tag}' from preset {preset_id}")

    con.commit()
    con.close()


# ---------------------------------------------------------------------------
# Rate command
# ---------------------------------------------------------------------------

def cmd_rate(args: argparse.Namespace) -> None:
    if not DB_PATH.exists():
        print("Database not built yet.", file=sys.stderr)
        sys.exit(1)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    preset_id = _resolve_preset(cur, args.name)
    cur.execute("UPDATE presets SET dave_rating=? WHERE id=?", (args.rating, preset_id))
    con.commit()
    print(f"Rated preset {preset_id}: {'★' * args.rating}")
    con.close()


# ---------------------------------------------------------------------------
# Fav command
# ---------------------------------------------------------------------------

def cmd_fav(args: argparse.Namespace) -> None:
    if not DB_PATH.exists():
        print("Database not built yet.", file=sys.stderr)
        sys.exit(1)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    preset_id = _resolve_preset(cur, args.name)
    current = cur.execute("SELECT is_favourite FROM presets WHERE id=?", (preset_id,)).fetchone()[0]
    new_val = 0 if current else 1
    cur.execute("UPDATE presets SET is_favourite=? WHERE id=?", (new_val, preset_id))
    con.commit()
    state = "♥ favourited" if new_val else "unfavourited"
    print(f"Preset {preset_id}: {state}")
    con.close()


# ---------------------------------------------------------------------------
# Enrich-packs command
# ---------------------------------------------------------------------------

def cmd_enrich_packs(args: argparse.Namespace) -> None:
    """Fetch/refresh pack metadata from ableton.com and re-apply tags to presets."""
    if not DB_PATH.exists():
        print("Database not built yet — run build first.", file=sys.stderr)
        sys.exit(1)

    con = sqlite3.connect(DB_PATH)
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript("""
        CREATE TABLE IF NOT EXISTS packs (
            name TEXT PRIMARY KEY,
            slug TEXT,
            url TEXT,
            author TEXT,
            description TEXT,
            genre_tags TEXT,
            instrument_tags TEXT,
            sample_providers TEXT,
            content_summary TEXT,
            enriched_at TEXT,
            installed INTEGER DEFAULT 0,
            pack_unique_id TEXT,
            download_mb INTEGER,
            install_mb INTEGER,
            relevance TEXT,
            relevance_reason TEXT
        );
    """)

    # Collect all distinct pack names from presets table
    cur = con.cursor()
    pack_names = [r[0] for r in cur.execute(
        "SELECT DISTINCT pack FROM presets WHERE pack IS NOT NULL AND pack != ''"
    ).fetchall()]

    print(f"Found {len(pack_names)} packs in database")
    force = getattr(args, 'force', False)
    ne = import_packs(con, pack_names, force=force)
    print(f"Scraped {ne} pack pages")

    na = apply_pack_tags_to_presets(con)
    print(f"Applied {na} pack tag assignments to presets")

    # Print summary
    enriched = cur.execute(
        "SELECT name, author, genre_tags, instrument_tags, content_summary FROM packs WHERE enriched_at IS NOT NULL ORDER BY name"
    ).fetchall()
    print(f"\nEnriched packs ({len(enriched)}):")
    for name, author, genre_j, inst_j, contents in enriched:
        genres = json.loads(genre_j or "[]") 
        insts = json.loads(inst_j or "[]")
        all_tags = genres + insts
        tag_str = ", ".join(all_tags) if all_tags else "(no tags)"
        print(f"  {name}")
        print(f"    by {author}  |  {contents}")
        print(f"    tags: {tag_str}")

    con.close()


# ---------------------------------------------------------------------------
# Catalog command
# ---------------------------------------------------------------------------

def cmd_catalog(args: argparse.Namespace) -> None:
    """Show available Ableton packs with IRON STATIC relevance ratings."""
    if not DB_PATH.exists():
        # Fall back to reading example_packs.json directly
        if not EXAMPLE_PACKS_JSON.exists():
            print("No DB and no Ableton app bundle found.", file=sys.stderr)
            sys.exit(1)
        ex = json.loads(EXAMPLE_PACKS_JSON.read_text())
        catalog_meta = {p["name"]: p for p in PACK_CATALOG}
        rows = []
        for e in ex:
            name = e["title"]
            meta = catalog_meta.get(name, {})
            rows.append((name, 0,
                         meta.get("install_mb", e.get("installation_size", 0) // (1024 * 1024)),
                         meta.get("relevance", "unknown"),
                         meta.get("relevance_reason", ""), ""))
    else:
        con = sqlite3.connect(DB_PATH)
        cur = con.cursor()
        rows = cur.execute(
            """SELECT name, installed, install_mb, relevance, relevance_reason, content_summary
               FROM packs WHERE pack_unique_id IS NOT NULL
               ORDER BY CASE relevance
                 WHEN 'high'   THEN 0
                 WHEN 'medium' THEN 1
                 WHEN 'low'    THEN 2
                 WHEN 'no'     THEN 3
                 ELSE 4
               END, name"""
        ).fetchall()
        con.close()

    relevance_filter = getattr(args, "relevance", None)
    show_all = getattr(args, "all", False)

    SYMBOLS = {"high": "\u2605\u2605\u2605", "medium": "\u2605\u2605 ", "low": "\u2605  ", "no": "---", "unknown": " ? "}
    COLORS  = {"high": "\033[92m", "medium": "\033[93m", "low": "\033[90m", "no": "\033[90m", "unknown": "\033[90m"}
    RESET   = "\033[0m"

    def row_ok(row):
        _, installed, _, rel, _, _ = row
        if not show_all and installed:
            return False
        if relevance_filter and rel != relevance_filter:
            return False
        return True

    shown = [r for r in rows if row_ok(r)]

    if not show_all:
        print("Available (not installed) packs — sorted by IRON STATIC relevance")
    else:
        print("All known packs — sorted by IRON STATIC relevance")
    print()

    current_rel = None
    for name, installed, size, rel, reason, contents in shown:
        if rel != current_rel:
            current_rel = rel
            label = {"high": "HIGH VALUE", "medium": "MEDIUM", "low": "LOW",
                     "no": "SKIP", "unknown": "UNRATED"}.get(rel, rel.upper())
            print(f"\n  [── {label} ──]")
        color = COLORS.get(rel, "")
        sym = SYMBOLS.get(rel, " ? ")
        inst_str = " [INSTALLED]" if installed else f"  {size:5d} MB"
        print(f"  {color}{sym}{RESET}  {name:42s}{inst_str}")
        if reason:
            words, line, lines = reason.split(), "", []
            for w in words:
                if len(line) + len(w) + 1 > 72:
                    lines.append(line)
                    line = w
                else:
                    line = (line + " " + w).strip()
            if line:
                lines.append(line)
            for ln in lines:
                print(f"       {color}{ln}{RESET}")
        if contents:
            print(f"       {contents}")

    print()
    total_high = sum(1 for r in shown if r[3] == "high")
    total_mb   = sum(r[2] for r in shown if r[3] in ("high", "medium") and not r[1])
    if not show_all:
        print(f"  High-value packs to install: {total_high}")
        print(f"  Combined high+medium estimate: ~{total_mb:,} MB")
        print(f"  Install via: Ableton Live → Help → Install Pack...")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(
        description="IRON STATIC preset database builder and query tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # build
    bp = sub.add_parser("build", help="Build/rebuild the database")
    bp.add_argument("--incremental", action="store_true",
                    help="Add new records without dropping existing ones")
    bp.add_argument("--no-use-count", action="store_true",
                    help="Skip Ableton use_count cross-reference")
    bp.add_argument("--no-enrich", action="store_true",
                    help="Skip fetching pack metadata from ableton.com")

    # query
    qp = sub.add_parser("query", help="Search presets")
    qp.add_argument("text", nargs="?", default=None, help="Text to search in name/description")
    qp.add_argument("--tag", nargs="+", default=[], help="Filter by tag(s) (AND logic)")
    qp.add_argument("--source", choices=["ableton_pack", "hardware", "software", "ableton_builtin"])
    qp.add_argument("--category", help="Category name (partial match)")
    qp.add_argument("--pack", help="Pack name (partial match)")
    qp.add_argument("--device", help="Device type in rack (partial match)")
    qp.add_argument("--instrument", help="Instrument slug for hardware presets")
    qp.add_argument("--favourite", action="store_true", help="Only favourited presets")
    qp.add_argument("--min-rating", type=int, default=0)
    qp.add_argument("--sort", choices=["name", "use_count"], default="name")
    qp.add_argument("--limit", type=int, default=25)

    # stats
    sub.add_parser("stats", help="Database statistics overview")

    # songs
    sub.add_parser("songs", help="List songs")

    # audio
    ap = sub.add_parser("audio", help="List generated audio files")
    ap.add_argument("--song", help="Filter by song slug")

    # midi
    mp2 = sub.add_parser("midi", help="List MIDI patterns")
    mp2.add_argument("--song", help="Filter by song slug")

    # catalog
    catp = sub.add_parser("catalog", help="Show available Ableton packs with relevance ratings")
    catp.add_argument("--relevance", choices=["high", "medium", "low", "no"],
                      help="Filter by relevance level")
    catp.add_argument("--all", action="store_true", help="Include already installed packs")

    # enrich-packs
    ep = sub.add_parser("enrich-packs", help="Fetch pack metadata from ableton.com and apply tags")
    ep.add_argument("--force", action="store_true", help="Re-scrape already enriched packs")

    # tag
    tp = sub.add_parser("tag", help="Manually add/remove tags")
    tp.add_argument("tag_action", choices=["add", "remove"])
    tp.add_argument("name", help="Preset name fragment")
    tp.add_argument("tag", help="Tag to add or remove")

    # rate
    rp = sub.add_parser("rate", help="Rate a preset 1-5")
    rp.add_argument("name", help="Preset name fragment")
    rp.add_argument("rating", type=int, choices=range(1, 6))

    # fav
    fp = sub.add_parser("fav", help="Toggle favourite on a preset")
    fp.add_argument("name", help="Preset name fragment")

    args = parser.parse_args()
    dispatch = {
        "build":         cmd_build,
        "query":         cmd_query,
        "stats":         cmd_stats,
        "songs":         cmd_songs,
        "audio":         cmd_audio,
        "midi":          cmd_midi,
        "catalog":       cmd_catalog,
        "tag":           cmd_tag,
        "rate":          cmd_rate,
        "fav":           cmd_fav,
        "enrich-packs":  cmd_enrich_packs,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
