---
description: Generate and push the Stream Deck profile (profile D4C1A9B3) to the app, then restart Stream Deck.
mode: agent
tools: [execute]
---

# Push Stream Deck Profile

Generate the Stream Deck profile, install it, and restart the app.

## Step 1: Run the Generator

From the repo root, run:
```bash
python streamdeck/generate_profile.py --install --restart
```

Capture the full output.

## Step 2: Confirm Page Manifests Were Written

Scan the output for two INFO lines containing page UUIDs — one for Page 1 (Copilot prompt buttons) and one for Page 2 (shell/bridge buttons). Both must appear before the install step.

If either is missing, report which page failed and stop.

## Step 3: Confirm Install and Restart

Check the output for:
- A line confirming the profile was copied to `~/Library/Application Support/com.elgato.StreamDeck/ProfilesV3/`
- A line confirming the Stream Deck app was restarted

## Step 4: Report

**Success**: State that both pages were written, the profile was installed, and Stream Deck restarted. Include the profile UUID (`D4C1A9B3-8F2E-4A7D-B650-1E3F9C2D5847`) for reference.

**Failure**: Show the relevant error lines from the output and suggest the likely fix (missing profile dir, app not found, script error).
