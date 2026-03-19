from pathlib import Path
from datetime import datetime
import logging

from services.short_service import generate_short
from services.youtube_service import upload_video_and_thumbnail

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def _find_job_dir(temp_dir: Path) -> Path:
    if not temp_dir.exists():
        raise FileNotFoundError(f"Pasta temp não encontrada: {temp_dir}")

    today = datetime.now().strftime("%Y%m%d")

    today_jobs = sorted(
        [p for p in temp_dir.iterdir() if p.is_dir() and p.name.startswith(f"job_{today}")],
        key=lambda p: p.name,
        reverse=True,
    )
    if today_jobs:
        return today_jobs[0]

    all_jobs = sorted(
        [p for p in temp_dir.iterdir() if p.is_dir() and p.name.startswith("job_")],
        key=lambda p: p.name,
        reverse=True,
    )
    if all_jobs:
        logger.warning("Nenhum job de hoje encontrado. Usando o mais recente: %s", all_jobs[0])
        return all_jobs[0]

    raise FileNotFoundError(f"Nenhum job encontrado em {temp_dir}")


def run() -> None:
    # 👇 CAMINHO CORRIGIDO PARA SUA ESTRUTURA
    temp_dir = Path.home() / "Documents" / "temp"

    job_dir = _find_job_dir(temp_dir)

    logger.info("Usando job: %s", job_dir)

    music_path = job_dir / "music.mp3"
    thumbnail_path = job_dir / "thumbnail.png"

    if not music_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {music_path}")
    if not thumbnail_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {thumbnail_path}")

    short_a_path, short_a_meta = generate_short(
        reel_type="A",
        music_path=str(music_path),
        output_path=job_dir / "manual_short_A.mp4",
        temp_dir=job_dir / "manual_short_assets_A",
    )

    short_a_upload = upload_video_and_thumbnail(
        video_path=short_a_path,
        thumbnail_path=str(thumbnail_path),
        title=short_a_meta["title"],
        description=short_a_meta["description"],
        tags=short_a_meta["tags"],
    )
    logger.info("Short A enviado: %s", short_a_upload.get("video_url"))

    short_b_path, short_b_meta = generate_short(
        reel_type="B",
        music_path=str(music_path),
        output_path=job_dir / "manual_short_B.mp4",
        temp_dir=job_dir / "manual_short_assets_B",
    )

    short_b_upload = upload_video_and_thumbnail(
        video_path=short_b_path,
        thumbnail_path=str(thumbnail_path),
        title=short_b_meta["title"],
        description=short_b_meta["description"],
        tags=short_b_meta["tags"],
    )
    logger.info("Short B enviado: %s", short_b_upload.get("video_url"))


if __name__ == "__main__":
    run()
