"""
Tests for Kanban Board — shared task tracking for all agents.
"""
import pytest
import sqlite3
from pathlib import Path


class TestKanbanInit:
    """Board initialization."""

    def test_kanban_importable(self):
        """Module must be importable."""
        from product_launcher.kanban import KanbanBoard

    def test_kanban_creates_in_memory_by_default(self):
        """Default board is in-memory (no file)."""
        from product_launcher.kanban import KanbanBoard
        board = KanbanBoard()
        assert board.db_path == ":memory:"

    def test_kanban_creates_file_db(self):
        """Can create file-based board."""
        from product_launcher.kanban import KanbanBoard
        board = KanbanBoard(db_path="/tmp/test_kanban.db")
        assert Path("/tmp/test_kanban.db").exists()

    def test_kanban_creates_tasks_table(self):
        """Board initializes the tasks table."""
        from product_launcher.kanban import KanbanBoard
        board = KanbanBoard()
        # Should not raise
        board._conn.execute("SELECT * FROM tasks LIMIT 0")


class TestKanbanTasks:
    """Task lifecycle."""

    def test_add_task_returns_task_id(self):
        """add_task returns a unique ID."""
        from product_launcher.kanban import KanbanBoard
        board = KanbanBoard()
        task_id = board.add_task(
            title="OCR брошюры",
            agent="ocr-extractor",
            input_data={"image": "photo.jpg"},
        )
        assert task_id
        assert task_id.startswith("T-")

    def test_added_task_is_in_todo(self):
        """New tasks start in 'todo' status."""
        from product_launcher.kanban import KanbanBoard
        board = KanbanBoard()
        task_id = board.add_task(title="Test", agent="test-agent")
        task = board.get_task(task_id)
        assert task is not None
        assert task["status"] == "todo"

    def test_task_has_correct_fields(self):
        """Task dict has all required fields."""
        from product_launcher.kanban import KanbanBoard
        board = KanbanBoard()
        task_id = board.add_task(
            title="Анализ продукта",
            agent="product-analyst",
            input_data={"kb_id": "abc"},
            depends_on=["T-001"],
        )
        task = board.get_task(task_id)
        assert task["title"] == "Анализ продукта"
        assert task["agent"] == "product-analyst"
        assert task["status"] == "todo"
        assert task["input_data"] == '{"kb_id": "abc"}'
        assert task["depends_on"] == '["T-001"]'

    def test_get_nonexistent_task_returns_none(self):
        """Non-existent task returns None."""
        from product_launcher.kanban import KanbanBoard
        board = KanbanBoard()
        assert board.get_task("nonexistent") is None


class TestKanbanStatusTransitions:
    """Task status changes."""

    def test_claim_task_changes_status_to_in_progress(self):
        """claim_task sets status to 'in_progress'."""
        from product_launcher.kanban import KanbanBoard
        board = KanbanBoard()
        task_id = board.add_task(title="Test", agent="agent-1")
        board.claim_task(task_id)
        task = board.get_task(task_id)
        assert task["status"] == "in_progress"

    def test_complete_task_changes_status_to_done(self):
        """complete_task sets status to 'done' with output."""
        from product_launcher.kanban import KanbanBoard
        board = KanbanBoard()
        task_id = board.add_task(title="Test", agent="agent-1")
        board.claim_task(task_id)
        board.complete_task(task_id, output_data={"result": "success"})
        task = board.get_task(task_id)
        assert task["status"] == "done"
        assert "success" in task["output_data"]

    def test_fail_task_changes_status_to_failed(self):
        """fail_task sets status to 'failed' with error."""
        from product_launcher.kanban import KanbanBoard
        board = KanbanBoard()
        task_id = board.add_task(title="Test", agent="agent-1")
        board.claim_task(task_id)
        board.fail_task(task_id, error="Something broke")
        task = board.get_task(task_id)
        assert task["status"] == "failed"
        assert task["error"] == "Something broke"

    def test_cannot_complete_task_not_in_progress(self):
        """Cannot complete a task that wasn't claimed."""
        from product_launcher.kanban import KanbanBoard
        board = KanbanBoard()
        task_id = board.add_task(title="Test", agent="agent-1")
        with pytest.raises(ValueError, match="in_progress"):
            board.complete_task(task_id)


class TestKanbanQueries:
    """Querying tasks by status/agent."""

    def test_get_tasks_by_status(self):
        """Filter tasks by status."""
        from product_launcher.kanban import KanbanBoard
        board = KanbanBoard()
        board.add_task(title="T1", agent="a")
        t2 = board.add_task(title="T2", agent="b")
        board.claim_task(t2)

        todo = board.get_tasks_by_status("todo")
        progress = board.get_tasks_by_status("in_progress")

        assert len(todo) == 1
        assert todo[0]["title"] == "T1"
        assert len(progress) == 1
        assert progress[0]["title"] == "T2"

    def test_get_next_ready_task(self):
        """Get next unclaimed task for an agent."""
        from product_launcher.kanban import KanbanBoard
        board = KanbanBoard()
        board.add_task(title="T1", agent="agent-1")
        board.add_task(title="T2", agent="agent-1")
        board.add_task(title="T3", agent="agent-2")

        next_task = board.get_next_task("agent-1")
        assert next_task is not None
        assert next_task["title"] == "T1"
        assert next_task["status"] == "todo"

    def test_no_next_task_when_all_claimed(self):
        """Returns None when no todo tasks for agent."""
        from product_launcher.kanban import KanbanBoard
        board = KanbanBoard()
        t = board.add_task(title="T1", agent="agent-1")
        board.claim_task(t)
        assert board.get_next_task("agent-1") is None
