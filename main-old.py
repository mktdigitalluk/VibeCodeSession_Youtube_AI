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

# ===== LOG CONFIG =====
log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=getattr(logging, Config.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def run() -> None:
    Path("temp").mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)

    job_id = datetime.now(timezone.utc).strftime("job_%Y%m%dT%H%M%SZ")
    job_dir = Path("temp") / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Starting pipeline in %s", job_dir)

    try:
        history = load_history()
        idea = generate_video_idea(history)
        logger.info("Idea selected: %s", idea["title"])

        thumbnail_path = generate_thumbnail(
            prompt=idea["visual_prompt"],
            output_path=job_dir / "thumbnail.png",
            title=idea["title"],
        )
        logger.info("Thumbnail ready: %s", thumbnail_path)

        music_path, music_meta = generate_music(
            prompt=idea["music_prompt"],
            output_path=job_dir / "music.mp3",
        )
        logger.info("Music ready: %s", music_path)

        video_path = create_video(
            image_path=thumbnail_path,
            audio_path=music_path,
            output_path=job_dir / "video.mp4",
            duration_seconds=idea["duration_minutes"] * 60,
            loop_audio=Config.loop_audio,
        )
        logger.info("Video ready: %s", video_path)

        long_upload = upload_video_and_thumbnail(
            video_path=video_path,
            thumbnail_path=thumbnail_path,
            title=idea["title"],
            description=idea["description"],
            tags=idea["tags"],
        )
        logger.info("Long upload finished: %s", long_upload.get("video_url"))

        short_a_path, short_a_meta = generate_short(
            reel_type="A",
            music_path=music_path,
            output_path=job_dir / "short_A.mp4",
            temp_dir=job_dir / "short_assets_A",
        )
        short_a_upload = upload_video_and_thumbnail(
            video_path=short_a_path,
            thumbnail_path=thumbnail_path,
            title=short_a_meta["title"],
            description=short_a_meta["description"],
            tags=short_a_meta["tags"],
        )
        logger.info("Short A uploaded: %s", short_a_upload.get("video_url"))

        short_b_path, short_b_meta = generate_short(
            reel_type="B",
            music_path=music_path,
            output_path=job_dir / "short_B.mp4",
            temp_dir=job_dir / "short_assets_B",
        )
        short_b_upload = upload_video_and_thumbnail(
            video_path=short_b_path,
            thumbnail_path=thumbnail_path,
            title=short_b_meta["title"],
            description=short_b_meta["description"],
            tags=short_b_meta["tags"],
        )
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
            "short_a": {
                "upload": short_a_upload,
                "meta": short_a_meta,
            },
            "short_b": {
                "upload": short_b_upload,
                "meta": short_b_meta,
            },
        })
        logger.info("History updated")

        if Config.cleanup_on_success:
            cleanup_temp_dir(job_dir)
            logger.info("Temporary files removed: %s", job_dir)
        else:
            logger.info("Temporary files kept at: %s", job_dir)

    except Exception:
        logger.exception("Pipeline failed. Temporary files preserved at %s", job_dir)
        raise


if __name__ == "__main__":
    run()
