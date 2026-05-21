"""Storage module for saving dialogs to JSON."""

import json
import os
from datetime import datetime
from typing import Optional


DIALOGS_FILE = "logs/dialogs.json"


def load_dialogs() -> dict:
    """Load all dialogs from JSON file."""
    if not os.path.exists(DIALOGS_FILE):
        return {}
    try:
        with open(DIALOGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}


def save_dialogs(dialogs: dict) -> None:
    """Save all dialogs to JSON file."""
    os.makedirs("logs", exist_ok=True)
    with open(DIALOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(dialogs, f, ensure_ascii=False, indent=2)


def get_user_dialog(user_id: int) -> Optional[dict]:
    """Get dialog for specific user."""
    dialogs = load_dialogs()
    return dialogs.get(str(user_id))


def create_dialog(user_id: int, username: str, name: str) -> dict:
    """Create new dialog entry."""
    dialog = {
        "user_id": user_id,
        "username": username or "",
        "name": name or "",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "history": [],
        "mission": None,
        "explanation": None,
        "neon_color": None,
        "neon_preview_sent": False,
        "completed": False
    }
    dialogs = load_dialogs()
    dialogs[str(user_id)] = dialog
    save_dialogs(dialogs)
    return dialog


def add_message(user_id: int, role: str, text: str, voice: bool = False) -> None:
    """Add message to dialog history."""
    dialogs = load_dialogs()
    user_key = str(user_id)
    if user_key not in dialogs:
        return

    message = {"role": role, "text": text}
    if role == "user":
        message["voice"] = voice

    dialogs[user_key]["history"].append(message)
    save_dialogs(dialogs)


def update_dialog(user_id: int, **kwargs) -> None:
    """Update dialog fields."""
    dialogs = load_dialogs()
    user_key = str(user_id)
    if user_key not in dialogs:
        return

    for key, value in kwargs.items():
        dialogs[user_key][key] = value

    save_dialogs(dialogs)


def get_history(user_id: int) -> list:
    """Get dialog history for user."""
    dialog = get_user_dialog(user_id)
    if dialog:
        return dialog.get("history", [])
    return []


def reset_dialog(user_id: int, username: str, name: str) -> dict:
    """Reset dialog for user (start fresh)."""
    return create_dialog(user_id, username, name)
