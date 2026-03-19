from pathlib import Path
import logging
import random
import subprocess
from config import Config
from services.pexels_service import fetch_reel_source_clip

logger = logging.getLogger(__name__)

BASE_SHORT_DESCRIPTIONS = {
    "A": "Music for developers in deep focus mode.",
    "B": "Coding vibes for developers in deep focus mode.",
}

CONDITION_LINES = [
    "Rainy coding session.",
    "Sunny build mode.",
    "Mountain focus energy.",
    "Beachside deep work.",
    "Late night programming flow.",
    "Calm office focus.",
    "Creative coding session.",
    "No distractions, just code.",
]

HOOKS_A = [
    "POV: you enter deep focus mode",
    "POV: coding with no distractions",
    "When the build finally starts flowing",
    "This is what real focus feels like",
]

HOOKS_B = [
    "How developers lock into focus mode",
    "Build mode activated",
    "When the coding vibe is perfect",
    "POV: one more feature before sleep",
]

def _run(cmd):
    cmd_str = [str(x) for x in cmd]
    logger.info("Running command: %s", " ".join(cmd_str))
    subprocess.run(cmd_str, check=True)

def _probe_duration(path):
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
        capture_output=True, text=True, check=True,
    )
    return float(result.stdout.strip())

def _short_title(reel_type):
    hook = random.choice(HOOKS_A if reel_type == "A" else HOOKS_B)
    return f"{hook} #shorts"[:100]

def _short_description(reel_type):
    base = BASE_SHORT_DESCRIPTIONS[reel_type]
    condition = random.choice(CONDITION_LINES)
    return f"{base}\n\n{condition}\n\nFull version on the channel.\n\n#coding #programming #focus #deepwork #shorts"

def _short_tags(reel_type):
    common = ["coding", "programming", "focus", "deep work", "shorts"]
    variant = ["developer"] if reel_type == "A" else ["female developer", "developer"]
    return common + variant

def generate_short(reel_type, music_path, output_path: Path, temp_dir: Path):
    temp_dir.mkdir(parents=True, exist_ok=True)
    source_clip_path = temp_dir / f"pexels_source_{reel_type}.mp4"
    clip_path, pexels_meta = fetch_reel_source_clip(reel_type, source_clip_path)

    clip_duration = _probe_duration(clip_path)
    if clip_duration <= Config.short_duration_seconds:
        video_start = 0
    else:
        max_start = max(0, int(clip_duration - Config.short_duration_seconds - 1))
        video_start = random.randint(0, max_start)

    audio_duration = _probe_duration(music_path)
    configured_audio_start = Config.short_start_offset_seconds
    if audio_duration <= Config.short_duration_seconds:
        audio_start = 0
    elif configured_audio_start + Config.short_duration_seconds < audio_duration:
        audio_start = configured_audio_start
    else:
        audio_start = max(0, int(audio_duration - Config.short_duration_seconds - 1))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    vf = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30"

    _run([
        "ffmpeg", "-y",
        "-ss", str(video_start), "-t", str(Config.short_duration_seconds), "-i", clip_path,
        "-ss", str(audio_start), "-t", str(Config.short_duration_seconds), "-i", music_path,
        "-vf", vf, "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(output_path),
    ])

    meta = {
        "reel_type": reel_type,
        "title": _short_title(reel_type),
        "description": _short_description(reel_type),
        "tags": _short_tags(reel_type),
        "video_start_seconds": video_start,
        "audio_start_seconds": audio_start,
        "pexels": pexels_meta,
    }
    return str(output_path), meta
