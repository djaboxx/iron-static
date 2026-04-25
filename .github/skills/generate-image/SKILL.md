# Skill: generate-image

Generate cover art and promo images for IRON STATIC using Gemini Imagen 3.
All imagery derives from active song context, brainstorm language, and band aesthetic.

## When to use this skill

- Generating cover art for a song
- Generating social media promo images (square, landscape, portrait)
- Iterating on image prompts to better match the song's conceptual direction
- Documenting a winning image prompt for reuse

## Required Context Files (read before any generation)

| File | Why |
|---|---|
| `knowledge/band-lore/manifesto.md` | Aesthetic constraints — must never be violated |
| `knowledge/band-lore/making-music.md` | Process imagery — what the rig looks like, how patches feel |
| `database/songs.json` | Active song key, scale, BPM, brainstorm path |
| `[brainstorm_path]` from songs.json | The conceptual brief — mine for thematic language |
| `knowledge/references/YYYY-MM-DD.md` (most recent) | Visual reference artists currently in scope |

## The Script

```bash
# Active song, all 3 formats
python scripts/generate_promo_image.py

# Specific song
python scripts/generate_promo_image.py --song <slug>

# With style override (most useful for iteration)
python scripts/generate_promo_image.py --song <slug> --style "<style clause>"

# Dry run — print prompt only
python scripts/generate_promo_image.py --song <slug> --dry-run

# Specific formats
python scripts/generate_promo_image.py --song <slug> --formats square
python scripts/generate_promo_image.py --song <slug> --formats square landscape portrait
```

## Output Paths

```
outputs/social/<song-slug>_cover_square.png      1:1  — Instagram, SoundCloud
outputs/social/<song-slug>_cover_landscape.png   16:9 — YouTube thumbnail
outputs/social/<song-slug>_cover_portrait.png    9:16 — Instagram Reels, TikTok
```

## Fixed Aesthetic Constraints (always in prompt — never override)

```
dark industrial aesthetic, high contrast, no people, no faces,
machine textures, rust and metal, electronic components,
harsh lighting, black background with accent colors,
typographic treatment with band name IRON STATIC in industrial sans-serif font,
photorealistic not illustrated, cinematic composition
```

**Negative prompt** (always active):
```
colorful, bright, cheerful, happy, soft, pastel, nature, animals,
people, faces, hands, cartoon, anime, illustrated, watercolor,
stock photo, cliche music imagery, guitar, DJ equipment, stage lighting
```

## Prompt Construction Pattern

```
Album artwork for '[Title]' by IRON STATIC.
[First non-header line from brainstorm — the conceptual seed].
Musical character: [key] [scale] — heavy, mechanical, abrasive.
[--style clause if provided].
[BASE_STYLE constants].
```

The script does this automatically. Use `--dry-run` to see the full assembled prompt before generating.

## Iteration Strategy

If the first result is too generic:
1. Run `--dry-run` to see what prompt was used
2. Identify the weakest element (usually missing song-specific texture)
3. Add a `--style` clause with one concrete, specific visual element from the brainstorm
4. Regenerate — one change at a time

Example style clauses that work for IRON STATIC:
- `--style "corroded circuit board as interrogation table, single cold fluorescent backlight"`
- `--style "unspooled magnetic tape forming a noose, electrical discharge in background"`
- `--style "oscilloscope trace flatlines against industrial concrete wall"`
- `--style "rusted iron filaments magnetized into standing wave patterns, cobalt accent light"`

## What NOT to generate

- Bright, colorful, or high-saturation images
- Illustrated or painterly styles
- Any human figures, faces, or body parts
- Generic metal imagery (flames, skulls, lightning bolts)
- Stage photography aesthetics
- Anything that could pass for stock imagery

## Documenting a Winning Prompt

Append to `knowledge/sound-design/visual-notes.md`:

```markdown
## [song-slug] — [YYYY-MM-DD]
**Brief**: [one-line conceptual summary]
**Style clause**: `[the --style value]`
**Full prompt** (from --dry-run):
> [paste full prompt]
**Output**: `outputs/social/[slug]_cover_square.png`
```

## Environment

Requires `GEMINI_API_KEY` or `GOOGLE_API_KEY`. Uses `imagen-3.0-generate-002`.
`person_generation` is locked to `dont_allow`.
