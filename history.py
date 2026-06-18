import json
import datetime
from pathlib import Path

HISTORY_FILE = Path("outputs/history.json")


def _ensure_file():
    Path("outputs").mkdir(exist_ok=True)
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text("[]", encoding="utf-8")


def load_history():
    """Returns the list of saved report entries, newest first."""
    _ensure_file()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return sorted(data, key=lambda x: x["timestamp"], reverse=True)
    except (json.JSONDecodeError, KeyError):
        return []


def add_entry(company_name: str, content: str, mode: str = "single", extra_label: str = ""):
    """Saves a new report entry to history and returns the entry dict."""
    _ensure_file()
    history = load_history()

    entry = {
        "id": datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f"),
        "company": company_name,
        "mode": mode,
        "label": extra_label or company_name,
        "timestamp": datetime.datetime.now().isoformat(),
        "display_time": datetime.datetime.now().strftime("%d %b, %I:%M %p"),
        "content": content,
    }

    history.insert(0, entry)
    # Keep only the most recent 50 to avoid the file growing unbounded
    history = history[:50]

    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)

    return entry


def clear_history():
    """Wipes all saved history entries."""
    _ensure_file()
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)