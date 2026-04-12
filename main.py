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
from services.state_service import load_state, init_state, mark_done, is_done, resolve_job_id
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
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# PIPELINE
# Steps: idea → thumbnail → music → video → upload_long
#        → short → upload_short → history
#
# Each step is checkpointed in data/state_YYYYMMDD.json.
# Re-running main.py on the same day skips completed steps and
# only re-executes what failed or was never reached.
# If a step's output file was deleted (e.g. after cleanup),
# that step is automatically re-run even if state says done.
# ─────────────────────────────────────────────────────────────

def run() -> None:
    Path("temp").mkdir(parents=True, exist_ok=True)
    Path("data").mkdir(parents=True, exist_ok=True)

    # Resume the most recent incomplete job; otherwise start today's job
    job_id = resolve_job_id()
    job_dir = Path("temp") / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    # Load existing state or create new one
    state = load_state(job_id)
    if not state:
        state = init_state(job_id)

    completed = [k for k, v in state.get("steps", {}).items() if v.get("status") == "done"]

    logger.info("=" * 60)
    logger.info("PIPELINE START | job_id=%s | log=%s", job_id, log_file)
    if completed:
        logger.info("Resuming — already done: %s", ", ".join(completed))
    else:
        logger.info("Fresh run — no completed steps yet.")
    logger.info("=" * 60)

    try:

        # ── [1/8] Idea ────────────────────────────────────────────
        if is_done(state, "idea"):
            idea = state["steps"]["idea"]["data"]
            logger.info("[1/8] SKIP idea | title=%r", idea["title"])
        else:
            logger.info("[1/8] Generating video idea")
            history = load_history()
            idea = generate_video_idea(history)
            state = mark_done(job_id, state, "idea", {"data": idea})
            logger.info("[1/8] DONE idea | title=%r | theme=%r | duration_minutes=%d",
                        idea["title"], idea.get("theme"), idea.get("duration_minutes"))

        # ── [2/8] Thumbnail ───────────────────────────────────────
        thumbnail_path = str(job_dir / "thumbnail.jpg")
        if is_done(state, "thumbnail", thumbnail_path):
            logger.info("[2/8] SKIP thumbnail | path=%s | size_kb=%.1f",
                        thumbnail_path, Path(thumbnail_path).stat().st_size / 1024)
        else:
            logger.info("[2/8] Generating thumbnail (Replicate Flux 16:9)")
            result = generate_thumbnail(
                prompt=idea["visual_prompt"],
                output_path=job_dir / "thumbnail.jpg",
                title=idea["title"],
            )
            thumbnail_path = str(result)
            state = mark_done(job_id, state, "thumbnail", {"path": thumbnail_path})
            logger.info("[2/8] DONE thumbnail | path=%s | size_kb=%.1f",
                        thumbnail_path, Path(thumbnail_path).stat().st_size / 1024)

        # ── [3/8] Music ───────────────────────────────────────────
        music_path = str(job_dir / "music.mp3")
        if is_done(state, "music", music_path):
            music_meta = state["steps"]["music"]["meta"]
            logger.info("[3/8] SKIP music | path=%s | size_kb=%.1f",
                        music_path, Path(music_path).stat().st_size / 1024)
        else:
            logger.info("[3/8] Generating music (Kie.ai)")
            result_path, music_meta = generate_music(
                prompt=idea["music_prompt"],
                output_path=job_dir / "music.mp3",
            )
            music_path = str(result_path)
            state = mark_done(job_id, state, "music", {"path": music_path, "meta": music_meta})
            logger.info("[3/8] DONE music | path=%s | size_kb=%.1f",
                        music_path, Path(music_path).stat().st_size / 1024)

        # ── [4/8] Long video ──────────────────────────────────────
        video_path = str(job_dir / "video.mp4")
        if is_done(state, "video", video_path):
            logger.info("[4/8] SKIP video | path=%s | size_mb=%.1f",
                        video_path, Path(video_path).stat().st_size / (1024 * 1024))
        else:
            duration_seconds = idea["duration_minutes"] * 60
            logger.info("[4/8] Creating long video | duration=%ds (%dmin) | loop_audio=%s",
                        duration_seconds, idea["duration_minutes"], Config.loop_audio)
            result_path = create_video(
                image_path=thumbnail_path,
                audio_path=music_path,
                output_path=job_dir / "video.mp4",
                duration_seconds=duration_seconds,
                loop_audio=Config.loop_audio,
            )
            video_path = str(result_path)
            state = mark_done(job_id, state, "video", {"path": video_path})
            logger.info("[4/8] DONE video | path=%s | size_mb=%.1f",
                        video_path, Path(video_path).stat().st_size / (1024 * 1024))

        # ── [5/8] Upload long video ───────────────────────────────
        if is_done(state, "upload_long"):
            long_upload = state["steps"]["upload_long"]
            logger.info("[5/8] SKIP upload_long | video_id=%s | url=%s",
                        long_upload.get("video_id"), long_upload.get("video_url"))
        else:
            logger.info("[5/8] Uploading long video | title=%r", idea["title"])
            long_upload = upload_video_and_thumbnail(
                video_path=video_path,
                thumbnail_path=thumbnail_path,
                title=idea["title"],
                description=idea["description"],
                tags=idea["tags"],
            )
            state = mark_done(job_id, state, "upload_long", long_upload)
            logger.info("[5/8] DONE upload_long | video_id=%s | url=%s",
                        long_upload.get("video_id"), long_upload.get("video_url"))

        # ── [6/8] Short video (Replicate 9:16 + music) ───────────
        short_path = str(job_dir / "short.mp4")
        if is_done(state, "short", short_path):
            short_meta = state["steps"]["short"]["meta"]
            logger.info("[6/8] SKIP short | path=%s | size_mb=%.1f",
                        short_path, Path(short_path).stat().st_size / (1024 * 1024))
        else:
            logger.info("[6/8] Generating short video (Replicate Flux 9:16)")
            result_path, short_meta = generate_short(
                idea=idea,
                music_path=music_path,
                output_path=job_dir / "short.mp4",
                temp_dir=job_dir / "short_assets",
            )
            short_path = str(result_path)
            state = mark_done(job_id, state, "short", {"path": short_path, "meta": short_meta})
            logger.info("[6/8] DONE short | path=%s | title=%r",
                        short_path, short_meta["title"])

        # ── [7/8] Upload short ────────────────────────────────────
        if is_done(state, "upload_short"):
            short_upload = state["steps"]["upload_short"]
            logger.info("[7/8] SKIP upload_short | video_id=%s | url=%s",
                        short_upload.get("video_id"), short_upload.get("video_url"))
        else:
            logger.info("[7/8] Uploading short | title=%r", short_meta["title"])
            short_upload = upload_video_and_thumbnail(
                video_path=short_path,
                thumbnail_path=thumbnail_path,
                title=short_meta["title"],
                description=short_meta["description"],
                tags=short_meta["tags"],
            )
            state = mark_done(job_id, state, "upload_short", short_upload)
            logger.info("[7/8] DONE upload_short | video_id=%s | url=%s",
                        short_upload.get("video_id"), short_upload.get("video_url"))

        # ── [8/8] Save history ────────────────────────────────────
        if is_done(state, "history"):
            logger.info("[8/8] SKIP history (already saved)")
        else:
            logger.info("[8/8] Saving history")
            save_history({
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "job_id": job_id,
                "title": idea["title"],
                "theme": idea["theme"],
                "place_id": idea.get("place_id"),
                "place": idea.get("place"),
                "time_of_day": idea.get("time_of_day"),
                "weather": idea.get("weather"),
                "mood": idea.get("mood"),
                "atmosphere": idea.get("atmosphere"),
                "duration_minutes": idea["duration_minutes"],
                "tags": idea["tags"],
                "youtube_video_id": long_upload["video_id"],
                "youtube_video_url": long_upload["video_url"],
                "music_meta": music_meta,
                "short": {
                    "upload": short_upload,
                    "meta": short_meta,
                },
            })
            state = mark_done(job_id, state, "history", {})
            logger.info("[8/8] DONE history")

        # ── Cleanup ───────────────────────────────────────────────
        # State file lives in data/ and is NOT deleted by cleanup.
        if Config.cleanup_on_success:
            cleanup_temp_dir(job_dir)
            logger.info("Cleanup complete | removed=%s", job_dir)
        else:
            logger.info("Cleanup skipped (CLEANUP_ON_SUCCESS=false) | files at=%s", job_dir)

        logger.info("=" * 60)
        logger.info("PIPELINE COMPLETE | job_id=%s", job_id)
        logger.info("State preserved at: data/state_%s.json", job_id)
        logger.info("=" * 60)

    except Exception as exc:
        logger.exception("PIPELINE FAILED | job_id=%s | error=%s", job_id, exc)
        logger.error(
            "Re-run ./run.sh to resume from the last completed step. "
            "State at: data/state_%s.json | Temp files at: %s",
            job_id, job_dir,
        )
        raise


if __name__ == "__main__":
    run()

