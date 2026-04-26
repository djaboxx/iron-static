# Stream Deck + Setup — IRON STATIC

Hardware: Elgato Stream Deck + (8 LCD buttons + 4 dials)

---

## Button Layout

| Button | Script | What it does |
|---|---|---|
| 1 (top-left) | `buttons/01_session_start.sh` | Lists active song + prints top of learnings digest |
| 2 | `buttons/02_git_commit.sh` | `git add -A && git commit` with timestamp message |
| 3 | `buttons/03_ableton_launch.sh` | Launch Ableton or bring it to front |
| 4 | `buttons/04_vela_generate.sh` | Prompt for lyrics → generate VELA vocals via ACE-Step |
| 5 | `buttons/05_run_brainstorm.sh` | Run feed digest + Gemini brainstorm in a Terminal window |
| 6 | `buttons/06_gcs_push.sh` | Push `audio/generated/` to GCS for active song |
| 7 | `buttons/07_transport_toggle.sh` | Play / Stop Ableton transport via Remote Script bridge |
| 8 (top-right) | `buttons/08_health_check.sh` | macOS notification: active song, ACE-Step, bridge, git status |

---

## Dial Layout

| Dial | Parameter | Range | Step | Notes |
|---|---|---|---|---|
| 1 (leftmost) | Ableton BPM | 40–300 | 1 BPM/tick | Calls `bridge_client.py transport_tempo` |
| 2 | Master Volume | 0–127 | 2/tick | Sends `set_master_volume` via bridge |
| 3 | Pigments Macro M1 | 0–127 | 3/tick | CC20 on MIDI ch 8 → IAC bus |
| 4 | Pigments Macro M2 | 0–127 | 3/tick | CC21 on MIDI ch 8 → IAC bus |

Dial state persists in `/tmp/iron-static-dial-state.json` between turns.

---

## Stream Deck App Configuration

### Button actions
In the Stream Deck app, each button uses **System → Open** or **System → Run**:

- Action type: `System: Open`
- App: `Terminal`  
- Command: `/Users/darnold/git/iron-static/streamdeck/buttons/01_session_start.sh`

Or use **System → Run** (runs silently, no Terminal window). Use `Open` for anything that needs visible output (brainstorm, VELA generate). Use `Run` for fire-and-forget (git commit, health check).

### Dial actions
Each dial uses **System → Run** with a command like:

```
python /Users/darnold/git/iron-static/streamdeck/dial_bridge.py --dial 1 --delta {DELTA}
```

Stream Deck + sends `{DELTA}` as a positive or negative integer per encoder tick. In the Stream Deck app's "Encoder" settings:
- **Rotate Right action**: `dial_bridge.py --dial 1 --delta 1`
- **Rotate Left action**: `dial_bridge.py --dial 1 --delta -1`
- **Press action**: `dial_bridge.py --dial 1 --status` (show current values)

For the LCD strip above dials — set it to display the current value by using the "title" field in Stream Deck app as a static label (the script sends macOS notifications for live feedback).

---

## Prerequisites

### IAC Driver (for MIDI CC from dials 3 & 4)
1. Open **Audio MIDI Setup** (`/Applications/Utilities/Audio MIDI Setup.app`)
2. Window → Show MIDI Studio
3. Double-click **IAC Driver** → check "Device is online"
4. In Ableton: Preferences → Link/Tempo/MIDI → enable IAC Bus as MIDI input
5. In Ableton: route MIDI ch 8 to the Pigments track

### IronStatic Remote Script (for BPM dial + transport)
Must be deployed and selected in Live:
```bash
python scripts/deploy_remote_script.py
```
Then: Ableton → Preferences → Link/Tempo/MIDI → Control Surface → IronStatic

### ACE-Step server (for Button 4 — VELA)
```bash
cd ~/tools/ACE-Step-1.5 && nohup ./start_api_server_macos.sh > /tmp/acestep-api.log 2>&1 &
```

### Python PATH for dial scripts
The Stream Deck app runs scripts with minimal environment. Ensure the shebang in button scripts resolves `python` correctly. If dials fail, edit `dial_bridge.py` line 1 to use the explicit path:
```
#!/usr/local/bin/python3
```
or set `PATH` in each script with `export PATH=/usr/local/bin:$PATH`.

---

## Testing

```bash
# Test any button script directly
bash streamdeck/buttons/08_health_check.sh

# Test dial bridge (BPM nudge)
python streamdeck/dial_bridge.py --dial 1 --delta 1
python streamdeck/dial_bridge.py --status

# Test Pigments CC (Ableton must be open with IAC routed)
python streamdeck/dial_bridge.py --dial 3 --set 80
```
