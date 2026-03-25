import os
import subprocess
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv("keys.env")

STREAM_URL = os.getenv("YOUTUBE_STREAM_URL")
STREAM_KEY = os.getenv("YOUTUBE_STREAM_KEY")

RTMP_URL = f"{STREAM_URL}/{STREAM_KEY}"

TEMP_DIR = Path("temp")
IMAGE_PATH = TEMP_DIR / "live.png"


def get_all_mp3_files():
    return sorted(TEMP_DIR.glob("job_*/music.mp3"))


def build_ffmpeg_command(audio_file):
    return [
        "ffmpeg",
        "-re",
        "-loop", "1",
        "-i", str(IMAGE_PATH),
        "-i", str(audio_file),
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-tune", "stillimage",
        "-c:a", "aac",
        "-b:a", "160k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        "-f", "flv",
        RTMP_URL
    ]


def stream_loop():
    while True:
        mp3_files = get_all_mp3_files()

        if not mp3_files:
            print("No MP3 files found. Waiting...")
            time.sleep(30)
            continue

        for audio in mp3_files:
            print(f"Streaming: {audio}")

            cmd = build_ffmpeg_command(audio)

            try:
                subprocess.run(cmd)
            except Exception as e:
                print(f"Error streaming {audio}: {e}")
                time.sleep(5)


if __name__ == "__main__":
    if not IMAGE_PATH.exists():
        raise FileNotFoundError("live.png not found in temp/ folder")

    print("Starting live stream...")
    stream_loop()
