import json
from pathlib import Path
FILE = Path("data/history.json")

def load_history():
    return json.loads(FILE.read_text()) if FILE.exists() else []

def save_history(h):
    FILE.write_text(json.dumps(h,indent=2))
