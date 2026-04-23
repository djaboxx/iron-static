// session_reporter.js
// IRON STATIC — session-reporter.amxd JavaScript core
//
// Reads the full Live session state (tracks, clips, scenes, devices, transport)
// and writes it to outputs/live_state.json in the repo root.
//
// Message handlers:
//   bang / dump   — trigger a full dump
//   set_path <p>  — override the output path (for debugging)
//
// Output (outlet 0):
//   "done <path>"  — dump succeeded
//   "error <msg>"  — dump failed

autowatch = 1;
outlets = 1;

// Hardcoded repo root — this is a band-specific device, not redistributable
var REPO_ROOT = "/Users/darnold/git/iron-static";
var OUTPUT_PATH = REPO_ROOT + "/outputs/live_state.json";

// Capture patcher path at load time (informational only)
var PATCHER_PATH = this.patcher.filepath;

// ---------------------------------------------------------------------------
// Entry points
// ---------------------------------------------------------------------------

function bang() {
    post("session-reporter: bang received. Output -> " + OUTPUT_PATH + "\n");
    dump();
}
function dump() { _do_dump(); }

function set_path() {
    var args = arrayfromargs(arguments);
    if (args.length > 0) {
        PATCHER_PATH = args.join(" ");
        post("session-reporter: output path override -> " + PATCHER_PATH + "\n");
    }
}

// ---------------------------------------------------------------------------
// Core dump
// ---------------------------------------------------------------------------

function _do_dump() {
    var liveSet = new LiveAPI(null, "live_set");
    var data = {};

    // --- Transport / global ---
    data.tempo               = _get(liveSet, "tempo", 120);
    data.signature_numerator = _get(liveSet, "signature_numerator", 4);
    data.signature_denominator = _get(liveSet, "signature_denominator", 4);
    data.is_playing          = _get(liveSet, "is_playing", 0);
    data.root_note           = _get(liveSet, "root_note", 0);
    data.scale_name          = _get(liveSet, "scale_name", "");
    data.timestamp           = new Date().toISOString();

    // --- Tracks ---
    data.tracks = [];
    var trackCount = liveSet.getcount("tracks");
    for (var i = 0; i < trackCount; i++) {
        var t = new LiveAPI(null, "live_set tracks " + i);
        var isMidi  = _get(t, "has_midi_input", 0);
        var isAudio = _get(t, "has_audio_input", 0);

        var track = {
            index:              i,
            name:               String(t.get("name")),
            is_midi:            isMidi,
            is_audio:           isAudio,
            mute:               _get(t, "mute", 0),
            arm:                isMidi ? _get(t, "arm", 0) : 0,
            playing_slot_index: _get(t, "playing_slot_index", -1),
            clips:              [],
            devices:            []
        };

        // Clip slots (first 8)
        var slotMax = Math.min(t.getcount("clip_slots"), 8);
        for (var s = 0; s < slotMax; s++) {
            var slot = new LiveAPI(null, "live_set tracks " + i + " clip_slots " + s);
            if (_get(slot, "has_clip", 0)) {
                var clip = new LiveAPI(null, "live_set tracks " + i + " clip_slots " + s + " clip");
                track.clips.push({
                    slot:         s,
                    name:         String(clip.get("name")),
                    length:       _get(clip, "length", 0),
                    is_playing:   _get(clip, "is_playing", 0),
                    is_recording: _get(clip, "is_recording", 0),
                    is_looping:   _get(clip, "looping", 0),
                    loop_start:   _get(clip, "loop_start", 0),
                    loop_end:     _get(clip, "loop_end", 0),
                });
            }
        }

        // Devices (first 6)
        var devMax = Math.min(t.getcount("devices"), 6);
        for (var d = 0; d < devMax; d++) {
            var dev = new LiveAPI(null, "live_set tracks " + i + " devices " + d);
            track.devices.push({
                index:      d,
                name:       String(dev.get("name")),
                class_name: String(dev.get("class_name")),
                is_active:  _get(dev, "is_active", 1),
            });
        }

        data.tracks.push(track);
    }

    // --- Return / Master track ---
    try {
        var ret = new LiveAPI(null, "live_set return_tracks 0");
        if (ret.id > 0) {
            data.return_tracks = [];
            var retCount = liveSet.getcount("return_tracks");
            for (var r = 0; r < retCount; r++) {
                var rt = new LiveAPI(null, "live_set return_tracks " + r);
                data.return_tracks.push({
                    index: r,
                    name:  String(rt.get("name")),
                    mute:  _get(rt, "mute", 0),
                });
            }
        }
    } catch(e) {}

    // --- Scenes ---
    data.scenes = [];
    var sceneCount = liveSet.getcount("scenes");
    for (var sc = 0; sc < sceneCount; sc++) {
        var scene = new LiveAPI(null, "live_set scenes " + sc);
        data.scenes.push({
            index: sc,
            name:  String(scene.get("name")),
            tempo: _get(scene, "tempo", 0),
        });
    }

    _write_json(data);
}

// ---------------------------------------------------------------------------
// File I/O
// ---------------------------------------------------------------------------

function _get_output_path() {
    return OUTPUT_PATH;
}

function _write_json(data) {
    var path    = _get_output_path();
    var jsonStr = JSON.stringify(data, null, 2);
    try {
        // Ensure outputs/ directory exists by attempting to write (Max File creates intermediates)
        var f = new File(path, "write", "TEXT");
        f.open();
        if (!f.isopen) {
            post("session-reporter: ERROR — could not open file for writing: " + path + "\n");
            outlet(0, "error cannot open " + path);
            return;
        }
        f.writestring(jsonStr);
        f.close();
        post("session-reporter: wrote " + path + "\n");
        outlet(0, "done " + path);
    } catch(e) {
        post("session-reporter: ERROR — " + e + "\n");
        outlet(0, "error " + e.toString());
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function _get(api, prop, fallback) {
    try {
        var val = api.get(prop);
        return (val && val.length > 0) ? val[0] : fallback;
    } catch(e) {
        return fallback;
    }
}
