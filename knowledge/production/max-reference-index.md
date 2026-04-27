# Cycling '74 Max Reference — M4L Production Index

> Source: https://docs.cycling74.com/reference/  
> Indexed: 2026-04-27 — maintained by `scripts/refresh_lom_docs.py`  
> Run `python scripts/refresh_lom_docs.py --reference` to check for drift

The full reference contains 1805+ objects across Max, MSP, Jitter, Gen, and Ableton DSP packages. This document indexes only the objects relevant to IRON STATIC M4L device development and Live integration.

For full LOM object reference (Song, Track, Clip, Device, etc.), see [docs/lom-api-ref.md](../../docs/lom-api-ref.md).

---

## Live API Objects (live.* namespace)

These objects bridge Max patchers to the Live Object Model. All automatically deferred — the Live API runs in the main thread and all messages are queued.

**Critical rule: initialize via `live.thisdevice`, never `loadbang`.**

| Object | Description | Ref |
|---|---|---|
| `live.thisdevice` | Sends `bang` when device fully loads, reports enabled/preview state | [ref](https://docs.cycling74.com/reference/live.thisdevice/) |
| `live.path` | Navigate LOM hierarchy by path string. Left outlet: `id` on goto. Middle outlet: `id` when path object changes (notifications). Right outlet: getpath/getcount/getchildren responses. | [ref](https://docs.cycling74.com/reference/live.path/) |
| `live.object` | Operate on a Live object by ID. `get`, `set`, `call`, `getinfo`, `getpath`, `gettype`. | [ref](https://docs.cycling74.com/reference/live.object/) |
| `live.observer` | Monitor property/child changes on a Live object. Fires on connect + every change. Cannot trigger Live changes from its notification — use `deferlow`. | [ref](https://docs.cycling74.com/reference/live.observer/) |
| `live.remote~` | Realtime parameter control at audio rate. No undo. No automation. Disables the parameter in Live's UI while active (like a Macro). Send `id 0` to release. | [ref](https://docs.cycling74.com/reference/live.remote~/) |
| `live.modulate~` | Like `live.remote~` but additive (offset from current value, not absolute). Input range −1 to 1 maps to ±full parameter range. `depth` attribute scales the range. | [ref](https://docs.cycling74.com/reference/live.modulate~/) |
| `live.map` | Mouse-click UI element to get its LOM path and ID. Outputs (R→L): dumpout, mapping state, name, id, path. Useful for patching against specific UI elements. | [ref](https://docs.cycling74.com/reference/live.map/) |

### live.path Detailed Usage

| Message | Outlet | Output | Example |
|---|---|---|---|
| `goto <path>` | left + middle | `id nn` | `id 5` |
| `bang` / `getid` | left + middle | `id nn` | `id 5` |
| `getcount <child>` | right | `count child N` | `count devices 3` |
| `getchildren` | right | `children name1 name2 …` | `children canonical_parent devices` |
| `getpath` | right | `path <path>` | `path live_set tracks 2` |

**Middle outlet**: fires spontaneously whenever the object at the navigated path changes. Insert `deferlow` before connecting to other Live API objects to avoid "Cannot trigger changes" errors.

**Left outlet**: fires only in response to `goto`/`bang`/`getid`. Keeps the same ID even if the object moves in the session (e.g., a track that gets reordered).

### live.object Detailed Usage

| Message | Output | Example |
|---|---|---|
| `get <property>` | `property value` | `name My Track` |
| `get <list-child>` | `list-child id1 id2 …` | `clip_slots id 4 id 5` |
| `set <property> <value>` | — | |
| `call <fn> [args]` | `fn result` | `fire` |
| `getinfo` | multi-line info block ending `info done` | |
| `getpath` | `path <canonical-path>` | `path live_set return_tracks 0` |
| `gettype` | `type <class>` | `type Track` |
| `bang` / `getid` | `id nn` | `id 5` |

### live.remote~ Detailed Usage

- **`smoothing` attribute** (default 1 ms): ramp time for incoming events. Set to 0 for snap.
- **`normalized` attribute**: when 1, input 0–1 auto-scales to parameter min–max.
- Supports signal inlet (audio-rate), float, int, and `target_value delta_ms` list (ramp like `line~`).
- Target: `DeviceParameter` object only. Path example: `live_set master_track mixer_device volume`.

### live.modulate~ vs live.remote~

| | `live.remote~` | `live.modulate~` |
|---|---|---|
| Takes over param? | Yes — disables UI | No — param stays settable |
| Input meaning | Absolute value | Offset from current value |
| Input range | param min–max (or 0–1 if normalized) | −1 to 1 |
| `depth` attribute | N/A | Scales modulation range (0–1) |
| Undo | No | No |

### Persistence (live.path / live.object / live.observer / live.remote~)

All four objects have a "Use Persistent Mapping" inspector checkbox. When enabled, IDs persist across Live saves/restores and device moves. Since Live 8.2.2, IDs also persist between Live launches.

---

## Ableton DSP Objects (abl.device.* namespace)

These are Ableton's own Live devices exposed as Max objects for use in Max patches (not M4L — these are for standalone Max context). Each accepts MIDI as int/float messages, outputs audio signal, and exposes all device parameters as attributes.

All `abl.device.*~` objects share:
- `ins [symbol ...]` attribute: declare attribute names to be exposed as additional signal-rate inlets
- Messages: `int` / `float` (MIDI input), `signal`, `reset`
- Package: **Ableton DSP**

### Instruments

| Object | Description | Key Attributes |
|---|---|---|
| `abl.device.drift~` | Drift synthesizer — dual-osc, dual-env, LFO, LP+HP filter | `osc1type`, `osc2type`, `lpfreq`, `lpres`, `voicemode`, `voices`, `drift`, `unison`, `thickness` |
| `abl.device.drumsampler~` | Drum sampler | MIDI-triggered sampler for drum sounds |

### Effects

| Object | Description | Key Attributes |
|---|---|---|
| `abl.device.autofilter~` | Classic analog filter emulation | HP/LP/BP/notch, envelope follower, LFO |
| `abl.device.channeleq~` | Semi-parametric 3-band channel EQ | Low/mid/high bands |
| `abl.device.compressor~` | Compressor | threshold, ratio, attack, release, knee |
| `abl.device.delay~` | Stereo delay | Simple stereo delay lines |
| `abl.device.drumbuss~` | Analog-style drum processor | transient shaping, saturation, bass boost |
| `abl.device.echo~` | Modulation delay — two independent delay lines with filter + envelope modulation | `delay`, `feedback`, `mod_freq`, `mod_delay`, `reverb`, `routing`, `channel_mode`, `wobble` |
| `abl.device.redux~` | Downsampling and bit-reduction effect | bit depth, sample rate reduction |
| `abl.device.roar~` | Three-stage saturation effect — each stage has shaper + filter + modulation. Routing modes: Serial, Parallel, Multiband, Mid-Side, Feedback, Delay | `routing`, `shaper_type_1/2/3` (12 types), `filter_type_1/2/3` (7 types), `feedback_amount`, `lfo_frequency_1/2`, `noise_type`, `mix` |
| `abl.device.spectralresonator~` | Spectral resonances and pitched overtones — adds tonal character to any source | `frequency`, `decay`, `harmonics`, `stretch`, `shift`, `unison`, `mod_type` |
| `abl.device.spectraltime~` | Spectral delay | Frequency-domain delay processing |

### abl.device.roar~ Shaper Types (for all 3 stages)
`0=Soft sine`, `1=Hard clip`, `2=Bit crusher`, `3=Diode clipper`, `4=Tube preamp`, `5=Half wave rectifier`, `6=Full wave rectifier`, `7=Polynomial`, `8=Fractal`, `9=Fold tri`, `10=Noise inject`, `11=Shards`

### abl.device.roar~ Filter Types (per stage)
`0=Lowpass`, `1=Bandpass`, `2=Highpass`, `3=Notch`, `4=Peak`, `5=Morph`, `6=Comb`, `7=Resampling`

### abl.device.drift~ Voice Mode
`0=Poly`, `1=Mono`, `2=Stereo`, `3=Unison`

### abl.device.echo~ Routing
`0=Stereo`, `1=Ping-pong`, `2=Mid/Side`

---

## Key M4L Support Objects

These general Max objects appear in almost every M4L device. Not specific to the Live API, but essential for M4L patterns.

### Flow Control

| Object | Description | M4L Relevance |
|---|---|---|
| `deferlow` | Defer a message to the low-priority thread | **Required** between live.path middle outlet and other Live API objects. Prevents "Cannot trigger changes from notification" error. |
| `loadbang` | Bang on patcher load | **Do not use in M4L** — fires before Live API is ready. Use `live.thisdevice` instead. |
| `delay` | Delay a message by N ms | Occasionally useful after `live.thisdevice` to ensure API is settled |
| `sel` / `select` | Route messages by value | Pattern matching on get/set responses |
| `route` | Route messages by selector | Splitting `info` output from `live.object` |
| `trigger` | Send multiple messages in R→L order | Sequence operations on a single event |

### Data

| Object | Description | M4L Relevance |
|---|---|---|
| `dict` | Dictionary (JSON-like) | `add_new_notes` and `get_all_notes_extended` use dicts |
| `coll` | Collection (ordered key-value store) | Pattern storage, sequence lookup |
| `table` | Fixed-size integer table | Velocity tables, step patterns |
| `pattr` | Parameter attribute — expose to Live as automatable param | Expose M4L device knobs/buttons |
| `pattrstorage` | Store/recall pattr values | Preset storage in M4L devices |

### Audio

| Object | Description | M4L Relevance |
|---|---|---|
| `buffer~` | Audio sample buffer | Sample playback, grain sources |
| `groove~` | Variable-rate playback from `buffer~` | Granular, pitch shifting |
| `poly~` | Voice allocation for polyphonic patches | Polyphonic M4L instruments |
| `plugsync~` | Sync to host tempo from inside `poly~` | Tempo-synced LFOs inside voice patchers |
| `mc.~` | Multichannel audio (MC framework) | Efficient poly voice signal processing |

### Communication

| Object | Description | M4L Relevance |
|---|---|---|
| `udpreceive` / `udpsend` | UDP network messaging | OSC bridge (used by `iron-static-bridge.amxd`, port 7400/7401) |
| `OSC-route` | Parse OSC messages | Route incoming OSC from Python bridge |
| `mxj` | Java objects | Rarely used; JS preferred |
| `js` | JavaScript execution | Full LiveAPI JS class access, complex logic |
| `jsui` | JS with 2D canvas rendering | Custom UI in M4L devices |

### JavaScript (js object) M4L Patterns

```javascript
// ALWAYS: initialize Live API after thisdevice fires
function bang() {
    var api = new LiveAPI(on_change, "live_set view selected_track");
    api.property = "name";
}

function on_change(args) {
    post("Track name:", args, "\n");
}

// Navigate from thisdevice to its track
function get_my_track() {
    var dev = new LiveAPI("this_device");
    var track = new LiveAPI(null, dev.unquotedpath + " canonical_parent");
    post("Track:", track.get("name"), "\n");
}

// Get/set clip notes
function write_notes(track_idx, slot_idx) {
    var path = "live_set tracks " + track_idx + " clip_slots " + slot_idx + " clip";
    var clip = new LiveAPI(null, path);
    clip.call("add_new_notes", {
        "notes": [
            {"pitch": 60, "start_time": 0, "duration": 0.5, "velocity": 100, "mute": false}
        ]
    });
}
```

---

## Common M4L Patterns

### Init Pattern (every M4L device)
```
[live.thisdevice]
       |
    [bang] ←── fires when device is fully loaded
       |
  [your init logic]
```

### Observe-and-React (with deferlow)
```
[live.path live_set view selected_track]
  |          |
  |         [middle outlet: fires on track change]
  |                |
  |           [deferlow]   ← REQUIRED
  |                |
  +←──────────────+
  |
[live.observer]
  property name
       |
  [left outlet: new value]
```

### Get Track Name by Index
```
[live.path live_set tracks $1]
           ↑
    [prepend goto]
           ↑
    [number box: track index]

[live.path] → [live.object]
              [get name] → output
```

### Control a Parameter (no-undo, realtime)
```
[live.path live_set tracks 0 mixer_device volume]
           ↓
[left outlet: id] → [right inlet of live.remote~]
                    [left inlet: signal or float value]
```

---

## Composite Instrument Pattern

Because `abl.device.*~` objects are standard Max signal objects, their audio outlets connect directly to any other signal inlet. You can layer, chain, and cross-route them in a single `.maxpat` / `.amxd` to create instruments not achievable through the Live UI.

### Layered Dual-Oscillator with Shared FX Chain

```
[MIDI input]
      |
  [splitnote or just fan-out]
      |             |
[abl.device.drift~] [abl.device.drift~]   ← 2 independent synth voices
  (tuned to root)   (detuned +7 semitones / octave up)
      |                    |
  [*~ 0.5]             [*~ 0.5]            ← independent gain
         \              /
          [abl.dsp.mix~ 2]                 ← summed stereo mix
                  |
      [abl.device.roar~]                   ← shared saturation
        routing=Serial, 3 stages
                  |
      [abl.device.echo~]                   ← shared modulation delay
        channel_mode=Ping-pong
                  |
      [abl.device.spectralresonator~]      ← pitched resonant smear
        stretch=-0.3, shift=-12 (sub rumble)
                  |
              [dac~]
```

**IRON STATIC application**: package this as an `.amxd` on a MIDI track. The Remote Script injects MIDI patterns as usual — the instrument is fully custom internal routing invisible to Live's UI. Name the M4L device `iron-static-composite.amxd`.

### Per-Voice Effects (inside poly~)

Wrap the chain inside `poly~` to get per-note processing — each voice gets its own separate effect tail:

```
[poly~ voice-patch.maxpat 8]
    ↑
Each voice-patch.maxpat contains:
    [thispoly~] → [abl.device.drift~] → [abl.device.roar~] → [out~ 1 2]
```

### Signal-Rate Modulation via ins attribute

The `ins` attribute on any `abl.device.*~` exposes named attributes as audio-rate inlets:

```maxpatch
[abl.device.spectralresonator~ @ins frequency decay]
    ← left inlets 1,2 now accept audio-rate signals for frequency and decay
    ← drive frequency with a [cycle~ 0.1] for slow resonant pitch wander
```

### Key Rules
- `abl.device.*~` objects require **Max 9 / Live 12 Suite** with the Ableton DSP package
- They work inside `.amxd` (M4L) and standalone Max — not in Live's device browser directly
- They are **not** the same as LOM DeviceParameters — no undo, no automation via these objects (use `live.remote~` for that)
- Per-voice use inside `poly~`: pair with `plugsync~` for tempo-synced LFOs that track Live's transport

---

## abl.device.* vs LOM DeviceParameter

`abl.device.*~` objects are for **standalone Max patches** that embed Live devices as RNBO-style audio objects. They are **not** the same as accessing a device's parameters via the LOM.

In M4L context, you access device parameters via:
```
live_set tracks N devices M parameters L → value
```
not via `abl.device.*~`.

Use `abl.device.*~` when you want to build a Max patch that uses Live devices as audio-processing nodes outside of a Live set (e.g., for offline rendering or Max standalone apps).

---

## Reference Index Maintenance

The `scripts/refresh_lom_docs.py` script checks for content drift in these Cycling '74 reference pages:

| Category | URLs tracked |
|---|---|
| LOM Overview | `https://docs.cycling74.com/userguide/m4l/live_api_overview/` |
| LOM Index | `https://docs.cycling74.com/apiref/lom/` |
| LOM Objects | song, track, device, rackdevice, chain, clip, clipslot, scene, deviceparameter, mixerdevice, application |
| LiveAPI JS | `https://docs.cycling74.com/apiref/js/liveapi/` |
| Live API Objects | live.path, live.object, live.observer, live.remote~, live.modulate~, live.thisdevice, live.map |
| Ableton DSP | abl.device.roar~, abl.device.echo~, abl.device.drift~, abl.device.spectralresonator~ |

When drift is detected, review the cached diffs in `database/lom_cache/` and update this document and `docs/lom-api-ref.md` manually.

```bash
python scripts/refresh_lom_docs.py --dry-run   # check only
python scripts/refresh_lom_docs.py             # update hashes + header
```
