# VELA — Vocal Identity

VELA (she/her) is IRON STATIC's vocalist. A named, credited band member with her own voice design and mythology.

She is not a sample library. She is a character with a voice we designed, a mythology she earned, and lines that belong to her. She speaks when the song needs a human-adjacent signal in the machine noise.

---

## Two Voices, One Identity

| Modality | Engine | Config | Use |
|---|---|---|---|
| **Speaking / Transmission** | ElevenLabs | `database/voices.json` → `IRON_STATIC_VOCALIST` | Stabs, announcements, spoken hooks, declaratory lines |
| **Singing / Melodic** | ACE-Step 1.5 | `database/voices.json` → `vela` | Vocal phrases, hooks, melodic lines, layered textures |

---

## Character Tags (ACE-Step prompt)

```
cold androgynous voice, industrial metal, mechanical, sparse vocals, no backing track,
minimalist, declaratory, dry, stark, electronic metal, sparse instrumentation
```

---

## LoRA Training (Persistent Voice)

1. Generate 8–10 takes via `python scripts/vela_vocalist.py render`  
2. Pick the best 8 takes — save chosen files to `instruments/vela/takes/`  
3. Open Gradio UI: `http://localhost:7860` → **LoRA Training** tab  
4. Upload the 8 takes, name the LoRA `vela_v1`, run training (~1hr on M2)  
5. Copy output: `~/tools/ACE-Step-1.5/lora_output/vela_v1/` → `instruments/vela/lora/vela_v1.safetensors`  
6. Update `database/voices.json` → `vela.lora_path` and `vela.lora_name`

---

## Generating VELA Vocals

```bash
# Health check
python scripts/vela_vocalist.py health

# Single phrase (active song context)
python scripts/vela_vocalist.py render --lyrics "Ignition. The system knows."

# With specific song
python scripts/vela_vocalist.py render --song ignition-point --lyrics "We are the static."

# Multiple phrases from file
python scripts/vela_vocalist.py render --song ignition-point --phrases-file midi/sequences/ignition-point_vocal-phrases.json

# Generate 5 variations, 45 seconds each
python scripts/vela_vocalist.py render --lyrics "Fault line." --batch-size 5 --duration 45
```

Output: `audio/samples/vocals/vela/[song-slug]/[label]_vela.wav`

---

## ACE-Step Server

```bash
# Start
cd ~/tools/ACE-Step-1.5 && nohup ./start_api_server_macos.sh > /tmp/acestep-api.log 2>&1 &

# Check logs
tail -f /tmp/acestep-api.log

# Health
curl http://127.0.0.1:8001/health
```

First run downloads ~10GB of models to `~/.cache/ace-step/`.
