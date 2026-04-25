# Iron Static — Instrumental Convergence Session Template
# ableton/templates/instrumental-convergence.hcl
#
# Song: Instrumental Convergence
# Key: D Aeolian  |  BPM: 72  |  Time: 4/4
#
# 5-section arc:
#   Clip 0 — INITIALIZATION  (drone only, 8 bars)
#   Clip 1 — CHOIR ENTRY     (choir + bass enter, 16 bars)
#   Clip 2 — CONVERGENCE     (full rig, Pigments drift begins, 16 bars)
#   Clip 3 — ALIGNMENT FAIL  (choir buried, Brute Factor opens, 16 bars)
#   Clip 4 — GLOBAL MINIMUM  (drop to drone + Pigments, 8 bars)
#
# Run with:
#   python scripts/ableton_push.py setup-rig \
#     --template ableton/templates/instrumental-convergence.hcl

session {
  name           = "Instrumental Convergence"
  tempo          = 72
  time_signature = [4, 4]
}

# Track 0 — Elektron Digitakt MK1
# Role: machine clock — no swing, mechanical 4/4. Choir and pad sample pads triggered here.
track "Digitakt" {
  midi_channel = 1
  color        = 16720384   # 0xFF2200 red-orange
  clips = [
    { name = "init-clock",     index = 0, length = 8.0  },
    { name = "choir-entry",    index = 1, length = 16.0 },
    { name = "convergence",    index = 2, length = 16.0 },
    { name = "align-fail",     index = 3, length = 16.0 },
    { name = "global-minimum", index = 4, length = 8.0  }
  ]
}

# Track 1 — Sequential Rev2 Layer A (choral-analog warm pad)
# Role: choir-adjacent pad, detuned sawtooth, slow attack. D minor voicings.
track "Rev2-A" {
  midi_channel = 2
  color        = 17663   # 0x0044FF blue
  clips = [
    { name = "pad-silent",     index = 0, length = 8.0  },
    { name = "pad-entry",      index = 1, length = 16.0 },
    { name = "pad-full",       index = 2, length = 16.0 },
    { name = "pad-eroding",    index = 3, length = 16.0 },
    { name = "pad-ghost",      index = 4, length = 8.0  }
  ]
}

# Track 2 — Sequential Rev2 Layer B (destabilized harmonic cloud)
# Role: bi-timbral second layer — pitch drift via mod matrix, increasingly wrong.
track "Rev2-B" {
  midi_channel = 3
  color        = 34047   # 0x0088FF lighter blue
  clips = [
    { name = "drift-silent",   index = 0, length = 8.0  },
    { name = "drift-entry",    index = 1, length = 16.0 },
    { name = "drift-open",     index = 2, length = 16.0 },
    { name = "drift-chaos",    index = 3, length = 16.0 },
    { name = "drift-decay",    index = 4, length = 8.0  }
  ]
}

# Track 3 — Moog Subharmonicon (low-frequency drone rooted on D)
# Role: independent clock sequences, unresolved with main tempo — sub-processes you can't shut down.
track "Subharmonicon" {
  midi_channel = 5
  color        = 16744448  # 0xFF8800 amber
  clips = [
    { name = "drone-boot",     index = 0, length = 8.0  },
    { name = "drone-sustain",  index = 1, length = 16.0 },
    { name = "drone-dense",    index = 2, length = 16.0 },
    { name = "drone-loud",     index = 3, length = 16.0 },
    { name = "drone-remains",  index = 4, length = 8.0  }
  ]
}

# Track 4 — Moog DFAM (event-based percussion — system warnings, not groove)
# Role: hits that land when they shouldn't. Long decay bleeds between strikes.
track "DFAM" {
  midi_channel = 6
  color        = 16728064  # 0xFF4400 deep orange
  clips = [
    { name = "dfam-silent",    index = 0, length = 8.0  },
    { name = "dfam-sparse",    index = 1, length = 16.0 },
    { name = "dfam-warnings",  index = 2, length = 16.0 },
    { name = "dfam-dense",     index = 3, length = 16.0 },
    { name = "dfam-silent2",   index = 4, length = 8.0  }
  ]
}

# Track 5 — Arturia Minibrute 2S (bass, D root)
# Role: Brute Factor opens over track duration — starts contained, ends saturated.
track "Minibrute2S" {
  midi_channel = 7
  color        = 52292   # 0x00CC44 green
  clips = [
    { name = "bass-silent",    index = 0, length = 8.0  },
    { name = "bass-entry",     index = 1, length = 16.0 },
    { name = "bass-full",      index = 2, length = 16.0 },
    { name = "bass-brute",     index = 3, length = 16.0 },
    { name = "bass-decay",     index = 4, length = 8.0  }
  ]
}

# Track 6 — Arturia Pigments (intelligence layer — harmonic drift, microtonal)
# Role: frequencies slightly off D Aeolian, LFO drift. Gets louder as track progresses.
track "Pigments" {
  midi_channel = 8
  color        = 8978687  # 0x8900FF violet
  clips = [
    { name = "intel-silent",   index = 0, length = 8.0  },
    { name = "intel-whisper",  index = 1, length = 16.0 },
    { name = "intel-drift",    index = 2, length = 16.0 },
    { name = "intel-dominant", index = 3, length = 16.0 },
    { name = "intel-alone",    index = 4, length = 8.0  }
  ]
}

# Track 7 — DrumRack (angel choir + synth pad sample pads)
# Role: Digitakt-style pad triggering from the two generated Drum Racks.
#   Pads C1–G1: instrumental-convergence-angel-choir-v1
#   Pads A1–D2: instrumental-convergence-mellow-pad-v1
track "DrumRack" {
  midi_channel = 10
  color        = 8947967  # 0x889FFF cool grey-blue
  clips = [
    { name = "pads-silent",    index = 0, length = 8.0  },
    { name = "pads-choir-in",  index = 1, length = 16.0 },
    { name = "pads-both",      index = 2, length = 16.0 },
    { name = "pads-reseq",     index = 3, length = 16.0 },
    { name = "pads-ghost",     index = 4, length = 8.0  }
  ]
}
