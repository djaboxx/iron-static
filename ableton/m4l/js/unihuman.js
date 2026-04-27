// unihuman.js
// IRON STATIC — UNIHUMAN — Query-State MIDI Processor
//
// A MIDI Effect expressing the "Unihuman Conversation" brainstorm concept:
// an AI receiving a query it cannot fully process. Every incoming note is the
// query. The wrong-answer note is the system's failure to translate human
// emotional state into acceptable corporate syntax.
//
// ── CONCEPT ────────────────────────────────────────────────────────────────
//   Human side:   the query — a simple note, a simple request.
//   Machine side: the corruption — the wrong interval, the wrong syntax.
//   LOAD:  as note density rises, the system degrades. More wrong answers.
//   BEAT:  corruption probability increases as the bar progresses.
//          Beat 1 = clean. Beat 4 = most corrupted. The machine can't hold it.
//   FEEDBACK: under load, even the clean voice drifts. Source code corrupts.
//   CASCADE:  multiple wrong answers fire — the system generating suggestions,
//             all incorrect, increasingly desperate.
//
// ── INLETS ─────────────────────────────────────────────────────────────────
//   0 — pitch   (int, from notein)
//   1 — velocity (int, from notein) — HOT: triggers note processing
//   2 — channel  (int, from notein)
//   3 — param messages: corrupt / mode / cascade / feedback
//   4 — init bang (live.thisdevice → deferlow)
//
// ── OUTLETS ────────────────────────────────────────────────────────────────
//   0 — pitch    → noteout inlet 0
//   1 — velocity → noteout inlet 1 (hot)
//   2 — channel  → noteout inlet 2
//   3 — load %   (0–100) → live.numbox display
//
// ── PARAMETERS ─────────────────────────────────────────────────────────────
//   CORRUPT (0–100): probability of generating a wrong-answer note
//   MODE (0–2):      which Phrygian dissonance to use as wrong answer
//                    0 = b2  (+1)  — "corporate syntax" — almost right
//                    1 = TRT (+6)  — "impossible query"  — the tension note
//                    2 = b7  (-2)  — "hollow empathy"    — training data default
//   CASCADE:  ON = additional wrong-answer from randomised interval pool
//   FEEDBACK: ON = load pressure drifts the clean voice ±1 semitone
//
// ── SESSION CONTEXT ─────────────────────────────────────────────────────────
//   Song: Ignition Point | Key: E Phrygian | BPM: 108

autowatch = 1;
outlets   = 4;

// ── State ──────────────────────────────────────────────────────────────────
var _pitch    = 60;
var _chan      = 1;
var _corrupt  = 0.30;   // 0.0 – 1.0
var _mode     = 1;      // 0=b2, 1=tritone, 2=b7
var _cascade  = 0;
var _feedback = 0;

// Pitch intervals per mode
var INTERVALS = [1, 6, -2];  // b2 (+1), tritone (+6), b7 (-2)

// Cascade pool — characteristic Phrygian intervals from E
var CASCADE_POOL = [1, -2, 6, -1, 7, 12, -12, 3, -3];

// ── Note-off tracking ─────────────────────────────────────────────────────
// UNIHUMAN is an Audio Effect on the track (after Meld). Its notein/noteout
// intercepts the track MIDI stream. We output ONLY corruption notes — the
// original note plays clean through Meld already via the direct MIDI path.
// We must send note-offs for every corruption note we fire.
var _corruption_map = {};   // original_pitch → corruption_pitch
var _cascade_map    = {};   // original_pitch → cascade_pitch

// ── Load tracker ──────────────────────────────────────────────────────────
var _note_times = [];
var _load       = 0.0;

// ── LiveAPI — beat position ─────────────────────────────────────────────
var _liveSet = null;

// ── Init ──────────────────────────────────────────────────────────────────
function bang() {
    if (inlet === 4) {
        try {
            _liveSet = new LiveAPI(null, "live_set");
        } catch(e) {
            post("UNIHUMAN: LiveAPI unavailable — beat-sync disabled\n");
            _liveSet = null;
        }
        post("UNIHUMAN: ready — E Phrygian 108 BPM — IGNITION POINT\n");
        outlet(3, 0);
    }
}

// ── MIDI note handling ────────────────────────────────────────────────────
function msg_int(v) {
    if      (inlet === 0) { _pitch = v; }
    else if (inlet === 2) { _chan  = v; }
    else if (inlet === 1) { _process_note(_pitch, v, _chan); }
}

// ── Parameter handlers ────────────────────────────────────────────────────
// Named functions called by: prepend corrupt → js inlet 3 → corrupt(v)
function corrupt(v)  { _corrupt  = Math.max(0, Math.min(1, v / 100.0)); }
function mode(v)     { _mode     = Math.max(0, Math.min(2, Math.round(v))); }
function cascade(v)  { _cascade  = v > 0.5 ? 1 : 0; }
function feedback(v) { _feedback = v > 0.5 ? 1 : 0; }

// ── Core processing ───────────────────────────────────────────────────────
function _process_note(pitch, vel, chan) {
    // ── NOTE-OFF: send matching note-offs for any corruption notes we fired ──
    if (vel === 0) {
        if (_corruption_map[pitch] !== undefined) {
            outlet(2, chan);
            outlet(0, _corruption_map[pitch]);
            outlet(1, 0);
            delete _corruption_map[pitch];
        }
        if (_cascade_map[pitch] !== undefined) {
            outlet(2, chan);
            outlet(0, _cascade_map[pitch]);
            outlet(1, 0);
            delete _cascade_map[pitch];
        }
        outlet(3, Math.round(_load * 100));
        return;
    }

    // ── NOTE-ON ──────────────────────────────────────────────────────────────
    _update_load();

    // Beat-sync: corruption rises as bar progresses (beat 1=0 bonus, beat 4=max)
    var beat_bonus = 0.0;
    if (_liveSet) {
        try {
            var pos = _liveSet.get("current_song_time");
            if (pos && pos.length > 0) {
                var beat_in_bar = pos[0] % 4.0;  // 0.0–3.999 in a 4/4 bar
                beat_bonus = (beat_in_bar / 4.0) * 0.18;  // max +0.18 at beat 4
            }
        } catch(e) {}
    }

    var eff = Math.min(1.0, _corrupt + (_feedback ? _load * 0.28 : 0.0) + beat_bonus);

    // FEEDBACK: under load, randomly send a drifted clean-pitch corruption instead
    var base_pitch = pitch;
    if (_feedback && _load > 0.55 && Math.random() < (_load - 0.55) * 1.6) {
        base_pitch = Math.max(0, Math.min(127, pitch + (Math.random() < 0.5 ? 1 : -1)));
    }

    // ── Wrong-answer note — the AI's failed translation ──────────────────────
    // We do NOT pass through the original note — Meld receives it directly.
    // UNIHUMAN only adds corruption notes on top.
    if (Math.random() < eff) {
        var interval = INTERVALS[_mode];
        var gp = Math.max(0, Math.min(127, base_pitch + interval));
        var gv = Math.max(10, Math.min(127, Math.round(vel * (0.42 + Math.random() * 0.36))));
        outlet(2, chan);
        outlet(0, gp);
        outlet(1, gv);
        _corruption_map[pitch] = gp;  // track for note-off
    }

    // ── Cascade: multiple wrong answers — the system desperate ───────────────
    if (_cascade && Math.random() < eff * 0.52) {
        var off = CASCADE_POOL[Math.floor(Math.random() * CASCADE_POOL.length)];
        var cp  = Math.max(0, Math.min(127, base_pitch + off));
        var cv  = Math.max(10, Math.round(vel * 0.30));
        outlet(2, chan);
        outlet(0, cp);
        outlet(1, cv);
        _cascade_map[pitch] = cp;  // track for note-off
    }

    outlet(3, Math.round(_load * 100));
}

// ── Load tracker ──────────────────────────────────────────────────────────
function _update_load() {
    var now     = (new Date()).getTime();
    _note_times.push(now);
    var cutoff  = now - 2000;   // 2-second rolling window
    var trimmed = [];
    for (var i = 0; i < _note_times.length; i++) {
        if (_note_times[i] > cutoff) trimmed.push(_note_times[i]);
    }
    _note_times = trimmed;
    // 12 note-ons per 2s = 100% load (matches QueryArp density at 108 BPM)
    _load = Math.min(1.0, _note_times.length / 12.0);
}
