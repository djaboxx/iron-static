#!/usr/bin/env python3
"""Parse an Ableton .als (gzipped XML) and emit a JSON summary.
Usage: python3 scripts/parse_als.py /path/to/Project.als /path/to/output.json
"""
import gzip, json, sys
import xml.etree.ElementTree as ET
from pathlib import Path

p = Path(sys.argv[1])
out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('outputs') / (p.stem + '_summary.json')
out.parent.mkdir(parents=True, exist_ok=True)
xml = gzip.open(p, 'rb').read()
root = ET.fromstring(xml)
ls = root.find('LiveSet')
summary = {}
summary['creator'] = root.get('Creator')
summary['ableton_version'] = root.get('MajorVersion') + '.' + root.get('MinorVersion')

# tempo(s)
tempos = [t.get('Value') for t in root.findall('.//Tempo') if t.get('Value')]
summary['tempos'] = tempos

# time signatures
ss = []
for ts in root.findall('.//TimeSignature'):
    num = ts.find('Numerator')
    den = ts.find('Denominator')
    if num is not None and den is not None:
        ss.append({'numerator': num.get('Value'),'denominator': den.get('Value')})
summary['time_signatures'] = ss

# Tracks and per-track devices
tracks = []
devices_index = []
tracks_node = ls.find('Tracks') if ls is not None else None
if tracks_node is not None:
    for t in tracks_node:
        ttype = t.tag
        name_node = t.find('Name/EffectiveName')
        name = name_node.get('Value') if name_node is not None else ''
        slots = t.find('Slots')
        slot_count = len(list(slots)) if slots is not None else 0
        raw_id = t.get('Id')
        # find devices by scanning descendants for tags containing 'Device' or 'Plugin'
        devs = []
        for d in t.iter():
            tag = d.tag
            if 'Device' in tag or 'Plugin' in tag or 'Vst' in tag or 'AudioEffect' in tag:
                # skip wrapper nodes
                if tag.endswith('DevicesListWrapper') or tag.endswith('DeviceChain'):
                    continue
                # name
                nm = None
                en = d.find('Name/EffectiveName')
                if en is not None:
                    nm = en.get('Value')
                elif d.find('PluginName') is not None:
                    nm = d.find('PluginName').get('Value')
                devs.append({'tag': tag, 'name': nm, 'raw': ET.tostring(d, encoding='unicode')[:400]})
                devices_index.append({'track_id': raw_id, 'track_name': name, 'device_tag': tag, 'device_name': nm})

        tracks.append({'type': ttype, 'name': name, 'slot_count': slot_count, 'device_count': len(devs), 'raw_id': raw_id, 'devices': devs})

summary['tracks'] = tracks

# Scenes
scenes = [s.find('Name/EffectiveName').get('Value') if s.find('Name/EffectiveName') is not None else '' for s in root.findall('.//Scene')]
summary['scenes_count'] = len(scenes)
summary['scenes'] = scenes[:20]

# Clips: session clips (Clip inside Slots) and arrangement clips
import csv
clip_rows = []
session_clips = []
for t in tracks_node or []:
    track_id = t.get('Id')
    track_name = t.find('Name/EffectiveName').get('Value') if t.find('Name/EffectiveName') is not None else ''
    # session slot clips
    slots = t.findall('.//Slots/*')
    for s in slots:
        clip = s.find('.//Clip')
        if clip is None:
            continue
        cname = clip.find('Name/EffectiveName')
        cname = cname.get('Value') if cname is not None else ''
        start = clip.find('Start/Value')
        length = clip.find('Length/Value')
        is_midi = bool(clip.find('.//Notes') is not None)
        notes_count = len(clip.findall('.//MidiNote')) if is_midi else 0
        session_clips.append({'track_id': track_id, 'track_name': track_name, 'clip_type': 'session', 'clip_name': cname, 'start': start.get('Value') if start is not None else '', 'length': length.get('Value') if length is not None else '', 'is_midi': is_midi, 'notes_count': notes_count})

# arrangement clips
arr_clips = []
for ac in root.findall('.//ArrangementClip'):
    trk = ac.find('TrackId/Value')
    cname = ac.find('Name/EffectiveName')
    st = ac.find('Start/Value')
    ln = ac.find('Length/Value')
    is_midi = bool(ac.find('.//Notes') is not None)
    notes_count = len(ac.findall('.//MidiNote')) if is_midi else 0
    arr_clips.append({'track_id': trk.get('Value') if trk is not None else '', 'clip_type': 'arrangement', 'clip_name': cname.get('Value') if cname is not None else '', 'start': st.get('Value') if st is not None else '', 'length': ln.get('Value') if ln is not None else '', 'is_midi': is_midi, 'notes_count': notes_count})

clip_rows = session_clips + arr_clips

# write CSV
out_dir = out.parent
csv_path = out_dir / (p.stem + '_clips.csv')
with open(csv_path, 'w', newline='') as cf:
    writer = csv.DictWriter(cf, fieldnames=['track_id','track_name','clip_type','clip_name','start','length','is_midi','notes_count'])
    writer.writeheader()
    for r in clip_rows:
        writer.writerow(r)

# write devices index
dev_path = out_dir / (p.stem + '_devices.json')
dev_path.write_text(json.dumps(devices_index, indent=2))

summary['clips_count'] = len(clip_rows)
summary['arrangement_clips_count'] = len(arr_clips)
summary['session_clips_count'] = len(session_clips)
summary['devices_index_path'] = str(dev_path)
summary['clips_csv_path'] = str(csv_path)

# Save summary JSON
out.write_text(json.dumps(summary, indent=2))
print('Wrote', out)
print('Wrote CSV', csv_path)
print('Wrote devices', dev_path)
