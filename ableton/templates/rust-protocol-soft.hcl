# Iron Static — Rust Protocol Session Template (Soft / In-Box Mode)
# ableton/templates/rust-protocol-soft.hcl
#
# Song:  Rust Protocol
# Key:   A Phrygian
# BPM:   95
# Mode:  SOFT — DFAM and Subharmonicon substituted with built-in Live 12 instruments.
#        Use this when hardware is unavailable or incomplete.
#        DFAM → Collision (analog percussion character)
#        Subharmonicon → Operator (FM drone + independent LFO polyrhythm)
#
# Always-present hardware (expected online):
#   Digitakt MK1    ch 1  (USB MIDI)
#   Sequential Rev2 ch 2/3 (USB MIDI)
#   Sequential Take 5 ch 4 (USB MIDI)
#   Arturia Minibrute 2S ch 7 (USB MIDI)
#   Arturia Pigments ch 8 (VST3 plugin)
#
# Run with:
#   python scripts/ableton_push.py setup-rig --template ableton/templates/rust-protocol-soft.hcl

session {
  name           = "Rust Protocol (soft)"
  tempo          = 95
  time_signature = [4, 4]

  midi_out_port_index  = 0
  midi_out_device_name = "Elektron Digitakt"
}

# Track 0 — Elektron Digitakt MK1
track "Digitakt" {
  midi_channel         = 1
  midi_out_port_index  = 0
  midi_out_device_name = "Elektron Digitakt"
  color                = 16720384   # 0xFF2200 — red-orange

  clips = [
    { name = "main-groove", index = 0, length = 2.0 },
    { name = "break-a",     index = 1, length = 2.0 },
    { name = "build",       index = 2, length = 4.0 },
    { name = "drop",        index = 3, length = 2.0 }
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

# Track 4 — Subharmonicon SUBSTITUTE: Operator (FM drone)
# Sub: Operator configured as a low-frequency FM drone with two independent LFOs
# running at different rates to approximate the Subharmonicon's polyrhythmic drift.
# Patch intent: carrier = A2 sine, modulator ratio 0.5 (subharmonic), LFO A at
# 1/8 note rate, LFO B at 1/6 note rate (phasing pair).
# See: database/ableton_devices.json — "Operator"
track "SubH-sub" {
  midi_channel = 5
  color        = 16744448  # 0xFF8800 — amber (matches hardware color)

  device {
    type = "instrument"
    name = "Operator"
  }

  clips = [
    { name = "root-drone",  index = 0, length = 16.0 },
    { name = "poly-shift",  index = 1, length = 8.0 }
  ]
}

# Track 5 — DFAM SUBSTITUTE: Collision (membrane + mallet analog percussion)
# Sub: Collision with membrane resonator tuned low, mallet attack sharp, high
# decay. Captures the DFAM's pitched-percussive character without the hardware.
# Patch intent: Membrane Freq ~80Hz, Mallet stiffness 80%, Resonator Decay long,
# low-pass filter on noise to kill harshness. Layer with a short reverb return.
# See: database/ableton_devices.json — "Collision"
track "DFAM-sub" {
  midi_channel = 6
  color        = 16728064  # 0xFF4400 — deep orange (matches hardware color)

  device {
    type = "instrument"
    name = "Collision"
  }

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
    { name = "bass-main", index = 0, length = 4.0 },
    { name = "bass-var",  index = 1, length = 4.0 }
  ]
}

# Track 7 — Arturia Pigments (atmospheric texture / evolving pads)
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
