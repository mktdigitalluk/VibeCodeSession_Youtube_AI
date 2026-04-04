import random
import json
from datetime import datetime
from pathlib import Path

HISTORY_PATH = Path("data/history.json")

WORLD_LOCATIONS = [
    "Eiffel Tower Paris",
    "Times Square New York",
    "Shibuya Tokyo neon street",
    "Santorini Greece sunset",
    "Dubai skyline night",
    "Swiss Alps mountains",
    "Bali beach sunset",
    "London city skyline",
    "Sydney Opera House",
    "Grand Canyon view",
    "Maldives beach",
    "Hong Kong skyline",
    "Rio de Janeiro Christ the Redeemer",
    "Iceland waterfalls",
    "Venice canals",
]

BASE_TAGS = ["music to work", "coding music", "focus music", "deep work", "chill"]

def _load_history():
    if not HISTORY_PATH.exists():
        return []
    with open(HISTORY_PATH, "r") as f:
        return json.load(f)

def _save_history(history):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_PATH, "w") as f:
        json.dump(history[-20:], f, indent=2)

def _get_recent_locations(history, limit=10):
    return [item.get("location") for item in history[-limit:] if item.get("location")]

def _pick_new_location(history):
    recent = set(_get_recent_locations(history))
    options = [loc for loc in WORLD_LOCATIONS if loc not in recent]

    if not options:
        options = WORLD_LOCATIONS

    return random.choice(options)

def generate_video_idea():
    history = _load_history()

    location = _pick_new_location(history)

    title = f"{location} Coding Flow | 3 Hours of Deep Work"

    description = (
        f"Focus music for deep work while coding in front of {location}.\n\n"
        "Perfect for programming, studying, and productivity sessions."
    )

    prompt = (
        f"A software developer coding on a laptop facing {location}, "
        "cinematic lighting, ultra realistic, 4k, no text"
    )

    idea = {
        "title": title,
        "description": description,
        "tags": BASE_TAGS,
        "location": location,
        "prompt": prompt,
        "created_at": datetime.utcnow().isoformat()
    }

    history.append(idea)
    _save_history(history)

    return idea
