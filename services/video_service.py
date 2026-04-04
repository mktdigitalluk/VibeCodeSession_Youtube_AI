from pathlib import Path
import logging
import subprocess
import tempfile

logger = logging.getLogger(__name__)


def _run(cmd):
    cmd_str = [str(part) for part in cmd]
    logger.info("ffmpeg command: %s", " ".join(cmd_str))
    try:
        result = subprocess.run(
            cmd_str,
            check=True,
            capture_output=True,
            text=True,
        )
        if result.stderr:
            logger.debug("ffmpeg stderr: %s", result.stderr[-2000:])  # last 2000 chars
    except subprocess.CalledProcessError as exc:
        logger.error("ffmpeg failed | returncode=%d | stderr=%s", exc.returncode, exc.stderr[-2000:])
        raise RuntimeError(f"ffmpeg command failed (exit {exc.returncode}). See logs above.") from exc


def create_video(
    image_path,
    audio_path,
    output_path: Path,
    duration_seconds: int,
    loop_audio: bool,
) -> str:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Creating video | image=%s | audio=%s | duration_seconds=%d | loop_audio=%s",
        image_path, audio_path, duration_seconds, loop_audio,
    )

    if not loop_audio:
        logger.info("Mode: single-pass (no audio loop) — video length = audio length")
        _run([
            "ffmpeg", "-y",
            "-loop", "1",
            "-framerate", "2",
            "-i", image_path,
            "-i", audio_path,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-shortest",
            str(output_path),
        ])
    else:
        logger.info("Mode: loop audio to fill %d seconds (%d minutes)", duration_seconds, duration_seconds // 60)
        with tempfile.TemporaryDirectory() as tmpdir:
            looped_audio = Path(tmpdir) / "looped_audio.mp3"
            logger.info("Creating looped audio at %s", looped_audio)
            _run([
                "ffmpeg", "-y",
                "-stream_loop", "-1",
                "-i", audio_path,
                "-t", str(duration_seconds),
                "-c:a", "libmp3lame",
                str(looped_audio),
            ])
            logger.info("Looped audio ready, composing final video")
            _run([
                "ffmpeg", "-y",
                "-loop", "1",
                "-framerate", "2",
                "-i", image_path,
                "-i", str(looped_audio),
                "-c:v", "libx264",
                "-preset", "veryfast",
                "-tune", "stillimage",
                "-c:a", "aac",
                "-b:a", "192k",
                "-pix_fmt", "yuv420p",
                "-shortest",
                str(output_path),
            ])

    size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info("Video created | path=%s | size_mb=%.1f", output_path, size_mb)
    return str(output_path)
