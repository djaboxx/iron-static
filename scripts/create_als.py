#!/usr/bin/env python3
"""
create_als.py — Generate a minimal Ableton Live 12 .als session file from
an Iron Static HCL template. Writes gzip-compressed XML directly.

Usage:
    python scripts/create_als.py --template ableton/templates/rust-protocol.hcl
    python scripts/create_als.py --template ableton/templates/rust-protocol.hcl \\
        --output ableton/sessions/rust-protocol_v1.als
    python scripts/create_als.py --template ... --open     # open in Ableton after write

The script reads the HCL template (same format as ableton_push.py setup-rig),
infers song metadata from database/songs.json if a matching slug is found,
and writes a valid .als that Live 12 can open cleanly.

MIDI output routing is left as "None" — set it in Ableton after opening by
selecting your MIDI interface on each track. All other track properties
(name, color, clip slot count) are set correctly from the template.

Requires: python-hcl2
    pip install python-hcl2
"""

import argparse
import gzip
import json
import logging
import re
import subprocess
import sys
from html import escape as xesc
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Live 12 scale name → integer index mapping
# (matches Live 12's ScaleInformation/Name Value encoding)
# ---------------------------------------------------------------------------
SCALE_NAME_INDEX = {
    "major":             0,
    "minor":             1,
    "dorian":            2,
    "mixolydian":        3,
    "lydian":            4,
    "phrygian":          5,
    "locrian":           6,
    "whole tone":        7,
    "half-whole dim":    8,
    "whole-half dim":    9,
    "minor blues":       10,
    "minor pentatonic":  11,
    "major pentatonic":  12,
    "harmonic minor":    13,
    "melodic minor":     14,
}

NOTE_NAME_ROOT = {
    "c": 0, "c#": 1, "db": 1, "d": 2, "d#": 3, "eb": 3,
    "e": 4, "f": 5, "f#": 6, "gb": 6, "g": 7, "g#": 8,
    "ab": 8, "a": 9, "a#": 10, "bb": 10, "b": 11,
}

# ---------------------------------------------------------------------------
# ID counter — every element with an Id or LomId needs a unique int
# ---------------------------------------------------------------------------
_id_counter = [1]

def _next_id():
    v = _id_counter[0]
    _id_counter[0] += 1
    return v


# ---------------------------------------------------------------------------
# HCL loading (mirrors load_hcl in ableton_push.py)
# ---------------------------------------------------------------------------

def load_hcl(path: Path) -> dict:
    try:
        import hcl2
    except ImportError:
        log.error("python-hcl2 not installed. Run: pip install python-hcl2")
        sys.exit(1)

    with path.open("r", encoding="utf-8") as f:
        raw = hcl2.load(f)

    rig = {"name": path.stem, "tempo": 120.0, "time_signature": [4, 4], "tracks": []}

    for session_block in raw.get("session", []):
        if "name" in session_block:
            rig["name"] = session_block["name"]
        if "tempo" in session_block:
            rig["tempo"] = float(session_block["tempo"])
        if "time_signature" in session_block:
            rig["time_signature"] = list(session_block["time_signature"])

    for track_entry in raw.get("track", []):
        for track_name_raw, track_attrs in track_entry.items():
            # hcl2 preserves block-label quotes: '"Digitakt"' → 'Digitakt'
            track_name = track_name_raw.strip('"')
            if isinstance(track_attrs, list):
                track_attrs = track_attrs[0]
            clips = []
            for clip_entry in track_attrs.get("clips", []):
                if isinstance(clip_entry, dict):
                    clips.append({
                        "index": int(clip_entry.get("index", 0)),
                        "length": float(clip_entry.get("length", 4.0)),
                        "name": str(clip_entry.get("name", "clip")).strip('"'),
                    })
            color = track_attrs.get("color", 0)
            if color is not None:
                color = int(color)
            rig["tracks"].append({
                "name": track_name,
                "midi_channel": int(track_attrs.get("midi_channel", 1)),
                "color": color or 0,
                "clips": clips,
            })
    return rig


# ---------------------------------------------------------------------------
# Song DB lookup
# ---------------------------------------------------------------------------

def get_song_meta(session_name: str) -> dict:
    """Try to find a matching song in songs.json for key/scale info."""
    songs_path = REPO_ROOT / "database" / "songs.json"
    if not songs_path.exists():
        return {}
    try:
        db = json.loads(songs_path.read_text())
        slug = re.sub(r"[^a-z0-9]+", "-", session_name.lower()).strip("-")
        for song in db.get("songs", []):
            if song.get("slug") == slug or song.get("title", "").lower() == session_name.lower():
                return song
        # Fall back to active song
        for song in db.get("songs", []):
            if song.get("status") == "active":
                return song
    except Exception:
        pass
    return {}


# ---------------------------------------------------------------------------
# XML building blocks (minimal Live 12–compatible XML via f-strings)
# ---------------------------------------------------------------------------

MPE_SETTINGS = """\
<MpeSettings>
  <ZoneType Value="0" />
  <FirstNoteChannel Value="1" />
  <LastNoteChannel Value="15" />
</MpeSettings>
<MpePitchBendUsesTuning Value="true" />"""


def _routing(target, upper, lower):
    return f"""\
<Target Value="{target}" />
<UpperDisplayString Value="{upper}" />
<LowerDisplayString Value="{lower}" />
{MPE_SETTINGS}"""


def _automation_lane(id_val):
    return f"""\
<AutomationLane Id="{id_val}">
  <SelectedDevice Value="0" />
  <SelectedEnvelope Value="0" />
  <IsContentSelectedInDocument Value="false" />
  <LaneHeight Value="51" />
</AutomationLane>"""


def _automation_target(id_val):
    return f"""\
<AutomationTarget Id="{id_val}">
  <LockEnvelope Value="0" />
</AutomationTarget>"""


def _modulation_target(id_val):
    return f"""\
<ModulationTarget Id="{id_val}">
  <LockEnvelope Value="0" />
</ModulationTarget>"""


def _mixer_block(id_base: int, tempo_val: float, num: int, denom: int, is_main=False):
    """Generate a Mixer XML block. For the MainTrack, includes Tempo + TimeSignature + GlobalGrooveAmount."""
    tid = id_base
    if is_main:
        tempo_block = f"""\
<Tempo>
  <LomId Value="{_next_id()}" />
  <Manual Value="{tempo_val:.6f}" />
  <MidiControllerRange>
    <Min Value="60" />
    <Max Value="200" />
  </MidiControllerRange>
  {_automation_target(_next_id())}
  {_modulation_target(_next_id())}
</Tempo>
<TimeSignature>
  <LomId Value="0" />
  <Manual Value="201" />
  {_automation_target(_next_id())}
  <MidiControllerRange>
    <Min Value="0" />
    <Max Value="494" />
  </MidiControllerRange>
</TimeSignature>
<GlobalGrooveAmount>
  <LomId Value="0" />
  <Manual Value="100" />
  <MidiControllerRange><Min Value="0" /><Max Value="131.25" /></MidiControllerRange>
  {_automation_target(_next_id())}
  {_modulation_target(_next_id())}
</GlobalGrooveAmount>"""
    else:
        tempo_block = ""

    on_id   = _next_id()
    ptr_id  = _next_id()
    spk_id  = _next_id()
    pan_id  = _next_id()
    pan_mod = _next_id()
    spl_id  = _next_id()
    spl_mod = _next_id()
    spr_id  = _next_id()
    spr_mod = _next_id()
    vol_id  = _next_id()
    vol_mod = _next_id()
    xfade_id = _next_id()

    return f"""\
<Mixer>
  <LomId Value="0" />
  <LomIdView Value="0" />
  <IsExpanded Value="true" />
  <BreakoutIsExpanded Value="false" />
  <On>
    <LomId Value="0" />
    <Manual Value="true" />
    <AutomationTarget Id="{on_id}"><LockEnvelope Value="0" /></AutomationTarget>
    <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
  </On>
  <ModulationSourceCount Value="0" />
  <ParametersListWrapper LomId="0" />
  <Pointee Id="{ptr_id}" />
  <LastSelectedTimeableIndex Value="0" />
  <LastSelectedClipEnvelopeIndex Value="0" />
  <LastPresetRef><Value /></LastPresetRef>
  <LockedScripts />
  <IsFolded Value="false" />
  <ShouldShowPresetName Value="false" />
  <UserName Value="" />
  <Annotation Value="" />
  <SourceContext><Value /></SourceContext>
  <MpePitchBendUsesTuning Value="true" />
  {tempo_block}
  <Sends />
  <Speaker>
    <LomId Value="0" />
    <Manual Value="true" />
    <AutomationTarget Id="{spk_id}"><LockEnvelope Value="0" /></AutomationTarget>
    <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
  </Speaker>
  <SoloSink Value="false" />
  <PanMode Value="0" />
  <Pan>
    <LomId Value="0" />
    <Manual Value="0" />
    <MidiControllerRange><Min Value="-1" /><Max Value="1" /></MidiControllerRange>
    <AutomationTarget Id="{pan_id}"><LockEnvelope Value="0" /></AutomationTarget>
    <ModulationTarget Id="{pan_mod}"><LockEnvelope Value="0" /></ModulationTarget>
  </Pan>
  <SplitStereoPanL>
    <LomId Value="0" />
    <Manual Value="-1" />
    <MidiControllerRange><Min Value="-1" /><Max Value="1" /></MidiControllerRange>
    <AutomationTarget Id="{spl_id}"><LockEnvelope Value="0" /></AutomationTarget>
    <ModulationTarget Id="{spl_mod}"><LockEnvelope Value="0" /></ModulationTarget>
  </SplitStereoPanL>
  <SplitStereoPanR>
    <LomId Value="0" />
    <Manual Value="1" />
    <MidiControllerRange><Min Value="-1" /><Max Value="1" /></MidiControllerRange>
    <AutomationTarget Id="{spr_id}"><LockEnvelope Value="0" /></AutomationTarget>
    <ModulationTarget Id="{spr_mod}"><LockEnvelope Value="0" /></ModulationTarget>
  </SplitStereoPanR>
  <Volume>
    <LomId Value="0" />
    <Manual Value="1" />
    <MidiControllerRange><Min Value="0.0003162277571" /><Max Value="1.99526238" /></MidiControllerRange>
    <AutomationTarget Id="{vol_id}"><LockEnvelope Value="0" /></AutomationTarget>
    <ModulationTarget Id="{vol_mod}"><LockEnvelope Value="0" /></ModulationTarget>
  </Volume>
  <ViewStateSessionTrackWidth Value="93" />
  <CrossFadeState>
    <LomId Value="0" />
    <Manual Value="1" />
    <AutomationTarget Id="{xfade_id}"><LockEnvelope Value="0" /></AutomationTarget>
    <MidiControllerRange><Min Value="0" /><Max Value="2" /></MidiControllerRange>
  </CrossFadeState>
  <SendsListWrapper LomId="0" />
</Mixer>"""


def _clip_slot(slot_id: int, clip_def: dict | None = None, root_note: int = 9, scale_idx: int = 5) -> str:
    """Generate a single ClipSlot entry. If clip_def provided, creates named empty clip."""
    if clip_def:
        clip_id = _next_id()
        beats = clip_def["length"] * 4  # bars → beats (assumes 4/4)
        name = clip_def["name"]
        clip_xml = f"""\
<MidiClip Id="{clip_id}" Time="0">
  <LomId Value="0" />
  <LomIdView Value="0" />
  <CurrentStart Value="0" />
  <CurrentEnd Value="{beats}" />
  <Loop>
    <LoopStart Value="0" />
    <LoopEnd Value="{beats}" />
    <StartRelative Value="0" />
    <LoopOn Value="true" />
    <OutMarker Value="{beats}" />
    <HiddenLoopStart Value="0" />
    <HiddenLoopEnd Value="{beats}" />
  </Loop>
  <Name Value="{xesc(name, quote=True)}" />
  <Annotation Value="" />
  <Color Value="-1" />
  <LaunchMode Value="0" />
  <LaunchQuantisation Value="0" />
  <TimeSignature>
    <TimeSignatures>
      <RemoteableTimeSignature Id="0">
        <Numerator Value="4" />
        <Denominator Value="4" />
        <Time Value="0" />
      </RemoteableTimeSignature>
    </TimeSignatures>
  </TimeSignature>
  <Envelopes><Envelopes /></Envelopes>
  <ScrollerTimePreserver><LeftTime Value="0" /><RightTime Value="{beats}" /></ScrollerTimePreserver>
  <TimeSelection><AnchorTime Value="0" /><OtherTime Value="0" /></TimeSelection>
  <Legato Value="false" />
  <Ram Value="false" />
  <GrooveSettings><GrooveId Value="-1" /></GrooveSettings>
  <Disabled Value="false" />
  <VelocityAmount Value="0" />
  <FollowAction>
    <FollowTime Value="4" />
    <IsLinked Value="true" />
    <LoopIterations Value="1" />
    <FollowActionA Value="4" /><FollowActionB Value="0" />
    <FollowChanceA Value="100" /><FollowChanceB Value="0" />
    <JumpIndexA Value="1" /><JumpIndexB Value="1" />
    <FollowActionEnabled Value="false" />
  </FollowAction>
  <Grid>
    <FixedNumerator Value="1" />
    <FixedDenominator Value="16" />
    <GridIntervalPixel Value="20" />
    <Ntoles Value="2" />
    <SnapToGrid Value="true" />
    <Fixed Value="true" />
  </Grid>
  <FreezeStart Value="0" />
  <FreezeEnd Value="0" />
  <IsWarped Value="true" />
  <TakeId Value="-1" />
  <IsInKey Value="true" />
  <ScaleInformation>
    <Root Value="{root_note}" />
    <Name Value="{scale_idx}" />
  </ScaleInformation>
  <Notes>
    <KeyTracks />
    <PerNoteEventStore><EventLists /></PerNoteEventStore>
    <NoteProbabilityGroups />
    <ProbabilityGroupIdGenerator><NextId Value="1" /></ProbabilityGroupIdGenerator>
    <NoteIdGenerator><NextId Value="1" /></NoteIdGenerator>
  </Notes>
  <BankSelectCoarse Value="-1" />
  <BankSelectFine Value="-1" />
  <ProgramChange Value="-1" />
  <NoteEditorFoldInZoom Value="-1" />
  <NoteEditorFoldInScroll Value="0" />
  <NoteEditorFoldOutZoom Value="2324" />
  <NoteEditorFoldOutScroll Value="-999" />
  <NoteEditorFoldScaleZoom Value="-1" />
  <NoteEditorFoldScaleScroll Value="0" />
  <NoteSpellingPreference Value="0" />
  <AccidentalSpellingPreference Value="3" />
  <PreferFlatRootNote Value="false" />
  <ExpressionGrid>
    <FixedNumerator Value="1" />
    <FixedDenominator Value="16" />
    <GridIntervalPixel Value="20" />
    <Ntoles Value="2" />
    <SnapToGrid Value="false" />
    <Fixed Value="false" />
  </ExpressionGrid>
</MidiClip>"""
        value_content = clip_xml
    else:
        value_content = ""

    return f"""\
<ClipSlot Id="{slot_id}">
  <LomId Value="0" />
  <ClipSlot>
    <Value>{value_content}</Value>
  </ClipSlot>
  <HasStop Value="true" />
  <NeedRefreeze Value="true" />
</ClipSlot>"""


def _main_sequencer(clip_slots_xml: str) -> str:
    on_id  = _next_id()
    ptr_id = _next_id()
    # Generate 131 ControllerTargets (indices 0-130, for all MIDI CCs + extras)
    ctrl_targets = "\n    ".join(
        f'<ControllerTargets.{i} Id="{_next_id()}"><LockEnvelope Value="0" /></ControllerTargets.{i}>'
        for i in range(131)
    )
    return f"""\
<MainSequencer>
  <LomId Value="0" />
  <LomIdView Value="0" />
  <IsExpanded Value="true" />
  <BreakoutIsExpanded Value="false" />
  <On>
    <LomId Value="0" />
    <Manual Value="true" />
    <AutomationTarget Id="{on_id}"><LockEnvelope Value="0" /></AutomationTarget>
    <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
  </On>
  <ModulationSourceCount Value="0" />
  <ParametersListWrapper LomId="0" />
  <Pointee Id="{ptr_id}" />
  <LastSelectedTimeableIndex Value="0" />
  <LastSelectedClipEnvelopeIndex Value="0" />
  <LastPresetRef><Value /></LastPresetRef>
  <LockedScripts />
  <IsFolded Value="false" />
  <ShouldShowPresetName Value="false" />
  <UserName Value="" />
  <Annotation Value="" />
  <SourceContext><Value /></SourceContext>
  <MpePitchBendUsesTuning Value="true" />
  <ClipSlotList>
    {clip_slots_xml}
  </ClipSlotList>
  <MonitoringEnum Value="1" />
  <KeepRecordMonitoringLatency Value="true" />
  <ClipTimeable>
    <ArrangerAutomation>
      <Events />
      <AutomationTransformViewState>
        <IsTransformPending Value="false" />
        <TimeAndValueTransforms />
      </AutomationTransformViewState>
    </ArrangerAutomation>
  </ClipTimeable>
  <Recorder>
    <IsArmed Value="false" />
    <TakeCounter Value="0" />
  </Recorder>
  <MidiControllers>
    {ctrl_targets}
  </MidiControllers>
</MainSequencer>"""


def _freeze_sequencer(scene_count: int) -> str:
    on_id  = _next_id()
    ptr_id = _next_id()
    vol_id = _next_id()
    trp_id = _next_id()
    ten_id = _next_id()
    grn_id = _next_id()
    flx_id = _next_id()
    sof_id = _next_id()
    cpf_id = _next_id()
    cpe_id = _next_id()
    empty_slots = "\n    ".join(
        f'<ClipSlot Id="{i}"><LomId Value="0" /><ClipSlot><Value /></ClipSlot><HasStop Value="true" /><NeedRefreeze Value="true" /></ClipSlot>'
        for i in range(scene_count)
    )
    return f"""\
<FreezeSequencer>
  <LomId Value="0" />
  <LomIdView Value="0" />
  <IsExpanded Value="true" />
  <BreakoutIsExpanded Value="false" />
  <On>
    <LomId Value="0" />
    <Manual Value="true" />
    <AutomationTarget Id="{on_id}"><LockEnvelope Value="0" /></AutomationTarget>
    <MidiCCOnOffThresholds><Min Value="64" /><Max Value="127" /></MidiCCOnOffThresholds>
  </On>
  <ModulationSourceCount Value="0" />
  <ParametersListWrapper LomId="0" />
  <Pointee Id="{ptr_id}" />
  <LastSelectedTimeableIndex Value="0" />
  <LastSelectedClipEnvelopeIndex Value="0" />
  <LastPresetRef><Value /></LastPresetRef>
  <LockedScripts />
  <IsFolded Value="false" />
  <ShouldShowPresetName Value="true" />
  <UserName Value="" />
  <Annotation Value="" />
  <SourceContext><Value /></SourceContext>
  <MpePitchBendUsesTuning Value="true" />
  <ClipSlotList>
    {empty_slots}
  </ClipSlotList>
  <MonitoringEnum Value="1" />
  <KeepRecordMonitoringLatency Value="true" />
  <Sample>
    <ArrangerAutomation>
      <Events />
      <AutomationTransformViewState>
        <IsTransformPending Value="false" />
        <TimeAndValueTransforms />
      </AutomationTransformViewState>
    </ArrangerAutomation>
  </Sample>
  <VolumeModulationTarget Id="{vol_id}"><LockEnvelope Value="0" /></VolumeModulationTarget>
  <TranspositionModulationTarget Id="{trp_id}"><LockEnvelope Value="0" /></TranspositionModulationTarget>
  <TransientEnvelopeModulationTarget Id="{ten_id}"><LockEnvelope Value="0" /></TransientEnvelopeModulationTarget>
  <GrainSizeModulationTarget Id="{grn_id}"><LockEnvelope Value="0" /></GrainSizeModulationTarget>
  <FluxModulationTarget Id="{flx_id}"><LockEnvelope Value="0" /></FluxModulationTarget>
  <SampleOffsetModulationTarget Id="{sof_id}"><LockEnvelope Value="0" /></SampleOffsetModulationTarget>
  <ComplexProFormantsModulationTarget Id="{cpf_id}"><LockEnvelope Value="0" /></ComplexProFormantsModulationTarget>
  <ComplexProEnvelopeModulationTarget Id="{cpe_id}"><LockEnvelope Value="0" /></ComplexProEnvelopeModulationTarget>
  <PitchViewScrollPosition Value="-1073741824" />
  <SampleOffsetModulationScrollPosition Value="-1073741824" />
  <Recorder>
    <IsArmed Value="false" />
    <TakeCounter Value="1" />
  </Recorder>
</FreezeSequencer>"""


def _device_chain(track_name: str, clip_slots_xml: str, scene_count: int, tempo: float, num: int, denom: int, is_main=False) -> str:
    lane_id = _next_id()
    return f"""\
<DeviceChain>
  <AutomationLanes>
    <AutomationLanes>
      {_automation_lane(lane_id)}
    </AutomationLanes>
    <AreAdditionalAutomationLanesFolded Value="false" />
  </AutomationLanes>
  <ClipEnvelopeChooserViewState>
    <SelectedDevice Value="0" />
    <SelectedEnvelope Value="0" />
    <PreferModulationVisible Value="false" />
  </ClipEnvelopeChooserViewState>
  <AudioInputRouting>
    {_routing("AudioIn/External/S0", "Ext. In", "1/2")}
  </AudioInputRouting>
  <MidiInputRouting>
    {_routing("MidiIn/External.All/-1", "Ext: All Ins", "")}
  </MidiInputRouting>
  <AudioOutputRouting>
    {_routing("AudioOut/Main", "Main", "")}
  </AudioOutputRouting>
  <MidiOutputRouting>
    {_routing("MidiOut/None", "None", "")}
  </MidiOutputRouting>
  {_mixer_block(_next_id(), tempo, num, denom, is_main=is_main)}
  <DeviceChain>
    <Devices />
    <SignalModulations />
  </DeviceChain>
  {_main_sequencer(clip_slots_xml) if not is_main else ""}
  {_freeze_sequencer(scene_count) if not is_main else ""}
</DeviceChain>"""


def _midi_track(track_id: int, idx: int, track_def: dict, scene_count: int, tempo: float, num: int, denom: int, root_note: int = 9, scale_idx: int = 5) -> str:
    name = track_def["name"]
    color = track_def.get("color", 0)
    clips_by_slot = {c["index"]: c for c in track_def.get("clips", [])}

    # Build one ClipSlot per scene
    slots_xml = ""
    for s in range(scene_count):
        clip_def = clips_by_slot.get(s)
        slots_xml += _clip_slot(s, clip_def, root_note, scale_idx) + "\n    "

    chain_xml = _device_chain(name, slots_xml.strip(), scene_count, tempo, num, denom)

    return f"""\
<MidiTrack Id="{track_id}" SelectedToolPanel="2" SelectedTransformationName="" SelectedGeneratorName="">
  <LomId Value="0" />
  <LomIdView Value="0" />
  <IsContentSelectedInDocument Value="false" />
  <PreferredContentViewMode Value="0" />
  <TrackDelay>
    <Value Value="0" />
    <IsValueSampleBased Value="false" />
  </TrackDelay>
  <Name>
    <EffectiveName Value="{xesc(name, quote=True)}" />
    <UserName Value="" />
    <Annotation Value="" />
    <MemorizedFirstClipName Value="" />
  </Name>
  <Color Value="{color}" />
  <AutomationEnvelopes><Envelopes /></AutomationEnvelopes>
  <TrackGroupId Value="-1" />
  <TrackUnfolded Value="false" />
  <DevicesListWrapper LomId="0" />
  <ClipSlotsListWrapper LomId="0" />
  <ArrangementClipsListWrapper LomId="0" />
  <TakeLanesListWrapper LomId="0" />
  <ViewData Value="{{}}" />
  <TakeLanes>
    <TakeLanes />
    <AreTakeLanesFolded Value="true" />
  </TakeLanes>
  <LinkedTrackGroupId Value="-1" />
  <SavedPlayingSlot Value="0" />
  <SavedPlayingOffset Value="0" />
  <Freeze Value="false" />
  <NeedArrangerRefreeze Value="true" />
  <PostProcessFreezeClips Value="0" />
  {chain_xml}
</MidiTrack>"""


def _main_track(tempo: float, num: int, denom: int, scene_count: int) -> str:
    """Generate the MainTrack (master track) with Tempo in its Mixer."""
    tid = _next_id()
    # Empty clip slots for master track
    slots = "\n".join(_clip_slot(s) for s in range(scene_count))
    chain = _device_chain("Main", slots, scene_count, tempo, num, denom, is_main=True)
    return f"""\
<MainTrack SelectedToolPanel="7" SelectedTransformationName="" SelectedGeneratorName="">
  <LomId Value="0" />
  <LomIdView Value="0" />
  <IsContentSelectedInDocument Value="false" />
  <PreferredContentViewMode Value="0" />
  <TrackDelay><Value Value="0" /><IsValueSampleBased Value="false" /></TrackDelay>
  <Name>
    <EffectiveName Value="Main" />
    <UserName Value="" />
    <Annotation Value="" />
    <MemorizedFirstClipName Value="" />
  </Name>
  <Color Value="0" />
  <AutomationEnvelopes><Envelopes /></AutomationEnvelopes>
  <TrackGroupId Value="-1" />
  <TrackUnfolded Value="false" />
  <DevicesListWrapper LomId="0" />
  <ClipSlotsListWrapper LomId="0" />
  <LinkedTrackGroupId Value="-1" />
  {chain}
</MainTrack>"""


def _pre_hear_track(scene_count: int) -> str:
    tid = _next_id()
    slots = "\n".join(_clip_slot(s) for s in range(scene_count))
    return f"""\
<PreHearTrack SelectedToolPanel="7" SelectedTransformationName="" SelectedGeneratorName="">
  <LomId Value="0" />
  <LomIdView Value="0" />
  <Name>
    <EffectiveName Value="Cue Out" />
    <UserName Value="" />
    <Annotation Value="" />
    <MemorizedFirstClipName Value="" />
  </Name>
  <Color Value="0" />
  <AutomationEnvelopes><Envelopes /></AutomationEnvelopes>
  <TrackGroupId Value="-1" />
  <TrackUnfolded Value="false" />
  <DevicesListWrapper LomId="0" />
  <ClipSlotsListWrapper LomId="0" />
  <LinkedTrackGroupId Value="-1" />
  <DeviceChain>
    <AutomationLanes>
      <AutomationLanes />
      <AreAdditionalAutomationLanesFolded Value="false" />
    </AutomationLanes>
    <ClipEnvelopeChooserViewState>
      <SelectedDevice Value="0" />
      <SelectedEnvelope Value="0" />
      <PreferModulationVisible Value="false" />
    </ClipEnvelopeChooserViewState>
    <AudioInputRouting>
      {_routing("AudioIn/External/S0", "Ext. In", "1/2")}
    </AudioInputRouting>
    <MidiInputRouting>
      {_routing("MidiIn/External.All/-1", "Ext: All Ins", "")}
    </MidiInputRouting>
    <AudioOutputRouting>
      {_routing("AudioOut/None", "None", "")}
    </AudioOutputRouting>
    <MidiOutputRouting>
      {_routing("MidiOut/None", "None", "")}
    </MidiOutputRouting>
    {_mixer_block(_next_id(), 120.0, 4, 4)}
    <DeviceChain><Devices /><SignalModulations /></DeviceChain>
  </DeviceChain>
</PreHearTrack>"""


def _scene(scene_id: int, name: str, tempo: float) -> str:
    sig_id = _next_id()
    return f"""\
<Scene Id="{scene_id}">
  <FollowAction>
    <FollowTime Value="4" />
    <IsLinked Value="true" />
    <LoopIterations Value="1" />
    <FollowActionA Value="0" /><FollowActionB Value="0" />
    <FollowChanceA Value="100" /><FollowChanceB Value="0" />
    <JumpIndexA Value="1" /><JumpIndexB Value="1" />
    <FollowActionEnabled Value="false" />
  </FollowAction>
  <Name Value="{xesc(name, quote=True)}" />
  <Annotation Value="" />
  <Color Value="-1" />
  <Tempo Value="{tempo:.1f}" />
  <IsTempoEnabled Value="false" />
  <TimeSignatureId Value="{sig_id}" />
  <IsTimeSignatureEnabled Value="false" />
  <LomId Value="0" />
  <ClipSlotsListWrapper LomId="0" />
</Scene>"""


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

SCENE_NAMES = ["INTRO", "VERSE", "CHORUS", "BREAK", "BUILD", "DROP", "OUTRO", "END"]


def generate_als(rig: dict, song_meta: dict) -> bytes:
    """Generate the full .als XML (as bytes) from a rig dict."""
    tempo     = rig["tempo"]
    num, denom = rig["time_signature"]
    session_name = rig["name"]

    # Determine scene count from max clip slot index across all tracks
    max_slot = 0
    for t in rig["tracks"]:
        for c in t.get("clips", []):
            max_slot = max(max_slot, c["index"])
    scene_count = max_slot + 1

    # Scale information from song meta
    key_str   = (song_meta.get("key") or "A").lower()
    scale_str = (song_meta.get("scale") or "phrygian").lower()
    root_note = NOTE_NAME_ROOT.get(key_str, 9)       # default A
    scale_idx = SCALE_NAME_INDEX.get(scale_str, 5)   # default Phrygian

    # Build tracks XML
    tracks_xml = ""
    for idx, track_def in enumerate(rig["tracks"]):
        tid = _next_id()
        tracks_xml += _midi_track(tid, idx, track_def, scene_count, tempo, num, denom, root_note, scale_idx) + "\n"

    # Build scenes XML
    scenes_xml = ""
    for s in range(scene_count):
        scene_name = SCENE_NAMES[s] if s < len(SCENE_NAMES) else f"Scene {s+1}"
        scenes_xml += _scene(_next_id(), scene_name, tempo) + "\n"

    # MainTrack + PreHearTrack
    main_track_xml = _main_track(tempo, num, denom, scene_count)
    prehear_xml    = _pre_hear_track(scene_count)

    # Global TimeSignatures list (used by scenes)
    timesig_id = _next_id()

    next_pointee = _id_counter[0] + 500  # generous headroom — Live needs room for internal IDs

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Ableton MajorVersion="5" MinorVersion="12.0_12203" SchemaChangeCount="3" Creator="Ableton Live 12.2.2" Revision="iron-static-generated">
  <LiveSet>
    <NextPointeeId Value="{next_pointee}" />
    <OverwriteProtectionNumber Value="2" />
    <LomId Value="0" />
    <LomIdView Value="0" />
    <Tracks>
      {tracks_xml.strip()}
    </Tracks>
    {main_track_xml}
    {prehear_xml}
    <SendsPre />
    <Scenes>
      {scenes_xml.strip()}
    </Scenes>
    <Transport>
      <PhaseNudgeTempo Value="10" />
      <LoopOn Value="true" />
      <LoopStart Value="0" />
      <LoopLength Value="64" />
      <LoopIsSongStart Value="false" />
      <CurrentTime Value="0" />
      <PunchIn Value="false" />
      <PunchOut Value="false" />
      <DrawMode Value="false" />
    </Transport>
    <SessionScrollPos X="0" Y="0" />
    <GlobalQuantisation Value="0" />
    <AutoQuantisation Value="0" />
    <Grid />
    <ScaleInformation>
      <Root Value="{root_note}" />
      <Name Value="{scale_idx}" />
    </ScaleInformation>
    <InKey Value="true" />
    <SmpteFormat Value="0" />
    <TimeSelection />
    <SequencerNavigator />
    <IsContentSplitterOpen Value="false" />
    <IsExpressionSplitterOpen Value="false" />
    <ExpressionLanes />
    <ContentLanes />
    <ViewStateFxSlotCount Value="4" />
    <ShouldSceneTempoAndTimeSignatureBeVisible Value="false" />
    <Locators />
    <TracksListWrapper LomId="0" />
    <VisibleTracksListWrapper LomId="0" />
    <ReturnTracksListWrapper LomId="0" />
    <ScenesListWrapper LomId="0" />
    <CuePointsListWrapper LomId="0" />
    <Annotation Value="{xesc(session_name, quote=True)} — IRON STATIC" />
    <SoloOrPflSavedValue Value="true" />
    <SoloInPlace Value="true" />
    <CrossfadeCurve Value="5" />
    <LatencyCompensation Value="2" />
    <GroovePool />
    <AutomationMode Value="false" />
    <SnapAutomationToGrid Value="true" />
    <ViewData Value="{{}}" />
    <LinkedTrackGroups />
    <NoteSpellingPreference Value="0" />
    <AccidentalSpellingPreference Value="3" />
    <NoteAlgorithms />
  </LiveSet>
</Ableton>
"""
    return gzip.compress(xml.encode("utf-8"))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Generate an Ableton .als session from an HCL template")
    ap.add_argument("--template", required=True, help="Path to HCL template (e.g. ableton/templates/rust-protocol.hcl)")
    ap.add_argument("--output",   help="Output .als path (default: ableton/sessions/<name>_v1.als)")
    ap.add_argument("--open",     action="store_true", help="Open the .als in Ableton after writing")
    args = ap.parse_args()

    template_path = Path(args.template)
    if not template_path.is_absolute():
        template_path = REPO_ROOT / template_path
    if not template_path.exists():
        log.error("Template not found: %s", template_path)
        sys.exit(1)

    log.info("Loading template: %s", template_path)
    rig = load_hcl(template_path)

    song_meta = get_song_meta(rig["name"])
    if song_meta:
        log.info("Found song metadata: %s (%s %s @ %s BPM)",
                 song_meta.get("title", ""), song_meta.get("key", ""),
                 song_meta.get("scale", ""), song_meta.get("bpm", ""))
    else:
        log.warning("No matching song in songs.json — scale/key defaults to A Phrygian")

    als_bytes = generate_als(rig, song_meta)

    if args.output:
        out_path = Path(args.output)
        if not out_path.is_absolute():
            out_path = REPO_ROOT / out_path
    else:
        slug = re.sub(r"[^a-z0-9]+", "-", rig["name"].lower()).strip("-")
        out_path = REPO_ROOT / "ableton" / "sessions" / f"{slug}_v1.als"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(als_bytes)
    log.info("Wrote %s (%.1f KB)", out_path, len(als_bytes) / 1024)

    if args.open:
        log.info("Opening in Ableton...")
        subprocess.run(["open", str(out_path)], check=True)

    print(f"\n--- ALS CREATED ---")
    print(f"File   : {out_path}")
    print(f"Tracks : {len(rig['tracks'])}")
    print(f"Tempo  : {rig['tempo']} BPM")
    print(f"Key    : {song_meta.get('key', 'A')} {song_meta.get('scale', 'phrygian').title()}")
    print(f"\nNext: open in Ableton and set MIDI output routing per track.")
    print(f"Channels: Digitakt=1, Rev2-A=2, Rev2-B=3, Take5=4, Subharmonicon=5, DFAM=6, Minibrute2S=7, Pigments=8")


if __name__ == "__main__":
    main()
