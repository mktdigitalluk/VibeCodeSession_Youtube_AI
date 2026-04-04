import json
import logging
from pathlib import Path
from config import Config

logger = logging.getLogger(__name__)


def load_history() -> list:
    path = Path(Config.history_file)
    if not path.exists():
        logger.info("History file not found, starting fresh | path=%s", path)
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        logger.info("History loaded | entries=%d | path=%s", len(data), path)
        return data
    except Exception as exc:
        logger.warning("Failed to parse history file, starting fresh | path=%s | error=%s", path, exc)
        return []


def save_history(entry: dict) -> None:
    path = Path(Config.history_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    history = load_history()
    history.append(entry)
    history = history[-Config.history_size:]
    try:
        path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("History saved | total_entries=%d | path=%s", len(history), path)
    except Exception as exc:
        logger.error("Failed to save history | path=%s | error=%s", path, exc)
        raise
