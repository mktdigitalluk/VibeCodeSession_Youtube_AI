import json
from pathlib import Path
FILE = Path("data/state.json")

def load_state():
    return json.loads(FILE.read_text()) if FILE.exists() else {}

def save_state(s):
    FILE.write_text(json.dumps(s,indent=2))

def is_done(s,k): return s.get(k)

def mark_done(s,k): s[k]=True
