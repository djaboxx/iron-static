#!/usr/bin/env python3
"""
dial_bridge.py — Stream Deck dial → IRON STATIC parameter bridge.

Maps the 4 Stream Deck + encoders to live Ableton/MIDI parameters.
Called by Stream Deck "System: Run" action on each dial tick.

Stream Deck + sends a signed integer delta per tick (typically +1 or -1).
Each dial is mapped to a specific parameter. The script reads a state file
to track the current value, applies the delta, clamps to range, and sends
the updated value to the appropriate destination (bridge TCP or MIDI CC).

Dial assignments (configurable in DIAL_MAP below):
  Dial 1 — Ableton Master BPM          (30–300, via Remote Script bridge)
  Dial 2 — Ableton Master Volume        (0–127, CC7 on ch 1 → IAC bus or bridge)
  Dial 3 — Pigments Macro M1 (CC20)    (0–127, MIDI ch 8)
  Dial 4 — Pigments Macro M2 (CC21)    (0–127, MIDI ch 8)

Usage (called by Stream Deck):
  python streamdeck/dial_bridge.py --dial 1 --delta +1
  python streamdeck/dial_bridge.py --dial 1 --delta -1
  python streamdeck/dial_bridge.py --dial 3 --delta +5   # hold + turn = faster
  python streamdeck/dial_bridge.py --dial 1 --set 138    # absolute set
  python streamdeck/dial_bridge.py --status              # print current values

State is persisted in /tmp/iron-static-dial-state.json between calls.
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

log = logging.getLogger("dial_bridge")

REPO_ROOT = Path(__file__).parent.parent
STATE_FILE = Path("/tmp/iron-static-dial-state.json")

# ---------------------------------------------------------------------------
# Dial configuration
# ---------------------------------------------------------------------------

DIAL_MAP = {
    1: {
        "name": "BPM",
        "type": "bridge_tempo",
        "default": 116,
        "min": 40,
        "max": 300,
        "step": 1,        # units per tick (hold modifier multiplies this)
        "display": "{:.0f} BPM",
    },
    2: {
        "name": "Master Vol",
        "type": "bridge_param",
        "bridge_cmd": "set_master_volume",  # extend bridge_client as needed
        "default": 100,
        "min": 0,
        "max": 127,
        "step": 2,
        "display": "Vol {:.0f}",
    },
    3: {
        "name": "Pigments M1",
        "type": "midi_cc",
        "cc": 20,
        "channel": 8,
        "port_hint": "IAC",   # fuzzy-matched; falls back to first available
        "default": 64,
        "min": 0,
        "max": 127,
        "step": 3,
        "display": "M1 {:.0f}",
    },
    4: {
        "name": "Pigments M2",
        "type": "midi_cc",
        "cc": 21,
        "channel": 8,
        "port_hint": "IAC",
        "default": 64,
        "min": 0,
        "max": 127,
        "step": 3,
        "display": "M2 {:.0f}",
    },
}

# ---------------------------------------------------------------------------
# State management
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {str(d): cfg["default"] for d, cfg in DIAL_MAP.items()}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2))


# ---------------------------------------------------------------------------
# Parameter senders
# ---------------------------------------------------------------------------

def send_bridge_tempo(value: float) -> bool:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        from bridge_client import BridgeClient
        with BridgeClient() as b:
            r = b.transport_tempo(value)
            return r.get("status") == "success"
    except Exception as e:
        log.error("bridge_tempo failed: %s", e)
        return False


def send_bridge_param(cmd: str, value: float) -> bool:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    try:
        from bridge_client import _call
        r = _call(cmd, {"value": value})
        return r.get("status") == "success"
    except Exception as e:
        log.error("bridge_param %s failed: %s", cmd, e)
        return False


def send_midi_cc(cc: int, value: int, channel: int, port_hint: str) -> bool:
    try:
        import mido
        ports = mido.get_output_names()
        port_name = next((p for p in ports if port_hint.lower() in p.lower()), None)
        if port_name is None:
            # Fall back to first available output
            port_name = ports[0] if ports else None
        if port_name is None:
            log.error("No MIDI output ports available.")
            return False
        # channel is 1-based in our config, mido uses 0-based
        msg = mido.Message("control_change", channel=channel - 1, control=cc, value=int(value))
        with mido.open_output(port_name) as out:
            out.send(msg)
        log.debug("CC%d=%d on ch%d → %s", cc, value, channel, port_name)
        return True
    except ImportError:
        log.error("mido not installed. Run: pip install mido python-rtmidi")
        return False
    except Exception as e:
        log.error("midi_cc failed: %s", e)
        return False


def dispatch(dial: int, value: float, cfg: dict) -> bool:
    t = cfg["type"]
    if t == "bridge_tempo":
        return send_bridge_tempo(value)
    elif t == "bridge_param":
        return send_bridge_param(cfg["bridge_cmd"], value)
    elif t == "midi_cc":
        return send_midi_cc(cfg["cc"], int(value), cfg["channel"], cfg["port_hint"])
    else:
        log.error("Unknown dial type: %s", t)
        return False


# ---------------------------------------------------------------------------
# Notification (macOS)
# ---------------------------------------------------------------------------

def notify(title: str, message: str) -> None:
    try:
        os.system(f'osascript -e \'display notification "{message}" with title "{title}"\'')
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Stream Deck dial → IRON STATIC parameter bridge")
    parser.add_argument("--dial", type=int, choices=[1, 2, 3, 4], help="Which dial (1–4)")
    parser.add_argument("--delta", type=float, help="Signed tick delta from Stream Deck")
    parser.add_argument("--set", type=float, dest="set_value", help="Set absolute value")
    parser.add_argument("--status", action="store_true", help="Print current dial values and exit")
    args = parser.parse_args()

    state = load_state()

    if args.status:
        for d, cfg in DIAL_MAP.items():
            val = state.get(str(d), cfg["default"])
            print(f"Dial {d} ({cfg['name']}): {cfg['display'].format(val)}")
        return

    if args.dial is None:
        parser.error("--dial required (unless --status)")

    dial = args.dial
    cfg = DIAL_MAP[dial]
    current = float(state.get(str(dial), cfg["default"]))

    if args.set_value is not None:
        new_val = args.set_value
    elif args.delta is not None:
        new_val = current + (args.delta * cfg["step"])
    else:
        parser.error("--delta or --set required")

    # Clamp
    new_val = max(cfg["min"], min(cfg["max"], new_val))

    ok = dispatch(dial, new_val, cfg)

    if ok:
        state[str(dial)] = new_val
        save_state(state)
        label = cfg["display"].format(new_val)
        log.info("Dial %d %s → %s", dial, cfg["name"], label)
        notify(f"Dial {dial}: {cfg['name']}", label)
    else:
        log.error("Dispatch failed for dial %d", dial)
        sys.exit(1)


if __name__ == "__main__":
    main()
