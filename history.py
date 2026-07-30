import datetime
import json
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
        with open(HISTORY_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return sorted(data, key=lambda x: x["timestamp"], reverse=True)
    except (json.JSONDecodeError, KeyError):
        return []


def add_entry(company_name: str, content: str, mode: str = "single", extra_label: str = ""):
    """Saves a new report entry to history and returns the entry dict."""
    _ensure_file()
    history = load_history()

    # Computed once and reused for id/timestamp/display_time so all three
    # reflect the exact same instant rather than three slightly-drifting
    # datetime.now() calls. UTC (tz-aware) instead of naive local time --
    # this shifts display_time from server-local to UTC, which is the
    # correct behaviour for a Streamlit Cloud deploy anyway, since the
    # server's local timezone isn't meaningful to the person viewing it.
    now = datetime.datetime.now(datetime.timezone.utc)

    entry = {
        "id": now.strftime("%Y%m%d_%H%M%S_%f"),
        "company": company_name,
        "mode": mode,
        "label": extra_label or company_name,
        "timestamp": now.isoformat(),
        "display_time": now.strftime("%d %b, %I:%M %p UTC"),
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