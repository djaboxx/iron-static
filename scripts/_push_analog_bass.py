"""
Temporary: program Analog bass patch + push bass MIDI for instrumental-convergence.
D Aeolian @ 72 BPM. Matches Subharmonicon drone-boot + 808 Aristocrat init kick/snare grid.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import mido
from ableton_push import AbletonClient, _resolve_track_index

client = AbletonClient()

# Resolve AnalogBass track index once
import argparse
class _FakeArgs:
    track = "AnalogBass"
TRACK_IDX = _resolve_track_index("AnalogBass", client)
print(f"AnalogBass is track index {TRACK_IDX}")

def sp(name, value):
    r = client.send("set_device_param", {
        "track_index": TRACK_IDX,
        "device_index": 0,
        "param_name": name,
        "value": float(value)
    })
    if r.get("status") == "error":
        print(f"  WARN {name}: {r.get('message')}")
    else:
        print(f"  {name} = {value}")

# ── Patch: "Corroded Root v2" ──────────────────────────────────────────────────
# Square wave body (maximum fundamental energy) + detuned saw layer + sub osc.
# Filter cracked hard open on attack, slams closed — big punch at 72 BPM.
print("=== Phat Bass Patch: 'Corroded Root v2' ===")

print("--- Global (mono, low priority) ---")
sp("Voices", 0)          # 1 voice = mono
sp("Volume", 0.9)
sp("Key Priority", 0)    # Lowest note wins (bass)

print("--- OSC 1 (Square, -2 oct, sub on — maximum low-end mass) ---")
sp("OSC1 Octave", -2)
sp("OSC1 Shape", 2)       # Square — fat fundamental, less harsh than saw alone
sp("O1 Sub/Sync", 1.0)    # Sub osc ON: adds an octave below for floor-shaking weight
sp("OSC1 Level", 1.0)
sp("OSC1 Balance", 1.0)

print("--- OSC 2 (Sawtooth, -2 oct, detuned -8 cents — grit layer) ---")
sp("OSC2 Octave", -2)
sp("OSC2 Shape", 1)       # Saw — adds harmonic grit and movement against the square
sp("OSC2 Detune", 0.46)   # -8 cents below center — beating against OSC1 creates slow churn
sp("OSC2 Level", 0.75)
sp("OSC2 Balance", 1.0)

print("--- Filter 1 (LP24, max drive, deep sweep) ---")
sp("F1 Type", 3)          # LP24 — 4-pole ladder, rolls off hard above cutoff
sp("F1 Drive", 5.0)       # Crank drive: pre-filter saturation = analog warmth + squash
sp("F1 Freq", 0.18)       # Start nearly closed — envelope blows it wide open
sp("F1 Resonance", 0.35)  # Enough to growl at the cutoff, not enough to squeal
sp("F1 Freq < Key", 0.4)  # Keytrack so upper bass notes don't turn to mud
sp("F1 Freq < Env", 0.65) # Big sweep — filter hammers open on attack

print("--- Filter Env 1 (explosive crack, fast close) ---")
sp("FEG1 Exp", 1.0)       # Exponential curve: fast crack at start
sp("FEG1 Attack", 0.0)    # Instantaneous
sp("FEG1 Decay", 0.22)    # ~130ms — quick snap closed
sp("FEG1 Sustain", 0.0)   # Fully closed by sustain phase
sp("FEG1 Rel", 0.18)
sp("FEG1 < Vel", 0.4)     # Harder hits open the filter more

print("--- Amp 1 ---")
sp("AMP1 Level", 0.95)
sp("AEG1 Attack", 0.0)
sp("AEG1 Decay", 0.55)
sp("AEG1 Sustain", 0.72)
sp("AEG1 Rel", 0.28)
sp("AEG1 < Vel", 0.55)

print("--- Amp 2 (OSC2 path) ---")
sp("AMP2 On/Off", 1.0)
sp("AMP2 Level", 0.70)
sp("AEG2 Attack", 0.0)
sp("AEG2 Decay", 0.55)
sp("AEG2 Sustain", 0.72)
sp("AEG2 Rel", 0.28)
sp("AEG2 < Vel", 0.55)

print("--- Glide (legato slides between notes) ---")
sp("Glide On/Off", 1.0)
sp("Glide Time", 0.22)    # Short glide — slides on tied notes, not all steps
sp("Glide Legato", 1.0)   # Only glide when notes overlap (legato playing)

print("--- Noise OFF ---")
sp("Noise On/Off", 0.0)

print("\nPatch done.")

# ── Bass Line ──────────────────────────────────────────────────────────────────
# D Aeolian @ 72 BPM, 4 beats
# Kick grid from 808 init: 0, 1.75, 2.5 — bass locks to those
# Snare: 1.0, 3.0 — bass lands there too (minor 3rd, 4th)
# Subharmonicon melody centers on E, C, B(nat), F#, G — bass echoes this chromatically
#
# MIDI pitch: D2=38, E2=40, F2=41, G2=43, A2=45, Bb2=46, C3=48
# F#2=42 for chromatic echo of Subharmonicon's tritone moment

notes = [
    # (pitch, start, duration, velocity)
    (38, 0.0,   0.75, 127),  # D2 — root, kick lock, long
    (40, 0.75,  0.125, 82),  # E2 — 16th pickup to snare
    (41, 1.0,   0.625, 108), # F2 — minor 3rd on snare, dark & heavy
    (38, 1.75,  0.25,  118), # D2 — root, kick lock
    (36, 2.0,   0.375, 80),  # C2 — sub-root movement (C = b7)
    (38, 2.5,   0.375, 122), # D2 — root, kick lock
    (43, 3.0,   0.25,  95),  # G2 — 4th on snare
    (45, 3.25,  0.125, 78),  # A2 — 5th passing
    (42, 3.5,   0.125, 72),  # F#2 — chromatic echo of Subharmonicon's F#3 (tritone tension)
    (43, 3.625, 0.25,  85),  # G2 — resolve to 4th
    (45, 3.875, 0.125, 90),  # A2 — 5th lift into next bar
]

# Build MIDI file
BPM = 72.0
TICKS_PER_BEAT = 480
mid = mido.MidiFile(ticks_per_beat=TICKS_PER_BEAT)
track = mido.MidiTrack()
mid.tracks.append(track)

tempo = mido.bpm2tempo(BPM)
track.append(mido.MetaMessage("set_tempo", tempo=tempo, time=0))
track.append(mido.MetaMessage("time_signature", numerator=4, denominator=4, time=0))

# Convert beat-time notes to absolute tick events
events = []
for pitch, start, dur, vel in notes:
    on_tick  = round(start * TICKS_PER_BEAT)
    off_tick = round((start + dur) * TICKS_PER_BEAT)
    events.append((on_tick,  "note_on",  pitch, vel))
    events.append((off_tick, "note_off", pitch, 0))

events.sort(key=lambda e: (e[0], 0 if e[1] == "note_off" else 1))

prev = 0
for abs_tick, etype, pitch, vel in events:
    delta = abs_tick - prev
    prev  = abs_tick
    track.append(mido.Message(etype, note=pitch, velocity=vel, time=delta))

out = "midi/sequences/instrumental-convergence_analogbass_v1.mid"
os.makedirs(os.path.dirname(out), exist_ok=True)
mid.save(out)
print(f"MIDI saved: {out}")

# ── Push to Ableton ─────────────────────────────────────────────────────────
# Create clip
r = client.send("create_clip", {"track_index": TRACK_IDX, "clip_index": 0, "length": 4.0})
print("Clip created:", r.get("status"))

# Push MIDI
notes_payload = [
    {"pitch": p, "start_time": s, "duration": d, "velocity": v, "mute": False}
    for p, s, d, v in notes
]
r = client.send("set_clip_notes", {
    "track_index": TRACK_IDX, "clip_index": 0, "notes": notes_payload
})
print("Notes pushed:", r.get("status"))

# Name the clip
r = client.send("set_clip_name", {
    "track_index": TRACK_IDX, "clip_index": 0, "name": "bass-root"
})
print("Clip named:", r.get("status"))

# Fire
r = client.send("fire_clip", {"track_index": TRACK_IDX, "clip_index": 0})
print("Fired:", r.get("status"))

print("\nAll done. 'Corroded Root' bass is live on AnalogBass.")
