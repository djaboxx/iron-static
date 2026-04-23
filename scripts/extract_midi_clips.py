#!/usr/bin/env python3
"""Extract MIDI notes from an Ableton .als file and write one .mid per clip.

Assumptions:
- Clip note times and durations are expressed in beats.
- KeyTrack elements include a <MidiKey Value="NN"/> giving the base MIDI note for that keytrack.

Usage:
  python3 scripts/extract_midi_clips.py /path/to/project.als /path/to/outdir --ticks 480
"""
from pathlib import Path
import argparse
import xml.etree.ElementTree as ET
import gzip
import mido
import json


def load_als(path):
    b = gzip.open(path, 'rb').read()
    return ET.fromstring(b)


def collect_clips(root):
    clips = []
    for clip in root.findall('.//Clip'):
        # find MidiClip inside
        midi = clip.find('.//MidiClip')
        if midi is None:
            continue
        clips.append(clip)
    return clips


def parse_clip(clip):
    # Find name
    name_el = clip.find('.//Name')
    name = name_el.get('Value') if name_el is not None else 'clip'
    # Collect keytracks
    keytracks = {}
    for kt in clip.findall('.//KeyTrack'):
        kid = kt.get('Id')
        midi_key_el = kt.find('MidiKey')
        base = None
        if midi_key_el is not None:
            try:
                base = int(midi_key_el.get('Value'))
            except Exception:
                base = None
        notes = []
        for ne in kt.findall('.//MidiNoteEvent'):
            t = float(ne.get('Time', '0'))
            d = float(ne.get('Duration', '0'))
            vel = float(ne.get('Velocity', '0'))
            noteid = int(ne.get('NoteId', '0'))
            notes.append({'time': t, 'dur': d, 'vel': vel, 'noteid': noteid})
        keytracks[kid] = {'base': base, 'notes': notes}
    return name, keytracks


def keytrack_note_to_midi(base, noteid):
    if base is None:
        return None
    return int(base + (noteid - 1))


def write_mid_for_clip(name, keytracks, outpath, ticks_per_beat=480, tempo_bpm=None):
    mid = mido.MidiFile(ticks_per_beat=ticks_per_beat)
    track = mido.MidiTrack()
    mid.tracks.append(track)
    if tempo_bpm:
        track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(tempo_bpm), time=0))
    events = []
    for kt in keytracks.values():
        base = kt['base']
        for n in kt['notes']:
            midi_note = keytrack_note_to_midi(base, n['noteid'])
            if midi_note is None:
                continue
            start = int(round(n['time'] * ticks_per_beat))
            end = int(round((n['time'] + n['dur']) * ticks_per_beat))
            vel = int(max(0, min(127, round(n['vel']))))
            events.append((start, 'on', midi_note, vel))
            events.append((end, 'off', midi_note, 64))
    events.sort(key=lambda e: (e[0], 0 if e[1]=='on' else 1))
    last = 0
    for ev in events:
        dt = ev[0] - last
        last = ev[0]
        if ev[1] == 'on':
            track.append(mido.Message('note_on', note=ev[2], velocity=ev[3], time=dt))
        else:
            track.append(mido.Message('note_off', note=ev[2], velocity=ev[3], time=dt))
    # ensure there's an end-of-track
    track.append(mido.MetaMessage('end_of_track', time=0))
    outpath.parent.mkdir(parents=True, exist_ok=True)
    mid.save(str(outpath))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('als')
    p.add_argument('outdir')
    p.add_argument('--ticks', type=int, default=480)
    p.add_argument('--tempo', type=float, default=None, help='Optional BPM to embed in MIDI')
    args = p.parse_args()

    root = load_als(args.als)
    clips = collect_clips(root)
    outdir = Path(args.outdir)
    results = []
    for i, clip in enumerate(clips):
        name, keytracks = parse_clip(clip)
        safe = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in name).strip()[:120]
        outp = outdir / f'clip_{i}_{safe}.mid'
        write_mid_for_clip(name, keytracks, outp, ticks_per_beat=args.ticks, tempo_bpm=args.tempo)
        results.append(str(outp))
    print('Wrote', len(results), 'midi files to', outdir)


if __name__ == '__main__':
    main()
