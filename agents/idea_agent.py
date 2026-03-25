# IDEA AGENT V4 - GEMINI + SMART POST PROCESSING

import json
import logging
import re
from google import genai
from config import Config

logger = logging.getLogger(__name__)

FIXED_SUFFIX = "3 Hours of Deep Work"

BASE_HASHTAGS = [
    "#musictowork",
    "#codingmusic",
    "#focusmusic",
    "#deepwork"
]

CONTEXT_MAP = {
    "beach": ["#beachvibes", "#chillcoding"],
    "rain": ["#rainymood", "#nightcoding"],
    "night": ["#nightcoding"],
    "forest": ["#forestvibes", "#naturefocus"],
    "mountain": ["#mountainvibes"],
    "sun": ["#daycoding"],
    "city": ["#cityvibes"]
}

SYSTEM_PROMPT = """
Generate a YouTube video idea for a coding music channel.

Return JSON with:
theme, title, description, music_prompt, visual_prompt, tags

Rules:
- Always include a developer working on laptop
- No text in image
- Music must be instrumental
- Vary environment (day, beach, forest, etc)
"""


def _extract_json(text):
    text = text.strip()
    text = re.sub(r"^```json", "", text)
    text = re.sub(r"```$", "", text)
    return json.loads(text)


def _fix_title(title):
    title = re.sub(r"\|.*$", "", title).strip()
    return f"{title} | {FIXED_SUFFIX}"


def _generate_hashtags(text):
    tags = BASE_HASHTAGS.copy()
    lower = text.lower()

    for key, values in CONTEXT_MAP.items():
        if key in lower:
            tags.extend(values)

    return list(dict.fromkeys(tags))


def generate_video_idea(history):
    if not Config.gemini_api_key:
        raise RuntimeError("Missing GEMINI_API_KEY")

    client = genai.Client(api_key=Config.gemini_api_key)

    response = client.models.generate_content(
        model=Config.gemini_text_model,
        contents=SYSTEM_PROMPT
    )

    data = _extract_json(response.text)

    title = _fix_title(data.get("title", "Coding Session"))
    context_text = data.get("theme", "") + " " + data.get("description", "")

    hashtags = _generate_hashtags(context_text)

    return {
        "title": title,
        "description": data.get("description", "") + "\n\n" + " ".join(hashtags),
        "tags": [h.replace("#","") for h in hashtags],
        "music_prompt": data.get("music_prompt", ""),
        "visual_prompt": data.get("visual_prompt", ""),
        "duration_minutes": Config.video_duration_minutes
    }
