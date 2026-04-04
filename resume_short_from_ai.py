from pathlib import Path
import subprocess
import logging
from dotenv import load_dotenv

from services.youtube_service import upload_video_and_thumbnail

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / "keys.env")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

JOB_ID = "job_ai_test_hk"

TITLE = "Hong Kong Coding Vibes 🌃 #shorts"
DESCRIPTION = "Coding in Hong Kong at night 🌃\n\nFull video on the channel 👇"
TAGS = ["musictowork", "coding", "hongkong", "shorts", "chill"]


def generate_short(video_path, output_path):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-t", "25",
        "-vf", "crop=ih*9/16:ih,scale=1080:1920",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-c:a", "aac",
        str(output_path)
    ]
    subprocess.run(cmd, check=True)


def extract_thumbnail(video_path, thumb_path):
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-frames:v", "1",
        str(thumb_path)
    ]
    subprocess.run(cmd, check=True)


def run():
    job_dir = Path("temp") / JOB_ID

    ai_video = job_dir / "ai_generated.mp4"
    short_video = job_dir / "short_ai.mp4"
    thumbnail = job_dir / "thumb_short.jpg"

    if not ai_video.exists():
        raise Exception(f"AI video not found: {ai_video}")

    logger.info("Generating SHORT from AI video...")
    generate_short(ai_video, short_video)

    logger.info("Extracting thumbnail...")
    extract_thumbnail(short_video, thumbnail)

    logger.info("Uploading SHORT to YouTube...")
    upload = upload_video_and_thumbnail(
        video_path=str(short_video),
        thumbnail_path=str(thumbnail),
        title=TITLE,
        description=DESCRIPTION,
        tags=TAGS,
    )

    logger.info(f"SHORT uploaded: {upload.get('video_url')}")


if __name__ == "__main__":
    run()
