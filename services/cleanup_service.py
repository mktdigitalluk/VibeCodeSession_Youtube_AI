import logging
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)


def cleanup_temp_dir(path) -> None:
    path = Path(path)
    if not path.exists():
        logger.warning("Cleanup skipped — path does not exist: %s", path)
        return

    try:
        size_mb = sum(f.stat().st_size for f in path.rglob("*") if f.is_file()) / (1024 * 1024)
        logger.info("Cleaning up temp dir | path=%s | size_mb=%.1f", path, size_mb)
        shutil.rmtree(str(path), ignore_errors=False)
        logger.info("Temp dir removed successfully: %s", path)
    except Exception as exc:
        logger.warning("Cleanup failed for %s — files may remain on disk: %s", path, exc)
