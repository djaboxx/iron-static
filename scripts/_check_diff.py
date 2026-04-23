#!/usr/bin/env python3
"""Check structural diff between generated .als and reference."""
import gzip, re, sys

ALS = "ableton/sessions/rust-protocol_v1.als"
REF = "ableton/templates/rust-protocol-template Project/rust-protocol-template.als"

xml = gzip.open(ALS).read().decode('utf-8', errors='replace')
ref_xml = gzip.open(REF).read().decode('utf-8', errors='replace')

ours_tags = set(re.findall(r'<([A-Za-z][A-Za-z0-9_.]*)', xml))
ref_tags  = set(re.findall(r'<([A-Za-z][A-Za-z0-9_.]*)', ref_xml))

def strip_controller(s):
    return {t for t in s if not re.match(r'ControllerTargets\.\d+', t)}

ours_clean = strip_controller(ours_tags)
ref_clean  = strip_controller(ref_tags)

# Plugin/device elements only in reference (we don't have devices)
# View state / arrangement elements not in our minimal session
plugin_specific = {
    'PluginDevice','BranchSourceContext','OriginalFileRef','BrowserContentPath','LocalFiltersJson',
    'PresetRef','BranchDeviceId','PluginDesc','Vst3PluginInfo','WinPosX','WinPosY',
    'NumAudioInputs','NumAudioOutputs','IsPlaceholderDevice','Preset','Vst3Preset','MpeEnabled',
    'ParameterSettings','IsOn','PowerMacroControlIndex','PowerMacroMappingRange','StoredAllParameters',
    'DeviceLomId','DeviceViewLomId','IsOnLomId','ParametersListWrapperLomId','Uid','DeviceType',
    'ProcessorState','ControllerState','ParameterList','PluginFloatParameter','ParameterName',
    'ParameterId','ParameterIdFlankBool','VisualIndex','ParameterValue','LastUserRange',
    'First','Last','LastInternalRange','AxisX','AxisY','SideChain','OnOff','RoutedInput',
    'Routable','DryWet','ReWireDeviceMidiTargetId','PitchbendRange','IsTuned',
    'ControllerLayoutRemoteable','ControllerLayoutCustomization','PitchClassSource',
    'OctaveSource','KeyNoteTarget','StepSize','OctaveEvery','AllowedKeys','FillerKeysMapTo',
    'KeyTrack','MidiNoteEvent','MidiKey','AutomationEnvelope','EnvelopeTarget','PointeeId',
    'Automation','EnumEvent','FloatEvent','CrossFade','TempoAutomationViewBottom',
    'TempoAutomationViewTop','AudioSequencer','AudioEffectGroupDevice','FilePresetRef',
    'FileRef','RelativePathType','RelativePath','Path','Type','LivePackName','LivePackId',
    'OriginalFileSize','OriginalCrc','Branches','AudioEffectBranch','IsSelected',
    'AudioToAudioDeviceChain','AuPluginDevice','AuPluginInfo','ComponentType',
    'ComponentSubType','ComponentManufacturer','ComponentFlags','Manufacturer','AuPreset',
    'Buffer','SubType','IsUnusable','KeyMidi','PersistentKeyString','IsNote','Channel',
    'NoteOrController','LowerRangeNote','UpperRangeNote','ControllerMapMode',
    'PluginEnumParameter','LastItemCount','BranchSelectorRange','CrossfadeMin','CrossfadeMax',
    'IsSoloed','SessionViewBranchWidth','IsHighlightedInSessionView','AutoColored',
    'AutoColorScheme','SoloActivatedInSessionMixer','MixerDevice','AbletonDefaultPresetRef',
    'DeviceId','Panorama','SendInfos','RoutingHelper','TargetEnum','IsBranchesListVisible',
    'IsReturnBranchesListVisible','IsRangesEditorVisible','AreDevicesVisible',
    'NumVisibleMacroControls','AreMacroControlsVisible','IsAutoSelectEnabled','ChainSelector',
    'ChainSelectorRelativePosition','ViewsToRestoreWhenUnfolding','ReturnBranches',
    'BranchesSplitterProportion','ShowBranchesInSessionMixer','LockId','LockSeal',
    'ChainsListWrapper','ReturnChainsListWrapper','MacroVariations','MacroSnapshots',
    'AreMacroVariationsControlsVisible','MetronomeTickDuration','SelectedBreakpointValue',
    'BeatTimeHelper','CurrentZoom','ScrollerPos','ClientSize','MidiEditorLaneModel','Size',
    'IsMinimized','ViewStateSessionMixerVolumeSectionHeight',
    'ViewStateArrangerMixerVolumeSectionHeight','WaveformVerticalZoomFactor',
    'IsWaveformVerticalZoomActive','DetailClipKeyMidis','SelectedDocumentViewInMainWindow',
    'HighlightedTrackIndex','Grooves','Groove','Clip','QuantizationAmount','TimingAmount',
    'RandomAmount','Selection','DefaultGrooveId','GroovesListWrapper','ArrangementOverdub',
    'ColorSequenceIndex','AutoColorPickerForPlayerAndGroupTracks','NextColorIndex',
    'AutoColorPickerForReturnAndMainTracks','ResetNonautomatedMidiControllersOnClipStarts',
    'MidiFoldIn','MidiFoldMode','MultiClipFocusMode','MultiClipLoopBarHeight','MidiPrelisten',
    'UseWarperLegacyHiQMode','VideoWindowRect','ShowVideoWindow','TuningSystems',
    'TrackHeaderWidth','ViewStateMainWindowClipDetailOpen',
    'ViewStateMainWindowHiddenOtherDocViewTypeClipDetailOpen',
    'ViewStateMainWindowHiddenOtherDocViewTypeDeviceDetailOpen',
    'ViewStateMainWindowDeviceDetailOpen','ViewStateSecondWindowClipDetailOpen',
    'ViewStateSecondWindowDeviceDetailOpen','ViewStates','MixerInArrangement',
    'ArrangerMixerIO','ArrangerMixerSends','ArrangerMixerReturns','ArrangerMixerVolume',
    'ArrangerMixerTrackOptions','ArrangerMixerCrossFade','ArrangerMixerTrackPerformanceImpactMeter',
    'MixerInSession','SessionIO','SessionSends','SessionReturns','SessionVolume',
    'SessionTrackOptions','SessionCrossFade','SessionTrackPerformanceImpactMeter',
    'SessionShowOverView','ArrangerIO','ArrangerReturns','ArrangerVolume',
    'ArrangerTrackOptions','ArrangerShowOverView','ArpeggiateAlgorithm','NamedKeyMidiRemoteables',
    'NamedRemoteableKeyMidi','Rate','Steps','Distance','Gate','Style','SpanAlgorithm','Mode',
    'ChordThreshold','LengthVariation','LengthOffset','ConnectAlgorithm','Tie','Density',
    'Spread','OrnamentAlgorithm','FlamEnabled','FlamPosition','FlamVelocity',
    'GraceNotesEnabled','GraceNotesChance','GraceNotesVelocity','GraceNotesPosition',
    'GraceNotesAmount','GraceNotesPitch','RecombineAlgorithm','PermutedDimension','Shuffle',
    'Mirror','RotateAmount','RotateOnGrid','QuantizeAlgorithm','Reference','TripletReference',
    'QuantizeNoteStarts','QuantizeNoteEnds','Amount','StrumAlgorithm','StrumLow','StrumHigh',
    'TensionAmount','TimeWarpAlgorithm','Breakpoints','Breakpoint','Control1X','Control1Y',
    'Control2X','Control2Y','IsActive','StretchNoteEnd','PreserveTimeRange','Quantize',
    'RhythmAlgorithm','Repetitions','Pattern','PatternLength','Pitch','Velocity','Accent',
    'Period','Offset','Shift','StepDuration','Split','StacksAlgorithm','Sequence','Chord',
    'RootDegree','Octave','RootPitch','Inversion','RuleNumber','Duration','ShapeAlgorithm',
    'ShapeLevels','RemoteableFloat','ShapePresets','MinPitch','MaxPitch','PitchVariation',
    'SeedAlgorithm','NotesDensity','MinDuration','MaxDuration','MinVelocity','MaxVelocity',
    'VerticalLimit','PitchFilterAlgorithm','PitchClasses','RemoteableBool','DrumPad',
    'Invert','TimeFilterAlgorithm','Start','Length','Repeat',
    # AudioSampler modulation targets (from audio tracks / instruments in reference)
    'FreezeSequencer','Sample','VolumeModulationTarget','TranspositionModulationTarget',
    'TransientEnvelopeModulationTarget','GrainSizeModulationTarget','FluxModulationTarget',
    'SampleOffsetModulationTarget','ComplexProFormantsModulationTarget',
    'ComplexProEnvelopeModulationTarget','PitchViewScrollPosition','SampleOffsetModulationScrollPosition',
}

remaining_missing = sorted((ref_clean - ours_clean) - plugin_specific)
remaining_extra   = sorted(ours_clean - ref_clean)

print("OURS has extra (structural bugs):", remaining_extra)
print()
print("In REF but missing from OURS (potentially needed):", remaining_missing)
print()

# Spot checks
checks = [
    ("No SequencerInsertMode",    "<SequencerInsertMode" not in xml),
    ("No GridQuantisation",       "<GridQuantisation" not in xml),
    ("No GridIntervalPixels",     "<GridIntervalPixels" not in xml),
    ("No bare TakeLane element",  not bool(re.search(r'<TakeLane\s', xml))),
    ("No LinkedTrackGroup elem",  not bool(re.search(r'<LinkedTrackGroup\s', xml))),
    ("Has Grid block",            "<Grid>" in xml),
    ("Has GridIntervalPixel",     "GridIntervalPixel " in xml or "GridIntervalPixel\n" in xml),
    ("Has TakeId",                bool(re.search(r'<TakeId\s', xml))),
    ("Has Disabled",              bool(re.search(r'<Disabled\s', xml))),
    ("Has IsInKey",               bool(re.search(r'<IsInKey\s', xml))),
    ("Has NoteProbabilityGroups", "<NoteProbabilityGroups" in xml),
    ("Has ProbabilityGroupIdGenerator", "<ProbabilityGroupIdGenerator>" in xml),
    ("Has BankSelectCoarse",      bool(re.search(r'<BankSelectCoarse\s', xml))),
    ("Has NoteEditorFoldInZoom",  bool(re.search(r'<NoteEditorFoldInZoom\s', xml))),
    ("Has ExpressionGrid",        "<ExpressionGrid>" in xml),
    ("Has PreferFlatRootNote",    bool(re.search(r'<PreferFlatRootNote\s', xml))),
    ("Has FreezeStart",           bool(re.search(r'<FreezeStart\s', xml))),
    ("Has Speaker",               "<Speaker>" in xml),
    ("No SpeakerOn",              "<SpeakerOn" not in xml),
    ("Has Sends",                 "<Sends />" in xml),
    ("Has SendsListWrapper",      "<SendsListWrapper" in xml),
    ("Has SplitStereoPanL",       "<SplitStereoPanL>" in xml),
    ("131 ControllerTargets",     "ControllerTargets.130" in xml),
    ("Has per-clip ScaleInformation", xml.count("<ScaleInformation>") >= 2),
]

passed = failed = 0
for name, result in checks:
    if result: passed += 1
    else:      failed += 1; print(f"  FAIL: {name}")

print(f"\n{passed}/{len(checks)} checks passed {'✓' if failed == 0 else ''}")
