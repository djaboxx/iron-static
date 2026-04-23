// ironstaticbridge.js
// IRON STATIC — iron-static-bridge.amxd JavaScript core
//
// OSC UDP bridge between Python scripts and Ableton Live's LOM.
// Receives commands on port 7400, sends responses on port 7401.
//
// ── OSC COMMAND SET (Python → Live, :7400) ──────────────────────────────────
//
//   /ping
//       → /pong
//
//   /transport/play
//       → start playback
//
//   /transport/stop
//       → stop playback
//
//   /transport/tempo <f:bpm>
//       → set session tempo
//
//   /scene/fire <i:scene_index>
//       → fire scene by index
//
//   /clip/create <i:track> <i:slot> <f:length_beats>
//       → create an empty clip of length_beats in the target slot
//
//   /clip/clear <i:track> <i:slot>
//       → remove all notes from the clip in the target slot
//
//   /clip/write <i:track> <i:slot> <s:notes_filepath>
//       → REPLACE all notes in clip; notes_filepath = absolute path to
//         a JSON file: {"notes": [{pitch, start_time, duration, velocity, mute}, ...]}
//
//   /clip/append <i:track> <i:slot> <s:notes_filepath>
//       → APPEND notes to clip (same file format as /clip/write)
//
//   /reporter/dump [<s:output_filepath>]
//       → dump live_state.json; optional filepath override
//
// ── RESPONSES (Live → Python, :7401) ────────────────────────────────────────
//
//   /pong
//   /ok <address>
//   /error <address> <message>
//
// ── OUTLETS ─────────────────────────────────────────────────────────────────
//   0 — response strings → udpsend 127.0.0.1 7401
//   1 — status strings   → print / display label
//
// ── NOTES JSON FORMAT ────────────────────────────────────────────────────────
//   {
//     "notes": [
//       {"pitch": 60, "start_time": 0.0, "duration": 0.25, "velocity": 100, "mute": 0},
//       ...
//     ]
//   }
//   pitch        = MIDI note number (0–127)
//   start_time   = beat position from clip start (float)
//   duration     = note length in beats (float)
//   velocity     = 1–127
//   mute         = 0 or 1

autowatch = 1;
outlets   = 2;

var REPO_ROOT    = "/Users/darnold/git/iron-static";
var DEFAULT_DUMP = REPO_ROOT + "/outputs/live_state.json";

// ---------------------------------------------------------------------------
// Init — triggered by live.thisdevice bang → deferlow → js
// ---------------------------------------------------------------------------

function bang() {
    post("iron-static-bridge: ready. rx :7400  tx :7401\n");
    _status("ready  rx:7400 → tx:7401");
}

// ---------------------------------------------------------------------------
// OSC dispatch
//
// Max calls anything() when a message arrives whose selector is not a
// standard Max keyword. udpreceive outputs OSC addresses as the selector,
// so every incoming OSC message lands here with:
//   messagename = OSC address string (e.g. "/transport/tempo")
//   arguments   = OSC arguments array
// ---------------------------------------------------------------------------

function anything() {
    var addr = messagename;
    var args = arrayfromargs(arguments);

    _status("rx " + addr);

    try {
        if      (addr === "/ping")             { _handle_ping(); }
        else if (addr === "/transport/play")   { _handle_transport_play(); }
        else if (addr === "/transport/stop")   { _handle_transport_stop(); }
        else if (addr === "/transport/tempo")  { _handle_transport_tempo(args); }
        else if (addr === "/scene/fire")       { _handle_scene_fire(args); }
        else if (addr === "/clip/create")      { _handle_clip_create(args); }
        else if (addr === "/clip/clear")       { _handle_clip_clear(args); }
        else if (addr === "/clip/write")       { _handle_clip_write(args, false); }
        else if (addr === "/clip/append")      { _handle_clip_write(args, true); }
        else if (addr === "/reporter/dump")    { _handle_reporter_dump(args); }
        else                                   { _error(addr, "unknown address"); }
    } catch (e) {
        _error(addr, e.message || String(e));
    }
}

// ---------------------------------------------------------------------------
// Handlers
// ---------------------------------------------------------------------------

function _handle_ping() {
    _send("/pong");
    _status("pong!");
}

function _handle_transport_play() {
    var ls = new LiveAPI(null, "live_set");
    ls.set("is_playing", 1);
    _ok("/transport/play");
}

function _handle_transport_stop() {
    var ls = new LiveAPI(null, "live_set");
    ls.set("is_playing", 0);
    _ok("/transport/stop");
}

function _handle_transport_tempo(args) {
    if (args.length < 1) { _error("/transport/tempo", "missing bpm arg"); return; }
    var bpm = parseFloat(args[0]);
    if (isNaN(bpm) || bpm < 20 || bpm > 999) {
        _error("/transport/tempo", "bpm out of range: " + args[0]);
        return;
    }
    var ls = new LiveAPI(null, "live_set");
    ls.set("tempo", bpm);
    _ok("/transport/tempo");
}

function _handle_scene_fire(args) {
    if (args.length < 1) { _error("/scene/fire", "missing scene_index arg"); return; }
    var idx = parseInt(args[0]);
    var scene = new LiveAPI(null, "live_set scenes " + idx);
    scene.call("fire");
    _ok("/scene/fire");
}

function _handle_clip_create(args) {
    if (args.length < 3) { _error("/clip/create", "need track slot length"); return; }
    var track  = parseInt(args[0]);
    var slot   = parseInt(args[1]);
    var length = parseFloat(args[2]);
    var cslot = new LiveAPI(null, "live_set tracks " + track + " clip_slots " + slot);
    cslot.call("create_clip", length);
    _ok("/clip/create");
}

function _handle_clip_clear(args) {
    if (args.length < 2) { _error("/clip/clear", "need track slot"); return; }
    var track = parseInt(args[0]);
    var slot  = parseInt(args[1]);
    _clear_clip_notes(track, slot);
    _ok("/clip/clear");
}

function _handle_clip_write(args, append) {
    var cmd = append ? "/clip/append" : "/clip/write";
    if (args.length < 3) { _error(cmd, "need track slot filepath"); return; }
    var track    = parseInt(args[0]);
    var slot     = parseInt(args[1]);
    var filepath = args.slice(2).join(" ");   // rejoin in case path had spaces

    // Read the notes JSON file
    var json_str = _read_file(filepath);
    if (json_str === null) {
        _error(cmd, "could not read file: " + filepath);
        return;
    }

    var data;
    try {
        data = JSON.parse(json_str);
    } catch (e) {
        _error(cmd, "JSON parse error: " + e.message);
        return;
    }

    if (!data.notes || !data.notes.length) {
        _error(cmd, "no notes in file");
        return;
    }

    var clip = new LiveAPI(null, "live_set tracks " + track + " clip_slots " + slot + " clip");

    if (!append) {
        _clear_clip_notes(track, slot);
    }

    // Build note spec dict for add_new_notes
    var note_spec = {
        notes: data.notes.map(function(n) {
            return {
                pitch:      parseInt(n.pitch)      || 60,
                start_time: parseFloat(n.start_time) || 0.0,
                duration:   parseFloat(n.duration)   || 0.25,
                velocity:   parseInt(n.velocity)   || 100,
                mute:       parseInt(n.mute)        || 0
            };
        })
    };

    clip.call("add_new_notes", note_spec);
    _ok(cmd);
}

function _handle_reporter_dump(args) {
    var out_path = (args.length > 0) ? args.join(" ") : DEFAULT_DUMP;
    _do_dump(out_path);
    _ok("/reporter/dump");
}

// ---------------------------------------------------------------------------
// Full session state dump (mirrors session_reporter.js logic)
// ---------------------------------------------------------------------------

function _do_dump(out_path) {
    var ls = new LiveAPI(null, "live_set");
    var data = {};

    data.tempo                 = _get(ls, "tempo",                 120);
    data.signature_numerator   = _get(ls, "signature_numerator",   4);
    data.signature_denominator = _get(ls, "signature_denominator", 4);
    data.is_playing            = _get(ls, "is_playing",            0);
    data.root_note             = _get(ls, "root_note",             0);
    data.scale_name            = String(ls.get("scale_name") || "");
    data.timestamp             = new Date().toISOString();

    // Tracks
    data.tracks = [];
    var trackCount = ls.getcount("tracks");
    for (var i = 0; i < trackCount; i++) {
        var t      = new LiveAPI(null, "live_set tracks " + i);
        var isMidi = _get(t, "has_midi_input", 0);
        var track  = {
            index:              i,
            name:               String(t.get("name") || ""),
            is_midi:            isMidi,
            mute:               _get(t, "mute",  0),
            arm:                isMidi ? _get(t, "arm", 0) : 0,
            playing_slot_index: _get(t, "playing_slot_index", -1),
            clips:              [],
            devices:            []
        };

        var slotMax = Math.min(t.getcount("clip_slots"), 8);
        for (var s = 0; s < slotMax; s++) {
            var cslot = new LiveAPI(null, "live_set tracks " + i + " clip_slots " + s);
            if (_get(cslot, "has_clip", 0)) {
                var clip = new LiveAPI(null, "live_set tracks " + i + " clip_slots " + s + " clip");
                track.clips.push({
                    slot:       s,
                    name:       String(clip.get("name") || ""),
                    length:     _get(clip, "length", 0),
                    is_playing: _get(clip, "is_playing", 0),
                    is_looping: _get(clip, "looping", 0)
                });
            }
        }

        var devMax = Math.min(t.getcount("devices"), 6);
        for (var d = 0; d < devMax; d++) {
            var dev = new LiveAPI(null, "live_set tracks " + i + " devices " + d);
            track.devices.push({
                index:      d,
                name:       String(dev.get("name") || ""),
                class_name: String(dev.get("class_name") || ""),
                is_active:  _get(dev, "is_active", 1)
            });
        }

        data.tracks.push(track);
    }

    // Scenes
    data.scenes = [];
    var sceneCount = ls.getcount("scenes");
    for (var sc = 0; sc < sceneCount; sc++) {
        var scene = new LiveAPI(null, "live_set scenes " + sc);
        data.scenes.push({
            index: sc,
            name:  String(scene.get("name") || ""),
            tempo: _get(scene, "tempo", 0)
        });
    }

    _write_file(out_path, JSON.stringify(data, null, 2));
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function _clear_clip_notes(track, slot) {
    var clip   = new LiveAPI(null, "live_set tracks " + track + " clip_slots " + slot + " clip");
    var length = _get(clip, "length", 1024);
    clip.call("remove_notes_extended", 0, 128, 0.0, length);
}

function _get(api, prop, fallback) {
    try {
        var val = api.get(prop);
        return (val && val.length > 0) ? val[0] : fallback;
    } catch (e) {
        return fallback;
    }
}

function _read_file(path) {
    try {
        var f = new File(path, "read", "TEXT");
        f.open();
        if (!f.isopen) { return null; }
        var content = f.readstring(f.eof);
        f.close();
        return content;
    } catch (e) {
        return null;
    }
}

function _write_file(path, content) {
    var f = new File(path, "write", "TEXT");
    f.open();
    if (!f.isopen) {
        post("iron-static-bridge: ERROR — cannot write to " + path + "\n");
        return;
    }
    f.writestring(content);
    f.close();
}

function _ok(cmd) {
    _send("/ok " + cmd);
    _status("ok " + cmd);
}

function _error(cmd, msg) {
    _send("/error " + cmd + " " + msg);
    _status("ERR " + cmd);
    post("iron-static-bridge ERROR [" + cmd + "]: " + msg + "\n");
}

function _send(msg) {
    outlet(0, msg);
}

function _status(msg) {
    outlet(1, "status", msg);
}
