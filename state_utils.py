import json
import os

STATE_FILE = "dataset_state.json"

# function to fetch load state of a file type
def load_state() -> dict:
    """Load per-dataset state from the state file; return {} if missing or unreadable."""
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return {}    

# function to save load state of a file type
def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)
