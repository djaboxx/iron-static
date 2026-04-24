#!/usr/bin/env python3
"""generate_als.py — Inject instruments into an Ableton Live Set (.als).

Pure executor. Reads a config JSON that maps target ALS track names to device
sources, clears existing Devices blocks, and injects the correct XML.

Device XML is extracted verbatim from Internal.als (Live-saved, valid IDs) —
no hand-coded XML, no ID=0 renaming. The config file is generated externally
by The Live Engineer agent, which makes all creative decisions.

Usage:
    # List tracks in a base ALS (what names to use in config):
    python scripts/generate_als.py --list --base ableton/sessions/rust-protocol_v1.als

    # List devices available in Internal.als:
    python scripts/generate_als.py --list-devices

    # Generate a session using a config file:
    python scripts/generate_als.py \\
        --base ableton/sessions/rust-protocol_v1.als \\
        --config ableton/m4l/configs/rust-protocol-internal.json \\
        --out ableton/sessions/rust-protocol_v1-internal.als

    # Dry run (print plan, write nothing):
    python scripts/generate_als.py --base ... --config ... --dry-run -v

Config JSON format:
    {
      "tracks": {
        "TrackName": "InternalAlsTrackName",   // inject device from Internal.als
        "OtherTrack": "pigments",              // special: inject Pigments VST3
        "HardwareTrack": null                  // clear devices (hardware present)
      }
    }

    InternalAlsTrackName values come from --list-devices output.
    Any track not mentioned in config is left completely untouched.
"""

import argparse
import gzip
import json
import logging
import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
REFERENCE_ALS = REPO_ROOT / "ableton" / "sessions" / "Internal Project" / "Internal.als"
SONGS_JSON = REPO_ROOT / "database" / "songs.json"

# ---------------------------------------------------------------------------
# Pigments VST3 — hardcoded because it's a VST3, not a native Live device.
# IDs 1-4 are placeholders; _offset_ids() remaps them to safe values on inject.
# ---------------------------------------------------------------------------
_PIGMENTS_TEMPLATE = """<PluginDevice Id="1">
  <LomId Value="0" /><LomIdView Value="0" />
  <IsExpanded Value="false" /><BreakoutIsExpanded Value="false" />
  <On>
    <LomId Value="0" /><Manual Value="true" />
    <AutomationTarget Id="2"><LockEnvelope Value="0" /></AutomationTarget>
    <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
  </On>
  <ParametersListWrapper LomId="0" />
  <LastSelectedTimeableIndex Value="0" /><LastSelectedClipEnvelopeIndex Value="0" />
  <LastPresetRef><Value /></LastPresetRef>
  <LockedScripts />
  <IsFolded Value="false" /><ShouldShowPresetName Value="true" />
  <UserName Value="" /><Annotation Value="" />
  <SourceContext>
    <Value>
      <BranchSourceContext Id="0">
        <OriginalFileRef />
        <BrowserContentPath Value="query:Plugins#VST3:Arturia:Pigments" />
        <PresetRef /><BranchDeviceId Value="" />
      </BranchSourceContext>
    </Value>
  </SourceContext>
  <PluginDesc>
    <Vst3PluginInfo Id="3">
      <WinPosX Value="0" /><WinPosY Value="0" />
      <Preset>
        <Vst3Preset Id="4">
          <OverwriteProtectionNumber Value="2561" />
          <ParameterSettings />
          <IsOn Value="true" /><PowerMacroControlIndex Value="-1" />
          <PowerMacroMappingRange><Min Value="64" /><Max Value="127" /></PowerMacroMappingRange>
          <IsFolded Value="false" /><StoredAllParameters Value="true" />
          <DeviceLomId Value="0" /><DeviceViewLomId Value="0" />
          <IsOnLomId Value="0" /><ParametersListWrapperLomId Value="0" />
          <Uid>
            <Fields.0 Value="1098019957" /><Fields.1 Value="1096173907" />
            <Fields.2 Value="1264677937" /><Fields.3 Value="1349676899" />
          </Uid>
          <DeviceType Value="1" />
          <ProcessorState /><ControllerState />
          <Name Value="" /><PresetRef />
        </Vst3Preset>
      </Preset>
      <Name Value="Pigments" />
      <Uid>
        <Fields.0 Value="1098019957" /><Fields.1 Value="1096173907" />
        <Fields.2 Value="1264677937" /><Fields.3 Value="1349676899" />
      </Uid>
      <DeviceType Value="1" />
    </Vst3PluginInfo>
  </PluginDesc>
  <Parameters />
</PluginDevice>"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_next_pointee_id(als: str) -> int:
    m = re.search(r'<NextPointeeId Value="(\d+)"', als)
    return int(m.group(1)) if m else 10000


def _set_next_pointee_id(als: str, new_id: int) -> str:
    return re.sub(
        r'<NextPointeeId Value="\d+"',
        f'<NextPointeeId Value="{new_id}"',
        als, count=1,
    )


def _offset_ids(xml: str, offset: int) -> str:
    """Add offset to every Id="N" where N > 0. Safe for both Pigments template
    (IDs 1-4) and Internal.als extracts (IDs already > 0, just need collision
    avoidance). Does not touch Id="0" (structural zero-ID elements in Live XML).
    """
    def _shift(m):
        n = int(m.group(1))
        return f'Id="{n + offset}"' if n > 0 else m.group(0)
    return re.sub(r'Id="(\d+)"', _shift, xml)


def _find_tracks(als: str) -> list[dict]:
    """Return list of {id, name, start, end} dicts for all MidiTracks."""
    tracks = []
    matches = list(re.finditer(r'<MidiTrack Id="(\d+)"', als))
    for i, m in enumerate(matches):
        track_start = m.start()
        name_m = re.search(
            r'<EffectiveName Value="([^"]+)"',
            als[track_start:track_start + 1000],
        )
        name = name_m.group(1) if name_m else f"Track-{m.group(1)}"
        end = matches[i + 1].start() if i + 1 < len(matches) else len(als)
        tracks.append({"id": m.group(1), "name": name, "start": track_start, "end": end})
    return tracks


def _extract_from_reference(ref_als: str, ref_track_name: str) -> str:
    """Extract the inner content of <Devices>...</Devices> from Internal.als
    for the named track. Returns the raw XML string (IDs intact as Live wrote them).
    """
    tracks = _find_tracks(ref_als)
    match = next((t for t in tracks if t["name"] == ref_track_name), None)
    if not match:
        available = [t["name"] for t in tracks]
        raise ValueError(
            f"Track '{ref_track_name}' not found in Internal.als.\n"
            f"Available: {available}"
        )
    seg = ref_als[match["start"]:match["end"]]
    d_open = seg.find("<Devices>")
    if d_open < 0:
        raise ValueError(f"No <Devices> block found in Internal.als track '{ref_track_name}'")
    d_close = seg.find("</Devices>", d_open)
    if d_close < 0:
        raise ValueError(f"Unclosed <Devices> in Internal.als track '{ref_track_name}'")
    return seg[d_open + 9:d_close].strip()


def _replace_devices_block(als: str, track: dict, new_inner: str) -> str:
    """Replace the <Devices .../> or <Devices>...</Devices> block for a track."""
    segment = als[track["start"]:track["end"]]

    sc_m = re.search(r"<Devices\s*/>", segment)
    oc_open = segment.find("<Devices>")

    if sc_m is not None and (oc_open < 0 or sc_m.start() < oc_open):
        dev_open, dev_close = sc_m.start(), sc_m.end()
    elif oc_open >= 0:
        dev_open = oc_open
        close_pos = segment.find("</Devices>", oc_open)
        if close_pos < 0:
            logging.warning("No </Devices> closing tag in track '%s' — skipping", track["name"])
            return als
        dev_close = close_pos + len("</Devices>")
    else:
        logging.warning("No <Devices> block in track '%s' — skipping", track["name"])
        return als

    prefix = segment[max(0, dev_open - 40):dev_open]
    ws_m = re.search(r"\n(\s*)$", prefix)
    indent = ws_m.group(1) if ws_m else "    "

    replacement = (
        f"<Devices>\n{new_inner}\n{indent}</Devices>" if new_inner else "<Devices />"
    )
    new_segment = segment[:dev_open] + replacement + segment[dev_close:]
    return als[:track["start"]] + new_segment + als[track["end"]:]


# ---------------------------------------------------------------------------
# Core injection
# ---------------------------------------------------------------------------

def inject_from_config(als: str, ref_als: str, config: dict) -> str:
    """Inject devices according to config['tracks'].

    config['tracks'] values:
        "InternalAlsTrackName"  → extract device XML from Internal.als track
        "pigments"              → inject hardcoded Pigments VST3 template
        null                    → clear devices (empty Devices block)
    """
    track_config: dict[str, str | None] = config.get("tracks", {})
    tracks = _find_tracks(als)
    base_id = _get_next_pointee_id(als)

    # Build name→track lookup
    track_by_name = {t["name"]: t for t in tracks}

    # Determine safe ID offset for each injected device so they don't collide.
    # We space each device block 2000 IDs apart (largest device in Internal.als
    # is ~950 IDs — Operator at 384, MIDI arp at 937).
    id_cursor = base_id + 100
    max_id_used = id_cursor

    # Process in reverse order to preserve string offsets
    for track_name in reversed(list(track_config.keys())):
        source = track_config[track_name]
        track = track_by_name.get(track_name)
        if not track:
            logging.warning("Track '%s' not found in base ALS — skipping", track_name)
            continue

        if source is None:
            # Clear devices
            als = _replace_devices_block(als, track, "")
            logging.info("  %-20s → (cleared)", track_name)
        elif source.lower() == "pigments":
            injected = _offset_ids(_PIGMENTS_TEMPLATE.strip(), id_cursor)
            als = _replace_devices_block(als, track, injected)
            logging.info("  %-20s → Pigments VST3", track_name)
            id_cursor += 50
            max_id_used = max(max_id_used, id_cursor)
        else:
            raw = _extract_from_reference(ref_als, source)
            # Count IDs in raw to estimate cursor advance
            ids_in_raw = [int(x) for x in re.findall(r'\bId="(\d+)"', raw) if int(x) > 0]
            id_range = max(ids_in_raw) - min(ids_in_raw) if ids_in_raw else 0
            injected = _offset_ids(raw, id_cursor - (min(ids_in_raw) if ids_in_raw else 0))
            als = _replace_devices_block(als, track, injected)
            logging.info("  %-20s → %s (from Internal.als)", track_name, source)
            id_cursor += id_range + 200
            max_id_used = max(max_id_used, id_cursor)

        # Re-resolve track positions after each replacement (offsets shift)
        tracks = _find_tracks(als)
        track_by_name = {t["name"]: t for t in tracks}

    als = _set_next_pointee_id(als, max_id_used + 200)
    return als


# ---------------------------------------------------------------------------
# Active song resolution
# ---------------------------------------------------------------------------

def _get_active_song() -> dict | None:
    if not SONGS_JSON.exists():
        return None
    data = json.loads(SONGS_JSON.read_text())
    songs = data.get("songs", data) if isinstance(data, dict) else data
    for s in (songs.values() if isinstance(songs, dict) else songs):
        if s.get("status") == "active":
            return s
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Inject instruments into an Ableton Live Set (.als) from a config file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("--base", help="Input .als file. Defaults to active song's als_path.")
    p.add_argument("--config", help="JSON config file specifying track→device assignments.")
    p.add_argument("--out", help="Output .als file. Defaults to <base-stem>-internal.als.")
    p.add_argument(
        "--list",
        action="store_true",
        help="List track names in the base ALS and exit (use these in config).",
    )
    p.add_argument(
        "--list-devices",
        action="store_true",
        help="List device tracks available in Internal.als and exit.",
    )
    p.add_argument("--dry-run", action="store_true", help="Print plan without writing output.")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # --list-devices: inspect Internal.als
    if args.list_devices:
        if not REFERENCE_ALS.exists():
            logging.error("Internal.als not found: %s", REFERENCE_ALS)
            sys.exit(1)
        ref_als = gzip.open(REFERENCE_ALS).read().decode("utf-8", errors="replace")
        tracks = _find_tracks(ref_als)
        print("Available devices in Internal.als:")
        for t in tracks:
            seg = ref_als[t["start"]:t["end"]]
            d_open = seg.find("<Devices>")
            root = "(empty)"
            if d_open >= 0:
                inner = seg[d_open + 9:seg.find("</Devices>", d_open)].strip()
                rm = re.search(r"<(\w+)", inner)
                root = f"<{rm.group(1)}>" if rm else "(empty)"
            print(f"  {t['name']:<25} {root}")
        print('\n  "pigments"               <PluginDevice> (Arturia Pigments VST3)')
        return

    # Resolve base ALS
    base_path = None
    if args.base:
        base_path = Path(args.base)
    else:
        song = _get_active_song()
        if song and song.get("als_path"):
            base_path = Path(song["als_path"])
    if not base_path:
        logging.error("No --base specified and no active song with als_path.")
        sys.exit(1)
    if not base_path.exists():
        logging.error("Base ALS not found: %s", base_path)
        sys.exit(1)

    als = gzip.open(base_path).read().decode("utf-8", errors="replace")

    # --list: show track names in base ALS
    if args.list:
        tracks = _find_tracks(als)
        print(f"Tracks in {base_path.name}:")
        for t in tracks:
            print(f"  {t['name']}")
        return

    # Require config for generation
    if not args.config:
        logging.error("--config is required for session generation. Use --list to see track names.")
        sys.exit(1)

    config_path = Path(args.config)
    if not config_path.exists():
        logging.error("Config not found: %s", config_path)
        sys.exit(1)

    config = json.loads(config_path.read_text())

    if not REFERENCE_ALS.exists():
        logging.error("Internal.als not found: %s", REFERENCE_ALS)
        sys.exit(1)
    ref_als = gzip.open(REFERENCE_ALS).read().decode("utf-8", errors="replace")

    out_path = Path(args.out) if args.out else base_path.parent / (base_path.stem + "-internal.als")

    logging.info("Base:    %s", base_path)
    logging.info("Config:  %s", config_path)
    logging.info("Output:  %s", out_path)
    logging.info("Injection plan:")

    for track_name, source in config.get("tracks", {}).items():
        label = "(clear)" if source is None else source
        logging.info("  %-20s → %s", track_name, label)

    if args.dry_run:
        logging.info("Dry run — no output written.")
        return

    als = inject_from_config(als, ref_als, config)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_path, "wb", compresslevel=6) as fh:
        fh.write(als.encode("utf-8"))

    size_kb = out_path.stat().st_size // 1024
    logging.info("Written: %s (%d KB)", out_path, size_kb)
    logging.info("Open in Live: open '%s'", out_path)


if __name__ == "__main__":
    main()
