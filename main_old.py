from pathlib import Path
import logging
from datetime import datetime, timezone
from agents.idea_agent import generate_video_idea
from services.image_service import generate_thumbnail
from services.music_service import generate_music
from services.video_service import create_video
from services.short_service import generate_short
from services.youtube_service import upload_video_and_thumbnail
from services.history_service import load_history, save_history
from services.cleanup_service import cleanup_temp_dir
from config import Config

logging.basicConfig(level=getattr(logging, Config.log_level.upper(), logging.INFO), format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

def run():
    Path("temp").mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)
    job_id = datetime.now(timezone.utc).strftime("job_%Y%m%dT%H%M%SZ")
    job_dir = Path("temp") / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Starting pipeline in %s", job_dir)
    try:
        history = load_history()
        idea = generate_video_idea(history)
        thumbnail_path = generate_thumbnail(idea["visual_prompt"], job_dir / "thumbnail.png", idea["title"])
        music_path, music_meta = generate_music(idea["music_prompt"], job_dir / "music.mp3")
        video_path = create_video(thumbnail_path, music_path, job_dir / "video.mp4", idea["duration_minutes"] * 60, Config.loop_audio)

        long_upload = upload_video_and_thumbnail(video_path, thumbnail_path, idea["title"], idea["description"], idea["tags"])
        logger.info("Long upload finished: %s", long_upload.get("video_url"))

        short_a_path, short_a_meta = generate_short("A", music_path, job_dir / "short_A.mp4", job_dir / "short_assets_A")
        short_a_upload = upload_video_and_thumbnail(short_a_path, thumbnail_path, short_a_meta["title"], short_a_meta["description"], short_a_meta["tags"])
        logger.info("Short A uploaded: %s", short_a_upload.get("video_url"))

        short_b_path, short_b_meta = generate_short("B", music_path, job_dir / "short_B.mp4", job_dir / "short_assets_B")
        short_b_upload = upload_video_and_thumbnail(short_b_path, thumbnail_path, short_b_meta["title"], short_b_meta["description"], short_b_meta["tags"])
        logger.info("Short B uploaded: %s", short_b_upload.get("video_url"))

        save_history({
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "title": idea["title"],
            "theme": idea["theme"],
            "duration_minutes": idea["duration_minutes"],
            "tags": idea["tags"],
            "youtube_video_id": long_upload["video_id"],
            "youtube_video_url": long_upload["video_url"],
            "music_meta": music_meta,
            "short_a": {"upload": short_a_upload, "meta": short_a_meta},
            "short_b": {"upload": short_b_upload, "meta": short_b_meta},
        })

        if Config.cleanup_on_success:
            cleanup_temp_dir(job_dir)
    except Exception:
        logger.exception("Pipeline failed. Temporary files preserved at %s", job_dir)
        raise

if __name__ == "__main__":
    run()
