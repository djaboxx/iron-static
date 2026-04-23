---
name: m4l-build
description: Build, package, and deploy Max for Live devices for IRON STATIC. Covers .maxpat authoring conventions, JS/LiveAPI patterns, amxd packaging, JS file co-location, and the full device checklist.
argument-hint: "[device name or description]"
user-invocable: true
disable-model-invocation: false
---

# Skill: m4l-build

## What This Skill Does

Guides the creation of a complete, loadable Max for Live device:
1. Writes the `.maxpat` JSON (patcher structure + wiring)
2. Writes the `.js` file (LiveAPI logic)
3. Packages both into a loadable `.amxd` binary
4. Co-locates the JS file so Max can find it at load time
5. Validates the result before committing

## When to Use

- When building any new M4L device for IRON STATIC
- When packaging an existing `.maxpat` into a `.amxd` for Ableton
- When debugging a device that loads but throws JS errors
- When wiring up LOM calls in a new JS file

---

## File Layout

```
ableton/m4l/
  <device-name>.maxpat        ← editable patcher source (JSON)
  <device-name>.amxd          ← Ableton-loadable binary (generated)
  <device-name>.js            ← JS logic, co-located with amxd
  js/
    <device-name>.js          ← canonical JS source (version-controlled here)
```

**Critical**: The `.js` file referenced inside the patcher MUST sit in the same directory as the `.amxd` at runtime. Max searches the device's own directory first. The `js/` subfolder is for version control only — always copy the JS file to `ableton/m4l/` when building the `.amxd`.

---

## .amxd Binary Format

An `.amxd` is a binary-wrapped `.maxpat`. The JSON content is **identical** — only the container differs.

```
[ampf] [version=4 LE32]
[aaaa] [meta] [meta_len=4 LE32] [0x00 0x00 0x00 0x00]
[ptch] [json_len+1 LE32] [json_bytes] [0x00]
```

**Build command** (always use this — never manually construct the binary):
```bash
# Single device
python3 scripts/maxpat_to_amxd.py ableton/m4l/<device>.maxpat

# All maxpat files missing a matching amxd
python3 scripts/maxpat_to_amxd.py --all
```

---

## .maxpat JSON Structure (Required Keys)

Every M4L device `.maxpat` must have these patcher-level keys:

```json
{
  "patcher": {
    "fileversion": 1,
    "appversion": {"major": 8, "minor": 6, "revision": 2, "architecture": "x64", "modernui": 1},
    "rect": [0.0, 0.0, <width>, <height>],
    "openinpresentation": 1,
    "classnamespace": "box",
    "boxes": [...],
    "lines": [...]
  }
}
```

- `"openinpresentation": 1` — opens the device in presentation view by default
- `"classnamespace": "box"` — required for M4L; missing this causes load failures
- `appversion` — always use the values above (Max 8.6.2); does not need to match your installed version

---

## Required Wiring Pattern (Every Device)

All IRON STATIC M4L devices use this standard init chain:

```
live.thisdevice  →  deferlow  →  js <scriptname>.js
```

**Why**:
- `live.thisdevice` fires a bang on device load (outlet 0) and Live set load (outlet 1)
- `deferlow` defers to the low-priority queue — required because LOM is not available immediately at load time; calling LiveAPI directly from `loadbang` or a naked `live.thisdevice` causes "object not found" errors
- The JS receives the bang after LOM is ready

**Never use `loadbang`** in M4L devices that call the LiveAPI. Always use `live.thisdevice → deferlow`.

---

## .maxpat Box Entry Format

```json
{
  "box": {
    "id": "obj-unique-id",
    "maxclass": "newobj",
    "text": "live.thisdevice",
    "numinlets": 0,
    "numoutlets": 2,
    "outlettype": ["bang", "bang"],
    "patching_rect": [30.0, 30.0, 110.0, 22.0],
    "presentation": 0
  }
}
```

For presentation-mode UI elements, add:
```json
"presentation": 1,
"presentation_rect": [x, y, width, height]
```

**Standard `numinlets`/`numoutlets` values**:
| Object | inlets | outlets | outlettype |
|---|---|---|---|
| `live.thisdevice` | 0 | 2 | `["bang","bang"]` |
| `deferlow` | 1 | 1 | `[""]` |
| `js <file>.js` (1 outlet) | 1 | 1 | `[""]` |
| `js <file>.js` (2 outlets) | 1 | 2 | `["",""]` |
| `udpreceive <port>` | 0 | 1 | `[""]` |
| `udpsend <host> <port>` | 1 | 0 | `[]` |
| `button` | 1 | 1 | `["bang"]` |
| `comment` | 1 | 0 | `[]` |
| `plugin~` | 0 | 2 | `["signal","signal"]` |
| `plugout~` | 2 | 0 | `[]` |
| `print <label>` | 1 | 0 | `[]` |

**Always include `plugin~` and `plugout~`** wired together in every device — Live requires audio passthrough even in MIDI devices.

---

## Patchline Entry Format

```json
{
  "patchline": {
    "source": ["obj-source-id", <outlet_index>],
    "destination": ["obj-dest-id", <inlet_index>]
  }
}
```

---

## JS File Conventions

### Init pattern
```javascript
autowatch = 1;   // reload JS on file change without restarting device
outlets   = 2;   // declare outlet count before use

function bang() {
    // called by live.thisdevice → deferlow at load time
    post("device-name: ready\n");
    _status("ready");
}
```

### `anything()` — OSC/message dispatch
When `udpreceive` feeds messages into the JS inlet, Max calls `anything()` with:
- `messagename` = the OSC address string (e.g. `"/transport/tempo"`)
- `arguments` = the OSC argument array (access via `arrayfromargs(arguments)`)

```javascript
function anything() {
    var addr = messagename;
    var args = arrayfromargs(arguments);
    // dispatch on addr
}
```

### LiveAPI best practices
```javascript
// Always null-callback (first arg) unless observing
var ls = new LiveAPI(null, "live_set");

// Get scalar property with fallback
function _get(api, prop, fallback) {
    try {
        var val = api.get(prop);
        return (val && val.length > 0) ? val[0] : fallback;
    } catch(e) { return fallback; }
}

// Iterate children
var count = ls.getcount("tracks");
for (var i = 0; i < count; i++) {
    var t = new LiveAPI(null, "live_set tracks " + i);
}

// Observe a property (fires callback when it changes)
var observer = new LiveAPI(function() {
    post("tempo changed: " + this.get("tempo") + "\n");
}, "live_set");
observer.observe("tempo");
```

### Outlet conventions (standard for all IRON STATIC devices)
- Outlet 0 → response data / OSC output → `udpsend`
- Outlet 1 → status string → `print` / UI label

```javascript
function _ok(cmd)   { outlet(0, "/ok " + cmd);   outlet(1, "status", "ok " + cmd); }
function _error(cmd, msg) {
    outlet(0, "/error " + cmd + " " + msg);
    outlet(1, "status", "ERR " + cmd);
    post("ERROR [" + cmd + "]: " + msg + "\n");
}
```

### File I/O
```javascript
// Write a file
function _write_file(path, content) {
    var f = new File(path, "write", "TEXT");
    f.open();
    if (!f.isopen) { post("ERROR: cannot write " + path + "\n"); return; }
    f.writestring(content);
    f.close();
}

// Read a file
function _read_file(path) {
    try {
        var f = new File(path, "read", "TEXT");
        f.open();
        if (!f.isopen) return null;
        var c = f.readstring(f.eof);
        f.close();
        return c;
    } catch(e) { return null; }
}
```

---

## Device Checklist

Before committing a new device:

- [ ] `.maxpat` has `"classnamespace": "box"` in patcher
- [ ] `.maxpat` has `"openinpresentation": 1`
- [ ] `live.thisdevice → deferlow → js` wiring present
- [ ] `plugin~ → plugout~` passthrough wired
- [ ] JS file has `autowatch = 1` and correct `outlets = N`
- [ ] JS `bang()` handler calls `_status("ready")`
- [ ] No `loadbang` objects (use `live.thisdevice` only)
- [ ] `.amxd` built via `python3 scripts/maxpat_to_amxd.py <file>.maxpat`
- [ ] JS file copied to `ableton/m4l/<device-name>.js` (same dir as `.amxd`)
- [ ] Tested: device loads in Live without Max console errors
- [ ] Tested: `bang()` fires on load and status shows "ready"

---

## Build + Deploy Sequence

```bash
# 1. Edit the maxpat and JS in their canonical locations
#    ableton/m4l/<device>.maxpat
#    ableton/m4l/js/<device>.js

# 2. Copy JS to co-located position (same dir as amxd)
cp ableton/m4l/js/<device>.js ableton/m4l/<device>.js

# 3. Build the amxd
python3 scripts/maxpat_to_amxd.py ableton/m4l/<device>.maxpat

# 4. Validate JSON structure
python3 -c "
import json
with open('ableton/m4l/<device>.maxpat') as f: d=json.load(f)
p = d['patcher']
assert p.get('classnamespace') == 'box', 'missing classnamespace'
assert p.get('openinpresentation') == 1, 'missing openinpresentation'
ids = [b['box']['id'] for b in p['boxes'] if 'box' in b]
assert len(ids) == len(set(ids)), 'duplicate box IDs'
print('OK:', len(p['boxes']), 'boxes,', len(p['lines']), 'lines')
"

# 5. Load in Ableton: drag ableton/m4l/<device>.amxd onto a MIDI track
# 6. Check Max console (View → Max Console) for errors
# 7. Commit
git add ableton/m4l/<device>.maxpat ableton/m4l/<device>.amxd ableton/m4l/js/<device>.js ableton/m4l/<device>.js
```

---

## IRON STATIC Device Registry

| Device | File | Status | Purpose |
|---|---|---|---|
| `session-reporter` | `session-reporter.amxd` | ✅ built | Dump `live_state.json` on demand |
| `iron-static-bridge` | `iron-static-bridge.amxd` | ✅ built | OSC bridge rx:7400 / tx:7401 |
| `pattern-injector` | `pattern-injector.amxd` | ⬜ planned | Write MIDI patterns into clips |
| `scene-tempo-map` | `scene-tempo-map.amxd` | ⬜ planned | Apply scene tempos from JSON config |
| `scale-broadcaster` | `scale-broadcaster.amxd` | ⬜ planned | Broadcast key/scale as CC on ch16 |
| `pigments-macro-lens` | `pigments-macro-lens.amxd` | ⬜ deferred | Read Pigments macro state |
| `arm-dispatcher` | `arm-dispatcher.amxd` | ⬜ deferred | MIDI note → track arm/disarm |
