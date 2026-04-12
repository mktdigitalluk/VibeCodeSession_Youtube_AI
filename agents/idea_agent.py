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

WORLD_PLACES = [
    {"id": "tokyo_jp", "place": "Tokyo, Japan", "scene": "neon apartment overlooking Shibuya"},
    {"id": "hong_kong_hk", "place": "Hong Kong", "scene": "high-rise apartment overlooking Victoria Harbour"},
    {"id": "new_york_us", "place": "New York, USA", "scene": "loft workspace overlooking Manhattan skyline"},
    {"id": "paris_fr", "place": "Paris, France", "scene": "balcony workspace with Eiffel Tower in the distance"},
    {"id": "london_uk", "place": "London, UK", "scene": "cozy flat workspace with rainy city view"},
    {"id": "dubai_ae", "place": "Dubai, UAE", "scene": "luxury apartment workspace above the downtown skyline"},
    {"id": "singapore_sg", "place": "Singapore", "scene": "modern workspace with Marina Bay skyline"},
    {"id": "sao_paulo_br", "place": "São Paulo, Brazil", "scene": "modern apartment office overlooking Avenida Paulista"},
    {"id": "seoul_kr", "place": "Seoul, South Korea", "scene": "night studio workspace with dense city lights"},
    {"id": "barcelona_es", "place": "Barcelona, Spain", "scene": "sunlit loft near the old city rooftops"},
    {"id": "vancouver_ca", "place": "Vancouver, Canada", "scene": "glass apartment workspace with mountains and harbor"},
    {"id": "sydney_au", "place": "Sydney, Australia", "scene": "harbour-side apartment workspace with city lights"},
    {"id": "berlin_de", "place": "Berlin, Germany", "scene": "industrial loft workspace in a creative district"},
    {"id": "toronto_ca", "place": "Toronto, Canada", "scene": "high-rise workspace overlooking the CN Tower"},
    {"id": "amsterdam_nl", "place": "Amsterdam, Netherlands", "scene": "canal-side home office with moody evening lights"},
]

SYSTEM_PROMPT = """
You are planning a faceless YouTube video for a channel called Vibe Coding Sessions.

Output strict JSON only with these fields:
title, music_prompt, visual_prompt, description, tags, duration_minutes

Rules:
- The concept is always a software developer coding in the provided real world place.
- The image must always show a software developer working on a laptop with code visible.
- Use the selected place and atmosphere exactly; do not change to another city.
- No text in the image.
- Music must be instrumental only, no vocals, no lyrics.
- Titles must be natural, YouTube-friendly, and must include the selected place.
- Keep tags short and relevant.
- duration_minutes must be an integer.
"""


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned)
    cleaned = re.sub(r"```$", "", cleaned).strip()
    return json.loads(cleaned)


def _recent_place_ids(history: list[dict[str, Any]]) -> list[str]:
    recent = [item.get("place_id") for item in history if item.get("place_id")]
    return recent[-10:]


def _pick_place(history: list[dict[str, Any]]) -> dict[str, str]:
    blocked = set(_recent_place_ids(history))
    available = [item for item in WORLD_PLACES if item["id"] not in blocked]
    if not available:
        available = WORLD_PLACES[:]
    return random.choice(available)


def _base_idea(place_cfg: dict[str, str], time_of_day: str, weather: str, mood: str) -> dict[str, Any]:
    place = place_cfg["place"]
    scene = place_cfg["scene"]
    atmosphere = f"{time_of_day}, {weather}"
    title = f"{time_of_day.title()} Coding in {place} | Deep Focus for Developers ({Config.video_duration_minutes} Hours)"
    visual_prompt = (
        f"A software developer coding on a laptop with code visible on screen, in {scene}, "
        f"during {time_of_day}, with {weather}, cinematic lighting, immersive atmosphere, no text."
    )
    music_prompt = (
        f"Instrumental ambient electronic music for {mood}, inspired by {place} at {time_of_day}, "
        f"steady energy for programming and deep work, no vocals, no lyrics."
    )
    description = (
        f"Code in flow with a developer session set in {place}. "
        f"This mix captures {time_of_day} energy with {weather} for long programming and study blocks."
    )
    tags = [
        "coding music",
        "focus music",
        "programming",
        place.split(',')[0].lower(),
        "deep work",
    ]
    return {
        "place_id": place_cfg["id"],
        "place": place,
        "time_of_day": time_of_day,
        "weather": weather,
        "mood": mood,
        "atmosphere": atmosphere,
        "theme": f"{mood.title()} coding in {place}",
        "title": title[:100],
        "music_prompt": music_prompt,
        "visual_prompt": visual_prompt,
        "description": description,
        "tags": tags,
        "duration_minutes": Config.video_duration_minutes,
        "short_hook": f"{time_of_day.title()} coding in {place}",
    }


def _fallback_idea(history: list[dict[str, Any]]) -> dict[str, Any]:
    place_cfg = _pick_place(history)
    idea = _base_idea(
        place_cfg=place_cfg,
        time_of_day=random.choice(TIMES_OF_DAY),
        weather=random.choice(WEATHER),
        mood=random.choice(MOODS),
    )
    logger.info("Fallback idea generated | title=%r | place=%r", idea["title"], idea["place"])
    return idea


def _normalize_idea(idea: dict[str, Any], place_cfg: dict[str, str], time_of_day: str, weather: str, mood: str) -> dict[str, Any]:
    base = _base_idea(place_cfg, time_of_day, weather, mood)
    merged = {**base, **(idea or {})}
    merged["place_id"] = place_cfg["id"]
    merged["place"] = place_cfg["place"]
    merged["time_of_day"] = time_of_day
    merged["weather"] = weather
    merged["mood"] = mood
    merged["atmosphere"] = f"{time_of_day}, {weather}"
    merged["duration_minutes"] = int(merged.get("duration_minutes") or Config.video_duration_minutes)
    if not isinstance(merged.get("tags"), list) or not merged["tags"]:
        merged["tags"] = base["tags"]
    title = str(merged.get("title") or "").strip()
    if place_cfg["place"].lower() not in title.lower():
        merged["title"] = base["title"]
    merged["title"] = merged["title"][:100]
    if not merged.get("visual_prompt"):
        merged["visual_prompt"] = base["visual_prompt"]
    if not merged.get("music_prompt"):
        merged["music_prompt"] = base["music_prompt"]
    if not merged.get("description"):
        merged["description"] = base["description"]
    merged["theme"] = merged.get("theme") or base["theme"]
    merged["short_hook"] = f"{time_of_day.title()} coding in {place_cfg['place']}"
    return merged


def generate_video_idea(history: list[dict[str, Any]]) -> dict[str, Any]:
    logger.info("Generating video idea | history_entries=%d | gemini_key_set=%s", len(history), bool(Config.gemini_api_key))
    place_cfg = _pick_place(history)
    time_of_day = random.choice(TIMES_OF_DAY)
    weather = random.choice(WEATHER)
    mood = random.choice(MOODS)

    if not Config.gemini_api_key:
        logger.warning("GEMINI_API_KEY not set — using fallback idea generator.")
        return _fallback_idea(history)

    recent = [
        {
            "title": item.get("title"),
            "theme": item.get("theme"),
            "place": item.get("place"),
            "place_id": item.get("place_id"),
        }
        for item in history[-12:]
    ]

    user_prompt = {
        "recent_videos": recent,
        "blocked_place_ids": _recent_place_ids(history),
        "selected_place": place_cfg,
        "selected_time_of_day": time_of_day,
        "selected_weather": weather,
        "selected_mood": mood,
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
            raise RuntimeError("Gemini returned an empty response — no text content.")
        idea = _extract_json(text)
        idea = _normalize_idea(idea, place_cfg, time_of_day, weather, mood)
        logger.info("Gemini idea accepted | title=%r | place=%r | duration_minutes=%d", idea["title"], idea["place"], idea["duration_minutes"])
        return idea
    except Exception as exc:
        logger.warning("Gemini idea generation failed, falling back | error=%s", exc)
        return _fallback_idea(history)
