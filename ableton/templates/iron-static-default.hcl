# Iron Static — Default Session Template
# ableton/templates/iron-static-default.hcl
#
# This file defines the default Ableton session layout for the Iron Static rig.
# Run with: python scripts/ableton_push.py setup-rig --template ableton/templates/iron-static-default.hcl
#
# HCL format notes:
#   session block  — global session settings
#   track blocks   — one per MIDI track (order = track index in Ableton)
#     clips attr   — list of {name, index, length} objects

session {
  name           = "Iron Static Default"
  tempo          = 140
  time_signature = [4, 4]
}

# Track 0 — Elektron Digitakt MK1
track "Digitakt" {
  midi_channel = 1
  color        = 16720384   # 0xFF2200 red-orange
  clips = [
    { name = "groove-a", index = 0, length = 2.0 },
    { name = "groove-b", index = 1, length = 2.0 }
  ]
}

# Track 1 — Sequential Rev2 Layer A (pads / main voice)
track "Rev2-A" {
  midi_channel = 2
  color        = 17663   # 0x0044FF blue
  clips = [
    { name = "pad-main", index = 0, length = 8.0 }
  ]
}

# Track 2 — Sequential Rev2 Layer B (leads / secondary)
track "Rev2-B" {
  midi_channel = 3
  color        = 34047   # 0x0088FF lighter blue
  clips = [
    { name = "lead-main", index = 0, length = 4.0 }
  ]
}

# Track 3 — Sequential Take 5 (punchy chords / tight leads)
track "Take5" {
  midi_channel = 4
  color        = 10027263  # 0x9900FF purple
  clips = [
    { name = "chords-main", index = 0, length = 4.0 }
  ]
}

# Track 4 — Moog Subharmonicon (drone / polyrhythm)
track "Subharmonicon" {
  midi_channel = 5
  color        = 16744448  # 0xFF8800 amber
  clips = [
    { name = "drone-main", index = 0, length = 16.0 }
  ]
}

# Track 5 — Moog DFAM (analog percussion)
track "DFAM" {
  midi_channel = 6
  color        = 16728064  # 0xFF4400 deep orange
  clips = [
    { name = "perc-main", index = 0, length = 2.0 }
  ]
}

# Track 6 — Arturia Minibrute 2S (mono lead / bass)
track "Minibrute2S" {
  midi_channel = 7
  color        = 52292     # 0x00CC44 green
  clips = [
    { name = "bass-main", index = 0, length = 4.0 }
  ]
}
