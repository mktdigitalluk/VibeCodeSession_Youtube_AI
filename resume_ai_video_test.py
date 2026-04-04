from pathlib import Path
import logging
from datetime import datetime, timezone
from dotenv import load_dotenv

from services.video_generation_service import create_video_from_ai
from services.youtube_service import upload_video_and_thumbnail

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / "keys.env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ===== CONFIG =====
JOB_ID = "job_ai_test_hk"

PROMPT = (
    "A software developer coding on a laptop facing the Hong Kong skyline at night, "
    "neon lights reflecting on the water, cinematic, ultra realistic, 4k, no text"
)

TITLE = "Hong Kong Night Coding Flow | AI Generated Visual"
DESCRIPTION = "AI generated video of a developer coding in front of Hong Kong skyline at night. Focus and deep work vibes."
TAGS = ["musictowork", "coding", "hongkong", "ai", "deepwork", "chill"]
# ==================


def run():
    job_dir = Path("temp") / JOB_ID
    job_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Generating AI video with Replicate...")

    video_path = create_video_from_ai(PROMPT, job_dir)

    if not Path(video_path).exists():
        raise Exception("AI video was not generated")

    logger.info("AI video generated: %s", video_path)

    # thumbnail fallback (use first frame extracted)
    thumbnail_path = job_dir / "thumbnail.jpg"

    import subprocess
    subprocess.run([
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-frames:v", "1",
        str(thumbnail_path)
    ], check=True)

    logger.info("Thumbnail generated")

    logger.info("Uploading to YouTube...")

    upload = upload_video_and_thumbnail(
        video_path=str(video_path),
        thumbnail_path=str(thumbnail_path),
        title=TITLE,
        description=DESCRIPTION,
        tags=TAGS,
    )

    logger.info("Upload complete: %s", upload.get("video_url"))


if __name__ == "__main__":
    run()
