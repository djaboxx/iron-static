# IRON STATIC Visual Identity — Style Reference Collection

This folder holds the canonical seed images used for style-anchored image generation.
When `--use-identity` is passed to `generate_promo_image.py`, up to 3 PNGs from this
directory are loaded as `StyleReferenceImage` inputs to Imagen's `edit_image` API.
The model reads the visual style from these images and applies it to new generations.

## Selection criteria

Images placed here should be **approved IRON STATIC outputs** that represent the
canonical aesthetic: dark, industrial, high-contrast, machine-textured, no people.

A good seed set covers:
- **Palette** — the color temperature and contrast range you want reproduced
- **Texture** — the dominant material feel (rust, circuit, metal, static)
- **Composition** — the spatial structure and density that makes it feel heavy

## Current seeds

| File | Description | Source |
|---|---|---|
| *(add images here)* | | |

## How to add a seed image

1. Copy or symlink the approved PNG here with a descriptive name:
   ```
   cp outputs/social/instrumental-convergence_cover_square.png \
      knowledge/visual-identity/anchor-01-ic-square.png
   ```
2. Update the table above with description and source.
3. Commit it. This collection is version-controlled — any change affects future generations.

## Usage

```bash
# Use all seeds in this directory (up to 3)
python scripts/generate_promo_image.py --use-identity

# Use specific seeds
python scripts/generate_promo_image.py \
  --style-ref knowledge/visual-identity/anchor-01-ic-square.png \
              knowledge/visual-identity/anchor-02-brand-profile.png

# Dry run — see what refs would be loaded without generating
python scripts/generate_promo_image.py --use-identity --dry-run
```

## Notes

- **Limit**: up to 3 style refs per call (Imagen API limit for `edit_image`)
- **Format**: PNG only (JPEG support untested)
- **Model**: `imagen-3.0-capability-001` (style-reference capable model)
- **Fallback**: if no refs, script falls back to standard `generate_images` (text-to-image)
