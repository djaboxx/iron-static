# CRITIQUE: instrumental-convergence_v3 — Session Architecture — 2026-04-25

*Song: Instrumental Convergence — D Aeolian @ 72.0 BPM*
*ALS: ableton/sessions/instrumental-convergence_v3.als*
*Config: ableton/m4l/configs/instrumental-convergence-v1.json*

## THE VERDICT

The track structure and scene count are correct. The device choices are not. One track failure is structural and critical — the session cannot tell its story without it being fixed. Two device substitutions undercut the sonic identity established by the blueprint. All three require Live Engineer action before Sound Designer work begins.

## WHAT WORKS

- **7 tracks, correct roles.** Nothing missing, nothing redundant. Grid / Clock / Interrogator / Witness / Drone / Dread maps cleanly to the blueprint. No track is doing two jobs.
- **Track naming.** `DRM_Grid_KickSnare / BASS_Interrogator / TEX_Witness_Vocal` communicate role and priority at a glance.
- **Scene structure.** 7 scenes = 7 sections. INTERROGATION split into P1/P2/ESC is correct — those phases are functionally distinct and need separate launch points.
- **`DRM_Clock_4_4 → Metallic Noise Pluck`** holds without qualification. Single metallic hit, Simpler-based, correct intent.
- **`PAD_Prison_Drone → Inclement Drone Pad`** is defensible. Low grinding drone, correct function.
- **`BASS_Interrogator → Noise Bass`** needs verification (see below) but may hold.

## REQUIRED CHANGES (blocking — must fix before Sound Designer)

### CRITICAL — TEX_Witness_Vocal → GranularStretch Kit

GranularStretch Kit is a Drum Rack preset. You cannot load a spoken word audio file into it, automate grain position, flux, or fragmentation, or carry a 5-section emotional arc through it. The Witness is the protagonist of this song. The session as-built cannot tell its story. This track must be an **empty MIDI track (null device)** with Granulator III (M4L) inserted manually by the Sound Designer, loaded with a Gemini TTS audio source.

**Required action:** Set device to `null`. Add note that Granulator III must be inserted. This is a Sound Designer task once the device slot is correct.

### WRONG — DRM_Grid_KickSnare → 808 Depth Charger Kit

The brainstorm said explicitly: *"industrial and weighty. Think metal, not 808."* 808s are round, sub-heavy, hip-hop. The Grid is supposed to carry groove-metal weight — metal snare crack, physical impact. This preset will produce trap drums under The Interrogator Bass, which is the wrong genre identity for the foundation layer.

**Required action:** Replace with `Ironman Kit` (Sampled). Named for iron. Sampled real drums. Correct weight class.

### WRONG — DRM_Grid_Perc_7_16 → 808 Core Kit

Same problem as above, compounded: the 7/16 phasing perc loop needs a single sharp metallic hit — not a full 808 kit. 808 Core Kit will fight the 7-step reprogramming with its own internal kit structure.

**Required action:** Replace with `AG Techno Kit` (Electronic). Electronic/synthesized techno hits = industrial character. Closer to what the 7/16 loop needs as a starting pad.

### QUESTIONABLE — PAD_Rising_Dread → Metal Pad

"Metal" implies abrasive at rest. The brainstorm calls for cold/dissonant/glassy — something that reads as almost harmless at 0% filter and dangerous at 100%. A pad that is already abrasive has nowhere to go in the 12-bar sweep. The automation arc loses its meaning.

**Required action:** Replace with `Dark Swell Pad`. "Swell" = built to grow. "Dark" = correct character. Automation arc will read.

## VERIFY (not blocking, but flag to Sound Designer)

### BASS_Interrogator → Noise Bass

"Noise Bass" may be a pitched noise source rather than a tonal oscillator. If it cannot hold a tritone (D + G#) as a pitched sequence, it fails the track's core role as a dissonant interrogator. Sound Designer must verify that Noise Bass tracks pitch before writing the sequence. If it doesn't hold pitch, swap to a Wavetable or Operator sawtooth with post-distortion.

## DEVICE CHANGES SUMMARY

| Track | Current Device | Required Device | Reason |
|---|---|---|---|
| TEX_Witness_Vocal | GranularStretch Kit | `null` → Granulator III (M4L) | Drum Rack cannot carry granular vocal transformation |
| DRM_Grid_KickSnare | 808 Depth Charger Kit | Ironman Kit | 808 = hip-hop, not groove-metal industrial |
| DRM_Grid_Perc_7_16 | 808 Core Kit | AG Techno Kit | 808 = wrong sonic identity; needs sharp electronic hit |
| PAD_Rising_Dread | Metal Pad | Dark Swell Pad | Already abrasive = no room for 12-bar sweep arc |

## NEXT

After Live Engineer rebuilds with these fixes → hand back to The Critic for re-evaluation, then → The Sound Designer for:
1. Granulator III insert on TEX_Witness_Vocal + audio source load
2. BASS_Interrogator pitch verification + D/G# tritone sequence
3. DRM_Grid_Perc_7_16 reprogramming to 7-step metallic loop
