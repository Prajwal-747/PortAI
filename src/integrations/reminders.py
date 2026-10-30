
import threading
import uuid
from datetime import datetime, timedelta

from winotify import Notification


MAX_DELAY_SECONDS = 7 * 24 * 60 * 60

_lock = threading.Lock()
_scheduled_items: dict[str, dict] = {}


def _format_duration(seconds: int) -> str:
    """Format a duration in a human-readable form."""
    if seconds % 86400 == 0:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''}"

    if seconds % 3600 == 0:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''}"

    if seconds % 60 == 0:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"

    return f"{seconds} second{'s' if seconds != 1 else ''}"


def _show_notification(title: str, message: str) -> None:
    """Display a Windows desktop notification."""
    notification = Notification(
        app_id="PortAI",
        title=title,
        msg=message,
    )
    notification.show()


def _finish_item(item_id: str) -> None:
    """Remove a completed item and notify the user."""
    with _lock:
        item = _scheduled_items.pop(item_id, None)

    if item is None:
        return

    try:
        _show_notification(item["title"], item["notification_message"])
    except Exception as exc:
        print(f"PortAI notification failed: {exc}")


def schedule_item(
    delay_seconds: int,
    message: str,
    title: str,
    kind: str,
    notification_message: str | None = None,
) -> str:
    """Schedule a timer or reminder."""

    if (
        isinstance(delay_seconds, bool)
        or not isinstance(delay_seconds, int)
        or delay_seconds < 1
    ):
        raise ValueError("The delay must be a positive whole number of seconds.")

    if delay_seconds > MAX_DELAY_SECONDS:
        raise ValueError("Timers and reminders cannot exceed 7 days.")

    if not isinstance(message, str) or not message.strip():
        raise ValueError("Please provide a non-empty message.")

    if kind not in {"timer", "reminder"}:
        raise ValueError("Unsupported scheduled item type.")

    item_id = uuid.uuid4().hex[:8]
    due_at = datetime.now() + timedelta(seconds=delay_seconds)

    item = {
        "id": item_id,
        "kind": kind,
        "title": title,
        "message": message.strip(),
        "notification_message": (
            notification_message or message.strip()
        ),
        "due_at": due_at,
        "timer": None,
    }

    timer = threading.Timer(
        delay_seconds,
        _finish_item,
        args=(item_id,),
    )
    timer.daemon = True
    item["timer"] = timer

    with _lock:
        _scheduled_items[item_id] = item

    try:
        timer.start()
    except Exception:
        with _lock:
            _scheduled_items.pop(item_id, None)
        raise

    return (
        f"{kind.capitalize()} scheduled for "
        f"{due_at.strftime('%I:%M %p')} "
        f"({ _format_duration(delay_seconds) }). "
        f"ID: {item_id}."
    )


def set_timer(seconds: int) -> str:
    """Create a countdown timer."""
    duration = _format_duration(seconds)

    return schedule_item(
        delay_seconds=seconds,
        message=f"{duration} timer",
        title="PortAI — Timer finished",
        kind="timer",
        notification_message=f"Your {duration} timer has finished.",
    )


def set_reminder(seconds: int, message: str) -> str:
    """Create a reminder that triggers after a delay."""
    return schedule_item(
        delay_seconds=seconds,
        message=message,
        title="PortAI — Reminder",
        kind="reminder",
        notification_message=message.strip() if isinstance(message, str) else message,
    )


def list_scheduled_items() -> list[dict]:
    """Return active timers and reminders, sorted by due time."""
    with _lock:
        items = list(_scheduled_items.values())

    return [
        {
            "id": item["id"],
            "kind": item["kind"],
            "title": item["title"],
            "message": item["message"],
            "due_at": item["due_at"].strftime("%Y-%m-%d %I:%M:%S %p"),
        }
        for item in sorted(items, key=lambda entry: entry["due_at"])
    ]


def cancel_scheduled_item(item_id: str) -> bool:
    """Cancel an active timer or reminder by its ID."""
    if not isinstance(item_id, str) or not item_id.strip():
        return False

    with _lock:
        item = _scheduled_items.pop(item_id.strip(), None)

    if item is None:
        return False

    item["timer"].cancel()
    return True
