from pathlib import Path
from datetime import datetime, timezone
import json
import logging

from dotenv import load_dotenv

from agents.idea_agent import generate_video_idea
from services.image_service import generate_thumbnail
from services.music_service import generate_music
from services.video_service import create_video
from services.short_service import generate_short
from services.youtube_service import upload_video_and_thumbnail
from services.history_service import load_history, save_history
from config import Config

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / "keys.env")

log_dir = Path("logs")
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=getattr(logging, getattr(Config, "log_level", "INFO").upper(), logging.INFO),
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def _write_job_state(job_dir: Path, state: dict) -> None:
    state_path = job_dir / "job_metadata.json"
    with state_path.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def run() -> None:
    Path("temp").mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)

    job_id = datetime.now(timezone.utc).strftime("job_%Y%m%dT%H%M%SZ")
    job_dir = Path("temp") / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "job_id": job_id,
        "created_at_utc": _now_utc(),
        "status": "started",
        "steps": {},
        "idea": None,
        "paths": {
            "job_dir": str(job_dir),
            "thumbnail": str(job_dir / "thumbnail.png"),
            "music": str(job_dir / "music.mp3"),
            "video": str(job_dir / "video.mp4"),
        },
        "uploads": {
            "long": None,
            "shorts": []
        }
    }
    _write_job_state(job_dir, state)

    logger.info("Starting pipeline in %s", job_dir)

    try:
        history = load_history()
        state["steps"]["history_loaded"] = {"done_at_utc": _now_utc()}
        _write_job_state(job_dir, state)

        # Supports both signatures: generate_video_idea() or generate_video_idea(history)
        try:
            idea = generate_video_idea(history)
        except TypeError:
            idea = generate_video_idea()

        state["idea"] = idea
        state["status"] = "idea_generated"
        state["steps"]["idea_generated"] = {"done_at_utc": _now_utc()}
        _write_job_state(job_dir, state)
        logger.info("Idea selected: %s", idea["title"])

        thumbnail_path = generate_thumbnail(
            prompt=idea.get("prompt") or idea.get("visual_prompt"),
            output_path=job_dir / "thumbnail.png",
            title=idea["title"],
        )
        state["status"] = "thumbnail_generated"
        state["steps"]["thumbnail_generated"] = {
            "done_at_utc": _now_utc(),
            "path": str(thumbnail_path),
        }
        _write_job_state(job_dir, state)
        logger.info("Thumbnail ready: %s", thumbnail_path)

        music_prompt = idea.get("music_prompt", "focus coding music")
        music_path, music_meta = generate_music(
            prompt=music_prompt,
            output_path=job_dir / "music.mp3",
        )
        state["music_meta"] = music_meta
        state["status"] = "music_generated"
        state["steps"]["music_generated"] = {
            "done_at_utc": _now_utc(),
            "path": str(music_path),
        }
        _write_job_state(job_dir, state)
        logger.info("Music ready: %s", music_path)

        duration_minutes = int(idea.get("duration_minutes", 180))
        duration_seconds = duration_minutes * 60

        video_path = create_video(
            image_path=thumbnail_path,
            audio_path=music_path,
            output_path=job_dir / "video.mp4",
            duration_seconds=duration_seconds,
            loop_audio=getattr(Config, "loop_audio", True),
        )
        state["status"] = "video_generated"
        state["steps"]["video_generated"] = {
            "done_at_utc": _now_utc(),
            "path": str(video_path),
            "duration_seconds": duration_seconds,
        }
        _write_job_state(job_dir, state)
        logger.info("Video ready: %s", video_path)

        long_upload = upload_video_and_thumbnail(
            video_path=video_path,
            thumbnail_path=thumbnail_path,
            title=idea["title"],
            description=idea["description"],
            tags=idea["tags"],
        )
        state["uploads"]["long"] = long_upload
        state["status"] = "long_uploaded"
        state["steps"]["long_uploaded"] = {"done_at_utc": _now_utc()}
        _write_job_state(job_dir, state)
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

            short_record = {
                "type": reel_type,
                "path": str(short_path),
                "meta": short_meta,
                "upload": short_upload,
            }
            shorts.append(short_record)
            state["uploads"]["shorts"] = shorts
            state["status"] = f"short_{reel_type}_uploaded"
            state["steps"][f"short_{reel_type}_uploaded"] = {"done_at_utc": _now_utc()}
            _write_job_state(job_dir, state)

            logger.info("Short %s uploaded: %s", reel_type, short_upload.get("video_url"))

        save_history({
            "created_at_utc": _now_utc(),
            "title": idea["title"],
            "theme": idea.get("theme"),
            "location": idea.get("location"),
            "duration_minutes": duration_minutes,
            "tags": idea["tags"],
            "youtube_video_id": long_upload["video_id"],
            "youtube_video_url": long_upload["video_url"],
            "music_meta": state.get("music_meta"),
            "shorts": shorts,
            "job_metadata_path": str(job_dir / "job_metadata.json"),
        })

        state["status"] = "completed"
        state["steps"]["history_saved"] = {"done_at_utc": _now_utc()}
        _write_job_state(job_dir, state)

        logger.info("Pipeline finished successfully. Metadata saved to %s", job_dir / "job_metadata.json")

    except Exception as exc:
        state["status"] = "failed"
        state["error"] = str(exc)
        state["failed_at_utc"] = _now_utc()
        _write_job_state(job_dir, state)
        logger.exception("Pipeline failed. Metadata preserved at %s", job_dir / "job_metadata.json")
        raise


if __name__ == "__main__":
    run()
