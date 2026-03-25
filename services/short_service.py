from pathlib import Path
import logging
import random
import subprocess

from config import Config
from services.pexels_service import fetch_reel_source_clip

logger = logging.getLogger(__name__)

BASE_SHORT_DESCRIPTIONS = {
    "female": "Music for developers in deep focus mode.",
    "male": "Coding vibes for developers in deep focus mode.",
    "futuristic": "Immersive futuristic coding vibes for deep focus.",
}

HOOKS = {
    "female": [
        "POV: you enter deep focus mode",
        "POV: coding with no distractions",
        "When the build finally starts flowing",
        "This is what real focus feels like",
    ],
    "male": [
        "How developers lock into focus mode",
        "Build mode activated",
        "When the coding vibe is perfect",
        "POV: one more feature before sleep",
    ],
    "futuristic": [
        "Enter the future of focus",
        "AI coding flow activated",
        "Digital deep work mode",
        "Futuristic coding ambience",
    ],
}


def _run(cmd):
    cmd_str = [str(x) for x in cmd]
    logger.info("Running command: %s", " ".join(cmd_str))
    subprocess.run(cmd_str, check=True)


def _probe_duration(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _extract_context_line(idea):
    if not idea:
        return "Deep focus coding session."

    theme = (idea.get("theme") or "").strip()
    description = (idea.get("description") or "").strip()
    title = (idea.get("title") or "").strip()

    if theme:
        return f"{theme}."
    if description:
        first_line = description.splitlines()[0].strip()
        if first_line:
            return first_line
    if title:
        clean_title = title.split("|")[0].strip()
        if clean_title:
            return f"{clean_title}."
    return "Deep focus coding session."


def _build_short_hashtags(idea, reel_type):
    ordered = [
        "#musictowork",
        "#codingmusic",
        "#focusmusic",
        "#deepwork",
        "#shorts",
        "#chill",
    ]

    if reel_type == "female":
        extra = ["#developer", "#coding"]
    elif reel_type == "male":
        extra = ["#developer", "#programming"]
    else:
        extra = ["#futuristic", "#ambient", "#lofi"]

    for item in extra:
        if item not in ordered:
            ordered.append(item)

    if idea:
        for tag in idea.get("tags") or []:
            clean = str(tag).strip().replace(" ", "")
            if clean:
                hash_tag = f"#{clean.lower()}"
                if hash_tag not in ordered:
                    ordered.append(hash_tag)

    return ordered


def _short_title(reel_type, idea):
    hook = random.choice(HOOKS[reel_type])

    if idea and idea.get("title"):
        base = idea["title"].split("|")[0].strip()
        return f"{hook} | {base} #shorts"[:100]

    return f"{hook} #shorts"[:100]


def _short_description(reel_type, idea):
    base = BASE_SHORT_DESCRIPTIONS[reel_type]
    context = _extract_context_line(idea)
    hashtags = _build_short_hashtags(idea, reel_type)

    return (
        f"{base}\n\n"
        f"{context}\n\n"
        f"Full version on the channel.\n\n"
        f"{' '.join(hashtags)}"
    )


def _short_tags(reel_type, idea):
    common = ["musictowork", "coding music", "focus music", "deep work", "shorts", "chill"]

    if reel_type == "female":
        variant = ["female developer", "developer"]
    elif reel_type == "male":
        variant = ["male developer", "developer"]
    else:
        variant = ["futuristic", "ambient", "lofi"]

    merged = (common + variant + list(idea.get("tags") or [])) if idea else (common + variant)

    result = []
    seen = set()
    for item in merged:
        key = str(item).strip().lower()
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _map_reel_type_for_pexels(reel_type):
    # Mantém compatibilidade com pexels_service atual (A/B).
    if reel_type in ("female", "futuristic"):
        return "A"
    return "B"


def generate_short(reel_type, music_path, output_path: Path, temp_dir: Path, idea=None):
    temp_dir.mkdir(parents=True, exist_ok=True)
    source_clip_path = temp_dir / f"pexels_source_{reel_type}.mp4"

    pexels_type = _map_reel_type_for_pexels(reel_type)
    clip_path, pexels_meta = fetch_reel_source_clip(pexels_type, source_clip_path)

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

    vf = (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "fps=30"
    )

    _run([
        "ffmpeg", "-y",
        "-ss", str(video_start),
        "-t", str(Config.short_duration_seconds),
        "-i", clip_path,
        "-ss", str(audio_start),
        "-t", str(Config.short_duration_seconds),
        "-i", music_path,
        "-vf", vf,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        str(output_path),
    ])

    meta = {
        "reel_type": reel_type,
        "title": _short_title(reel_type, idea),
        "description": _short_description(reel_type, idea),
        "tags": _short_tags(reel_type, idea),
        "video_start_seconds": video_start,
        "audio_start_seconds": audio_start,
        "pexels": pexels_meta,
    }
    return str(output_path), meta
