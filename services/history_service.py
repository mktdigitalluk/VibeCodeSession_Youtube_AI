from pathlib import Path
import json
from config import Config

def load_history():
    path = Path(Config.history_file)
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_history(entry):
    path = Path(Config.history_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    history = load_history()
    history.append(entry)
    history = history[-Config.history_size:]
    path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
