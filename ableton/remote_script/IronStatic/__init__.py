# IronStatic/__init__.py
# Ableton Live MIDI Remote Script — purpose-built for IRON STATIC
#
# Install: copy the IronStatic/ folder to Ableton's MIDI Remote Scripts directory.
#   macOS: ~/Library/Preferences/Ableton/Live XX/User Remote Scripts/
# Then select "IronStatic" in Ableton → Settings → Link/Tempo/MIDI → Control Surface
#
# Listens on TCP port 9877 (same port as AbletonMCP — do not run both simultaneously).
#
# Commands supported:
#   get_session_info    — read tempo, time sig, track list, scenes
#   get_clip_notes      — read all notes from a clip (read-only)
#   get_clip_info       — read clip metadata (name, length, color)
#   find_clip_by_name   — search for a clip by name across all tracks
#   get_track_devices   — list devices on a track
#   get_device_params   — list parameters on a device (supports rack chain navigation)
#   setup_rig           — create/name/configure tracks and scenes from a rig definition dict
#   create_scene        — append or insert a named scene
#   set_tempo           — set session tempo
#   create_clip         — create a MIDI clip in a track/slot
#   add_notes_to_clip   — push MIDI notes into a clip
#   clear_clip          — remove all notes from a clip
#   set_clip_name       — rename a clip
#   set_device_param    — set a device parameter value (by name or index, supports rack chains)
#   fire_clip           — start playing a clip
#   stop_clip           — stop a clip
#   fire_scene          — fire a scene by index
#   start_playback      — start session
#   stop_playback       — stop session
#   insert_device       — insert a native Live device into a track or rack chain (Live 12.3)
#   insert_chain        — insert a new chain into a rack device (Live 12.3)
#   build_rack          — create an Instrument Rack and populate chains with devices (Live 12.3)

from __future__ import absolute_import, print_function, unicode_literals

from _Framework.ControlSurface import ControlSurface
import socket
import json
import threading
import traceback

try:
    import Queue as queue  # Python 2 (Live uses Python 2 internally)
except ImportError:
    import queue  # Python 3

HOST = "localhost"
PORT = 9877


_RELOADING = False


def create_instance(c_instance):
    global _RELOADING
    if not _RELOADING:
        try:
            import importlib
            import sys as _sys
            _RELOADING = True
            importlib.reload(_sys.modules[__name__])
            _RELOADING = False
            return _sys.modules[__name__].IronStatic(c_instance)
        except Exception:
            _RELOADING = False
    return IronStatic(c_instance)


class IronStatic(ControlSurface):

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self._song = self.song()
        self.server = None
        self.server_thread = None
        self.client_threads = []
        self.running = False
        self.log_message("IronStatic Remote Script initialized on port {}".format(PORT))
        self.show_message("IronStatic: listening on port {}".format(PORT))
        self._start_server()

    def disconnect(self):
        self.running = False
        if self.server:
            try:
                self.server.close()
            except Exception:
                pass
        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(1.0)
        ControlSurface.disconnect(self)

    # ------------------------------------------------------------------
    # Socket server
    # ------------------------------------------------------------------

    def _start_server(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((HOST, PORT))
            self.server.listen(5)
            self.running = True
            self.server_thread = threading.Thread(target=self._server_loop)
            self.server_thread.daemon = True
            self.server_thread.start()
        except Exception as e:
            self.log_message("IronStatic: error starting server: {}".format(e))
            self.show_message("IronStatic: server error — {}".format(e))

    def _server_loop(self):
        self.server.settimeout(1.0)
        while self.running:
            try:
                client, address = self.server.accept()
                self.log_message("IronStatic: client connected from {}".format(address))
                t = threading.Thread(target=self._handle_client, args=(client,))
                t.daemon = True
                t.start()
                self.client_threads.append(t)
                self.client_threads = [t for t in self.client_threads if t.is_alive()]
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    self.log_message("IronStatic: server accept error: {}".format(e))

    def _handle_client(self, client):
        client.settimeout(None)
        buf = ""
        try:
            while self.running:
                data = client.recv(65536)
                if not data:
                    break
                try:
                    buf += data.decode("utf-8")
                except AttributeError:
                    buf += data

                try:
                    command = json.loads(buf)
                    buf = ""
                    response = self._dispatch(command)
                    payload = json.dumps(response)
                    try:
                        client.sendall(payload.encode("utf-8"))
                    except AttributeError:
                        client.sendall(payload)
                except ValueError:
                    continue  # incomplete JSON — wait for more data
        except Exception as e:
            self.log_message("IronStatic: client handler error: {}".format(e))
        finally:
            try:
                client.close()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def _dispatch(self, command):
        cmd_type = command.get("type", "")
        params = command.get("params", {})
        response = {"status": "success", "result": {}}

        # Read-only commands — safe to run on socket thread
        try:
            if cmd_type == "get_session_info":
                response["result"] = self._get_session_info()
                return response

            if cmd_type == "get_clip_notes":
                response["result"] = self._get_clip_notes(
                    params["track_index"], params["clip_index"])
                return response

            if cmd_type == "get_clip_info":
                response["result"] = self._get_clip_info(
                    params["track_index"], params["clip_index"])
                return response

            if cmd_type == "find_clip_by_name":
                response["result"] = self._find_clip_by_name(
                    params["name"], params.get("track_name"))
                return response

            if cmd_type == "get_track_devices":
                response["result"] = self._get_track_devices(
                    params["track_index"])
                return response

            if cmd_type == "get_device_params":
                response["result"] = self._get_device_params(
                    params["track_index"], params["device_index"],
                    params.get("chain_index"), params.get("chain_device_index"))
                return response

            if cmd_type == "inspect_drum_rack":
                response["result"] = self._inspect_drum_rack(
                    params["track_index"], params["device_index"])
                return response

            # All mutating commands must run on Ableton's main thread
            MUTATING = {
                "setup_rig", "create_track", "create_scene", "set_tempo",
                "create_clip", "add_notes_to_clip", "clear_clip",
                "set_clip_name", "set_device_param", "batch_set_device_params",
                "fire_clip", "stop_clip",
                "fire_scene",
                "set_scene_tempo", "set_scene_name",
                "start_playback", "stop_playback",
                "insert_device", "insert_chain", "build_rack",
                "delete_device",
                "load_preset",
            }

            if cmd_type in MUTATING:
                q = queue.Queue()

                def task():
                    try:
                        result = self._run_mutating(cmd_type, params)
                        q.put({"status": "success", "result": result})
                    except Exception as e:
                        self.log_message(traceback.format_exc())
                        q.put({"status": "error", "message": str(e)})

                try:
                    self.schedule_message(0, task)
                except AssertionError:
                    task()  # already on main thread

                try:
                    return q.get(timeout=15.0)
                except queue.Empty:
                    return {"status": "error", "message": "Timeout waiting for Ableton main thread"}

            response["status"] = "error"
            response["message"] = "Unknown command: {}".format(cmd_type)
        except Exception as e:
            self.log_message(traceback.format_exc())
            response["status"] = "error"
            response["message"] = str(e)

        return response

    # ------------------------------------------------------------------
    # Mutating command implementations (called on Ableton main thread)
    # ------------------------------------------------------------------

    def _run_mutating(self, cmd_type, params):
        if cmd_type == "setup_rig":
            return self._setup_rig(params)
        elif cmd_type == "create_track":
            return self._create_track(params)
        elif cmd_type == "set_tempo":
            return self._set_tempo(params["tempo"])
        elif cmd_type == "create_clip":
            return self._create_clip(params["track_index"], params["clip_index"], params.get("length", 4.0))
        elif cmd_type == "add_notes_to_clip":
            return self._add_notes_to_clip(params["track_index"], params["clip_index"], params["notes"])
        elif cmd_type == "clear_clip":
            return self._clear_clip(params["track_index"], params["clip_index"])
        elif cmd_type == "set_clip_name":
            return self._set_clip_name(params["track_index"], params["clip_index"], params["name"])
        elif cmd_type == "fire_clip":
            return self._fire_clip(params["track_index"], params["clip_index"])
        elif cmd_type == "stop_clip":
            return self._stop_clip(params["track_index"], params["clip_index"])
        elif cmd_type == "fire_scene":
            return self._fire_scene(params["scene_index"])
        elif cmd_type == "set_scene_tempo":
            return self._set_scene_tempo(params["scene_index"], params["tempo"],
                                          params.get("numerator"), params.get("denominator"))
        elif cmd_type == "set_scene_name":
            return self._set_scene_name(params["scene_index"], params["name"])
        elif cmd_type == "set_device_param":
            return self._set_device_param(
                params["track_index"], params["device_index"], params["value"],
                param_index=params.get("param_index"),
                param_name=params.get("param_name"),
                chain_index=params.get("chain_index"),
                chain_device_index=params.get("chain_device_index"))
        elif cmd_type == "batch_set_device_params":
            return self._batch_set_device_params(
                params["track_index"], params["device_index"], params["operations"])
        elif cmd_type == "create_scene":
            return self._create_scene(
                name=params.get("name"), index=params.get("index", -1))
        elif cmd_type == "insert_device":
            return self._insert_device(
                params["track_index"], params["device_name"],
                target_index=params.get("target_index"),
                chain_index=params.get("chain_index"))
        elif cmd_type == "insert_chain":
            return self._insert_chain(
                params["track_index"], params["device_index"],
                index=params.get("index"),
                name=params.get("name"))
        elif cmd_type == "build_rack":
            return self._build_rack(params)
        elif cmd_type == "delete_device":
            return self._delete_device(
                params["track_index"], params["device_index"],
                chain_index=params.get("chain_index"))
        elif cmd_type == "load_preset":
            return self._load_preset(
                params["track_index"], params["preset_name"])
        elif cmd_type == "start_playback":
            self._song.start_playing()
            return {"playing": True}
        elif cmd_type == "stop_playback":
            self._song.stop_playing()
            return {"playing": False}
        raise ValueError("Unhandled mutating command: {}".format(cmd_type))

    def _batch_set_device_params(self, track_index, device_index, operations):
        """
        Apply multiple parameter changes to a device in one main-thread call.

        operations: list of dicts, each with:
            param   — parameter name (str) or index (int)
            value   — float value to set
            chain_index        — (optional) int, index of rack chain
            chain_device_index — (optional) int, device index within chain (default 0)
        """
        results = []
        for op in operations:
            raw_param = op["param"]
            try:
                param_index = int(raw_param)
                param_name = None
            except (ValueError, TypeError):
                param_index = None
                param_name = str(raw_param)
            r = self._set_device_param(
                track_index, device_index, op["value"],
                param_index=param_index,
                param_name=param_name,
                chain_index=op.get("chain_index"),
                chain_device_index=op.get("chain_device_index", 0) if "chain_index" in op else None,
            )
            results.append(r)
        return {"applied": len(results), "results": results}

    # ------------------------------------------------------------------
    # create_track — append a single MIDI track
    # ------------------------------------------------------------------

    def _create_track(self, params):
        """
        Append a new MIDI track at the end of the session.

        params = {
            "name": "Take5",
            "midi_channel": 4,
            "color": 10027263,   # optional
            "clips": [           # optional
                {"index": 0, "length": 4.0, "name": "main"}
            ]
        }
        """
        name = params.get("name", "New Track")
        midi_channel = int(params.get("midi_channel", 1))
        color = params.get("color", None)
        clips = params.get("clips", [])

        self._song.create_midi_track(-1)
        track = self._song.tracks[len(self._song.tracks) - 1]
        track.name = name

        if color is not None:
            try:
                track.color = int(color)
            except Exception:
                pass

        try:
            track.current_output_sub_routing = str(midi_channel)
        except Exception:
            pass

        for clip_def in clips:
            slot_index = clip_def.get("index", 0)
            length = float(clip_def.get("length", 4.0))
            clip_name = clip_def.get("name", "")
            if slot_index < len(track.clip_slots):
                slot = track.clip_slots[slot_index]
                if not slot.has_clip:
                    slot.create_clip(length)
                if clip_name:
                    slot.clip.name = clip_name

        return {
            "index": len(self._song.tracks) - 1,
            "name": track.name,
            "midi_channel": midi_channel,
        }

    # ------------------------------------------------------------------
    # setup_rig — the Iron Static-specific command
    # ------------------------------------------------------------------

    def _setup_rig(self, params):
        """
        Create and configure MIDI tracks from a rig definition.

        params = {
            "tempo": 140,
            "time_signature": [4, 4],
            "tracks": [
                {"name": "Digitakt",  "midi_channel": 1, "color": 0xFF0000},
                {"name": "Rev2-A",    "midi_channel": 2, "color": 0x0000FF},
                ...
            ]
        }
        """
        created = []

        # Set tempo if provided
        if "tempo" in params:
            self._song.tempo = float(params["tempo"])

        # Set time signature if provided
        if "time_signature" in params:
            num, denom = params["time_signature"]
            self._song.signature_numerator = int(num)
            self._song.signature_denominator = int(denom)

        # Create/rename scenes if specified
        if "scenes" in params:
            scene_names = params["scenes"]
            for i, sname in enumerate(scene_names):
                if i >= len(self._song.scenes):
                    self._song.create_scene(-1)
                if i < len(self._song.scenes):
                    self._song.scenes[i].name = sname

        tracks_def = params.get("tracks", [])
        existing_count = len(self._song.tracks)

        for i, track_def in enumerate(tracks_def):
            track_name = track_def.get("name", "Track {}".format(i))
            midi_channel = track_def.get("midi_channel", i + 1)
            color = track_def.get("color", None)

            # Reuse existing tracks before creating new ones
            if i < existing_count:
                track = self._song.tracks[i]
                if not track.has_midi_input:
                    # Can't convert audio tracks — skip with warning
                    self.log_message("IronStatic: track {} is audio, skipping".format(i))
                    continue
            else:
                self._song.create_midi_track(-1)
                track = self._song.tracks[len(self._song.tracks) - 1]

            track.name = track_name

            if color is not None:
                try:
                    track.color = int(color)
                except Exception:
                    pass  # color API varies by Live version

            # Set MIDI output channel on the track
            try:
                track.current_output_sub_routing = str(midi_channel)
            except Exception:
                pass  # not all Live versions expose this via Remote Script

            # Pre-create clips if specified
            for clip_def in track_def.get("clips", []):
                slot_index = clip_def.get("index", 0)
                length = clip_def.get("length", 4.0)
                clip_name = clip_def.get("name", "")
                if slot_index < len(track.clip_slots):
                    slot = track.clip_slots[slot_index]
                    if not slot.has_clip:
                        slot.create_clip(float(length))
                    if clip_name:
                        slot.clip.name = clip_name

            created.append({
                "index": i,
                "name": track.name,
                "midi_channel": midi_channel,
            })

        return {
            "tracks_configured": len(created),
            "tracks": created,
            "tempo": self._song.tempo,
        }

    # ------------------------------------------------------------------
    # Read-only helpers
    # ------------------------------------------------------------------

    def _get_session_info(self):
        tracks = []
        for i, track in enumerate(self._song.tracks):
            try:
                arm = track.arm
            except Exception:
                arm = False
            tracks.append({
                "index": i,
                "name": track.name,
                "is_midi": track.has_midi_input,
                "is_audio": track.has_audio_input,
                "mute": track.mute,
                "arm": arm,
            })
        scenes = []
        for i, scene in enumerate(self._song.scenes):
            scenes.append({"index": i, "name": scene.name})
        return {
            "tempo": self._song.tempo,
            "signature_numerator": self._song.signature_numerator,
            "signature_denominator": self._song.signature_denominator,
            "track_count": len(self._song.tracks),
            "scene_count": len(self._song.scenes),
            "scenes": scenes,
            "tracks": tracks,
        }

    def _find_clip_by_name(self, clip_name, track_name=None):
        """Search all tracks (optionally filtered by track name) for a clip by name.
        Returns {track_index, track_name, clip_index, clip_name} or raises."""
        results = []
        for i, track in enumerate(self._song.tracks):
            if track_name and track.name.lower() != track_name.lower():
                continue
            for j, slot in enumerate(track.clip_slots):
                if slot.has_clip and slot.clip.name.lower() == clip_name.lower():
                    results.append({
                        "track_index": i,
                        "track_name":  track.name,
                        "clip_index":  j,
                        "clip_name":   slot.clip.name,
                    })
        if not results:
            raise ValueError("No clip named '{}' found".format(clip_name))
        return results[0] if len(results) == 1 else {"matches": results}

    def _get_clip_info(self, track_index, clip_index):
        clip = self._get_clip(track_index, clip_index)
        return {
            "name": clip.name,
            "length": clip.length,
            "is_playing": clip.is_playing,
            "is_recording": clip.is_recording,
            "loop_start": clip.loop_start,
            "loop_end": clip.loop_end,
            "color": clip.color if hasattr(clip, 'color') else None,
        }

    def _get_clip_notes(self, track_index, clip_index):
        clip = self._get_clip(track_index, clip_index)
        # get_notes(from_time, from_pitch, time_span, pitch_span)
        # returns tuple of (pitch, time, duration, velocity, mute)
        try:
            raw_notes = clip.get_notes(0.0, 0, float(clip.length), 128)
        except Exception as e:
            self.log_message("IronStatic: get_clip_notes error: {}".format(e))
            raw_notes = ()
        notes = [
            {
                "pitch":      int(n[0]),
                "start_time": float(n[1]),
                "duration":   float(n[2]),
                "velocity":   int(n[3]),
                "mute":       bool(n[4]),
            }
            for n in raw_notes
        ]
        notes.sort(key=lambda n: (n["start_time"], n["pitch"]))
        return {
            "clip_name":   clip.name,
            "clip_length": float(clip.length),
            "note_count":  len(notes),
            "notes":       notes,
        }

    # ------------------------------------------------------------------
    # Clip helpers
    # ------------------------------------------------------------------

    def _get_clip(self, track_index, clip_index):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index {} out of range".format(track_index))
        track = self._song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index {} out of range".format(clip_index))
        slot = track.clip_slots[clip_index]
        if not slot.has_clip:
            raise ValueError("No clip in track {} slot {}".format(track_index, clip_index))
        return slot.clip

    def _create_clip(self, track_index, clip_index, length):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index {} out of range".format(track_index))
        track = self._song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index {} out of range".format(clip_index))
        slot = track.clip_slots[clip_index]
        if slot.has_clip:
            raise ValueError("Clip slot already occupied")
        slot.create_clip(float(length))
        return {"name": slot.clip.name, "length": slot.clip.length}

    def _add_notes_to_clip(self, track_index, clip_index, notes):
        """
        notes: list of dicts with keys:
            pitch       (MIDI note number, 0–127)
            start_time  (beat position, float)
            duration    (beat duration, float)
            velocity    (0–127)
            mute        (bool, optional)
        """
        clip = self._get_clip(track_index, clip_index)
        live_notes = tuple(
            (
                int(n["pitch"]),
                float(n["start_time"]),
                float(n["duration"]),
                int(n.get("velocity", 100)),
                bool(n.get("mute", False)),
            )
            for n in notes
        )
        clip.set_notes(live_notes)
        return {"note_count": len(live_notes)}

    def _clear_clip(self, track_index, clip_index):
        clip = self._get_clip(track_index, clip_index)
        clip.set_notes(())
        return {"cleared": True}

    def _set_clip_name(self, track_index, clip_index, name):
        clip = self._get_clip(track_index, clip_index)
        clip.name = name
        return {"name": clip.name}

    def _fire_clip(self, track_index, clip_index):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index {} out of range".format(track_index))
        track = self._song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index {} out of range".format(clip_index))
        track.clip_slots[clip_index].fire()
        return {"fired": True}

    def _stop_clip(self, track_index, clip_index):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index {} out of range".format(track_index))
        track = self._song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index {} out of range".format(clip_index))
        track.clip_slots[clip_index].stop()
        return {"stopped": True}

    def _fire_scene(self, scene_index):
        scenes = self._song.scenes
        if scene_index < 0 or scene_index >= len(scenes):
            raise IndexError("Scene index {} out of range".format(scene_index))
        scenes[scene_index].fire()
        return {"fired": True, "scene_index": scene_index}

    def _set_scene_tempo(self, scene_index, tempo, numerator=None, denominator=None):
        scenes = self._song.scenes
        if scene_index < 0 or scene_index >= len(scenes):
            raise IndexError("Scene index {} out of range".format(scene_index))
        scene = scenes[scene_index]
        scene.tempo = float(tempo)
        if numerator is not None:
            scene.time_signature_numerator = int(numerator)
        if denominator is not None:
            scene.time_signature_denominator = int(denominator)
        return {
            "scene_index": scene_index,
            "tempo": scene.tempo,
        }

    def _set_scene_name(self, scene_index, name):
        scenes = self._song.scenes
        if scene_index < 0 or scene_index >= len(scenes):
            raise IndexError("Scene index {} out of range".format(scene_index))
        scenes[scene_index].name = name
        return {"scene_index": scene_index, "name": scenes[scene_index].name}

    def _set_tempo(self, tempo):
        self._song.tempo = float(tempo)
        return {"tempo": self._song.tempo}

    # ------------------------------------------------------------------
    # Device inspection and control
    # ------------------------------------------------------------------

    def _get_track_devices(self, track_index):
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index {} out of range".format(track_index))
        track = self._song.tracks[track_index]
        devices = []
        for i, device in enumerate(track.devices):
            can_have_chains = getattr(device, "can_have_chains", False)
            entry = {
                "index": i,
                "name": device.name,
                "class_name": getattr(device, "class_name", ""),
                "num_parameters": len(device.parameters),
                "can_have_chains": can_have_chains,
            }
            if can_have_chains:
                entry["num_chains"] = len(device.chains)
            devices.append(entry)
        return {"track_index": track_index, "track_name": track.name, "devices": devices}

    def _get_device(self, track_index, device_index, chain_index=None, chain_device_index=None):
        """Resolve a device, optionally navigating into a rack chain."""
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index {} out of range".format(track_index))
        track = self._song.tracks[track_index]
        if device_index < 0 or device_index >= len(track.devices):
            raise IndexError("Device index {} out of range on track '{}'".format(
                device_index, track.name))
        device = track.devices[device_index]
        if chain_index is not None:
            chains = getattr(device, "chains", [])
            if chain_index >= len(chains):
                raise IndexError("Chain index {} out of range".format(chain_index))
            chain = chains[chain_index]
            cdx = chain_device_index if chain_device_index is not None else 0
            if cdx >= len(chain.devices):
                raise IndexError("Chain device index {} out of range".format(cdx))
            device = chain.devices[cdx]
        return device

    def _get_device_params(self, track_index, device_index,
                           chain_index=None, chain_device_index=None):
        device = self._get_device(track_index, device_index, chain_index, chain_device_index)
        params = []
        for i, p in enumerate(device.parameters):
            params.append({
                "index": i,
                "name": p.name,
                "value": float(p.value),
                "min": float(p.min),
                "max": float(p.max),
                "is_quantized": bool(p.is_quantized),
            })
        return {
            "device_name": device.name,
            "class_name": getattr(device, "class_name", ""),
            "parameters": params,
        }

    def _inspect_drum_rack(self, track_index, device_index):
        """Return all pad chain info from a DrumGroupDevice.

        For each active pad chain returns:
            chain_index    — position in device.chains
            receiving_note — MIDI note number that triggers this pad (36=C1)
            name           — pad chain name
            num_devices    — number of devices inside the chain
            sample_path    — absolute path to the loaded sample, or None
        """
        device = self._get_device(track_index, device_index)
        chains = getattr(device, "chains", None)
        if chains is None:
            raise ValueError("Device '{}' has no chains — not a Drum Rack".format(device.name))
        pads = []
        for i, chain in enumerate(chains):
            # Live Remote Script API uses in_note (M4L/LOM calls it receiving_note)
            receiving_note = getattr(chain, "in_note", None)
            sample_path = None
            for dev in chain.devices:
                sp = self._find_simpler_sample_path(dev)
                if sp is not None:
                    sample_path = sp
                    break
            pads.append({
                "chain_index": i,
                "receiving_note": receiving_note,
                "name": chain.name,
                "num_devices": len(chain.devices),
                "sample_path": sample_path,
            })
        return {
            "device_name": device.name,
            "class_name": getattr(device, "class_name", ""),
            "num_chains": len(chains),
            "pads": pads,
        }

    def _find_simpler_sample_path(self, device):
        """Recursively search a device tree for a Simpler with a loaded sample.
        Returns the file_path string or None.
        """
        class_name = getattr(device, "class_name", "")
        if "Simpler" in class_name or "OriginalSimpler" in class_name:
            sample = getattr(device, "sample", None)
            if sample is not None:
                fp = getattr(sample, "file_path", None)
                if fp:
                    return fp
        # Recurse into rack chains
        for chain in getattr(device, "chains", []):
            for sub_dev in chain.devices:
                result = self._find_simpler_sample_path(sub_dev)
                if result is not None:
                    return result
        return None

    def _set_device_param(self, track_index, device_index, value,
                          param_index=None, param_name=None,
                          chain_index=None, chain_device_index=None):
        device = self._get_device(track_index, device_index, chain_index, chain_device_index)
        param = None
        if param_name is not None:
            for p in device.parameters:
                if p.name.lower() == param_name.lower():
                    param = p
                    break
            if param is None:
                raise ValueError("Parameter '{}' not found on device '{}'".format(
                    param_name, device.name))
        elif param_index is not None:
            if param_index < 0 or param_index >= len(device.parameters):
                raise IndexError("Parameter index {} out of range".format(param_index))
            param = device.parameters[param_index]
        else:
            raise ValueError("Must specify param_index or param_name")
        param.value = float(value)
        return {
            "device_name": device.name,
            "param_name": param.name,
            "value": float(param.value),
        }

    # ------------------------------------------------------------------
    # Scene management
    # ------------------------------------------------------------------

    def _create_scene(self, name=None, index=-1):
        self._song.create_scene(int(index))
        scenes = self._song.scenes
        scene = scenes[len(scenes) - 1] if index == -1 else scenes[int(index)]
        if name:
            scene.name = name
        scene_index = len(scenes) - 1 if index == -1 else int(index)
        return {"scene_index": scene_index, "name": scene.name}

    # ------------------------------------------------------------------
    # Device manipulation — Live 12.3 APIs
    # ------------------------------------------------------------------

    def _resolve_track(self, track_index):
        """Return track object by index, raising IndexError if out of range."""
        if track_index < 0 or track_index >= len(self._song.tracks):
            raise IndexError("Track index {} out of range".format(track_index))
        return self._song.tracks[track_index]

    def _insert_device(self, track_index, device_name, target_index=None, chain_index=None):
        """
        Insert a native Live device by name.

        If chain_index is None: inserts into the track's top-level device chain.
        If chain_index is given: inserts into that chain of the FIRST rack device on the track
          (device index 0 is assumed; override by passing device_index separately if needed).

        Returns the new device count and the inserted device's name.
        """
        track = self._resolve_track(track_index)
        if chain_index is None:
            if target_index is not None:
                track.insert_device(device_name, target_index)
            else:
                track.insert_device(device_name)
            devices = track.devices
        else:
            # Insert into rack chain — assumes first device on track is the rack
            rack = track.devices[0]
            chains = getattr(rack, "chains", [])
            if chain_index >= len(chains):
                raise IndexError("Chain index {} out of range on rack '{}'".format(
                    chain_index, rack.name))
            chain = chains[chain_index]
            if target_index is not None:
                chain.insert_device(device_name, target_index)
            else:
                chain.insert_device(device_name)
            devices = chain.devices
        inserted = devices[len(devices) - 1]
        return {
            "device_name": inserted.name,
            "class_name": getattr(inserted, "class_name", ""),
            "device_count": len(devices),
        }

    def _load_preset(self, track_index, preset_name):
        """
        Load a browser preset (.adg / .adv / .agr) onto a track by name.

        Searches Browser > Packs and Browser > User Library depth-first.
        Accepts names with or without the file extension:
            "808 Depth Charger Kit"   or   "808 Depth Charger Kit.adg"

        Live loads the item onto the currently selected track, so we select
        the target track first via Song.view.selected_track.
        """
        track = self._resolve_track(track_index)
        self._song.view.selected_track = track

        browser = self.application().browser

        # Normalise: strip .adg/.adv extension for comparison, add back when searching
        bare_name = preset_name
        for ext in (".adg", ".adv", ".agr"):
            if bare_name.lower().endswith(ext):
                bare_name = bare_name[: -len(ext)]
                break

        def _find(parent, depth=0):
            if depth > 12:          # safety: don't traverse infinitely deep
                return None
            try:
                children = parent.children
            except Exception:
                return None
            for item in children:
                item_bare = item.name
                for ext in (".adg", ".adv", ".agr"):
                    if item_bare.lower().endswith(ext):
                        item_bare = item_bare[: -len(ext)]
                        break
                if item_bare.lower() == bare_name.lower() and item.is_loadable:
                    return item
                found = _find(item, depth + 1)
                if found:
                    return found
            return None

        item = None
        for root in [browser.packs, browser.user_library]:
            item = _find(root)
            if item:
                break

        if item is None:
            raise ValueError(
                "Preset '{}' not found in Packs or User Library".format(preset_name))

        browser.load_item(item)
        return {
            "loaded": item.name,
            "track": track.name,
            "track_index": track_index,
        }

    def _insert_chain(self, track_index, device_index, index=None, name=None):
        """
        Insert a new empty chain into a RackDevice.

        track_index:  index of the track
        device_index: index of the RackDevice on that track
        index:        where to insert (None = append at end)
        name:         optional name to set on the new chain
        """
        track = self._resolve_track(track_index)
        if device_index >= len(track.devices):
            raise IndexError("Device index {} out of range on track '{}'".format(
                device_index, track.name))
        rack = track.devices[device_index]
        chains = getattr(rack, "chains", None)
        if chains is None:
            raise ValueError("Device '{}' is not a Rack and has no chains".format(rack.name))
        if index is not None:
            rack.insert_chain(int(index))
            new_chain = rack.chains[int(index)]
            chain_index = int(index)
        else:
            rack.insert_chain()
            chain_index = len(rack.chains) - 1
            new_chain = rack.chains[chain_index]
        if name:
            new_chain.name = name
        return {
            "rack_name": rack.name,
            "chain_index": chain_index,
            "chain_name": new_chain.name,
            "chain_count": len(rack.chains),
        }

    def _delete_device(self, track_index, device_index, chain_index=None):
        """
        Delete a device by index from a track or from a rack chain.

        chain_index: if set, deletes from that chain of the first rack device on the track.
        """
        track = self._resolve_track(track_index)
        if chain_index is None:
            if device_index >= len(track.devices):
                raise IndexError("Device index {} out of range on track '{}'".format(
                    device_index, track.name))
            device_name = track.devices[device_index].name
            track.delete_device(device_index)
            return {"deleted": device_name, "track": track.name}
        else:
            rack = track.devices[device_index]
            chains = getattr(rack, "chains", [])
            if chain_index >= len(chains):
                raise IndexError("Chain index {} out of range".format(chain_index))
            chain = chains[chain_index]
            # chain_device_index not exposed here — always deletes index 0 in the chain
            # for more control use chain_index + explicit device_index via a second param
            device_name = chain.devices[0].name if chain.devices else "(none)"
            chain.delete_device(0)
            return {"deleted": device_name, "chain_index": chain_index}

    def _build_rack(self, params):
        """
        Build an Instrument Rack with multiple chains from a spec.

        params = {
            "track_index": 5,
            "rack_name": "DFAM Rack",          # optional — renames the rack
            "chains": [
                {"name": "Hit",    "device": "Collision"},
                {"name": "Tone",   "device": "Collision"},
                {"name": "Noise",  "device": "Collision"},
            ]
        }

        If the track already has an Instrument Rack, adds chains to it.
        If non-rack devices exist, deletes them first before inserting the rack.
        """
        track_index = params["track_index"]
        rack_name = params.get("rack_name")
        chain_specs = params.get("chains", [])

        track = self._resolve_track(track_index)

        # Find existing rack, or clear non-rack devices and create one
        rack = None
        for dev in track.devices:
            if getattr(dev, "can_have_chains", False):
                rack = dev
                break

        if rack is None:
            # Delete any non-rack instruments sitting on the track (e.g. bare Collision)
            # Iterate in reverse so indices stay valid after each deletion
            devices_to_delete = [
                i for i, dev in enumerate(track.devices)
                if not getattr(dev, "can_have_chains", False)
                and getattr(dev, "type", 0) == 1  # type 1 = instrument
            ]
            for i in reversed(devices_to_delete):
                track.delete_device(i)
            track.insert_device("Instrument Rack")
            rack = track.devices[len(track.devices) - 1]

        if rack_name:
            rack.name = rack_name

        created_chains = []
        for spec in chain_specs:
            rack.insert_chain()
            chain_idx = len(rack.chains) - 1
            chain = rack.chains[chain_idx]
            if spec.get("name"):
                chain.name = spec["name"]
            if spec.get("device"):
                chain.insert_device(spec["device"])
            created_chains.append({
                "chain_index": chain_idx,
                "chain_name": chain.name,
                "device": spec.get("device"),
            })

        return {
            "track_name": track.name,
            "rack_name": rack.name,
            "chains_created": len(created_chains),
            "chains": created_chains,
        }
