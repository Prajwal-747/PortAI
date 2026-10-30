
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path


# Store the database in the project root's data directory.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "portai.db"


def get_connection() -> sqlite3.Connection:
    """Open a connection to PortAI's task database."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_db() -> None:
    """Create the tasks table if it does not already exist."""
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                due_at TEXT,
                completed INTEGER NOT NULL DEFAULT 0
                    CHECK (completed IN (0, 1))
            )
        """)


def _validate_due_at(due_at: str | None) -> str | None:
    """Validate an optional ISO date or datetime."""
    if due_at is None:
        return None

    if not isinstance(due_at, str) or not due_at.strip():
        raise ValueError("The due date must be a valid date or datetime.")

    due_at = due_at.strip()

    try:
        parsed = datetime.fromisoformat(due_at)
    except ValueError:
        # Also accept a date without a time, such as 2026-11-05.
        try:
            parsed_date = datetime.strptime(due_at, "%Y-%m-%d").date()
        except ValueError as exc:
            raise ValueError(
                "Use YYYY-MM-DD or an ISO datetime, "
                "such as 2026-11-05T18:00:00."
            ) from exc

        return parsed_date.isoformat()

    return parsed.isoformat()


def create_task(
    title: str,
    due_at: str | None = None,
) -> dict:
    """Create a task and return its details."""
    if not isinstance(title, str) or not title.strip():
        raise ValueError("A task title cannot be empty.")

    title = title.strip()
    due_at = _validate_due_at(due_at)
    task_id = uuid.uuid4().hex[:8]
    created_at = datetime.now().astimezone().isoformat(timespec="seconds")

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO tasks (id, title, created_at, due_at)
            VALUES (?, ?, ?, ?)
            """,
            (task_id, title, created_at, due_at),
        )

    return {
        "id": task_id,
        "title": title,
        "created_at": created_at,
        "due_at": due_at,
        "completed": False,
    }


def list_tasks(include_completed: bool = False) -> list[dict]:
    """List tasks, with pending tasks first."""
    query = """
        SELECT id, title, created_at, due_at, completed
        FROM tasks
    """

    if not include_completed:
        query += " WHERE completed = 0"

    query += " ORDER BY completed ASC, due_at IS NULL ASC, due_at ASC, created_at ASC"

    with get_connection() as connection:
        rows = connection.execute(query).fetchall()

    return [
        {
            "id": row["id"],
            "title": row["title"],
            "created_at": row["created_at"],
            "due_at": row["due_at"],
            "completed": bool(row["completed"]),
        }
        for row in rows
    ]


def complete_task(task_id: str) -> bool:
    """Mark a task as complete. Return False if it doesn't exist."""
    if not isinstance(task_id, str) or not task_id.strip():
        return False

    with get_connection() as connection:
        cursor = connection.execute(
            "UPDATE tasks SET completed = 1 WHERE id = ?",
            (task_id.strip(),),
        )

    return cursor.rowcount > 0


def delete_task(task_id: str) -> bool:
    """Delete a task by ID. Return False if it doesn't exist."""
    if not isinstance(task_id, str) or not task_id.strip():
        return False

    with get_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ?",
            (task_id.strip(),),
        )

    return cursor.rowcount > 0


# Ensure the database and table exist when this module is imported.
initialize_db()
