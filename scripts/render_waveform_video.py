#!/usr/bin/env python3
"""
render_waveform_video.py — ffmpeg-based waveform visualizer for IRON STATIC promos.

Renders a waveform visualizer video suitable for YouTube, Instagram Reels, and TikTok.
Uses ffmpeg's showwaves / avectorscope filters with IRON STATIC's visual aesthetic:
dark background, high-contrast waveform, optional cover art overlay.

Output formats:
  landscape  1920×1080  16:9  — YouTube, standard
  square     1080×1080  1:1   — Instagram feed
  portrait   1080×1920  9:16  — Instagram Reels, TikTok

Usage:
  python scripts/render_waveform_video.py --audio audio/generated/rust-protocol_teaser.mp3
  python scripts/render_waveform_video.py \\
      --audio audio/generated/rust-protocol_teaser.mp3 \\
      --cover outputs/social/rust-protocol_cover_landscape.png \\
      --format landscape portrait \\
      --duration 60
  python scripts/render_waveform_video.py --audio ... --dry-run   # print ffmpeg command only
"""

import argparse
import logging
import shutil
import subprocess
import sys
from pathlib import Path

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent
SOCIAL_OUT = REPO_ROOT / "outputs" / "social"

# Per-format: (width, height, suffix)
FORMAT_SPECS = {
    "landscape": (1920, 1080, "landscape"),
    "square":    (1080, 1080, "square"),
    "portrait":  (1080, 1920, "portrait"),
}

# IRON STATIC waveform color: high-voltage cyan-white on near-black
WAVEFORM_COLOR = "0xb0e8ff"   # cold metallic blue-white
BG_COLOR       = "0x0a0a0a"   # near-black
ACCENT_COLOR   = "0x2a2a2a"   # dark grey for cover art letterbox bars


def check_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        log.error("ffmpeg not found. Install with: brew install ffmpeg")
        sys.exit(1)
    return ffmpeg


def get_audio_duration(audio_path: Path, ffmpeg: str) -> float:
    """Return audio duration in seconds via ffprobe."""
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        # Fall back to estimating from ffmpeg stderr
        return None
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)],
        capture_output=True, text=True,
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def build_ffmpeg_command(
    audio_path: Path,
    cover_path: Path | None,
    output_path: Path,
    width: int,
    height: int,
    duration: float | None,
    ffmpeg: str,
) -> list[str]:
    """Build the ffmpeg command for a single output format."""
    cmd = [ffmpeg, "-y"]

    if cover_path and cover_path.exists():
        # Input 0: cover image (looped), Input 1: audio
        cmd += ["-loop", "1", "-i", str(cover_path)]
        cmd += ["-i", str(audio_path)]
        has_cover = True
    else:
        # Input 0: audio only — generate solid background
        cmd += ["-i", str(audio_path)]
        has_cover = False

    if duration:
        cmd += ["-t", str(duration)]

    # Build filtergraph
    if has_cover:
        # Scale cover to fit inside target resolution (letterbox with accent bars)
        # Then overlay the waveform on top
        filtergraph = (
            f"[0:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color={ACCENT_COLOR}[bg];"
            f"[1:a]showwaves=s={width}x{height}:mode=cline:rate=30:"
            f"colors={WAVEFORM_COLOR}:scale=sqrt[wave];"
            f"[bg][wave]blend=all_mode=screen[out]"
        )
        cmd += [
            "-filter_complex", filtergraph,
            "-map", "[out]",
            "-map", "1:a",
        ]
    else:
        # No cover art — solid dark background + waveform
        filtergraph = (
            f"color=c={BG_COLOR}:s={width}x{height}:r=30[bg];"
            f"[0:a]showwaves=s={width}x{height}:mode=cline:rate=30:"
            f"colors={WAVEFORM_COLOR}:scale=sqrt[wave];"
            f"[bg][wave]blend=all_mode=screen[out]"
        )
        cmd += [
            "-filter_complex", filtergraph,
            "-map", "[out]",
            "-map", "0:a",
        ]

    cmd += [
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "18",          # high quality
        "-pix_fmt", "yuv420p", # broad compatibility
        "-c:a", "aac",
        "-b:a", "320k",
        "-movflags", "+faststart",  # YouTube streaming optimization
        str(output_path),
    ]
    return cmd


def render(
    audio_path: Path,
    cover_path: Path | None,
    formats: list[str],
    duration: float | None,
    dry_run: bool,
) -> dict[str, Path]:
    ffmpeg = check_ffmpeg()
    SOCIAL_OUT.mkdir(parents=True, exist_ok=True)

    # Derive slug from audio filename
    slug = audio_path.stem.split("_")[0] if "_" in audio_path.stem else audio_path.stem

    if not duration:
        detected = get_audio_duration(audio_path, ffmpeg)
        if detected:
            log.info("Audio duration: %.1fs", detected)
            duration = min(detected, 60.0)  # cap at 60s for social
        else:
            duration = 60.0
            log.warning("Could not detect audio duration, defaulting to 60s")

    results = {}
    for fmt in formats:
        width, height, suffix = FORMAT_SPECS[fmt]
        out_path = SOCIAL_OUT / f"{slug}_visualizer_{suffix}.mp4"
        cmd = build_ffmpeg_command(audio_path, cover_path, out_path, width, height, duration, ffmpeg)

        if dry_run:
            print(f"\n=== {fmt} ({width}x{height}) ===")
            print(" \\\n  ".join(cmd))
            continue

        log.info("Rendering %s visualizer → %s", fmt, out_path)
        result = subprocess.run(cmd, capture_output=not log.isEnabledFor(logging.DEBUG))
        if result.returncode != 0:
            log.error("ffmpeg failed for %s:\n%s", fmt, result.stderr.decode() if result.stderr else "")
            continue

        log.info("Done: %s", out_path)
        results[fmt] = out_path

    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render waveform visualizer videos for IRON STATIC social media."
    )
    parser.add_argument(
        "--audio",
        required=True,
        metavar="PATH",
        help="Path to the audio file (MP3 or WAV).",
    )
    parser.add_argument(
        "--cover",
        metavar="PATH",
        default=None,
        help="Optional cover art image to use as background.",
    )
    parser.add_argument(
        "--format", "--formats",
        dest="formats",
        nargs="+",
        choices=list(FORMAT_SPECS.keys()),
        default=["landscape"],
        help="Output format(s). Default: landscape. Options: landscape square portrait.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=None,
        metavar="SECONDS",
        help="Clip duration in seconds. Default: auto-detect from audio, capped at 60s.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print ffmpeg commands without executing them.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    audio_path = Path(args.audio)
    if not audio_path.is_absolute():
        audio_path = REPO_ROOT / audio_path
    if not audio_path.exists():
        log.error("Audio file not found: %s", audio_path)
        sys.exit(1)

    cover_path = None
    if args.cover:
        cover_path = Path(args.cover)
        if not cover_path.is_absolute():
            cover_path = REPO_ROOT / cover_path
        if not cover_path.exists():
            log.warning("Cover art not found: %s — rendering without it", cover_path)
            cover_path = None

    results = render(audio_path, cover_path, args.formats, args.duration, args.dry_run)

    if not args.dry_run:
        if results:
            print("\nRendered:")
            for fmt, path in results.items():
                w, h, _ = FORMAT_SPECS[fmt]
                print(f"  {fmt:12s} ({w}×{h})  {path}")
        else:
            log.error("No videos rendered.")
            sys.exit(1)


if __name__ == "__main__":
    main()
