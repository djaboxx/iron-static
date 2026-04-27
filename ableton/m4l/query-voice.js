// QUERY VOICE — composite macro controller for Query Arp chain
// Controls Meld [dev 0] + Roar [dev 1] + Echo [dev 2] via LOM
// Lives as Audio Effect at end of the same track.
// Song context: Ignition Point | E Phrygian | 108 BPM

autowatch = 1;
outlets = 1;   // outlet 0 = status string
inlets  = 1;

var _track_idx = -1;
var _resolved  = false;

// ── init ─────────────────────────────────────────────────────────────────────

function bang() {
    _init();
}

function _init() {
    _resolved  = false;
    _track_idx = -1;

    // Ask Live where THIS device lives — path = "live_set tracks N devices M"
    var me     = new LiveAPI(null, "this_device");
    var myPath = me.path ? me.path.toString() : "";
    var m      = myPath.match(/tracks\s+(\d+)/);
    if (m) {
        _track_idx = parseInt(m[1], 10);
        _resolved  = true;
        outlet(0, "status", "QUERY VOICE bound · track=" + _track_idx);
    } else {
        outlet(0, "status", "ERR: path=" + myPath);
    }
}

// ── LOM param setter ─────────────────────────────────────────────────────────

function _set(dev, param, val) {
    if (!_resolved || _track_idx < 0) {
        _resolve_track();
        if (!_resolved) return;
    }
    try {
        var api = new LiveAPI(
            null,
            "live_set tracks " + _track_idx +
            " devices " + dev +
            " parameters " + param
        );
        api.set("value", val);
    } catch (e) {
        post("QUERY VOICE ERR  dev=" + dev + " param=" + param + " : " + e + "\n");
    }
}

// ── TEXTURE ───────────────────────────────────────────────────────────────────
// Meld oscillator character — 0=smooth spectral, 1=full grit
// Maps: A Osc Shape [8]  0→0.80   (harmonic content)
//       A Osc Rough [9]  0→x²     (non-linearity, quadratic so it bites late)
//       A Tone Filter[56] 0.50→0.25 (subtle brightness drop as grit rises)

function texture(v) {
    if (!_resolved) _init();
    _set(0,  8, v * 0.80);
    _set(0,  9, v * v);
    _set(0, 56, 0.50 - v * 0.25);
}

// ── TENSION ───────────────────────────────────────────────────────────────────
// Filter gate — 0=open bright, 1=choked dark resonance
// Maps: A Filter Freq [15]  0.90→0.25  (sweeps down)
//       A Filter Q    [16]  0.20→0.80  (resonance builds as gate closes)

function tension(v) {
    if (!_resolved) _init();
    _set(0, 15, 0.90 - v * 0.65);
    _set(0, 16, 0.20 + v * 0.60);
}

// ── BREATH ────────────────────────────────────────────────────────────────────
// Envelope width — 0=machine stab, 1=slow swell
// Maps: A Amp Attack  [37]  0.00→0.45
//       A Amp Release [39]  0.05→0.60
//       A Amp Sustain [43]  0.00→0.25  (sustain body at long settings)

function breath(v) {
    if (!_resolved) _init();
    _set(0, 37, v * 0.45);
    _set(0, 39, 0.05 + v * 0.55);
    _set(0, 43, v * 0.25);
}

// ── BURN ──────────────────────────────────────────────────────────────────────
// Saturation pressure — 0=controlled heat, 1=shredded
// Maps: Roar Drive        [1]   0.25→1.00
//       Roar Shaper1 Amt  [11]  0.00→0.85
//       Roar Blend        [5]   0.30→0.80

function burn(v) {
    if (!_resolved) _init();
    _set(1,  1, 0.25 + v * 0.75);
    _set(1, 11, v * 0.85);
    _set(1,  5, 0.30 + v * 0.50);
}

// ── TAIL ──────────────────────────────────────────────────────────────────────
// Echo decay depth — 0=dry, 1=long dark drowning
// Maps: Echo Feedback [16]  0.00→0.80  (kept below self-osc)
//       Echo LP Freq  [31]  0.75→0.30  (darkens as feedback grows)

function tail(v) {
    if (!_resolved) _init();
    _set(2, 16, v * 0.80);
    _set(2, 31, 0.75 - v * 0.45);
}

// ── DRIFT ─────────────────────────────────────────────────────────────────────
// Pitch stability — 0=locked machine, 1=floating ghost
// Maps: Meld A Detune    [6]   0.15→0.90
//       Meld A LFO1 Rate [22]  0.08→0.58

function drift(v) {
    if (!_resolved) _init();
    _set(0,  6, 0.15 + v * 0.75);
    _set(0, 22, 0.08 + v * 0.50);
}
