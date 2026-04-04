from pathlib import Path
from datetime import datetime, timezone
import logging

from dotenv import load_dotenv

from agents.idea_agent import generate_video_idea
from services.short_service import generate_short
from services.youtube_service import upload_video_and_thumbnail
from services.history_service import load_history, save_history

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / "keys.env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def run():
    job_dir = Path("temp/job_20260403T170424Z")

    thumbnail_path = job_dir / "thumbnail.png"
    music_path = job_dir / "music.mp3"
    video_path = job_dir / "video.mp4"

    if not thumbnail_path.exists():
        raise FileNotFoundError(f"Thumbnail não encontrada: {thumbnail_path}")
    if not music_path.exists():
        raise FileNotFoundError(f"Música não encontrada: {music_path}")
    if not video_path.exists():
        raise FileNotFoundError(f"Vídeo não encontrado: {video_path}")

    history = load_history()

    idea = generate_video_idea(history)
    logger.info("Retomando pipeline com ideia: %s", idea["title"])

    long_upload = upload_video_and_thumbnail(
        video_path=str(video_path),
        thumbnail_path=str(thumbnail_path),
        title=idea["title"],
        description=idea["description"],
        tags=idea["tags"],
    )
    logger.info("Long upload finished: %s", long_upload.get("video_url"))

    shorts = []
    for reel_type in ["female", "male", "futuristic"]:
        short_path, short_meta = generate_short(
            reel_type=reel_type,
            music_path=str(music_path),
            output_path=job_dir / f"short_{reel_type}.mp4",
            temp_dir=job_dir / f"short_assets_{reel_type}",
            idea=idea,
        )

        short_upload = upload_video_and_thumbnail(
            video_path=short_path,
            thumbnail_path=str(thumbnail_path),
            title=short_meta["title"],
            description=short_meta["description"],
            tags=short_meta["tags"],
        )

        logger.info("Short %s uploaded: %s", reel_type, short_upload.get("video_url"))
        shorts.append({
            "type": reel_type,
            "upload": short_upload,
            "meta": short_meta,
        })

    save_history({
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "title": idea["title"],
        "theme": idea.get("theme"),
        "duration_minutes": idea.get("duration_minutes"),
        "tags": idea.get("tags"),
        "youtube_video_id": long_upload["video_id"],
        "youtube_video_url": long_upload["video_url"],
        "shorts": shorts,
        "resumed_from_job": str(job_dir),
    })

    logger.info("Resume pipeline finished successfully")


if __name__ == "__main__":
    run()
