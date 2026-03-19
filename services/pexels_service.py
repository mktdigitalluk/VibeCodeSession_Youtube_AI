from pathlib import Path
import logging
import random
import requests
from config import Config

logger = logging.getLogger(__name__)

TYPE_A_QUERIES = [
    "developer coding laptop aesthetic",
    "programmer working laptop",
    "software engineer typing laptop",
    "coding workspace aesthetic",
    "developer typing dark room",
    "minimal desk coding",
]

TYPE_B_QUERIES = [
    "female developer coding laptop",
    "woman programmer laptop aesthetic",
    "female freelancer laptop cafe",
    "tech woman working desk laptop",
    "woman coding dark room laptop",
    "female software engineer working laptop",
]

def _headers():
    if not Config.pexels_api_key:
        raise RuntimeError("PEXELS_API_KEY is missing in keys.env")
    return {"Authorization": Config.pexels_api_key}

def _pick_query(reel_type):
    pool = TYPE_A_QUERIES if reel_type == "A" else TYPE_B_QUERIES
    return random.choice(pool)

def _score_video(video):
    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    duration = int(video.get("duration") or 0)
    score = 0
    if duration >= Config.short_duration_seconds + 2:
        score += 100
    else:
        score -= 100
    if width >= 1080:
        score += 20
    if height >= 1080:
        score += 20
    if width > height:
        score += 10
    score += random.randint(0, 15)
    return score

def search_pexels_video(reel_type):
    query = _pick_query(reel_type)
    logger.info("Searching Pexels for type=%s query=%s", reel_type, query)
    response = requests.get(
        "https://api.pexels.com/videos/search",
        headers=_headers(),
        params={"query": query, "per_page": 12},
        timeout=120,
    )
    response.raise_for_status()
    data = response.json()
    videos = data.get("videos") or []
    if not videos:
        raise RuntimeError(f"No Pexels videos found for query: {query}")
    best_video = max(videos, key=_score_video)
    video_files = best_video.get("video_files") or []
    if not video_files:
        raise RuntimeError(f"Pexels returned video without downloadable files. Query: {query}")

    def file_score(vf):
        width = int(vf.get("width") or 0)
        height = int(vf.get("height") or 0)
        quality = (vf.get("quality") or "").lower()
        file_type = (vf.get("file_type") or "").lower()
        score = 0
        if file_type == "video/mp4":
            score += 100
        if quality == "sd":
            score += 20
        if quality == "hd":
            score += 40
        if 720 <= height <= 1440:
            score += 40
        if width >= 1080:
            score += 10
        return score

    best_file = max(video_files, key=file_score)
    return best_file["link"], {
        "query": query,
        "video_id": best_video.get("id"),
        "duration_seconds": best_video.get("duration"),
        "pexels_url": best_video.get("url"),
        "author": ((best_video.get("user") or {}).get("name")),
        "reel_type": reel_type,
    }

def download_pexels_video(url, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Downloading Pexels clip to %s", output_path)
    with requests.get(url, stream=True, timeout=300) as response:
        response.raise_for_status()
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 512):
                if chunk:
                    f.write(chunk)
    return output_path

def fetch_reel_source_clip(reel_type, output_path: Path):
    url, meta = search_pexels_video(reel_type)
    local_path = download_pexels_video(url, output_path)
    meta["download_url"] = url
    return str(local_path), meta
