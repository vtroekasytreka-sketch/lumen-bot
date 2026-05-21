"""Dialog state management."""

from enum import Enum
from typing import Optional
import storage


class DialogState(Enum):
    """Possible dialog states."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    AWAITING_SYNTHESIS = "awaiting_synthesis"
    SHOWING_MISSION = "showing_mission"
    AWAITING_NEON_CHOICE = "awaiting_neon_choice"
    COMPLETED = "completed"


user_states: dict[int, DialogState] = {}


def get_state(user_id: int) -> DialogState:
    """Get current dialog state for user."""
    return user_states.get(user_id, DialogState.NOT_STARTED)


def set_state(user_id: int, state: DialogState) -> None:
    """Set dialog state for user."""
    user_states[user_id] = state


def start_dialog(user_id: int, username: str, name: str) -> None:
    """Initialize new dialog for user."""
    storage.create_dialog(user_id, username, name)
    set_state(user_id, DialogState.IN_PROGRESS)


def restart_dialog(user_id: int, username: str, name: str) -> None:
    """Restart dialog for user."""
    storage.reset_dialog(user_id, username, name)
    set_state(user_id, DialogState.IN_PROGRESS)


def add_bot_message(user_id: int, text: str) -> None:
    """Add bot message to history."""
    storage.add_message(user_id, "bot", text)


def add_user_message(user_id: int, text: str, voice: bool = False) -> None:
    """Add user message to history."""
    storage.add_message(user_id, "user", text, voice)


def get_history(user_id: int) -> list:
    """Get dialog history."""
    return storage.get_history(user_id)


def get_message_count(user_id: int) -> int:
    """Get number of messages in dialog."""
    history = get_history(user_id)
    return len([m for m in history if m["role"] == "user"])


def save_mission(user_id: int, mission: str, explanation: str, neon_color: str) -> None:
    """Save synthesized mission."""
    storage.update_dialog(
        user_id,
        mission=mission,
        explanation=explanation,
        neon_color=neon_color
    )
    set_state(user_id, DialogState.SHOWING_MISSION)


def mark_neon_sent(user_id: int) -> None:
    """Mark that neon preview was sent."""
    storage.update_dialog(user_id, neon_preview_sent=True)


def mark_completed(user_id: int) -> None:
    """Mark dialog as completed."""
    storage.update_dialog(user_id, completed=True)
    set_state(user_id, DialogState.COMPLETED)


def get_user_mission(user_id: int) -> Optional[dict]:
    """Get saved mission for user if exists."""
    dialog = storage.get_user_dialog(user_id)
    if dialog and dialog.get("mission"):
        return {
            "mission": dialog["mission"],
            "explanation": dialog["explanation"],
            "neon_color": dialog["neon_color"]
        }
    return None


def has_completed_dialog(user_id: int) -> bool:
    """Check if user has completed dialog before."""
    dialog = storage.get_user_dialog(user_id)
    return dialog is not None and dialog.get("completed", False)
