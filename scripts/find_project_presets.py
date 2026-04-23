#!/usr/bin/env python3
"""Scan an Ableton Live Project folder for files that match referenced plugin/device names.

Usage:
  python3 scripts/find_project_presets.py --project "/path/to/project" --als "/path/to/file.als" --out outputs/presets_map.json

The script gathers device names from either a provided `--devices-json` (from parse_als outputs)
or directly from an `.als` file, then searches the project folder for filenames or file contents
that mention those device names. Results are written as JSON: { device_name: [matching_paths] }
"""
from pathlib import Path
import argparse
import json
import xml.etree.ElementTree as ET
import urllib.parse


def extract_names_from_als(als_path):
    xml = None
    try:
        import gzip
        xml = gzip.open(als_path, 'rb').read()
    except Exception:
        with open(als_path, 'rb') as f:
            xml = f.read()
    root = ET.fromstring(xml)
    names = set()
    # DeviceId Name="..."
    for el in root.findall('.//DeviceId'):
        name = el.get('Name')
        if name:
            names.add(name)
    # BranchDeviceId Value="device:...n=Name%20Here"
    for el in root.findall('.//BranchDeviceId'):
        val = el.get('Value')
        if val and 'n=' in val:
            try:
                q = val.split('n=')[-1]
                names.add(urllib.parse.unquote(q))
            except Exception:
                pass
    # PluginDesc -> look for textual plugin info
    for el in root.findall('.//PluginDesc'):
        txt = ET.tostring(el, encoding='unicode')
        # heuristically find common plugin name attributes
        if 'Plugin' in txt:
            # rough parse
            parts = txt.split()[:6]
            for p in parts:
                if len(p) > 2:
                    names.add(p.strip('\"<>'))
    return sorted(n for n in names if n)


def extract_names_from_devices_json(path):
    data = json.loads(Path(path).read_text())
    names = set()
    import re
    # Support either the older dict structure or the list-of-devices format
    if isinstance(data, dict):
        for t in data.get('tracks', []):
            for d in t.get('devices', []):
                raw = d.get('raw') or ''
                for m in re.findall(r'Name=\"([^\"]+)\"', raw):
                    names.add(m)
                for m in re.findall(r'Value=\"([^\"]+)\"', raw):
                    if 'n=' in m:
                        try:
                            names.add(urllib.parse.unquote(m.split('n=')[-1]))
                        except Exception:
                            pass
    elif isinstance(data, list):
        # parse list entries produced by parse_als outputs
        for item in data:
            # prefer device_name
            dn = item.get('device_name') or ''
            if dn:
                names.add(dn)
            raw = item.get('raw') or ''
            for m in re.findall(r'Name=\"([^\"]+)\"', raw):
                names.add(m)
            for m in re.findall(r'Value=\"([^\"]+)\"', raw):
                if 'n=' in m:
                    try:
                        names.add(urllib.parse.unquote(m.split('n=')[-1]))
                    except Exception:
                        pass
    return sorted(n for n in names if n)


def search_project_for_names(project_dir: Path, names):
    out = {n: [] for n in names}
    for f in project_dir.rglob('*'):
        if f.is_dir():
            continue
        # skip very large files
        try:
            if f.stat().st_size > 5_000_000:
                continue
        except Exception:
            continue
        try:
            txt = f.read_text(errors='ignore')
        except Exception:
            continue
        lowered = txt.lower()
        fname = f.name.lower()
        for n in names:
            key = n.lower()
            if key in fname or key in lowered:
                out[n].append(str(f))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--project', '-p', required=True)
    p.add_argument('--als', help='Optional .als file to extract device names from')
    p.add_argument('--devices-json', help='Optional devices JSON file produced by parse_als')
    p.add_argument('--out', '-o', default='outputs/project_presets_map.json')
    args = p.parse_args()

    names = set()
    if args.devices_json:
        names.update(extract_names_from_devices_json(args.devices_json))
    if args.als:
        names.update(extract_names_from_als(args.als))
    if not names:
        print('No device names found from inputs; exiting')
        return

    project_dir = Path(args.project)
    mapping = search_project_for_names(project_dir, sorted(names))
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(mapping, indent=2))
    print('Wrote', outp)


if __name__ == '__main__':
    main()
