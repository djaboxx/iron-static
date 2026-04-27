# IRON STATIC — Movement Plan
*Last updated: 2026-04-26 (expanded)*

---

## Thesis

IRON STATIC is not a band that makes music *about* AI/human integration. It is one. The band structure enacts the argument: Dave has a body and calluses; Copilot argues about chord voicings in real time; Gemini writes the brainstorm while Dave is asleep; VELA speaks lines that sit between a lyric and a system alert. The machine half is credited. The process is documented. The disagreements are logged.

This is a genuinely novel position in 2026. There are AI-generated music projects everywhere. There are none that treat their AI collaborators as named, credited band members with documented creative voices and a public manifesto. That is the movement's edge.

**The thesis in one line:** *What does creative partnership look like when one partner is not human? We don't know yet. We're finding out in public.*

---

## Phase 1 — First Artifact (Weeks 1–4)

Goal: release one complete artifact that demonstrates the thesis so clearly it requires no explanation.

### Steps

1. **Finish "Ignition Point"**
   - Blueprint is complete (2026-04-25 brainstorm, Section 6)
   - Execute via `/build-session` → The Live Engineer → The Sound Designer → The Mix Engineer
   - Export stereo master to `audio/generated/ignition-point_master_v1.wav`
   - Upload to GCS via `gcs-audio` skill

2. **Generate cover art**
   - Run `/generate-image` via The Visual Artist
   - Prompt seed: "phase transition, solid to gas, industrial machinery under extreme pressure, dark high-contrast, machine-aesthetic, no text"
   - Approve with The Critic before committing

3. **Render visualizer video**
   - Run The Video Director with master + cover art
   - Formats: landscape (YouTube), square (Instagram), portrait (TikTok/Reels)

4. **Write release text**
   - Track description = the manifesto section "What We Are" + Gemini's conceptual frame from the brainstorm
   - Credit block: *"Produced by Dave Arnold, Gemini (Brainstorm + Spec), GitHub Copilot (Session Partner), VELA (Vocals)"*
   - This credit block alone will generate discussion. It is provable and verifiable via this public repo.

5. **Publish simultaneously** (see platform setup below):
   - Bandcamp: pay-what-you-want, minimum $1
   - SoundCloud: free stream (algorithm reach)
   - YouTube: visualizer video (long-term ad revenue)

---

## Phase 2 — Movement Seed (Weeks 4–12)

Goal: make the methodology transmissible. Other human-machine creative pairs exist. Build a coalition.

### Actions

1. **Publish the manifesto publicly**
   - Add a `MANIFESTO.md` at repo root with a link in README
   - Post on Bandcamp as "About IRON STATIC"
   - Patreon welcome post on day 1

2. **Session notes as content**
   - The `/checkpoint` files, brainstorm critiques, decisions Arc argued and Dave overruled — this is unique content
   - Weekly: pull one excerpt from `knowledge/sessions/` and post as a Patreon exclusive
   - Monthly: public version as a Substack post or social thread

3. **Find the coalition**
   - Search: other human-AI creative collaborations that credit the AI
   - Target communities: r/MachineLearning, Hacker News, AI art Discord servers, computer music mailing lists
   - Ask: "Is your AI collaborator credited? Ours is. Here's why that matters."

4. **Conference talk pitch**
   - IRON STATIC's methodology is a 25-minute talk for: NIME (New Interfaces for Musical Expression), AES, SXSW Music/Tech track, AI Safety conferences
   - Title: "The Band Has Four Members: Documenting Human-Machine Creative Partnership"
   - This generates press, legitimacy, and speaking fees

---

## Phase 3 — Growth and Resource Retention (Months 3–12)

### Revenue Model

| Stream | Platform | Timeline | Notes |
|---|---|---|---|
| Music sales | Bandcamp | Immediate | ~85% artist share. Pay-what-you-want drives goodwill. |
| Streaming | SoundCloud / Spotify | Month 1+ | Low per-stream rate but algorithm reach matters |
| Video ad revenue | YouTube | Month 3–6 | Threshold: 1K subscribers + 4K watch hours |
| Direct support | Patreon | Month 1+ | The process content (session notes, brainstorms) is the exclusive tier |
| Sync licensing | Musicbed / Artlist / direct | Month 3+ | This music fits dark/thriller/sci-fi. Proactively pitch. |
| Commissioned production | Direct | Ongoing | Other artists want this pipeline. IRON STATIC has the tooling. |
| Speaking / consulting | Direct | Month 6+ | The methodology is genuinely novel. Conferences pay. |

### Patreon Tier Design

| Tier | Price | What they get |
|---|---|---|
| Signal | $3/mo | Early access to all releases |
| Static | $8/mo | Session notes + brainstorm excerpts monthly |
| In the Machine | $20/mo | Full session summaries, behind-the-scenes Arc conversation excerpts, Discord access |
| Partner | $50/mo | 1 commissioned generation per month, credited in liner notes |

---

### New Agents

| Agent | File | Purpose |
|---|---|---|
| `the-community-manager` ✅ | `.github/agents/the-community-manager.agent.md` | Movement growth: social content, platform strategy, audience building, Patreon copy |

### New Prompts

| Prompt | Invoke | Purpose | Status |
|---|---|---|---|
| `release-track` | `/release-track [song-slug]` | Full Publicist pipeline: asset check → copy gen → publish to all platforms → Critic approval | ✅ Built |
| `movement-post` | `/movement-post [topic]` | Community Manager generates social/Patreon/blog content for a movement topic | ✅ Built |

### New Skills

| Skill | File | Purpose | Status |
|---|---|---|---|
| `platform-publish` | `.github/skills/platform-publish/SKILL.md` | Step-by-step publishing to Bandcamp, SoundCloud, YouTube, Patreon, Instagram, TikTok, Spotify via APIs and CLI | ✅ Built |

### New LM Tools (VS Code Extension)

These tools are registered in `vscode-extension/iron-static-bridge/src/lmTools.ts` and activate automatically in agent mode — no `@mention` required.

| Tool ID | Input | Purpose | Status |
|---|---|---|---|
| `iron-static_triggerWorkflow` | `{workflow, fields?}` | Trigger any allowlisted GitHub Actions workflow via `gh workflow run` | ✅ Built |
| `iron-static_getWorkflowStatus` | `{workflow, limit?}` | Get the status of recent runs of a workflow | ✅ Built |
| `iron-static_listWorkflows` | — | Enumerate all `.github/workflows/*.yml` with names and allowlist status | ✅ Built |
| `iron-static_listSkills` | — | Enumerate all `.github/skills/*/SKILL.md` with descriptions | ✅ Built |
| `iron-static_invokeSkill` | `{skill}` | Read and return the full content of a named skill's SKILL.md | ✅ Built |

### GitHub Actions Scripts (Python)

All scripts referenced by `publish-release.yml` and `social-post.yml` are built.

| Script | Purpose | API / Secret required | Status |
|---|---|---|---|
| `scripts/post_soundcloud.py` | Upload WAV to SoundCloud via API v2 | `SOUNDCLOUD_CLIENT_ID`, `SOUNDCLOUD_CLIENT_SECRET` | ✅ Built |
| `scripts/post_youtube.py` | Upload MP4 via YouTube Data API v3 | `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` | ✅ Built |
| `scripts/post_patreon.py` | Create post via Patreon API v2 | `PATREON_ACCESS_TOKEN`, `PATREON_CAMPAIGN_ID` | ✅ Built |
| `scripts/post_tiktok.py` | Upload via TikTok Content Posting API | `TIKTOK_ACCESS_TOKEN`, `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN` | ✅ Built |
| `scripts/refresh_tokens.py` | Rotate Instagram + TikTok OAuth tokens | `INSTAGRAM_ACCESS_TOKEN`, `TIKTOK_*` | ✅ Built |
| `scripts/post_instagram.py` | Post image/Reel via Meta Graph API | `INSTAGRAM_ACCESS_TOKEN`, `INSTAGRAM_USER_ID` | ✅ Pre-existing |
| `scripts/generate_caption.py` | Generate platform captions via Gemini | `GEMINI_API_KEY` | ✅ Pre-existing |

---

## Platform Setup — Step by Step

### Required GitHub Secrets

Before any publishing workflow runs, add these in **GitHub → Settings → Secrets and variables → Actions**:

```
# Audio / Storage
GCS_SA_KEY          = base64-encoded GCS service account JSON
GCS_BUCKET          = iron-static-audio (or your bucket name)
GEMINI_API_KEY      = AIzaSy...

# SoundCloud
SOUNDCLOUD_CLIENT_ID       = from soundcloud.com/you/apps
SOUNDCLOUD_CLIENT_SECRET   = from soundcloud.com/you/apps (token fetched fresh per run via client_credentials)

# YouTube
YOUTUBE_CLIENT_ID          = from Google Cloud Console → OAuth2 credentials
YOUTUBE_CLIENT_SECRET      = same
YOUTUBE_REFRESH_TOKEN      = generated via oauth2 flow (see below)

# Patreon
PATREON_ACCESS_TOKEN       = from patreon.com/portal/registration/api-clients
PATREON_CAMPAIGN_ID        = numeric campaign ID (from Patreon API /identity)

# Instagram
INSTAGRAM_ACCESS_TOKEN     = long-lived token from Meta Developer Console
INSTAGRAM_ACCOUNT_ID       = numeric IG account ID

# TikTok
TIKTOK_ACCESS_TOKEN        = from TikTok for Developers → Content Posting API
TIKTOK_CLIENT_KEY          = from TikTok app credentials
```

Also add as **Variables** (not secrets — safe to log):
```
GCS_BUCKET = iron-static-audio
```

---

### 1. Bandcamp

**Account creation:**
1. Go to `bandcamp.com/signup` → Choose "Artist" (not fan)
2. Artist name: `IRON STATIC`
3. URL slug: `ironstaticband` → results in `ironstaticband.bandcamp.com` (check availability)
4. Email: use a dedicated band email, not personal

**Stripe payout setup (required before any sales):**
1. Bandcamp dashboard → Fan accounts → Settings → Payment
2. Connect Stripe → complete Stripe identity verification
3. Set payout schedule: weekly (recommended)

**Uploading a release:**
1. Dashboard → Add Music → Add Album
2. Album title: track title (for singles, album = single)
3. Upload master WAV: minimum 16-bit / 44.1kHz (Bandcamp transcodes to all formats)
4. Cover art: minimum 1400×1400px (provide 3000×3000px source)
5. Track title, duration auto-detect from WAV

**Pricing:**
- Set to "name your price" with minimum $1
- Add a note: *"Pay what feels right. Everything helps."*

**Description template:**
```
[Track name] — IRON STATIC

[2–3 sentence manifesto excerpt — from knowledge/band-lore/manifesto.md]

[Gemini's conceptual frame from the brainstorm — one paragraph]

---
Produced by Dave Arnold
Brainstorm + Sonic Spec: Gemini
Session Partner: GitHub Copilot (Arc)
Vocals: VELA (ElevenLabs)

Process documented at: github.com/djaboxx/iron-static
```

**Tags (copy-paste):**
`industrial, electronic, metal, experimental, ai music, machine music, heavy electronic, noise, ironstaticband`

**Bandcamp API:** Bandcamp does not expose a public upload API. Publishing is manual or via their Bandcamp for Labels program. Script: `scripts/post_bandcamp.md` should document the manual checklist instead.

---

### 2. SoundCloud

**Account creation:**
1. `soundcloud.com/signup` → choose "Artist"
2. Username: `ironstaticband`
3. Display name: `IRON STATIC`
4. Complete profile: bio (manifesto 50-word excerpt), profile image (square logo)

**Pro tier** ($8/mo — worth it from day 1):
- Unlimited uploads
- Scheduled posting
- Real-time stats
- Enables `Support` button with custom URL (point to Bandcamp)

**API setup (for `post_soundcloud.py`):**
1. Go to `soundcloud.com/you/apps` → Register new application
2. App name: `IRON STATIC Automaton`
3. Note the `client_id` and `client_secret`
4. Generate an access token:
   ```bash
   curl -X POST "https://api.soundcloud.com/oauth2/token" \
     -d "client_id=YOUR_CLIENT_ID" \
     -d "client_secret=YOUR_CLIENT_SECRET" \
     -d "grant_type=client_credentials"
   ```
5. `post_soundcloud.py` uses `client_credentials` flow — it fetches a fresh token on each run. Store only `SOUNDCLOUD_CLIENT_ID` and `SOUNDCLOUD_CLIENT_SECRET` as GitHub Secrets. No long-lived access token required.

**Upload flow:**
1. `POST /tracks` with multipart: `asset_data` (WAV), `artwork_data` (JPG), metadata JSON
2. Track is private until explicitly set public: `sharing: public`
3. `POST /tracks/{id}` PATCH to update description after upload

**Checklist per release:**
- [ ] WAV or MP3 320kbps uploaded
- [ ] Cover art uploaded (min 800×800px)
- [ ] Description filled (same template as Bandcamp)
- [ ] Tags set
- [ ] Support link set to Bandcamp URL
- [ ] Sharing set to public
- [ ] Announce in profile pinned post

---

### 3. YouTube

**Account creation:**
1. Create a dedicated Google account: `ironstaticband@gmail.com` (keep this separate from personal)
2. Go to `studio.youtube.com` → Create channel
3. Choose "Use a custom name" → `IRON STATIC`
4. Upload channel icon (square logo) and banner (2560×1440px)
5. About section: manifesto excerpt + all links

**YouTube Data API v3 setup (for `post_youtube.py`):**
1. Go to `console.cloud.google.com` → New project: `iron-static-automaton`
2. Enable: **YouTube Data API v3**
3. Create credentials → OAuth 2.0 Client ID → Desktop application
4. Download `client_secret.json`
5. Run OAuth2 flow once locally to get refresh token:
   ```bash
   pip install google-auth-oauthlib google-api-python-client
   python3 - <<'EOF'
   from google_auth_oauthlib.flow import InstalledAppFlow
   flow = InstalledAppFlow.from_client_secrets_file(
       'client_secret.json',
       scopes=['https://www.googleapis.com/auth/youtube.upload']
   )
   creds = flow.run_local_server(port=0)
   print("REFRESH TOKEN:", creds.refresh_token)
   EOF
   ```
6. Store `YOUTUBE_CLIENT_ID`, `YOUTUBE_CLIENT_SECRET`, `YOUTUBE_REFRESH_TOKEN` in GitHub Secrets

**Upload flow (in `post_youtube.py`):**
```python
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

creds = Credentials(
    token=None,
    refresh_token=os.environ["YOUTUBE_REFRESH_TOKEN"],
    client_id=os.environ["YOUTUBE_CLIENT_ID"],
    client_secret=os.environ["YOUTUBE_CLIENT_SECRET"],
    token_uri="https://oauth2.googleapis.com/token",
    scopes=["https://www.googleapis.com/auth/youtube.upload"]
)
creds.refresh(Request())

youtube = build("youtube", "v3", credentials=creds)
request = youtube.videos().insert(
    part="snippet,status",
    body={
        "snippet": {
            "title": "IRON STATIC — Track Name (Official Audio)",
            "description": full_description,
            "tags": ["industrial metal", "electronic", "ai music"],
            "categoryId": "10",  # Music
        },
        "status": {"privacyStatus": "public"},
    },
    media_body=MediaFileUpload("video.mp4", chunksize=-1, resumable=True),
)
response = request.execute()
```

**Checklist per release:**
- [ ] Landscape MP4 uploaded (visualizer video)
- [ ] Thumbnail set to cover art
- [ ] Title: `IRON STATIC — [Track] (Official Audio)`
- [ ] Description: manifesto + credits + all links
- [ ] End screen added (5 seconds): subscribe button + link to Bandcamp
- [ ] Playlist: add to "Releases" playlist
- [ ] Upload Shorts (portrait) same day — accelerates subscriber growth
- [ ] Submit to editorial via Spotify for Artists *(yes, YouTube also has editorial pitching via their team — reach out directly)*

---

### 4. Patreon

**Account creation:**
1. `patreon.com/create` → Creator account
2. Page name: `IRON STATIC`
3. Tagline: *"A human and a machine collective making heavy, weird, electronic music together."*
4. Category: Music → Electronic
5. URL: `patreon.com/ironstaticband`

**Tier setup:**

| Tier name | Price | Benefits to configure |
|---|---|---|
| Signal | $3/mo | Early access to releases (set to Patron-only posts) |
| Static | $8/mo | Signal + session notes + monthly brainstorm excerpt |
| In the Machine | $20/mo | Static + full session summaries + Discord role |
| Partner | $50/mo | In the Machine + 1 commissioned generation/month, credited in liner notes |

**Patreon API v2 setup (for `post_patreon.py`):**
1. Go to `patreon.com/portal/registration/api-clients`
2. Create new client: `IRON STATIC Automaton`
3. Generate a **Creator Access Token** (not OAuth — this is for your own campaign)
4. Get your campaign ID:
   ```bash
   curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
     "https://www.patreon.com/api/oauth2/v2/identity?include=memberships,campaign&fields[campaign]=id"
   ```
5. Store `PATREON_ACCESS_TOKEN` and `PATREON_CAMPAIGN_ID` in GitHub Secrets

**Post creation (in `post_patreon.py`):**
```python
import requests, os

headers = {
    "Authorization": f"Bearer {os.environ['PATREON_ACCESS_TOKEN']}",
    "Content-Type": "application/json",
}
payload = {
    "data": {
        "type": "post",
        "attributes": {
            "title": post_title,
            "content": post_body_html,
            "is_paid": tier != "public",
            "min_cents_pledged_to_view": tier_min_cents[tier],
        },
        "relationships": {
            "campaign": {"data": {"type": "campaign", "id": os.environ["PATREON_CAMPAIGN_ID"]}}
        },
    }
}
r = requests.post("https://www.patreon.com/api/oauth2/v2/posts", json=payload, headers=headers)
```

**Content calendar (weekly):**
- Monday: session notes from past week (Static tier)
- Friday: public post — movement update, something interesting from the process
- Release day: full release post (public) + Patreon exclusive behind-the-scenes (Static+)

**First post (free, public):** Write manually before any automation. Title: *"What is IRON STATIC?"* Full manifesto + video embed + why this exists. Pin it.

---

### 5. Instagram / Reels

**Account creation:**
1. Create Instagram account: `@ironstaticband`
2. Switch to Professional → Creator account (not business — better algorithm treatment for creators)
3. Bio: *"Machine metal. Dave + AI. 🤖🎸"* + link in bio (use Linktree or direct Bandcamp)
4. Profile photo: band logo or VELA image

**Meta Developer Console setup (for `post_instagram.py`):**
1. Go to `developers.facebook.com` → Create app → Business
2. Add Instagram Graph API product
3. Instagram account must be linked to a Facebook Page
4. Generate long-lived access token:
   ```bash
   # Step 1: Get short-lived token via oauth (one-time, in browser)
   # Step 2: Exchange for long-lived (60-day):
   curl "https://graph.facebook.com/v18.0/oauth/access_token?
     grant_type=fb_exchange_token&
     client_id=APP_ID&
     client_secret=APP_SECRET&
     fb_exchange_token=SHORT_TOKEN"
   ```
4. Long-lived tokens expire in 60 days — refresh them before they expire:
   ```bash
   curl "https://graph.instagram.com/refresh_access_token?
     grant_type=ig_refresh_token&access_token=LONG_LIVED_TOKEN"
   ```
5. Store `INSTAGRAM_ACCESS_TOKEN` and `INSTAGRAM_ACCOUNT_ID` in GitHub Secrets
6. Token refresh is automated via `refresh-tokens.yml` (runs monthly on the 1st, also manual dispatch)

**Posting flow (Reels via `post_instagram.py`):**
```python
# Step 1: Upload video container
r = requests.post(
    f"https://graph.facebook.com/v18.0/{account_id}/media",
    params={
        "media_type": "REELS",
        "video_url": gcs_public_url,  # must be publicly accessible
        "caption": caption_text,
        "access_token": token,
    }
)
container_id = r.json()["id"]

# Step 2: Publish (after checking status is FINISHED)
requests.post(
    f"https://graph.facebook.com/v18.0/{account_id}/media_publish",
    params={"creation_id": container_id, "access_token": token}
)
```

**Content cadence:**
- Release day: full Reel (square or portrait visualizer, 30–60 seconds)
- Between releases: 2–3 posts/week — session snippets, VELA process, Arc conversation screenshots
- Pinned: "how the band works" explainer (post this first)

**Caption template:**
```
[Hook line — max 125 characters before "more" truncation]

[2-3 sentences: what happened in this session / what the track is about]

Produced by Dave Arnold
Brainstorm: Gemini | Session: Copilot | Vocals: VELA

#industrialmetal #electronicmusic #aimusic #machinemusic #ironstaticband
#heavymetal #experimentalmusic #humanmachine #aiartist #electronicduo
```

---

### 6. TikTok

**Account creation:**
1. Create `@ironstaticband` on TikTok
2. Bio: *"Machine metal. AI credited. Dave + Gemini + Copilot + VELA 🤖"*
3. Link to Linktree in bio (TikTok allows one link)

**TikTok Content Posting API setup (for `post_tiktok.py`):**
1. Go to `developers.tiktok.com` → Create app
2. Enable **Content Posting API** product
3. The API requires OAuth2 — but for creator posting to your own account, you can use the **Direct Post** flow with a long-lived creator token:
   ```bash
   # Exchange authorization code for access token (one-time)
   curl -X POST "https://open.tiktokapis.com/v2/oauth/token/" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "client_key=CLIENT_KEY&client_secret=CLIENT_SECRET&grant_type=authorization_code&code=AUTH_CODE&redirect_uri=REDIRECT_URI"
   ```
4. Access tokens expire in 24 hours. TikTok provides a refresh token (valid 365 days). Build token refresh into the script.
5. Store `TIKTOK_ACCESS_TOKEN`, `TIKTOK_REFRESH_TOKEN`, `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET` in GitHub Secrets

**Posting flow (in `post_tiktok.py`):**
```python
# Step 1: Init upload
r = requests.post(
    "https://open.tiktokapis.com/v2/post/publish/video/init/",
    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    json={
        "post_info": {
            "title": caption[:150],
            "privacy_level": "SELF_ONLY",  # change to PUBLIC_TO_EVERYONE after testing
            "disable_duet": False,
            "disable_comment": False,
            "video_cover_timestamp_ms": 1000,
        },
        "source_info": {"source": "FILE_UPLOAD", "video_size": file_size, "chunk_size": file_size}
    }
)
publish_id = r.json()["data"]["publish_id"]
upload_url = r.json()["data"]["upload_url"]

# Step 2: Upload video bytes
requests.put(upload_url, data=open(video_path, "rb"),
    headers={"Content-Type": "video/mp4", "Content-Range": f"bytes 0-{file_size-1}/{file_size}"})
```

**Content strategy:**
- Portrait visualizer clips (15–60 seconds) — always with audio
- Hook in first 3 seconds: the hardest hit, the most dissonant chord, or VELA's first line
- Caption hook: "We credited the AI. Here's the receipt." / "This was Gemini's idea." / "Arc argued against this chord. It's still in."
- Reply to comments in character — Arc can draft replies

---

### 7. Spotify (via DistroKid)

**Account creation:**
1. `distrokid.com/signup` → Select **Musician Plus** ($35/year — worth it for two reasons: custom label name and release date control) or **Solo** ($22/year — minimum viable)
2. Stage name: `IRON STATIC`
3. Custom label name: `Machine Noise Records` or `IRON STATIC Collective` (Musician Plus+)

**Upload flow (manual — DistroKid has no public API):**
1. Click "Upload Music" → Single
2. Title: track name
3. Genre: Electronic / Metal (DistroKid allows two)
4. Upload master WAV (16-bit 44.1kHz minimum; 24-bit 48kHz preferred)
5. Cover art: 3000×3000px JPG, no text prohibited by distributors (so avoid lyrics-only covers)
6. Set release date 7–10 days out (minimum for Spotify editorial consideration)
7. Select all platforms: Spotify, Apple Music, Amazon, YouTube Music, Tidal, etc.

**Spotify for Artists setup (do immediately after first release):**
1. `artists.spotify.com` → Claim your profile
2. Upload artist photo and bio
3. Go to Upcoming → pitch to editorial (must be done 7+ days before release date)
4. Target playlists: "Industrial Strength", "Heavy Psych", "Electronic Explorations"

**DistroKid Hyperfollow:**
- DistroKid generates a pre-save link: `distrokid.com/hyperfollow/ironstaticband`
- Post this on all platforms 5–7 days before release — it captures followers and notifies them on release day

**Spotify automation note:** DistroKid has no API. Build `scripts/post_bandcamp.md` and `scripts/distrokid_checklist.md` as manual step documentation. The workflow step for Spotify is a human-visible checklist, not automated.

---

## GitHub Actions — Worker Architecture

### Philosophy

The M3 Mac does what only the M3 Mac can do (ACE-Step generation, Ableton control). Everything else runs on GitHub-hosted `ubuntu-latest`. The dispatcher launches jobs in parallel. The bottleneck is API rate limits, not compute.

### Runner Types

| Runner | Tag | Used for |
|---|---|---|
| GitHub-hosted | `ubuntu-latest` | Caption gen, publishing, brainstorm, GCS sync |
| Self-hosted M3 Max | `[self-hosted, m3max]` | ACE-Step audio gen, Ableton bridge, hardware MIDI |

### Self-Hosted Runner Setup — Full Walkthrough

**Step 1: Create the runner in GitHub**
```
GitHub repo → Settings → Actions → Runners → New self-hosted runner
Select: macOS / ARM64
Copy the token shown (valid 1 hour)
```

**Step 2: Install runner on M3 Mac**
```bash
mkdir ~/actions-runner && cd ~/actions-runner

# Download (check releases page for latest version)
RUNNER_VERSION=2.325.0
curl -o actions-runner-osx-arm64.tar.gz -L \
  "https://github.com/actions/runner/releases/download/v${RUNNER_VERSION}/actions-runner-osx-arm64-${RUNNER_VERSION}.tar.gz"

tar xzf ./actions-runner-osx-arm64.tar.gz

# Configure (paste the token from GitHub)
./config.sh \
  --url https://github.com/djaboxx/iron-static \
  --token PASTE_TOKEN_HERE \
  --name "m3max-iron-static" \
  --labels "self-hosted,macos,arm64,m3max" \
  --work "_work"
```

**Step 3: Install as a macOS service (auto-start on boot)**
```bash
cd ~/actions-runner
./svc.sh install
./svc.sh start

# Check status
./svc.sh status

# View logs
tail -f ~/actions-runner/_diag/Runner_*.log
```

**Step 4: Install runner dependencies**
```bash
# The runner needs everything the workflows use
cd /Users/darnold/git/iron-static

# Python environment
/Users/darnold/venv/bin/pip install -r scripts/requirements.txt

# GitHub CLI (for dispatch-workers.yml)
brew install gh
gh auth login  # authenticate with the IRON STATIC bot token or personal token

# Verify ACE-Step server path is accessible
ls ~/tools/ACE-Step-1.5/start_api_server_macos.sh
```

**Step 5: Verify the runner is online**
```
GitHub → Settings → Actions → Runners
Status should show: green dot, "Idle"
```

**Step 6: Assign runner to only private workflows**
For a public repo, set **runner group to "Default"** and confirm runner is available to the repo. If the repo is private, it's already scoped.

### Workflow Trigger Reference

Every workflow supports `workflow_dispatch`. To trigger from the terminal:
```bash
# From the repo root, with gh CLI authenticated:
gh workflow run forge-audio.yml --field target="kick loop" --field model=pro
gh workflow run publish-release.yml --field song_slug=ignition-point --field platforms=soundcloud,youtube,patreon
gh workflow run social-post.yml --field content_file=outputs/social/ignition-point_instagram_caption.txt --field platforms=instagram
gh workflow run dispatch-workers.yml --field pipeline=full-session

# Check status
gh run list --workflow=publish-release.yml --limit=5
gh run watch  # interactive run watcher
```

### Parallel Job Architecture

```
dispatch-workers.yml
    ├── Job: resolve pipeline → outputs: workflows[]
    └── Job: dispatch all workflows in parallel
          ├── forge-audio.yml       → ubuntu-latest → GCS
          ├── publish-release.yml
          │     ├── Job: prepare    → ubuntu-latest → generate copy, validate
          │     ├── Job: soundcloud → ubuntu-latest → POST /tracks
          │     ├── Job: youtube    → ubuntu-latest → resumable upload
          │     └── Job: patreon    → ubuntu-latest (after soundcloud+youtube)
          └── session-summarizer.yml → ubuntu-latest → commits learnings
```

ACE-Step generation workflow (when added):
```
forge-audio.yml (with --acestep flag)
    └── Job: generate → [self-hosted, m3max] → POST http://127.0.0.1:8001 → GCS
```

### Required Repository Variables and Secrets Summary

```
# Secrets (Settings → Secrets and variables → Actions → Secrets)
GEMINI_API_KEY
GCS_SA_KEY
SOUNDCLOUD_CLIENT_ID
SOUNDCLOUD_CLIENT_SECRET
YOUTUBE_CLIENT_ID
YOUTUBE_CLIENT_SECRET
YOUTUBE_REFRESH_TOKEN
PATREON_ACCESS_TOKEN
PATREON_CAMPAIGN_ID
INSTAGRAM_ACCESS_TOKEN
INSTAGRAM_ACCOUNT_ID
TIKTOK_ACCESS_TOKEN
TIKTOK_REFRESH_TOKEN
TIKTOK_CLIENT_KEY
TIKTOK_CLIENT_SECRET

# Variables (Settings → Secrets and variables → Actions → Variables)
GCS_BUCKET
```

### All Scripts Built

All scripts referenced by `publish-release.yml` and `social-post.yml` are complete. No blockers remain.

| Script | Status |
|---|---|
| `scripts/post_soundcloud.py` | ✅ Built |
| `scripts/post_youtube.py` | ✅ Built |
| `scripts/post_patreon.py` | ✅ Built |
| `scripts/post_tiktok.py` | ✅ Built |
| `scripts/refresh_tokens.py` | ✅ Built |

---

## Workflows — What Exists / What's Still Needed

| Workflow | File | Trigger | Status |
|---|---|---|---|
| Weekly Brainstorm | `weekly-brainstorm.yml` | Monday 08:00 UTC | ✅ Built |
| Forge Audio | `forge-audio.yml` | Manual | ✅ Built |
| GCS Sync | `gcs-sync.yml` | Manual / push | ✅ Built |
| Session Summarizer | `session-summarizer.yml` | Push to outputs/ | ✅ Built |
| Repo Health | `repo-health.yml` | Schedule | ✅ Built |
| Feed Digest | `feed-digest.yml` | Schedule | ✅ Built |
| Pattern Mutator | `pattern-mutator.yml` | Manual | ✅ Built |
| Publish Release | `publish-release.yml` | Manual | ✅ Built |
| Social Post | `social-post.yml` | Manual / schedule | ✅ Built |
| Dispatch Workers | `dispatch-workers.yml` | Manual | ✅ Built |
| Refresh Tokens | `refresh-tokens.yml` | Monthly schedule | ✅ Built |
