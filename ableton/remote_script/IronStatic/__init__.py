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
#   get_session_info    — read tempo, time sig, track list
#   setup_rig           — create/name/configure tracks from a rig definition dict
#   set_tempo           — set session tempo
#   create_clip         — create a MIDI clip in a track/slot
#   add_notes_to_clip   — push MIDI notes into a clip
#   clear_clip          — remove all notes from a clip
#   set_clip_name       — rename a clip
#   fire_clip           — start playing a clip
#   stop_clip           — stop a clip
#   start_playback      — start session
#   stop_playback       — stop session

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


def create_instance(c_instance):
    return IronStatic(c_instance)


class IronStatic(ControlSurface):

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self._song = self.song()
        self.server = None
        self.server_thread = None
        self.client_threads = []
        self.running = False
        self._start_server()
        self.log_message("IronStatic Remote Script initialized on port {}".format(PORT))
        self.show_message("IronStatic: listening on port {}".format(PORT))

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

            # All mutating commands must run on Ableton's main thread
            MUTATING = {
                "setup_rig", "set_tempo",
                "create_clip", "add_notes_to_clip", "clear_clip",
                "set_clip_name", "fire_clip", "stop_clip",
                "start_playback", "stop_playback",
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
        elif cmd_type == "start_playback":
            self._song.start_playing()
            return {"playing": True}
        elif cmd_type == "stop_playback":
            self._song.stop_playing()
            return {"playing": False}
        raise ValueError("Unhandled mutating command: {}".format(cmd_type))

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

        tracks_def = params.get("tracks", [])

        for i, track_def in enumerate(tracks_def):
            track_name = track_def.get("name", "Track {}".format(i))
            midi_channel = track_def.get("midi_channel", i + 1)
            color = track_def.get("color", None)

            # Always create a new MIDI track at the end
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
        return {
            "tempo": self._song.tempo,
            "signature_numerator": self._song.signature_numerator,
            "signature_denominator": self._song.signature_denominator,
            "track_count": len(self._song.tracks),
            "tracks": tracks,
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

    def _set_tempo(self, tempo):
        self._song.tempo = float(tempo)
        return {"tempo": self._song.tempo}
