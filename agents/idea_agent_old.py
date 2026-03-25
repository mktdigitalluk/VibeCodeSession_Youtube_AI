# IDEA AGENT V3 - STRONG TITLES + DYNAMIC HASHTAGS

import random
from config import Config

FIXED_SUFFIX = "3 Hours of Deep Work"

BASE_HASHTAGS = [
    "#musictowork",
    "#codingmusic",
    "#focusmusic",
    "#deepwork"
]

SCENARIOS = [
    {
        "name": "Rainy Night",
        "title": "Rainy Night Coding Session",
        "extra_tags": ["#nightcoding", "#rainymood", "#chillcoding"]
    },
    {
        "name": "Beach",
        "title": "Chill Beach Coding Flow",
        "extra_tags": ["#beachvibes", "#chillmusic", "#lofi"]
    },
    {
        "name": "Forest",
        "title": "Forest Deep Focus Coding",
        "extra_tags": ["#forestvibes", "#naturefocus", "#ambient"]
    },
    {
        "name": "Mountain",
        "title": "Mountain Developer Focus Session",
        "extra_tags": ["#mountainvibes", "#deepfocus", "#chillcoding"]
    },
    {
        "name": "Sunny Day",
        "title": "Sunny Day Programming Flow",
        "extra_tags": ["#daycoding", "#productive", "#focusmode"]
    }
]


def build_title(base):
    return f"{base} | {FIXED_SUFFIX}"


def build_hashtags(extra):
    return BASE_HASHTAGS + extra


def generate_video_idea(history):
    scenario = random.choice(SCENARIOS)

    hashtags = build_hashtags(scenario["extra_tags"])

    return {
        "title": build_title(scenario["title"]),
        "description": "Deep focus coding music for developers.\n\n" + " ".join(hashtags),
        "tags": [h.replace("#","") for h in hashtags],
        "music_prompt": "ambient chill coding music, lofi, deep focus",
        "visual_prompt": f"developer working on laptop in {scenario['name']} environment, code visible",
        "duration_minutes": Config.video_duration_minutes
    }
