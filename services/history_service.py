import json
import logging
from datetime import datetime
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
        backup = path.with_suffix(f".corrupt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        try:
            path.rename(backup)
        except Exception:
            backup = None
        logger.warning("Failed to parse history file, starting fresh | path=%s | backup=%s | error=%s", path, backup, exc)
        return []


def save_history(entry: dict) -> None:
    path = Path(Config.history_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    history = load_history()
    history.append(entry)
    history = history[-Config.history_size:]
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("History saved | total_entries=%d | path=%s", len(history), path)
