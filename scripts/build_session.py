#!/usr/bin/env python3
"""build_session.py — Build an Ableton Live Set (.als) from a spec without a template.

Uses Live's own Default MIDI Track as the track skeleton and the indexed ADG device
library as the device source. No hand-curated Internal.als required.

Session skeleton: Default MIDI Track.als (single-track valid session shipped with Live)
Track template:   Extracted from the skeleton's single MidiTrack — cloned per track
Devices:          database/device_library.json (run discover_devices.py first)
                  Falls back to Arturia Pigments VST3 hardcoded template for "pigments"

Usage:
    # Build device index first:
    python scripts/discover_devices.py

    # Build a session from JSON spec:
    python scripts/build_session.py --config ableton/m4l/configs/my-song.json \\
                                    --out ableton/sessions/my-song_v1.als

    # Dry run (no output written):
    python scripts/build_session.py --config ... --dry-run -v

Config JSON format:
    {
      "name": "My Song",
      "bpm": 138,
      "key": "E",
      "scale": "phrygian",
      "scenes": 8,
      "tracks": [
        {"name": "Bass Line",    "device": "808 Drifter"},
        {"name": "Drum Rack",    "device": "Strutter Kit",     "color": 10},
        {"name": "Pad Layer",    "device": "Warm Analog Pad",  "color": 8},
        {"name": "Lead Voice",   "device": "pigments",         "color": 12},
        {"name": "Noise Layer",  "device": null,               "color": 3}
      ]
    }

    "device" values:
      "Name of preset"   -- fuzzy-searched in device_library.json (name/file/type/category)
      "pigments"         -- injects hardcoded Arturia Pigments VST3 template
      null               -- empty MIDI track (no device)
"""

import argparse
import copy
import gzip
import json
import logging
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
SONGS_JSON = REPO_ROOT / "database" / "songs.json"
DEVICE_LIBRARY = REPO_ROOT / "database" / "device_library.json"

# Live's canonical blank track template — always current with installed Live version
SKELETON_ALS = Path(
    "/Applications/Ableton Live 12 Suite.app/Contents/App-Resources"
    "/Core Library/Defaults/Creating Tracks/MIDI Track/Default MIDI Track.als"
)

# IDs used by infrastructure in the skeleton (MainTrack, PreHearTrack, Transport…).
# The skeleton's NextPointeeId is 4416 — we start cloned track IDs well above this.
_INFRA_MAX_ID = 4416
_ID_STRIDE = 100000  # ID slots per track. Large enough for the biggest drum rack ADG.
# Per-track layout (relative to track_id_base):
#   0 – 49999  : track infrastructure (template IDs, shifted by _offset_ids)
#   50000 – 99999 : device preset IDs (normalized sequentially from base+50000)

# ---------------------------------------------------------------------------
# Branch MixerDevice template — used when reconstructing rack branches from ADG
# BranchPresets. All Id values are 1 so _renumber_ids assigns unique IDs.
# ---------------------------------------------------------------------------
_BRANCH_MIXER_DEVICE_XML = """<MixerDevice>
  <LomId Value="0" /><LomIdView Value="0" />
  <IsExpanded Value="true" /><BreakoutIsExpanded Value="false" />
  <On><LomId Value="0" /><Manual Value="true" />
    <AutomationTarget Id="1"><LockEnvelope Value="0" /></AutomationTarget>
    <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
  </On>
  <ModulationSourceCount Value="0" /><ParametersListWrapper LomId="1" />
  <Pointee Id="1" />
  <LastSelectedTimeableIndex Value="0" /><LastSelectedClipEnvelopeIndex Value="0" />
  <LastPresetRef><Value>
    <AbletonDefaultPresetRef Id="1">
      <FileRef>
        <RelativePathType Value="0" /><RelativePath Value="" /><Path Value="" />
        <Type Value="2" /><LivePackName Value="" /><LivePackId Value="" />
        <OriginalFileSize Value="0" /><OriginalCrc Value="0" /><SourceHint Value="" />
      </FileRef>
      <DeviceId Name="AudioBranchMixerDevice" />
    </AbletonDefaultPresetRef>
  </Value></LastPresetRef>
  <LockedScripts />
  <IsFolded Value="false" /><ShouldShowPresetName Value="false" />
  <UserName Value="" /><Annotation Value="" />
  <SourceContext><Value /></SourceContext>
  <MpePitchBendUsesTuning Value="true" /><ViewData Value="{}" />
  <OverwriteProtectionNumber Value="3075" />
  <Speaker><LomId Value="0" /><Manual Value="true" />
    <AutomationTarget Id="1"><LockEnvelope Value="0" /></AutomationTarget>
    <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
  </Speaker>
  <Volume><LomId Value="0" /><Manual Value="1" />
    <MidiControllerRange><Min Value="0.0003162277571" /><Max Value="1.99526238" /></MidiControllerRange>
    <AutomationTarget Id="1"><LockEnvelope Value="0" /></AutomationTarget>
    <ModulationTarget Id="1"><LockEnvelope Value="0" /></ModulationTarget>
  </Volume>
  <Panorama><LomId Value="0" /><Manual Value="0" />
    <MidiControllerRange><Min Value="-1" /><Max Value="1" /></MidiControllerRange>
    <AutomationTarget Id="1"><LockEnvelope Value="0" /></AutomationTarget>
    <ModulationTarget Id="1"><LockEnvelope Value="0" /></ModulationTarget>
  </Panorama>
  <SendInfos />
  <RoutingHelper><Routable>
    <Target Value="AudioOut/None" /><UpperDisplayString Value="No Output" />
    <LowerDisplayString Value="" />
    <MpeSettings><ZoneType Value="0" /><FirstNoteChannel Value="1" /><LastNoteChannel Value="15" /></MpeSettings>
    <MpePitchBendUsesTuning Value="true" />
  </Routable><TargetEnum Value="0" /></RoutingHelper>
  <SendsListWrapper LomId="1" />
</MixerDevice>"""


# ---------------------------------------------------------------------------
# Pigments VST3 hardcoded template (no ADG exists for VST3 plugins)
# ---------------------------------------------------------------------------
_PIGMENTS_DEVICE = """\
<PluginDevice Id="PLACEHOLDER_1">
  <LomId Value="0" /><LomIdView Value="0" />
  <IsExpanded Value="false" /><BreakoutIsExpanded Value="false" />
  <On>
    <LomId Value="0" /><Manual Value="true" />
    <AutomationTarget Id="PLACEHOLDER_2"><LockEnvelope Value="0" /></AutomationTarget>
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
    <Vst3PluginInfo Id="PLACEHOLDER_3">
      <WinPosX Value="0" /><WinPosY Value="0" />
      <Preset>
        <Vst3Preset Id="PLACEHOLDER_4">
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
# Device library
# ---------------------------------------------------------------------------

def _load_device_library() -> list[dict]:
    if not DEVICE_LIBRARY.exists():
        logging.warning(
            "Device library not found at %s. Run 'python scripts/discover_devices.py' first.",
            DEVICE_LIBRARY,
        )
        return []
    return json.loads(DEVICE_LIBRARY.read_text())


def _search_library(entries: list[dict], query: str) -> dict | None:
    """Return the best ADG entry matching query (case-insensitive, partial)."""
    q = query.lower()
    for e in entries:
        if (
            q == e["name"].lower()
            or q == e["file"].lower()
        ):
            return e  # exact match wins
    for e in entries:
        if q in e["name"].lower() or q in e["file"].lower():
            return e
    for e in entries:
        if q in e["device_type"].lower() or q in e["category"].lower():
            return e
    return None


def _reconstruct_branches_from_adg(gp: ET.Element, device: ET.Element) -> None:
    """Fill empty Branches in a rack device from the ADG's sibling BranchPresets.

    ADG rack presets store the rack shell with zero Branches. The actual per-branch
    content (instruments, samples, effects) lives in BranchPresets at the
    GroupDevicePreset level. This function reads BranchPresets and builds the
    Branches element so Live sees a fully-populated rack.

    Works for both DrumGroupDevice (DrumBranch) and InstrumentGroupDevice
    (InstrumentBranch).
    """
    branches_el = device.find("Branches")
    if branches_el is None or len(list(branches_el)) > 0:
        return  # Already populated or no Branches element

    bp_el = gp.find("BranchPresets")
    if bp_el is None or len(list(bp_el)) == 0:
        return

    is_drum = device.tag == "DrumGroupDevice"
    branch_tag = "DrumBranch" if is_drum else "InstrumentBranch"
    mixer_template = ET.fromstring(_BRANCH_MIXER_DEVICE_XML)

    for i, bp in enumerate(bp_el):
        # --- extract inner device -------------------------------------------
        dp = bp.find("DevicePresets")
        if dp is None or len(list(dp)) == 0:
            continue
        adp = list(dp)[0]  # First AbletonDevicePreset = the instrument
        inner_dev_wrapper = adp.find("Device")
        if inner_dev_wrapper is None or len(list(inner_dev_wrapper)) == 0:
            continue
        inner_device = copy.deepcopy(list(inner_dev_wrapper)[0])

        # --- metadata --------------------------------------------------------
        name_el = bp.find("Name")
        name_val = name_el.get("Value", "") if name_el is not None else ""
        zone_el = bp.find("ZoneSettings")  # has ReceivingNote for drum racks
        bsr_el = bp.find("BranchSelectorRange")

        # --- build branch element --------------------------------------------
        branch = ET.Element(branch_tag, attrib={"Id": str(i + 1)})

        ET.SubElement(branch, "LomId", attrib={"Value": "0"})
        name_tag = ET.SubElement(branch, "Name")
        ET.SubElement(name_tag, "EffectiveName", attrib={"Value": name_val})
        ET.SubElement(name_tag, "UserName", attrib={"Value": ""})
        ET.SubElement(name_tag, "Annotation", attrib={"Value": ""})
        ET.SubElement(name_tag, "MemorizedFirstClipName", attrib={"Value": ""})
        ET.SubElement(branch, "IsSelected", attrib={"Value": "false"})

        dc = ET.SubElement(branch, "DeviceChain")
        mtadc = ET.SubElement(dc, "MidiToAudioDeviceChain", attrib={"Id": "1"})
        devs_el = ET.SubElement(mtadc, "Devices")
        devs_el.append(inner_device)
        ET.SubElement(mtadc, "SignalModulations")

        if bsr_el is not None:
            branch.append(copy.deepcopy(bsr_el))
        else:
            bsr = ET.SubElement(branch, "BranchSelectorRange")
            for k in ("Min", "Max", "CrossfadeMin", "CrossfadeMax"):
                ET.SubElement(bsr, k, attrib={"Value": "0"})

        ET.SubElement(branch, "IsSoloed", attrib={"Value": "false"})
        ET.SubElement(branch, "SessionViewBranchWidth", attrib={"Value": "74"})
        ET.SubElement(branch, "IsHighlightedInSessionView", attrib={"Value": "false"})
        sc = ET.SubElement(branch, "SourceContext")
        ET.SubElement(sc, "Value")
        ET.SubElement(branch, "Color", attrib={"Value": "-1"})
        ET.SubElement(branch, "AutoColored", attrib={"Value": "true"})
        ET.SubElement(branch, "AutoColorScheme", attrib={"Value": "0"})
        ET.SubElement(branch, "SoloActivatedInSessionMixer", attrib={"Value": "false"})
        ET.SubElement(branch, "DevicesListWrapper", attrib={"LomId": "0"})
        branch.append(copy.deepcopy(mixer_template))

        if is_drum:
            recv_val = str(36 + i)  # default: C1 upward
            send_val = "60"
            choke_val = "0"
            if zone_el is not None:
                r = zone_el.find("ReceivingNote")
                s = zone_el.find("SendingNote")
                c = zone_el.find("ChokeGroup")
                if r is not None:
                    recv_val = r.get("Value", recv_val)
                if s is not None:
                    send_val = s.get("Value", send_val)
                if c is not None:
                    choke_val = c.get("Value", choke_val)
            bi = ET.SubElement(branch, "BranchInfo")
            ET.SubElement(bi, "ReceivingNote", attrib={"Value": recv_val})
            ET.SubElement(bi, "SendingNote", attrib={"Value": send_val})
            ET.SubElement(bi, "ChokeGroup", attrib={"Value": choke_val})
        else:
            zs = ET.SubElement(branch, "ZoneSettings")
            kr = ET.SubElement(zs, "KeyRange")
            for k, v in (("Min", "0"), ("Max", "127"), ("CrossfadeMin", "0"), ("CrossfadeMax", "127")):
                ET.SubElement(kr, k, attrib={"Value": v})
            vr = ET.SubElement(zs, "VelocityRange")
            for k, v in (("Min", "1"), ("Max", "127"), ("CrossfadeMin", "1"), ("CrossfadeMax", "127")):
                ET.SubElement(vr, k, attrib={"Value": v})

        branches_el.append(branch)


def _extract_device_from_adg(adg_path: str) -> str:
    """Extract the device XML string from a .adg file.

    ADG rack presets store the rack shell in GroupDevicePreset > Device, and
    the actual per-branch content in GroupDevicePreset > BranchPresets. We
    extract the rack shell, reconstruct its Branches from BranchPresets, then
    serialise the fully-populated device.

    Returns the serialised <DeviceTag …>…</DeviceTag> XML string.
    """
    xml_bytes = gzip.open(adg_path).read()
    root = ET.fromstring(xml_bytes)
    gp = root.find("GroupDevicePreset")
    dev_wrapper = gp.find("Device")
    device = next(iter(dev_wrapper), None)
    if device is None:
        raise ValueError(f"No device element found in {adg_path}")

    # Reconstruct branches from BranchPresets (fills the empty Branches element)
    _reconstruct_branches_from_adg(gp, device)

    device_xml = ET.tostring(device, encoding="unicode")
    # Zero out stale runtime ID references that would cause "Invalid Pointee Id"
    # when Live validates the session at load time. These are repopulated by Live.
    device_xml = re.sub(r'(<LockId\s+Value=")(?!0")(\d+)"', r'\g<1>0"', device_xml)
    device_xml = re.sub(r'(<LomIdView\s+Value=")(?!0")(\d+)"', r'\g<1>0"', device_xml)
    # Live requires every <Pointee> element to have a non-zero ID. ADG presets store
    # Pointee as Id="0" (null/unassigned). Bump to Id="1" so _renumber_ids assigns a
    # real unique ID.
    device_xml = device_xml.replace('<Pointee Id="0" />', '<Pointee Id="1" />')
    # Live also requires AutomationTarget and ModulationTarget elements to have non-zero
    # IDs (they are the per-parameter automation hooks). ADG files store them as Id="0"
    # (unassigned). Assign unique placeholder values so _renumber_ids promotes each one
    # to a real unique ID. A shared counter starting at 100 avoids collisions with the
    # MacroSnapshot IDs (1, 2, 3) already present in some ADG presets.
    _tc: list[int] = [100]

    def _bump_target(m: re.Match) -> str:
        v = _tc[0]
        _tc[0] += 1
        return f"{m.group(1)}Id=\"{v}\""

    device_xml = re.sub(
        r'(<(?:AutomationTarget|ModulationTarget)\s+)Id="0"',
        _bump_target,
        device_xml,
    )
    # Pack ADGs store RelativePath as a container element with RelativePathElement
    # children. Live requires RelativePath to be a simple leaf: <RelativePath Value="" />.
    # A RelativePath with children causes "Base types can't have children"; without
    # Value causes "Required attribute 'Value' missing". Strip children and self-close.
    device_xml = re.sub(
        r'<RelativePath(?!\s+Value=)[^>]*>.*?</RelativePath>',
        '<RelativePath Value="" />',
        device_xml,
        flags=re.DOTALL,
    )
    return device_xml


# ---------------------------------------------------------------------------
# ID utilities
# ---------------------------------------------------------------------------

def _renumber_ids(xml: str, id_base: int) -> tuple[str, int]:
    """Assign a unique sequential ID to EVERY Id="N" (N > 0) occurrence in xml.

    The Default MIDI Track template (and device ADGs) use duplicate Id values across
    different sub-contexts — Live normally reassigns them at load time. We must do the
    same here to produce a valid ALS.

    - Every `Id="N"` occurrence gets its own new unique ID (even if two elements share the
      same old N, they get different new IDs).
    - `PointeeId Value="N"` cross-references are remapped to the new ID of the FIRST
      occurrence of old Id="N" — which is the standard forward-reference pattern used
      by Live's automation and remote-control system.
    - Id="0" is left as 0 (Live uses 0 as a null/no-pointee sentinel).

    Returns (rewritten_xml, next_available_id).
    """
    counter = id_base
    first_occurrence: dict[int, int] = {}   # old_id → new_id of first occurrence
    replacements: list[tuple[int, int, int]] = []  # (start, end, new_id)

    for m in re.finditer(r'Id="(\d+)"', xml):
        n = int(m.group(1))
        if n == 0:
            continue
        new_id = counter
        counter += 1
        replacements.append((m.start(), m.end(), new_id))
        if n not in first_occurrence:
            first_occurrence[n] = new_id

    # Apply id replacements from right to left so positions stay valid
    parts = list(xml)
    for start, end, new_id in reversed(replacements):
        parts[start:end] = list(f'Id="{new_id}"')
    xml = "".join(parts)

    # Remap PointeeId references
    def _remap_pointee(m: re.Match) -> str:
        n = int(m.group(1))
        if n == 0 or n not in first_occurrence:
            return m.group(0)
        return f'PointeeId Value="{first_occurrence[n]}"'

    xml = re.sub(r'PointeeId\s+Value="(\d+)"', _remap_pointee, xml)

    return xml, counter


def _normalize_device_ids(device_xml: str, id_base: int) -> tuple[str, int]:
    """Remap all Id=\"N\" (N > 0) in device XML to fresh sequential IDs starting at id_base.
    Returns (rewritten_xml, next_available_id).
    """
    result, next_id = _renumber_ids(device_xml, id_base)
    return result, next_id


def _set_placeholder_ids(xml: str, base: int) -> str:
    """Replace PLACEHOLDER_1..N markers with sequential IDs starting at base."""
    counter = [base]

    def _next(_: re.Match) -> str:
        val = counter[0]
        counter[0] += 1
        return f'Id="{val}"'

    return re.sub(r'Id="PLACEHOLDER_\d+"', _next, xml)


# ---------------------------------------------------------------------------
# ClipSlot expansion
# ---------------------------------------------------------------------------

_CLIP_SLOT_TMPL = """\
                                                        <ClipSlot Id="{slot_id}">
                                                                <LomId Value="0" />
                                                                <ClipSlot>
                                                                        <Value />
                                                                </ClipSlot>
                                                                <HasStop Value="true" />
                                                                <NeedRefreeze Value="true" />
                                                        </ClipSlot>"""


def _expand_clip_slots(track_xml: str, scene_count: int) -> str:
    """Replace ClipSlotList content with scene_count placeholder slots.

    Uses incrementing IDs starting at 1 across both lists so _renumber_ids (called later
    in _clone_track) can assign globally unique IDs to every slot occurrence.
    """
    list_index = [0]

    def _replace_list(_m: re.Match) -> str:
        base = list_index[0] * scene_count + 1
        list_index[0] += 1
        slots = "\n".join(_CLIP_SLOT_TMPL.format(slot_id=base + i) for i in range(scene_count))
        return (
            f"<ClipSlotList>\n{slots}\n"
            "                                                </ClipSlotList>"
        )

    return re.sub(
        r"<ClipSlotList>.*?</ClipSlotList>",
        _replace_list,
        track_xml,
        flags=re.DOTALL,
    )


# ---------------------------------------------------------------------------
# Track cloning
# ---------------------------------------------------------------------------

def _clone_track(
    template_xml: str,
    track_index: int,
    track_id_base: int,
    name: str,
    color: int,
    scene_count: int,
    device_xml: str | None,
) -> str:
    """Clone a MidiTrack XML block with fresh IDs, name, color, clip slots, and device.

    ID strategy: _renumber_ids() gives every Id="N" occurrence a unique sequential ID
    starting at track_id_base. This handles the template's pre-existing duplicate IDs
    (the Default MIDI Track template is not a standalone valid session — Live would
    normally reassign IDs at load time). Device XML is injected BEFORE renumbering so
    all IDs — track infrastructure + device — are renumbered in one pass.
    """
    xml = template_xml

    # 1. Expand ClipSlots — use placeholder IDs (all "0") so they get unique IDs in step 4
    xml = _expand_clip_slots(xml, scene_count)

    # 2. Set track name
    xml = re.sub(
        r'(<EffectiveName\s+Value=")[^"]*"',
        rf'\g<1>{_escape_xml_attr(name)}"',
        xml,
        count=1,
    )
    xml = re.sub(
        r'(<UserName\s+Value=")[^"]*"',
        r'\g<1>"',
        xml,
        count=1,
    )

    # 3. Set color
    xml = re.sub(r'(<Color\s+Value=")[^"]*"', rf'\g<1>{color}"', xml, count=1)

    # 4. Inject device XML RAW (IDs will be renumbered in step 5 along with track IDs)
    if device_xml is not None:
        xml = re.sub(
            r"<Devices\s*/>|<Devices>\s*</Devices>",
            f"<Devices>\n                                        {device_xml}\n                                </Devices>",
            xml,
            count=1,
            flags=re.DOTALL,
        )

    # 5. Renumber ALL Id= occurrences (track infrastructure + device) in one pass.
    xml, next_id = _renumber_ids(xml, track_id_base)

    # 6. The outer <MidiTrack> element retains Id="0" (template default, skipped by _renumber_ids).
    #    Assign it the next available unique ID so it has a valid non-zero pointee ID.
    xml = re.sub(r'^(<MidiTrack\s[^>]*?)Id="0"', rf'\g<1>Id="{next_id}"', xml, count=1)

    return xml


def _escape_xml_attr(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


# ---------------------------------------------------------------------------
# Scene expansion
# ---------------------------------------------------------------------------

def _expand_scenes(skeleton_xml: str, scene_count: int) -> str:
    """Replace the Scenes block with scene_count scenes (Ids 0…N-1)."""
    scene_tmpl = """\
                <Scene Id="{i}">
                        <Name>
                                <EffectiveName Value="" />
                                <UserName Value="" />
                                <Annotation Value="" />
                                <MemorizedFirstClipName Value="" />
                        </Name>
                        <Tempo>
                                <LomId Value="0" />
                                <Manual Value="-1" />
                                <MidiControllerRange><Min Value="60" /><Max Value="200" /></MidiControllerRange>
                                <AutomationTarget Id="{at_id}"><LockEnvelope Value="0" /></AutomationTarget>
                                <ModulationTarget Id="{mt_id}"><LockEnvelope Value="0" /></ModulationTarget>
                        </Tempo>
                        <IsTempoEnabled Value="false" />
                        <TimeSignatureId Value="201" />
                        <IsTimeSignatureEnabled Value="false" />
                        <LomId Value="0" />
                        <Color Value="-1" />
                        <Next>
                                <LomId Value="0" />
                                <Manual Value="" />
                                <AutomationTarget Id="{at2_id}"><LockEnvelope Value="0" /></AutomationTarget>
                        </Next>
                        <IsNextEnabled Value="false" />
                </Scene>"""

    # Use IDs starting at _INFRA_MAX_ID + 1 + num_tracks*_ID_STRIDE + 1000
    # These are guaranteed not to collide with track IDs
    scene_id_base = _INFRA_MAX_ID + 60000
    scenes = []
    for i in range(scene_count):
        scenes.append(
            scene_tmpl.format(
                i=i,
                at_id=scene_id_base + i * 3,
                mt_id=scene_id_base + i * 3 + 1,
                at2_id=scene_id_base + i * 3 + 2,
            )
        )
    scenes_xml = "\n".join(scenes)
    return re.sub(
        r"<Scenes>.*?</Scenes>",
        f"<Scenes>\n{scenes_xml}\n        </Scenes>",
        skeleton_xml,
        count=1,
        flags=re.DOTALL,
    )


# ---------------------------------------------------------------------------
# BPM / scale
# ---------------------------------------------------------------------------

def _set_tempo(xml: str, bpm: float) -> str:
    return re.sub(
        r'(<Tempo>.*?<Manual\s+Value=")[^"]*"',
        rf'\g<1>{bpm}"',
        xml,
        count=1,
        flags=re.DOTALL,
    )


# ---------------------------------------------------------------------------
# Active song
# ---------------------------------------------------------------------------

def _active_song() -> dict | None:
    if not SONGS_JSON.exists():
        return None
    data = json.loads(SONGS_JSON.read_text())
    songs = data.get("songs", data) if isinstance(data, dict) else data
    for s in (songs.values() if isinstance(songs, dict) else songs):
        if s.get("status") == "active":
            return s
    return None


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_session(config: dict, dry_run: bool = False, verbose: bool = False) -> str:
    """Build an ALS from config dict. Returns the final XML string."""
    song_name = config.get("name", "Untitled")
    bpm = float(config.get("bpm", 120))
    scene_count = int(config.get("scenes", 8))
    track_specs = config.get("tracks", [])

    logging.info("Building session: %r  bpm=%.1f  scenes=%d  tracks=%d", song_name, bpm, scene_count, len(track_specs))

    # Load skeleton
    if not SKELETON_ALS.exists():
        raise FileNotFoundError(f"Default MIDI Track not found at {SKELETON_ALS}")
    skeleton_xml = gzip.open(SKELETON_ALS).read().decode("utf-8", errors="replace")

    # Extract the template track from the skeleton
    track_m = re.search(r"<MidiTrack\s[^>]*>.*?</MidiTrack>", skeleton_xml, re.DOTALL)
    if not track_m:
        raise ValueError("No MidiTrack found in skeleton ALS")
    track_template = track_m.group(0)
    logging.debug("Extracted track template (%d chars)", len(track_template))

    # Remove the existing track from skeleton so we can add ours
    skeleton_xml = skeleton_xml[:track_m.start()] + skeleton_xml[track_m.end():]

    # Expand scenes
    skeleton_xml = _expand_scenes(skeleton_xml, scene_count)

    # Set BPM
    skeleton_xml = _set_tempo(skeleton_xml, bpm)

    # Load device library
    library = _load_device_library()

    # Build tracks
    tracks_xml_parts = []
    for i, spec in enumerate(track_specs):
        track_name = spec.get("name", f"Track {i + 1}")
        color = int(spec.get("color", 0))
        device_spec = spec.get("device")

        # Resolve device XML
        device_xml: str | None = None
        if device_spec is None:
            logging.info("  [%d] %s  → (no device)", i, track_name)
        elif device_spec.lower() == "pigments":
            id_base = _INFRA_MAX_ID + (i + 1) * _ID_STRIDE + 50000
            device_xml = _set_placeholder_ids(_PIGMENTS_DEVICE, id_base)
            logging.info("  [%d] %s  → Pigments VST3", i, track_name)
        elif device_spec.endswith(".adg") or ("/" in device_spec) or device_spec.startswith("."):
            # Direct file path — resolve relative to repo root
            adg_path = Path(device_spec) if Path(device_spec).is_absolute() else REPO_ROOT / device_spec
            try:
                device_xml = _extract_device_from_adg(str(adg_path))
                logging.info("  [%d] %s  → %s (direct path)", i, track_name, adg_path.name)
            except Exception as exc:
                logging.warning("  [%d] %s  → failed to load ADG at %s: %s", i, track_name, adg_path, exc)
        else:
            entry = _search_library(library, device_spec)
            if entry:
                try:
                    device_xml = _extract_device_from_adg(entry["path"])
                    logging.info("  [%d] %s  → %s [%s]", i, track_name, entry["name"], entry["source"])
                except Exception as exc:
                    logging.warning("  [%d] %s  → failed to load ADG (%s): %s", i, track_name, entry["path"], exc)
            else:
                logging.warning(
                    "  [%d] %s  → device %r not found in library (use discover_devices.py --search to check)",
                    i, track_name, device_spec,
                )

        track_id_base = _INFRA_MAX_ID + (i + 1) * _ID_STRIDE
        track_xml = _clone_track(
            template_xml=track_template,
            track_index=i,
            track_id_base=track_id_base,
            name=track_name,
            color=color,
            scene_count=scene_count,
            device_xml=device_xml,
        )
        tracks_xml_parts.append(track_xml)
        logging.debug("    → cloned track XML (%d chars)", len(track_xml))

    # Inject all tracks into <Tracks>…</Tracks>
    tracks_block = "\n".join(tracks_xml_parts)
    skeleton_xml = re.sub(
        r"<Tracks>\s*</Tracks>|<Tracks/>",
        f"<Tracks>\n{tracks_block}\n        </Tracks>",
        skeleton_xml,
        count=1,
        flags=re.DOTALL,
    )

    # Also handle non-empty Tracks from skeleton (the one we stripped the track from)
    if "<Tracks>" in skeleton_xml and "</Tracks>" in skeleton_xml:
        skeleton_xml = re.sub(
            r"(<Tracks>)\s*(</Tracks>)",
            rf"\g<1>\n{tracks_block}\n        \g<2>",
            skeleton_xml,
            count=1,
            flags=re.DOTALL,
        )

    # Update NextPointeeId
    # Final global renumber — eliminates pre-existing duplicate IDs in the skeleton
    # infrastructure (Default MIDI Track.als was designed as a per-track template, not a
    # standalone valid session; its infrastructure has duplicate IDs that Live normally
    # patches at load time). One sequential pass over the complete assembled XML makes
    # every Id= globally unique and keeps all PointeeId cross-references consistent.
    skeleton_xml, next_id = _renumber_ids(skeleton_xml, 1)

    # Update NextPointeeId to be above all assigned IDs
    skeleton_xml = re.sub(
        r'<NextPointeeId Value="\d+"',
        f'<NextPointeeId Value="{next_id + 1000}"',
        skeleton_xml,
        count=1,
    )

    return skeleton_xml


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Build an Ableton Live Set from a JSON spec without a template.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--config",
        help="JSON config file. If omitted, builds a minimal test session from the active song.",
    )
    p.add_argument(
        "--out",
        help="Output .als path. Defaults to ableton/sessions/<name>.als.",
    )
    p.add_argument("--dry-run", action="store_true", help="Build but do not write output.")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    # Load config
    if args.config:
        config = json.loads(Path(args.config).read_text())
    else:
        # Build a minimal test config from the active song
        song = _active_song()
        if not song:
            logging.error("No active song found and no --config supplied.")
            sys.exit(1)
        config = {
            "name": song.get("title", song.get("slug", "session")),
            "bpm": song.get("bpm", 120),
            "scenes": 8,
            "tracks": [
                {"name": "Bass Voice",        "device": None, "color": 5},
                {"name": "Machine Events",    "device": None, "color": 10},
                {"name": "Intelligence Layer","device": "pigments", "color": 8},
                {"name": "Choir Pads",        "device": None, "color": 12},
                {"name": "Drum Rack",         "device": None, "color": 3},
            ],
        }
        logging.info("No config supplied — using active song: %s", config["name"])

    # Determine output path
    if args.out:
        out_path = Path(args.out)
    else:
        slug = re.sub(r"[^\w-]", "-", config.get("name", "session").lower())
        out_path = REPO_ROOT / "ableton" / "sessions" / f"{slug}_v1.als"

    if args.dry_run:
        logging.info("Dry run — no output will be written.")

    # Build
    result_xml = build_session(config, dry_run=args.dry_run, verbose=args.verbose)

    if args.dry_run:
        logging.info("Dry run complete. Would write %d chars to %s", len(result_xml), out_path)
        return

    # Write
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(out_path, "wb") as fh:
        fh.write(result_xml.encode("utf-8"))
    logging.info("Written: %s  (%d bytes gzipped)", out_path, out_path.stat().st_size)


if __name__ == "__main__":
    main()
