# services/video_generation_service.py
# NEW: Replicate PixVerse integration (5s / 360p)
# Compatible with existing pipeline (returns video path)

import os
import replicate
import requests
from pathlib import Path

REPLICATE_MODEL = "pixverse/pixverse-v4"

def generate_ai_video(prompt: str, output_path: Path):
    """
    Generates a short AI video using Replicate PixVerse (5s, 360p)
    Returns path to video file
    """

    client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

    output = client.run(
        REPLICATE_MODEL,
        input={
            "prompt": prompt,
            "duration": 5,
            "resolution": "360p",
            "aspect_ratio": "9:16"
        }
    )

    # PixVerse returns URL
    video_url = output[0] if isinstance(output, list) else output

    response = requests.get(video_url)
    response.raise_for_status()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "wb") as f:
        f.write(response.content)

    return str(output_path)


# Wrapper to keep compatibility with existing pipeline
def create_video_from_ai(prompt: str, temp_dir: Path):
    video_path = temp_dir / "ai_generated.mp4"
    return generate_ai_video(prompt, video_path)
