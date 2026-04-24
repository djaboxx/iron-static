# Iron Static — Rust Protocol / Tetanus Pulse Session Template
# ableton/templates/rust-protocol.hcl
#
# Song:   Rust Protocol — "Tetanus Pulse"
# Key:    A Phrygian Dominant
# BPM:    95
# Time:   4/4
#
# Arrangement (80 bars total):
#   Scene 0 — [01] Intro 95bpm       — 8 bars   (2 loops × 4 bars)
#   Scene 1 — [02] Build 95bpm       — 16 bars  (4 loops × 4 bars)
#   Scene 2 — [03] Drop 95bpm        — 16 bars  (4 loops × 4 bars)
#   Scene 3 — [04] Breakdown 95bpm   — 8 bars   (2 loops × 4 bars)
#   Scene 4 — [05] Climax 95bpm      — 16 bars  (4 loops × 4 bars)
#   Scene 5 — [06] Outro 95bpm       — 8 bars   (2 loops × 4 bars)
#
# Device assignments (in-box, from rust-protocol-internal.json):
#   Digitakt:      null (hardware — I-beam sample + kick/snare grid)
#   Rev2-A:        Wavetable (Climax only — 8-voice unison saw pad)
#   Rev2-B:        Meld Fold FM (Climax only — harmonic movement layer)
#   Take5:         Drift (Drop only — chord stabs every 2 bars)
#   Subharmonicon: Operator (Build+Drop+Breakdown+Climax — FM feedback drone)
#   DFAM:          Collision (all sections — Instrument Rack: clinical→destroyed at bar 49)
#   Minibrute2S:   Analog (Drop+Climax — main lead riff)
#   Pigments:      Pigments VST3 (Breakdown only — granular scraping-metal)
#
# MIDI FX per track (add manually in Live after setup-rig):
#   Take5:         Chord (+1 Bb, +7 E) → Scale (A Phrygian Dominant) → Drift
#   Subharmonicon: Chord (+1 Bb) → Scale (A Phrygian Dominant) → Operator
#   Minibrute2S:   Scale (A Phrygian Dominant) → Analog
#
# Run with:
#   python scripts/ableton_push.py setup-rig --template ableton/templates/rust-protocol.hcl

session {
  name           = "Rust Protocol — Tetanus Pulse"
  tempo          = 95
  time_signature = [4, 4]

  # Scene names drive scene-tempo-map.amxd — keep [NN] prefix + BPM suffix format
  scenes = [
    "[01] Intro 95bpm",
    "[02] Build 95bpm",
    "[03] Drop 95bpm",
    "[04] Breakdown 95bpm",
    "[05] Climax 95bpm",
    "[06] Outro 95bpm"
  ]

  midi_out_port_index  = 0
  midi_out_device_name = "Elektron Digitakt"
}

# ---------------------------------------------------------------------------
# Track 0 — Elektron Digitakt MK1
# Role: I-beam sample (tr8, one-shot), kick/snare grid, drum patterns
# Hardware — no in-box device. Clip content: send patterns via Digitakt USB MIDI
# ---------------------------------------------------------------------------
track "Digitakt" {
  midi_channel         = 1
  midi_out_port_index  = 0
  midi_out_device_name = "Elektron Digitakt"
  color                = 16720384  # 0xFF2200 — red-orange

  # Clip index = scene index. length in bars (4/4 at 95bpm).
  # Intro: I-beam reverb tail only (pattern with tr8 one-shot, no repeat)
  # Build: kick/snare enter bar 1 of Build
  # Drop: full beat
  # Breakdown: beat drops, only sends to reverb return
  # Climax: full beat returns
  # Outro: no MIDI — only reverb tail persists
  clips = [
    { name = "digitakt_intro_v1",      index = 0, length = 8.0 },
    { name = "digitakt_build_v1",      index = 1, length = 8.0 },
    { name = "digitakt_drop_v1",       index = 2, length = 8.0 },
    { name = "digitakt_breakdown_v1",  index = 3, length = 8.0 },
    { name = "digitakt_climax_v1",     index = 4, length = 8.0 },
    { name = "digitakt_outro_v1",      index = 5, length = 8.0 }
  ]
}

# ---------------------------------------------------------------------------
# Track 1 — Sequential Rev2 Layer A
# In-box: Wavetable (8-voice unison saw pad, Moog ladder LP 22%, 1.5s attack)
# Active scenes: Climax only (scene 4)
# Routing: Scale MIDI FX (A Phrygian Dominant) → Wavetable
# ---------------------------------------------------------------------------
track "Rev2-A" {
  midi_channel         = 2
  midi_out_port_index  = 1
  midi_out_device_name = "Sequential Rev2"
  color                = 17663     # 0x0044FF — blue

  # Empty clips in non-Climax scenes — placeholders keep scene matrix complete
  clips = [
    { name = "rev2a_intro_empty",      index = 0, length = 8.0 },
    { name = "rev2a_build_empty",      index = 1, length = 8.0 },
    { name = "rev2a_drop_empty",       index = 2, length = 8.0 },
    { name = "rev2a_breakdown_empty",  index = 3, length = 8.0 },
    { name = "rev2a_climax_v1",        index = 4, length = 16.0 },
    { name = "rev2a_outro_empty",      index = 5, length = 8.0 }
  ]
}

# ---------------------------------------------------------------------------
# Track 2 — Sequential Rev2 Layer B
# In-box: Meld Fold FM (Fold 0.25→0.55 via LFO over 16 bars)
# Active scenes: Climax only (scene 4), enters 4 bars after Rev2-A
# Routing: Scale MIDI FX (A Phrygian Dominant) → Meld
# ---------------------------------------------------------------------------
track "Rev2-B" {
  midi_channel         = 3
  midi_out_port_index  = 1
  midi_out_device_name = "Sequential Rev2"
  color                = 34047     # 0x0088FF — lighter blue

  clips = [
    { name = "rev2b_intro_empty",      index = 0, length = 8.0 },
    { name = "rev2b_build_empty",      index = 1, length = 8.0 },
    { name = "rev2b_drop_empty",       index = 2, length = 8.0 },
    { name = "rev2b_breakdown_empty",  index = 3, length = 8.0 },
    { name = "rev2b_climax_v1",        index = 4, length = 16.0 },
    { name = "rev2b_outro_empty",      index = 5, length = 8.0 }
  ]
}

# ---------------------------------------------------------------------------
# Track 3 — Sequential Take 5
# In-box: Drift (per-voice detuning, sawtooth, 2ms attack)
# Active scenes: Drop only (scene 2) — chord stabs every 2 bars
# MIDI FX chain: Chord (+1 Bb, +7 E) → Scale (A Phrygian Dom) → Drift
# FX: Roar Hard curve 40% / 50% D/W
# ---------------------------------------------------------------------------
track "Take5" {
  midi_channel         = 4
  midi_out_port_index  = 2
  midi_out_device_name = "Sequential Take 5"
  color                = 10027263  # 0x9900FF — purple

  clips = [
    { name = "take5_intro_empty",      index = 0, length = 8.0 },
    { name = "take5_build_empty",      index = 1, length = 8.0 },
    { name = "take5_drop_v1",          index = 2, length = 8.0 },
    { name = "take5_breakdown_empty",  index = 3, length = 8.0 },
    { name = "take5_climax_empty",     index = 4, length = 8.0 },
    { name = "take5_outro_empty",      index = 5, length = 8.0 }
  ]
}

# ---------------------------------------------------------------------------
# Track 4 — Moog Subharmonicon
# In-box: Operator (Alg 7, Op B feedback=62, LFO→mod level 0.08Hz)
# Active scenes: Build, Drop, Breakdown, Climax (scenes 1–4)
# MIDI FX chain: Chord (+1 Bb) → Scale (A Phrygian Dom) → Operator
# Note: A drone sustained — Chord FX generates Bb alongside. Play A only.
# Routing: via Digitakt DIN (no USB MIDI on Subharmonicon)
# ---------------------------------------------------------------------------
track "Subharmonicon" {
  midi_channel         = 5
  midi_out_port_index  = 0
  midi_out_device_name = "Elektron Digitakt"
  color                = 16744448  # 0xFF8800 — amber

  clips = [
    { name = "sub_intro_empty",      index = 0, length = 8.0 },
    { name = "sub_build_v1",         index = 1, length = 8.0 },
    { name = "sub_drop_v1",          index = 2, length = 8.0 },
    { name = "sub_breakdown_v1",     index = 3, length = 8.0 },
    { name = "sub_climax_v1",        index = 4, length = 8.0 },
    { name = "sub_outro_empty",      index = 5, length = 8.0 }
  ]
}

# ---------------------------------------------------------------------------
# Track 5 — Moog DFAM
# In-box: Collision (Tube resonator, A2, 1.8s decay) in Instrument Rack
#   Chain 1 (selector 0–63):   clinical  — Utility + EQ Eight (bars 1–48)
#   Chain 2 (selector 64–127): destroyed — Saturator Sinoid→Amp Heavy→Cabinet 4x12
#   Automate Chain Selector: 0 at scene start, jumps to 64 at bar 49 (Breakdown onset)
# Routing: via Digitakt DIN
# ---------------------------------------------------------------------------
track "DFAM" {
  midi_channel         = 6
  midi_out_port_index  = 0
  midi_out_device_name = "Elektron Digitakt"
  color                = 16728064  # 0xFF4400 — deep orange

  clips = [
    { name = "dfam_intro_v1",       index = 0, length = 8.0 },
    { name = "dfam_build_v1",       index = 1, length = 8.0 },
    { name = "dfam_drop_v1",        index = 2, length = 8.0 },
    { name = "dfam_breakdown_v1",   index = 3, length = 8.0 },
    { name = "dfam_climax_v1",      index = 4, length = 8.0 },
    { name = "dfam_outro_empty",    index = 5, length = 8.0 }
  ]
}

# ---------------------------------------------------------------------------
# Track 6 — Arturia Minibrute 2S
# In-box: Analog (HP filter 600Hz/65% res, Drive 70%, sawtooth, 0ms attack)
# Active scenes: Drop, Climax (scenes 2, 4)
# MIDI FX chain: Scale (A Phrygian Dom) → Analog
# FX: Roar Feedback Note → Overdrive bandpass 2.5kHz → Echo Repitch
# ---------------------------------------------------------------------------
track "Minibrute2S" {
  midi_channel         = 7
  midi_out_port_index  = 3
  midi_out_device_name = "Arturia MiniBrute 2S"
  color                = 52292     # 0x00CC44 — green

  clips = [
    { name = "mini_intro_empty",      index = 0, length = 8.0 },
    { name = "mini_build_empty",      index = 1, length = 8.0 },
    { name = "mini_drop_v1",          index = 2, length = 8.0 },
    { name = "mini_breakdown_empty",  index = 3, length = 8.0 },
    { name = "mini_climax_v1",        index = 4, length = 8.0 },
    { name = "mini_outro_empty",      index = 5, length = 8.0 }
  ]
}

# ---------------------------------------------------------------------------
# Track 7 — Arturia Pigments VST3
# In-box: Pigments (granular scraping-metal, M1→pitch -12st bars 55–56)
# Active scenes: Breakdown only (scene 3)
# No MIDI FX needed — pitch automation via M1 macro inside Pigments
# ---------------------------------------------------------------------------
track "Pigments" {
  midi_channel = 8
  color        = 16711935  # 0xFF00FF — magenta

  plugin {
    type         = "vst3"
    name         = "Pigments"
    uid          = "41727475415649534B61743150726F63"
    path         = "/Library/Audio/Plug-Ins/VST3/Pigments.vst3"
    manufacturer = "Arturia"
    version      = "5.0.3.5024"
    sdk_version  = "VST 3.7.5"
    category     = "Instrument|Synth"
  }

  clips = [
    { name = "pigments_intro_empty",      index = 0, length = 8.0 },
    { name = "pigments_build_empty",      index = 1, length = 8.0 },
    { name = "pigments_drop_empty",       index = 2, length = 8.0 },
    { name = "pigments_breakdown_v1",     index = 3, length = 8.0 },
    { name = "pigments_climax_empty",     index = 4, length = 8.0 },
    { name = "pigments_outro_empty",      index = 5, length = 8.0 }
  ]
}
