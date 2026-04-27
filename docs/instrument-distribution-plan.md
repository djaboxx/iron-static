# IRON STATIC — Instrument Distribution Plan

> How to package, version, and distribute the custom instruments we build as M4L devices and Ableton Packs.

---

## Overview

IRON STATIC is building original instruments as Max for Live composite chains (e.g. `drift~` → `roar~` → `echo~` → `spectralresonator~` wrapped as `.amxd`). These instruments are part of the band's sound and will eventually be released so others can use them.

This document covers the full pipeline:
1. **M4L Device Packaging** — how to freeze, version, and prepare `.amxd` files for distribution
2. **Ableton Pack Assembly** — how to package one or more devices + presets + templates into an `.alp` pack
3. **Distribution Channels** — where to release and how each channel works
4. **IRON STATIC Release Workflow** — the git-native process we actually follow

All source material: `instruments/` in this repo.

---

## 1. M4L Device Packaging (`.amxd`)

Source: [Ableton M4L Production Guidelines](https://github.com/Ableton/maxdevtools/blob/main/m4l-production-guidelines/m4l-production-guidelines.md) (official Ableton/Cycling '74 documentation)

### 1.1 The Freeze Step

Freezing is mandatory before distributing a device. It bundles all dependencies — sub-patches (abstractions), audio files, images, JS files, and third-party Max externals — into a single portable `.amxd` file.

**How to freeze:**
1. Open the device for editing in Max (right-click device title bar → Edit in Max)
2. Optional: check dependencies first — Max File menu → **List Externals and Subpatcher Files**
3. Click the **snowflake icon** in the device toolbar
4. Save under a **new name** (append version, e.g. `drift-beast_v1.0.amxd`)

**Important:** Never continue developing from the frozen copy. Keep the unfrozen `.maxpat` source in git. When you need to update, edit the unfrozen source → re-freeze → distribute the new frozen version.

### 1.2 Version Management

- Store unfrozen source patches in `instruments/[instrument-name]/` in this repo
- Frozen, release-ready `.amxd` files go in `instruments/[instrument-name]/releases/`
- Name pattern: `[instrument-slug]_v[major].[minor].amxd` — e.g. `drift-beast_v1.0.amxd`
- Avoid renaming parameter Long Names between versions — this breaks parameter recall in existing Live Sets
- If you make breaking changes: publish as a new filename with a new version number

### 1.3 Pre-Distribution QA Checklist

From the official Ableton M4L Production Guidelines final checklist:

**Core:**
- [ ] No errors in Max Console on load (right-click device title bar → Open Max Window)
- [ ] Undo history is not flooded during playback
- [ ] Device is frozen and all dependencies are bundled
- [ ] At least one preset demonstrating the device's character
- [ ] Parameters save and recall correctly when re-opening a Live Set

**Audio:**
- [ ] No unintended clicks when changing parameters
- [ ] Sounds identical on live playback, frozen track, and rendered audio file
- [ ] Plays in sync (check latency in Live status bar when hovering over device title)

**UI:**
- [ ] Works with all Live color themes (Preferences → Look/Feel, cycle through themes)
- [ ] All UI fonts set to Ableton Sans
- [ ] All `[live.*]` objects have MIDI-mappable parameters (Cmd+M to verify blue overlay)

**Robustness:**
- [ ] Tested on both Mac and Windows if possible
- [ ] Multiple simultaneous instances run without issues
- [ ] Tested by someone who didn't build it

**For updates to existing devices:**
- [ ] Parameter Long Names are unchanged (or intentional break documented in changelog)
- [ ] Old Live Sets with the device still load and recall parameters correctly

---

## 2. Ableton Pack Assembly (`.alp`)

Source: [Ableton Reference Manual Chapter 5.10 — Packing Projects into Packs](https://www.ableton.com/en/live-manual/12/managing-files-and-sets/#packing-projects-into-packs)

### 2.1 What a Pack Is

An `.alp` file is a losslessly-compressed archive of a Live Project. It includes whatever files are in the project folder: presets (`.adg`, `.adv`, `.amxd`), audio samples, template sets (`.als`), grooves (`.agr`). Live uses its own compression and can save up to 50% on audio-heavy packs.

Recipients install a pack by:
- Double-clicking the `.alp` file, or
- Dragging it into Live's main window, or
- File menu → **Install Pack**

### 2.2 How to Create a Pack

**Prerequisites — collect all files first:**
1. Open the Live Project that contains your devices, presets, and templates
2. File menu → **Collect All and Save** — this copies all external audio, M4L device references, etc. into the project folder so nothing is missing

**Create the pack:**
1. File menu → **Manage Files**
2. Click **Manage Project**
3. Unfold the **Packing** section
4. Click **Create Pack**
5. Choose name and save location — Live creates the `.alp` file

Creating a pack does **not** affect the original project folder. You can delete the project folder separately if you want to archive it.

### 2.3 Pack Folder Convention for IRON STATIC

```
instruments/[instrument-name]/
├── releases/
│   ├── [instrument-name]_v1.0.amxd        # frozen, distributable M4L device
│   └── [instrument-name]_v1.0.alp         # full pack (device + presets + template)
├── presets/                               # .adg or .adv preset files
├── templates/                             # .als template sets (if any)
└── [instrument-name].maxpat              # unfrozen source (in git, not in pack)
```

The `.maxpat` source lives in git. Frozen `.amxd` and compiled `.alp` are build artifacts — store them in `releases/` and distribute via GitHub Releases.

---

## 3. Distribution Channels

### 3.1 GitHub Releases (Primary — Use This First)

**What it is:** Attach release artifacts to a tagged GitHub Release. Free, versioned, integrated with the repo.

**How:**
```bash
gh release create v1.0 \
  instruments/drift-beast/releases/drift-beast_v1.0.amxd \
  instruments/drift-beast/releases/drift-beast_v1.0.alp \
  --title "Drift Beast v1.0" \
  --notes "Initial release — Drift → Roar → Echo → Spectral Resonator composite instrument"
```

**Who it's for:** Direct fans, IRON STATIC community, other producers who follow the repo.

### 3.2 maxforlive.com (Community Marketplace)

**What it is:** The standard community site for M4L devices — mentioned directly in Ableton's own Production Guidelines documentation. Free or paid pricing. Wide M4L user reach.

**How:** Create an account at [maxforlive.com](https://maxforlive.com), upload the frozen `.amxd`, add description + screenshots. Free tier available; paid listings require a Gumroad or similar link for checkout.

**Who it's for:** M4L-specific audience actively looking for new devices.

### 3.3 Gumroad / Sellfy (Paid Direct Sales)

**What it is:** Hosted digital product storefronts. You control pricing, delivery, and customer list. No platform cut on Gumroad free tier (just payment processing fees).

**How:** Upload `.alp` (or a `.zip` containing both `.amxd` + demo set), set price, embed buy button anywhere.

**Who it's for:** When you want to sell devices with full control over pricing and audience data.

### 3.4 Ableton Pack Marketplace (Long-Term Goal)

**What it is:** Official Ableton.com/packs marketplace. Highest visibility but requires the Ableton Partner Program.

**Requirements:**
- Apply to the Ableton Partner Program (application process, invitation-based for most)
- Ableton hosts the files and handles licensing/DRM
- Revenue share with Ableton

**Timeline:** Not viable until we have a catalog of polished, tested instruments. Use other channels first to build reputation and catalog.

---

## 4. IRON STATIC Release Workflow

### 4.1 Development Phase (in this repo)

1. Build the instrument as a Max patch in `instruments/[name]/`
2. Store unfrozen `.maxpat` in git — this is the source of truth
3. Track progress in `database/instruments.json` (instrument slug, status, description)

### 4.2 Release Prep

1. Run the M4L QA checklist (Section 1.3)
2. Freeze the device: snowflake icon → save as `[name]_v[x.y].amxd` → move to `releases/`
3. Collect all files in the Live project (File → Collect All and Save)
4. Create the `.alp` pack via File Manager → Manage Project → Create Pack
5. Move `.alp` to `releases/`

### 4.3 Release

```bash
# Tag the release
git tag -a instrument/[name]/v1.0 -m "Drift Beast v1.0 — initial release"
git push origin instrument/[name]/v1.0

# Create GitHub Release with artifacts
gh release create instrument/[name]/v1.0 \
  instruments/[name]/releases/[name]_v1.0.amxd \
  instruments/[name]/releases/[name]_v1.0.alp \
  --title "[Instrument Display Name] v1.0" \
  --notes-file instruments/[name]/CHANGELOG.md
```

Then post to maxforlive.com and (when ready) Gumroad for paid sales.

### 4.4 Automation (Future)

A GitHub Action at `.github/workflows/package-instrument.yml` can automate the freeze + pack step when triggered manually (workflow_dispatch). This is on the backlog — build manually for the first release.

---

## 5. Key References

| Topic | Source |
|---|---|
| M4L freezing + QA | [Ableton maxdevtools — M4L Production Guidelines](https://github.com/Ableton/maxdevtools/blob/main/m4l-production-guidelines/m4l-production-guidelines.md) |
| `.alp` pack creation | [Ableton Manual §5.10 — Packing Projects into Packs](https://www.ableton.com/en/live-manual/12/managing-files-and-sets/#packing-projects-into-packs) |
| M4L device editing | [Ableton Manual §31.3 — Editing Max for Live Devices](https://www.ableton.com/en/live-manual/12/max-for-live/#editing-max-for-live-devices) |
| M4L dependencies | [Ableton Manual §31.5 — Max Dependencies](https://www.ableton.com/en/live-manual/12/max-for-live/#max-dependencies) |
| M4L community distribution | [maxforlive.com](https://maxforlive.com) |
| IRON STATIC instrument source | `instruments/` in this repo |
