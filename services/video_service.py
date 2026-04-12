import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)


def _run(cmd: list[str]) -> None:
    logger.info("Running ffmpeg command | cmd=%s", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _ffmpeg_exists() -> bool:
    return shutil.which("ffmpeg") is not None


def _ffprobe_exists() -> bool:
    return shutil.which("ffprobe") is not None


def _get_audio_duration_seconds(audio_path: Path) -> float:
    if not _ffprobe_exists():
        raise RuntimeError("ffprobe not found in PATH")

    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(audio_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"Could not read audio duration from {audio_path}") from exc


def _generate_silence(output_path: Path, duration_seconds: int) -> None:
    _run([
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", "anullsrc=r=48000:cl=stereo",
        "-t", str(duration_seconds),
        "-c:a", "aac",
        "-b:a", "256k",
        "-ar", "48000",
        "-ac", "2",
        str(output_path),
    ])


def _create_looped_audio(audio_path: Path, output_path: Path, duration_seconds: int) -> None:
    """
    Cria um áudio temporário com duração exata do vídeo.
    Usa stream_loop para repetir e corta no tempo desejado.
    """
    _run([
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(audio_path),
        "-t", str(duration_seconds),
        "-c:a", "libmp3lame",
        "-b:a", "320k",
        str(output_path),
    ])


def _create_padded_audio(audio_path: Path, output_path: Path, duration_seconds: int) -> None:
    """
    Mantém o áudio original e completa o restante com silêncio para chegar
    exatamente na duração do vídeo.
    """
    original_duration = _get_audio_duration_seconds(audio_path)

    if original_duration >= duration_seconds:
        _run([
            "ffmpeg", "-y",
            "-i", str(audio_path),
            "-t", str(duration_seconds),
            "-c:a", "libmp3lame",
            "-b:a", "320k",
            str(output_path),
        ])
        return

    silence_duration = max(0, int(duration_seconds - original_duration))
    with tempfile.TemporaryDirectory() as tmpdir:
        silence_path = Path(tmpdir) / "silence.m4a"
        list_path = Path(tmpdir) / "concat.txt"

        _generate_silence(silence_path, silence_duration)

        list_path.write_text(
            f"file '{audio_path.resolve()}'\nfile '{silence_path.resolve()}'\n",
            encoding="utf-8",
        )

        _run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_path),
            "-t", str(duration_seconds),
            "-c:a", "libmp3lame",
            "-b:a", "320k",
            str(output_path),
        ])


def generate_video(
    image_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    duration_seconds: int,
    loop_audio: bool = True,
) -> Path:
    """
    Gera o vídeo principal a partir de uma imagem e um áudio.

    Regras:
    - O vídeo SEMPRE respeita duration_seconds.
    - Se loop_audio=True, repete o áudio até a duração desejada.
    - Se loop_audio=False, mantém o áudio original e preenche o restante com silêncio.
    - Saída em AAC 256k, 48kHz, estéreo, com loudnorm.
    """
    if not _ffmpeg_exists():
        raise RuntimeError("ffmpeg not found in PATH")

    image_path = Path(image_path)
    audio_path = Path(audio_path)
    output_path = Path(output_path)

    if not image_path.exists():
        raise FileNotFoundError(f"Image not found: {image_path}")
    if not audio_path.exists():
        raise FileNotFoundError(f"Audio not found: {audio_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        prepared_audio = Path(tmpdir) / "prepared_audio.mp3"

        if loop_audio:
            logger.info(
                "Preparing looped audio to exact duration | duration_seconds=%s",
                duration_seconds,
            )
            _create_looped_audio(audio_path, prepared_audio, duration_seconds)
        else:
            logger.info(
                "Preparing padded audio to exact duration | duration_seconds=%s",
                duration_seconds,
            )
            _create_padded_audio(audio_path, prepared_audio, duration_seconds)

        _run([
            "ffmpeg", "-y",
            "-loop", "1",
            "-framerate", "2",
            "-i", str(image_path),
            "-i", str(prepared_audio),
            "-t", str(duration_seconds),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "256k",
            "-ar", "48000",
            "-ac", "2",
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            str(output_path),
        ])

    logger.info("Video generated successfully | path=%s", output_path)
    return output_path
