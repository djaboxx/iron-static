# VELA Takes — Selection Log

Track which takes were selected for LoRA training.

## Round 1 (pending)

Place 8–10 chosen `.wav` files here before training LoRA `vela_v1`.

- [ ] Generate takes: `python scripts/vela_vocalist.py render --lyrics "..." --batch-size 5`
- [ ] Listen, select best 8
- [ ] Copy selected files to this folder as `take_01.wav` through `take_08.wav`
- [ ] Train in Gradio → LoRA Training tab
- [ ] Copy trained weights to `instruments/vela/lora/vela_v1.safetensors`
- [ ] Update `database/voices.json` → `vela.lora_path` and `vela.lora_name`
