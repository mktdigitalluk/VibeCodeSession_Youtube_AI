"""
state_service.py — daily job checkpoint system.

State files live in data/state_YYYYMMDD.json (outside temp/).
This means temp media files can be cleaned up safely without losing checkpoint info.

Step names used throughout the pipeline:
  idea | thumbnail | music | video | upload_long | short | upload_short | history
"""

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from config import Config

logger = logging.getLogger(__name__)


def _state_path(job_id: str) -> Path:
    """State files live in data/ so they survive temp/ cleanup."""
    return Path(Config.history_file).parent / f"state_{job_id}.json"


def load_state(job_id: str) -> dict:
    path = _state_path(job_id)
    if not path.exists():
        logger.info("No existing state for job_id=%s — starting fresh.", job_id)
        return {}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
        done = [k for k, v in state.get("steps", {}).items() if v.get("status") == "done"]
        logger.info("State loaded | job_id=%s | completed_steps=%s", job_id, done or "none")
        return state
    except Exception as exc:
        logger.warning("Failed to load state file %s — starting fresh. error=%s", path, exc)
        return {}


def save_state(job_id: str, state: dict) -> None:
    path = _state_path(job_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        logger.error("Failed to save state file %s: %s", path, exc)
        raise


def init_state(job_id: str) -> dict:
    """Create and persist an empty state for a new job."""
    state = {
        "job_id": job_id,
        "date": date.today().isoformat(),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "steps": {},
    }
    save_state(job_id, state)
    logger.info("New state initialised | job_id=%s", job_id)
    return state


def mark_done(job_id: str, state: dict, step: str, data: dict = None) -> dict:
    """Mark a step as done, merge optional data, and persist."""
    if "steps" not in state:
        state["steps"] = {}
    state["steps"][step] = {
        "status": "done",
        "completed_at": datetime.now(timezone.utc).isoformat(),
        **(data or {}),
    }
    save_state(job_id, state)
    logger.info("Step marked done | step=%s | job_id=%s", step, job_id)
    return state


def is_done(state: dict, step: str, file_path: str = None) -> bool:
    """
    Returns True only when:
    - the step is marked 'done' in state, AND
    - if file_path is provided, the file actually exists on disk.

    The file check protects against the case where temp files were cleaned up
    but the state still says the step was completed.
    """
    step_data = state.get("steps", {}).get(step, {})
    if step_data.get("status") != "done":
        return False
    if file_path and not Path(file_path).exists():
        logger.info(
            "Step %r is marked done but file is missing (%s) — will re-run.",
            step, file_path,
        )
        return False
    return True


def today_job_id() -> str:
    return f"job_{date.today().strftime('%Y%m%d')}"
