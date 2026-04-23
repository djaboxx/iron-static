# Iron Static — Rust Protocol Session Template
# ableton/templates/rust-protocol.hcl
#
# Song:  Rust Protocol
# Key:   A Phrygian
# BPM:   95
# Time:  4/4 (odd-meter breaks planned per scene)
#
# Run with:
#   python scripts/ableton_push.py setup-rig --template ableton/templates/rust-protocol.hcl

session {
  name           = "Rust Protocol"
  tempo          = 95
  time_signature = [4, 4]

  # MIDI output routing defaults — override per track as needed.
  # midi_out_port_index: 0-based index of the MIDI output port in Live's MIDI preferences.
  # midi_out_device_name: display label for Ableton's MIDI To dropdown.
  # Digitakt USB MIDI is port 0 on this rig. Adjust if Live orders ports differently.
  midi_out_port_index  = 0
  midi_out_device_name = "Elektron Digitakt"
}

# Track 0 — Elektron Digitakt MK1
# Role: drums, sampled hits, main groove engine
track "Digitakt" {
  midi_channel         = 1
  midi_out_port_index  = 0
  midi_out_device_name = "Elektron Digitakt"
  color                = 16720384   # 0xFF2200 — red-orange

  clips = [
    { name = "main-groove",  index = 0, length = 2.0 },
    { name = "break-a",      index = 1, length = 2.0 },
    { name = "build",        index = 2, length = 4.0 },
    { name = "drop",         index = 3, length = 2.0 }
  ]
}

# Track 1 — Sequential Rev2 Layer A (dark pads / A Phrygian wash)
track "Rev2-A" {
  midi_channel         = 2
  midi_out_port_index  = 1
  midi_out_device_name = "Sequential Rev2"
  color                = 17663     # 0x0044FF — blue

  clips = [
    { name = "phryg-pad",   index = 0, length = 8.0 },
    { name = "phryg-build", index = 1, length = 4.0 }
  ]
}

# Track 2 — Sequential Rev2 Layer B (detuned lead / tension line)
track "Rev2-B" {
  midi_channel         = 3
  midi_out_port_index  = 1
  midi_out_device_name = "Sequential Rev2"
  color                = 34047     # 0x0088FF — lighter blue

  clips = [
    { name = "tension-lead", index = 0, length = 4.0 },
    { name = "release-line", index = 1, length = 4.0 }
  ]
}

# Track 3 — Sequential Take 5 (punchy chord stabs)
track "Take5" {
  midi_channel         = 4
  midi_out_port_index  = 2
  midi_out_device_name = "Sequential Take 5"
  color                = 10027263  # 0x9900FF — purple

  clips = [
    { name = "phryg-stabs", index = 0, length = 2.0 },
    { name = "chaos-stabs", index = 1, length = 1.0 }
  ]
}

# Track 4 — Moog Subharmonicon (polyrhythmic drone / A root + subharmonics)
# No USB MIDI — clocked via Digitakt DIN MIDI out (port 0)
track "Subharmonicon" {
  midi_channel         = 5
  midi_out_port_index  = 0
  midi_out_device_name = "Elektron Digitakt"
  color                = 16744448  # 0xFF8800 — amber

  clips = [
    { name = "root-drone",  index = 0, length = 16.0 },
    { name = "poly-shift",  index = 1, length = 8.0 }
  ]
}

# Track 5 — Moog DFAM (industrial percussion / extra hits)
# No USB MIDI — clocked via Digitakt DIN MIDI out (port 0)
track "DFAM" {
  midi_channel         = 6
  midi_out_port_index  = 0
  midi_out_device_name = "Elektron Digitakt"
  color                = 16728064  # 0xFF4400 — deep orange

  clips = [
    { name = "perc-main",  index = 0, length = 2.0 },
    { name = "perc-fill",  index = 1, length = 1.0 }
  ]
}

# Track 6 — Arturia Minibrute 2S (bass line / Phrygian riff)
track "Minibrute2S" {
  midi_channel         = 7
  midi_out_port_index  = 3
  midi_out_device_name = "Arturia MiniBrute 2S"
  color                = 52292     # 0x00CC44 — green

  clips = [
    { name = "bass-main",  index = 0, length = 4.0 },
    { name = "bass-var",   index = 1, length = 4.0 }
  ]
}

# Track 7 — Arturia Pigments (atmospheric texture / evolving pads)
# Software synth — VST3 plugin loaded directly on the track, no external MIDI routing.
# uid sourced from Live 12.2.5 PluginScanDb.txt entry.
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
    { name = "atmo-main",  index = 0, length = 16.0 },
    { name = "atmo-rise",  index = 1, length = 8.0 }
  ]
}
