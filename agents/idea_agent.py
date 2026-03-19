import json
import logging
import random
import re
from typing import Any

from google import genai
from config import Config

logger = logging.getLogger(__name__)

TIMES_OF_DAY = [
    "bright morning",
    "sunny afternoon",
    "golden sunset",
    "blue hour",
    "late night",
]

PLACES = [
    "beach house workspace with ocean view",
    "mountain cabin workspace with valley view",
    "modern city apartment with skyline view",
    "forest retreat workspace surrounded by trees",
    "minimal home office with large windows",
    "startup office with panoramic buildings",
    "cozy room with a wide window facing nature",
]

WEATHER = [
    "clear sky",
    "light rain",
    "soft fog",
    "snow falling outside",
    "warm sunlight",
    "cloudy atmosphere",
]

MOODS = [
    "deep focus",
    "calm concentration",
    "creative flow",
    "immersive coding session",
    "productive build session",
]

SYSTEM_PROMPT = """
You are planning a faceless YouTube video for a channel called Vibe Coding Sessions.

Output strict JSON only with these fields:
theme, title, music_prompt, visual_prompt, description, tags, duration_minutes

Rules:
- The image must always show a software developer working on a laptop with code visible.
- The environment must vary naturally across day, sunset, night, beach, mountain, forest, office, and home settings.
- Avoid repeating city at night too often.
- No text in the image.
- Music must be instrumental only, no vocals, no lyrics.
- Titles must be natural, YouTube-friendly, and specific.
- Keep tags short and relevant.
- duration_minutes must be an integer.
"""

def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned)
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return json.loads(cleaned)

def _pick_fallback_scenario() -> tuple[str, str, str, str]:
    return (
        random.choice(TIMES_OF_DAY),
        random.choice(PLACES),
        random.choice(WEATHER),
        random.choice(MOODS),
    )

def _fallback_idea(history: list[dict[str, Any]]) -> dict[str, Any]:
    time_of_day, place, weather, mood = _pick_fallback_scenario()

    theme = f"{mood.title()} in a {place}"
    title = f"Coding Focus Music • {place.title()} • {time_of_day.title()}".replace("Workspace", "").strip()

    visual_prompt = (
        f"A software developer working on a laptop with code visible on screen, "
        f"in a {place}, during {time_of_day}, with {weather}, cinematic lighting, "
        f"immersive atmosphere, high quality digital illustration, no text."
    )

    music_prompt = (
        f"Instrumental ambient electronic music for {mood}, calm and immersive, "
        f"designed for programming and deep work, no vocals, no lyrics, smooth progression."
    )

    return {
        "theme": theme[:120],
        "title": title[:95],
        "music_prompt": music_prompt,
        "visual_prompt": visual_prompt,
        "description": (
            "Ambient coding music for developers, makers, and deep work sessions. "
            "Designed for focus, flow, and long programming blocks."
        ),
        "tags": [
            "coding music",
            "focus music",
            "programming",
            "deep work",
            "ambient music",
        ],
        "duration_minutes": Config.video_duration_minutes,
    }

def generate_video_idea(history: list[dict[str, Any]]) -> dict[str, Any]:
    if not Config.gemini_api_key:
        logger.warning("GEMINI_API_KEY missing. Using fallback idea.")
        return _fallback_idea(history)

    recent = [
        {
            "title": item.get("title"),
            "theme": item.get("theme"),
        }
        for item in history[-12:]
    ]

    user_prompt = {
        "recent_videos": recent,
        "times_of_day": TIMES_OF_DAY,
        "places": PLACES,
        "weather_options": WEATHER,
        "moods": MOODS,
        "target_channel": "Vibe Coding Sessions",
        "duration_minutes": Config.video_duration_minutes,
    }

    try:
        client = genai.Client(api_key=Config.gemini_api_key)
        response = client.models.generate_content(
            model=Config.gemini_text_model,
            contents=[
                {"role": "user", "parts": [{"text": SYSTEM_PROMPT}]},
                {"role": "user", "parts": [{"text": json.dumps(user_prompt, ensure_ascii=False)}]},
            ],
        )

        text = getattr(response, "text", None)
        if not text:
            raise RuntimeError("Gemini did not return text.")

        idea = _extract_json(text)
        idea["duration_minutes"] = int(idea.get("duration_minutes") or Config.video_duration_minutes)

        if not isinstance(idea.get("tags"), list):
            idea["tags"] = [
                "coding music",
                "focus music",
                "programming",
                "deep work",
                "ambient music",
            ]

        return idea

    except Exception as exc:
        logger.warning("Gemini idea generation failed, using fallback: %s", exc)
        return _fallback_idea(history)
