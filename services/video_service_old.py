from pathlib import Path
import logging, subprocess, tempfile
logger = logging.getLogger(__name__)

def _run(cmd):
    cmd_str = [str(part) for part in cmd]
    logger.info("Running command: %s", " ".join(cmd_str))
    subprocess.run(cmd_str, check=True)

def create_video(image_path, audio_path, output_path: Path, duration_seconds: int, loop_audio: bool):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not loop_audio:
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
        return str(output_path)
    with tempfile.TemporaryDirectory() as tmpdir:
        looped_audio = Path(tmpdir) / "looped_audio.mp3"
        _run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", audio_path, "-t", str(duration_seconds), "-c:a", "libmp3lame", str(looped_audio)])
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
    return str(output_path)
