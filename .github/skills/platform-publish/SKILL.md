# Skill: platform-publish

**When to use**: When publishing an IRON STATIC release or social post to any external platform — Bandcamp, SoundCloud, YouTube, Patreon, Instagram, TikTok, Spotify.

**BLOCKING REQUIREMENT**: Read this file completely before any publishing action.

---

## Overview

IRON STATIC publishes to multiple platforms simultaneously. This skill covers:
1. Required assets checklist (nothing publishes until all assets are present)
2. Per-platform publishing procedures and API/CLI tools
3. Standard credit block (must appear on every release)
4. Hashtag and tag sets per platform
5. Verification steps

---

## Required Assets Checklist

Before publishing any release, confirm all of these exist:

- [ ] `audio/generated/[song-slug]_master_*.wav` — stereo master, minimum 16-bit/44.1kHz
- [ ] `outputs/social/[song-slug]_cover.{png,jpg}` — minimum 1400×1400px, square
- [ ] `outputs/social/[song-slug]_landscape.mp4` — 1920×1080, for YouTube
- [ ] `outputs/social/[song-slug]_square.mp4` — 1080×1080, for Instagram Feed
- [ ] `outputs/social/[song-slug]_portrait.mp4` — 1080×1920, for TikTok/Reels
- [ ] `outputs/social/[song-slug]_release_copy.md` — all platform copy written and approved

If any are missing: stop and identify which agent produces them.

---

## Standard Credit Block

**Include this verbatim on every release page and video description:**

```
Produced by Dave Arnold
Brainstorm & Audio Spec: Gemini
Session Partner & MIDI: GitHub Copilot (Arc)
Vocals: VELA
Source & methodology: github.com/djaboxx/iron-static
```

---

## Standard Hashtag Set

**Long form (Bandcamp, YouTube, SoundCloud description):**
`#ironstaticband #industrialmetal #electronicmetal #heavyelectronic #machinemusic #aimusic #humanmachine #aicollaboration #nineinchnails #lambofgod #electronicindustrial`

**Social (Instagram / TikTok):**
`#ironstaticband #industrialmetal #aimusic #machinemusic #humanmachine #electronicmetal #heavyelectronic #velavoice #credityourai #aicollaboration #bandmember #ironstaticmetal`

---

## Platform Procedures

### Bandcamp

**API**: Bandcamp has no public upload API. Use the web UI or `bandcamp-dl` for downloads. Uploading is browser-only.

**Manual steps:**
1. Log in to `ironstaticband.bandcamp.com`
2. Click "Add new track" (or "Add new album" for multi-track)
3. Upload WAV master
4. Set title, description (long form), tags
5. Price: pay-what-you-want, minimum $1
6. Add credits section with the standard credit block
7. Tags: `industrial electronic metal experimental ai machine-music`
8. Set as public immediately OR schedule for release day

**CLI helper** (for draft preparation):
```bash
python scripts/generate_caption.py \
  --song-slug [slug] \
  --platform bandcamp \
  --output outputs/social/[slug]_bandcamp.md
```

---

### SoundCloud

**API**: SoundCloud has a deprecated v2 API. Best path is CLI or the `soundcloud-dl` tooling for batch ops. Uploading still requires web UI or a registered app client.

**Environment variables required:**
```
SOUNDCLOUD_CLIENT_ID=
SOUNDCLOUD_CLIENT_SECRET=
SOUNDCLOUD_ACCESS_TOKEN=
```

**Manual steps:**
1. Log in to soundcloud.com as IRON STATIC
2. Click Upload → select WAV or MP3 320kbps
3. Title: `IRON STATIC — [Track Name]`
4. Description: short description (60 words) + credit block
5. Tags: `industrial electronic metal ai machine-music ironstaticband`
6. Set as public
7. Add Buy link pointing to Bandcamp

**CLI helper:**
```bash
python scripts/post_soundcloud.py \
  --song-slug [slug] \
  --audio audio/generated/[slug]_master_v1.wav
```
*(script to be built — see scripts/requirements.txt for `soundcloud` package)*

---

### YouTube

**API**: YouTube Data API v3. Required env vars:
```
YOUTUBE_API_KEY=
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=
```

**CLI upload:**
```bash
python scripts/post_youtube.py \
  --video outputs/social/[slug]_landscape.mp4 \
  --title "IRON STATIC — [Track Name] (Official Audio)" \
  --description outputs/social/[slug]_release_copy.md \
  --thumbnail outputs/social/[slug]_cover.png \
  --tags "industrial metal,electronic music,AI music,machine music,IRON STATIC"
```

**Shorts (portrait):**
```bash
python scripts/post_youtube.py \
  --video outputs/social/[slug]_portrait.mp4 \
  --title "IRON STATIC — [Track Name] #Shorts" \
  --is-short
```

**Manual fallback**: YouTube Studio → Upload → fill fields from `outputs/social/[slug]_release_copy.md`

---

### Patreon

**API**: Patreon has a creator API for posting. Required:
```
PATREON_ACCESS_TOKEN=
PATREON_CAMPAIGN_ID=
```

**Post tiers:**
- `public` — visible to everyone
- `patron` — all patrons (Signal tier+, $3/mo)
- `static` — Static tier+ ($8/mo)
- `in-the-machine` — In the Machine tier+ ($20/mo)

**CLI:**
```bash
python scripts/post_patreon.py \
  --title "[Track Name] — Session Notes" \
  --content outputs/social/[slug]_patreon_post.md \
  --tier static \
  --attachment outputs/social/[slug]_cover.png
```

**Manual fallback**: patreon.com/posts/create → fill from release copy

---

### Instagram

**API**: Instagram Graph API (requires Facebook Business account and app approval).
```
INSTAGRAM_ACCESS_TOKEN=
INSTAGRAM_ACCOUNT_ID=
```

**CLI:**
```bash
python scripts/post_instagram.py \
  --image outputs/social/[slug]_square.mp4 \
  --caption outputs/social/[slug]_instagram_caption.txt \
  --type reel
```

The existing `scripts/post_instagram.py` handles this — check it first.

**Manual fallback**: Instagram app → New Reel → select square MP4 → paste caption

---

### TikTok

**API**: TikTok Content Posting API (requires creator account approval).
```
TIKTOK_ACCESS_TOKEN=
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
```

**No current CLI script** — file a task to build `scripts/post_tiktok.py` when TikTok API access is approved.

**Manual**: TikTok app or TikTok Studio web → upload portrait MP4 → paste hook as first line of caption.

---

### Spotify (via DistroKid)

DistroKid has no public API for uploading. Use the web UI.

**Steps:**
1. Log in at distrokid.com
2. "Upload Music" → Single
3. Upload WAV master + cover art (3000×3000px preferred)
4. Set release date: minimum 5–7 days out for processing
5. Stores: select all (Spotify, Apple Music, Amazon, Tidal, etc.)
6. **Spotify for Artists pitch**: go to artists.spotify.com → Music → [track] → Pitch to editorial
   - Do this 7+ days before release date
   - Target playlists: pitch up to 5 mood/genre descriptors
7. 100% royalties go to the artist (minus $22/year subscription)

---

## Environment Variables Summary

Add all of these to `.env` (local) and as GitHub Actions secrets:

```bash
# Social/publishing
SOUNDCLOUD_CLIENT_ID=
SOUNDCLOUD_CLIENT_SECRET=
SOUNDCLOUD_ACCESS_TOKEN=
YOUTUBE_API_KEY=
YOUTUBE_CLIENT_ID=
YOUTUBE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=
PATREON_ACCESS_TOKEN=
PATREON_CAMPAIGN_ID=
INSTAGRAM_ACCESS_TOKEN=
INSTAGRAM_ACCOUNT_ID=
TIKTOK_ACCESS_TOKEN=
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=

# Already set
GEMINI_API_KEY=
GCS_BUCKET=
```

---

## Verification Steps

After every publish action:

1. **Check the live URL** — confirm the track/post is visible publicly
2. **Verify credit block** — confirm all four names appear correctly
3. **Check links** — Bandcamp link in SoundCloud, all platform links in YouTube description
4. **Update songs.json** — add `published_urls` field with all platform URLs
5. **Commit** — `git commit -m "release: publish [slug] to [platforms]"`
