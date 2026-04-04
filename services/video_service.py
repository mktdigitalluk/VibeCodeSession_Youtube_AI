from pathlib import Path
import logging
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)


def _run(cmd):
    cmd_str = [str(x) for x in cmd]
    logger.info("Running command: %s", " ".join(cmd_str))
    subprocess.run(cmd_str, check=True)


def _probe_duration(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def _loop_audio_to_duration(audio_path: Path, duration_seconds: int, temp_dir: Path) -> Path:
    output_path = temp_dir / "looped_audio.mp3"

    _run([
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(audio_path),
        "-t", str(duration_seconds),
        "-c:a", "libmp3lame",
        "-b:a", "128k",
        str(output_path),
    ])

    return output_path


def create_video(image_path, audio_path, output_path, duration_seconds, loop_audio=True):
    image_path = Path(image_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir_str:
        tmp_dir = Path(tmp_dir_str)

        final_audio_path = audio_path
        if loop_audio:
            audio_duration = _probe_duration(audio_path)
            if audio_duration < duration_seconds:
                final_audio_path = _loop_audio_to_duration(audio_path, duration_seconds, tmp_dir)

        temp_output = output_path.with_suffix(".tmp.mp4")

        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-framerate", "1",
            "-i", str(image_path),
            "-i", str(final_audio_path),
            "-t", str(duration_seconds),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "28",
            "-threads", "1",
            "-tune", "stillimage",
            "-pix_fmt", "yuv420p",
            "-r", "1",
            "-g", "4",
            "-keyint_min", "4",
            "-sc_threshold", "0",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            "-movflags", "+faststart",
            str(temp_output),
        ]

        _run(cmd)

        shutil.move(str(temp_output), str(output_path))

    logger.info("Video created successfully: %s", output_path)
    return str(output_path)
