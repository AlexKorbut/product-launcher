"""
Kanban Board — shared task tracking for all agents.
SQLite-backed, thread-safe, supports todo/in_progress/done/failed statuses.
"""
import sqlite3
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    agent TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'todo',
    input_data TEXT DEFAULT '{}',
    output_data TEXT DEFAULT NULL,
    error TEXT DEFAULT NULL,
    depends_on TEXT DEFAULT '[]',
    created_at TEXT NOT NULL,
    claimed_at TEXT DEFAULT NULL,
    completed_at TEXT DEFAULT NULL
);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_agent ON tasks(agent);
"""

VALID_STATUSES = {"todo", "in_progress", "done", "failed"}


class KanbanBoard:
    """Shared Kanban board for agent task management."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    # ─── Task CRUD ───

    def add_task(
        self,
        title: str,
        agent: str,
        input_data: dict | None = None,
        depends_on: list[str] | None = None,
    ) -> str:
        """Add a task to the board. Returns task ID."""
        task_id = f"T-{uuid.uuid4().hex[:8]}"
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """INSERT INTO tasks (id, title, agent, status, input_data, depends_on, created_at)
               VALUES (?, ?, ?, 'todo', ?, ?, ?)""",
            (
                task_id,
                title,
                agent,
                json.dumps(input_data or {}),
                json.dumps(depends_on or []),
                now,
            ),
        )
        self._conn.commit()
        return task_id

    def get_task(self, task_id: str) -> dict | None:
        """Get a task by ID. Returns dict or None."""
        row = self._conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    # ─── Status transitions ───

    def claim_task(self, task_id: str) -> None:
        """Claim a task (todo → in_progress)."""
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        if task["status"] != "todo":
            raise ValueError(f"Cannot claim task with status '{task['status']}'")
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE tasks SET status = 'in_progress', claimed_at = ? WHERE id = ?",
            (now, task_id),
        )
        self._conn.commit()

    def complete_task(self, task_id: str, output_data: dict | None = None) -> None:
        """Mark task as done (in_progress → done)."""
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        if task["status"] != "in_progress":
            raise ValueError(
                f"Cannot complete task with status '{task['status']}'. Must be 'in_progress'."
            )
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE tasks SET status = 'done', output_data = ?, completed_at = ? WHERE id = ?",
            (json.dumps(output_data or {}), now, task_id),
        )
        self._conn.commit()

    def fail_task(self, task_id: str, error: str) -> None:
        """Mark task as failed (in_progress → failed)."""
        task = self.get_task(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        if task["status"] != "in_progress":
            raise ValueError(
                f"Cannot fail task with status '{task['status']}'. Must be 'in_progress'."
            )
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE tasks SET status = 'failed', error = ?, completed_at = ? WHERE id = ?",
            (error, now, task_id),
        )
        self._conn.commit()

    # ─── Queries ───

    def get_tasks_by_status(self, status: str) -> list[dict]:
        """Get all tasks with given status."""
        rows = self._conn.execute(
            "SELECT * FROM tasks WHERE status = ? ORDER BY created_at", (status,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_next_task(self, agent: str) -> dict | None:
        """Get the next unclaimed task for an agent."""
        row = self._conn.execute(
            "SELECT * FROM tasks WHERE agent = ? AND status = 'todo' ORDER BY created_at LIMIT 1",
            (agent,),
        ).fetchone()
        return dict(row) if row else None
