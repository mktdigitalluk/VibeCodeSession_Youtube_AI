import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config import Config

logger = logging.getLogger(__name__)


def _data_dir() -> Path:
    return Path(Config.history_file).parent


def _state_path(job_id: str) -> Path:
    return _data_dir() / f"state_{job_id}.json"


def _now_local() -> datetime:
    try:
        return datetime.now(ZoneInfo(Config.business_timezone))
    except Exception:
        return datetime.now()


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
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def init_state(job_id: str) -> dict:
    state = {
        "job_id": job_id,
        "date": _now_local().date().isoformat(),
        "created_at_local": _now_local().isoformat(),
        "steps": {},
    }
    save_state(job_id, state)
    logger.info("New state initialised | job_id=%s", job_id)
    return state


def mark_done(job_id: str, state: dict, step: str, data: dict = None) -> dict:
    state.setdefault("steps", {})
    state["steps"][step] = {
        "status": "done",
        "completed_at_local": _now_local().isoformat(),
        **(data or {}),
    }
    save_state(job_id, state)
    logger.info("Step marked done | step=%s | job_id=%s", step, job_id)
    return state


def is_done(state: dict, step: str, file_path: str = None) -> bool:
    step_data = state.get("steps", {}).get(step, {})
    if step_data.get("status") != "done":
        return False
    if file_path and not Path(file_path).exists():
        logger.info("Step %r is marked done but file is missing (%s) — will re-run.", step, file_path)
        return False
    return True


def today_job_id() -> str:
    return f"job_{_now_local().strftime('%Y%m%d')}"


def list_state_paths() -> list[Path]:
    return sorted(_data_dir().glob('state_job_*.json'))


def first_incomplete_job_id() -> str | None:
    required_steps = ["idea", "thumbnail", "music", "video", "upload_long", "short", "upload_short", "history"]
    for path in sorted(list_state_paths(), reverse=True):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        steps = state.get("steps", {})
        if any(steps.get(step, {}).get("status") != "done" for step in required_steps):
            job_id = state.get("job_id")
            if job_id:
                logger.info("Found incomplete prior job to resume | job_id=%s", job_id)
                return job_id
    return None


def resolve_job_id() -> str:
    return first_incomplete_job_id() or today_job_id()
