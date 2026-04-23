// pattern_injector.js
// IRON STATIC — pattern-injector.amxd JavaScript core
//
// Reads a generated pattern JSON from disk and writes its notes into
// a target clip in the current Live session. Triggered by a bang from
// the device UI (or from a Max message).
//
// ── INLET MESSAGES ──────────────────────────────────────────────────────────
//
//   bang
//       Inject notes from the current profile path into the current
//       track/slot target.
//
//   set_profile <path>
//       Set the JSON profile path to inject from.
//       e.g.: set_profile /Users/.../midi/patterns/generated/rust-protocol_3_0_vrnd.json
//
//   set_target <track_index> <slot_index>
//       Set the target clip slot.
//
//   set_mode replace|append
//       replace: clear existing notes before writing (default)
//       append:  add notes without clearing first
//
// ── OUTLETS ─────────────────────────────────────────────────────────────────
//   0 — status / result strings → UI label
//   1 — error strings           → print / UI label
//
// ── NOTES JSON FORMAT ────────────────────────────────────────────────────────
//   {
//     "notes": [
//       {"pitch": 60, "start_time": 0.0, "duration": 0.25, "velocity": 100, "mute": 0},
//       ...
//     ]
//   }
//   Compatible with both pattern_learn.py generated profiles and bridge_client notes_file format.

autowatch = 1;
outlets   = 2;

var _profile_path = "";
var _track_index  = 0;
var _slot_index   = 0;
var _mode         = "replace";  // "replace" | "append"

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

function bang() {
    if (!_profile_path) {
        _error("no profile set — send: set_profile <path>");
        return;
    }
    _inject();
}

// ---------------------------------------------------------------------------
// Config messages
// ---------------------------------------------------------------------------

function set_profile() {
    var args = arrayfromargs(arguments);
    _profile_path = args.join(" ");
    _status("profile: " + _profile_path);
}

function set_target() {
    var args = arrayfromargs(arguments);
    if (args.length < 2) { _error("set_target requires track_index slot_index"); return; }
    _track_index = parseInt(args[0]);
    _slot_index  = parseInt(args[1]);
    _status("target: track " + _track_index + " slot " + _slot_index);
}

function set_mode() {
    var args = arrayfromargs(arguments);
    var m = args[0];
    if (m !== "replace" && m !== "append") { _error("mode must be replace or append"); return; }
    _mode = m;
    _status("mode: " + _mode);
}

// ---------------------------------------------------------------------------
// Core inject logic
// ---------------------------------------------------------------------------

function _inject() {
    // 1. Read the JSON profile from disk
    var raw = _read_file(_profile_path);
    if (raw === null) {
        _error("could not read file: " + _profile_path);
        return;
    }

    var profile;
    try {
        profile = JSON.parse(raw);
    } catch(e) {
        _error("JSON parse error: " + e.message);
        return;
    }

    // Accept both full pattern_learn profile (has .notes nested) and flat notes array
    var notes;
    if (profile.notes && Array.isArray(profile.notes)) {
        notes = profile.notes;
    } else if (profile.result && profile.result.notes) {
        notes = profile.result.notes;
    } else {
        _error("no 'notes' array found in profile");
        return;
    }

    // 2. Resolve the target clip via LOM
    var clip_path = "live_set tracks " + _track_index + " clip_slots " + _slot_index + " clip";
    var clip = new LiveAPI(null, clip_path);

    if (!clip || clip.id === "0") {
        _error("no clip at track " + _track_index + " slot " + _slot_index + " — create one first");
        return;
    }

    // 3. Optionally clear existing notes
    if (_mode === "replace") {
        try {
            clip.call("remove_notes_extended", 0, 0, 1e9, 128);
        } catch(e) {
            // Fallback for older Live versions
            try { clip.call("set_notes"); } catch(e2) {}
        }
    }

    // 4. Write notes using select_all_notes / replace_selected_notes pattern
    //    (Live 11/12 preferred API)
    try {
        clip.call("deselect_all_notes");

        var live_notes = [];
        for (var i = 0; i < notes.length; i++) {
            var n = notes[i];
            live_notes.push(
                parseInt(n.pitch),
                parseFloat(n.start_time),
                parseFloat(n.duration),
                parseInt(n.velocity),
                n.mute ? 1 : 0
            );
        }

        // notes_count header + flat array
        var call_args = ["notes_count", notes.length].concat(live_notes);
        clip.call.apply(clip, ["set_notes"].concat(call_args));

    } catch(e) {
        _error("write error: " + e.message);
        return;
    }

    var clip_name = clip.get("name");
    _status("injected " + notes.length + " notes → " + (clip_name || ("track " + _track_index + " slot " + _slot_index)));
}

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

function _read_file(path) {
    try {
        var f = new File(path, "read", "TEXT");
        f.open();
        if (!f.isopen) return null;
        var content = f.readstring(f.eof);
        f.close();
        return content;
    } catch(e) {
        return null;
    }
}

function _status(msg) {
    outlet(0, "status", msg);
    post("[pattern-injector] " + msg + "\n");
}

function _error(msg) {
    outlet(1, "error", msg);
    post("[pattern-injector] ERROR: " + msg + "\n");
}
