"""
Tests for the task manager agent: date parsing, action detection,
routing, CRUD, and reminder queries.

Run with: cd /root/assistant-brain-os && python -m pytest tests/test_task_manager.py -v
"""

import pytest
import sys
import os
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ── Action detection ─────────────────────────────────────────────────

class TestActionDetection:
    """Test that _detect_action classifies intent correctly."""

    def test_add_intent_remind_me(self):
        from agents.task_manager import _detect_action
        assert _detect_action("remind me to submit the report by Friday") == "add"

    def test_add_intent_todo(self):
        from agents.task_manager import _detect_action
        assert _detect_action("todo: buy groceries") == "add"

    def test_add_intent_set_reminder(self):
        from agents.task_manager import _detect_action
        assert _detect_action("set a reminder for the meeting tomorrow") == "add"

    def test_add_intent_dont_forget(self):
        from agents.task_manager import _detect_action
        assert _detect_action("don't forget to call mom") == "add"

    def test_add_intent_plain_task(self):
        from agents.task_manager import _detect_action
        assert _detect_action("prepare slides for the presentation") == "add"

    def test_list_intent_my_tasks(self):
        from agents.task_manager import _detect_action
        assert _detect_action("my tasks") == "list"

    def test_list_intent_show_todos(self):
        from agents.task_manager import _detect_action
        assert _detect_action("show my todos") == "list"

    def test_list_intent_pending_reminders(self):
        from agents.task_manager import _detect_action
        assert _detect_action("pending reminders") == "list"

    def test_list_intent_what_tasks(self):
        from agents.task_manager import _detect_action
        assert _detect_action("what tasks do I have") == "list"

    def test_list_intent_upcoming_tasks(self):
        from agents.task_manager import _detect_action
        assert _detect_action("upcoming tasks") == "list"

    def test_complete_intent_done(self):
        from agents.task_manager import _detect_action
        assert _detect_action("done with #1") == "complete"

    def test_complete_intent_finished(self):
        from agents.task_manager import _detect_action
        assert _detect_action("finished task 2") == "complete"

    def test_complete_intent_mark_done(self):
        from agents.task_manager import _detect_action
        assert _detect_action("mark done #3") == "complete"

    def test_complete_intent_completed(self):
        from agents.task_manager import _detect_action
        assert _detect_action("completed task 1") == "complete"

    def test_delete_intent(self):
        from agents.task_manager import _detect_action
        assert _detect_action("delete task #2") == "delete"

    def test_delete_intent_cancel(self):
        from agents.task_manager import _detect_action
        assert _detect_action("cancel reminder for meeting") == "delete"


# ── Date extraction ──────────────────────────────────────────────────

class TestDateExtraction:
    """Test date parsing from natural language."""

    def test_explicit_by_friday(self):
        from agents.task_manager import _extract_date_and_task
        due, reminder, title = _extract_date_and_task("remind me to submit report by Friday")
        assert due is not None
        assert title  # Should have a non-empty title

    def test_tomorrow(self):
        from agents.task_manager import _extract_date_and_task
        due, reminder, title = _extract_date_and_task("todo: call the dentist tomorrow")
        expected = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        assert due == expected

    def test_today(self):
        from agents.task_manager import _extract_date_and_task
        due, reminder, title = _extract_date_and_task("finish the report today")
        expected = datetime.now().strftime("%Y-%m-%d")
        assert due == expected

    def test_no_date(self):
        from agents.task_manager import _extract_date_and_task
        due, reminder, title = _extract_date_and_task("buy groceries")
        # dateparser may or may not find a date in "buy groceries"
        # The important thing is the title is preserved
        assert "groceries" in title.lower()

    def test_reminder_at_defaults_to_9am(self):
        from agents.task_manager import _extract_date_and_task
        due, reminder, title = _extract_date_and_task("submit report tomorrow")
        if due:
            assert reminder is not None
            assert "T09:00:00" in reminder

    def test_title_cleaned(self):
        from agents.task_manager import _extract_date_and_task
        _, _, title = _extract_date_and_task("remind me to buy milk tomorrow")
        assert title.lower().startswith("buy") or "milk" in title.lower()
        # Should not start with "remind me to"
        assert not title.lower().startswith("remind")


# ── Prefix stripping ────────────────────────────────────────────────

class TestPrefixStripping:

    def test_strip_remind_me_to(self):
        from agents.task_manager import _strip_task_prefix
        assert _strip_task_prefix("remind me to call John") == "call John"

    def test_strip_todo_colon(self):
        from agents.task_manager import _strip_task_prefix
        result = _strip_task_prefix("todo: prepare slides")
        assert result == "prepare slides"

    def test_strip_dont_forget(self):
        from agents.task_manager import _strip_task_prefix
        result = _strip_task_prefix("don't forget to send invoice")
        assert "send invoice" in result

    def test_strip_set_reminder(self):
        from agents.task_manager import _strip_task_prefix
        result = _strip_task_prefix("set a reminder for doctor appointment")
        assert "doctor" in result.lower()

    def test_no_prefix(self):
        from agents.task_manager import _strip_task_prefix
        assert _strip_task_prefix("buy milk") == "buy milk"


# ── Priority extraction ──────────────────────────────────────────────

class TestPriorityExtraction:

    def test_urgent(self):
        from agents.task_manager import _extract_priority
        assert _extract_priority("urgent: call the client") == "high"

    def test_asap(self):
        from agents.task_manager import _extract_priority
        assert _extract_priority("fix this asap") == "high"

    def test_no_rush(self):
        from agents.task_manager import _extract_priority
        assert _extract_priority("someday organize photos") == "low"

    def test_default_medium(self):
        from agents.task_manager import _extract_priority
        assert _extract_priority("buy groceries") == "medium"


# ── Routing from main.py ────────────────────────────────────────────

class TestTaskRouting:
    """Test that task-related messages route to task_manager."""

    def test_route_remind_me(self):
        from main import route_deterministic
        assert route_deterministic("remind me to call John tomorrow") == "task_manager"

    def test_route_todo(self):
        from main import route_deterministic
        assert route_deterministic("todo: prepare the slides") == "task_manager"

    def test_route_task(self):
        from main import route_deterministic
        assert route_deterministic("add a task: review PR") == "task_manager"

    def test_route_my_tasks(self):
        from main import route_deterministic
        assert route_deterministic("my tasks") == "task_manager"

    def test_route_show_reminders(self):
        from main import route_deterministic
        assert route_deterministic("show reminders") == "task_manager"

    def test_route_done_with(self):
        from main import route_deterministic
        assert route_deterministic("done with #1 task") == "task_manager"

    def test_route_set_reminder(self):
        from main import route_deterministic
        assert route_deterministic("set a reminder for Friday meeting") == "task_manager"

    def test_route_dont_forget(self):
        from main import route_deterministic
        assert route_deterministic("don't forget to submit the report") == "task_manager"

    def test_route_deadline(self):
        from main import route_deterministic
        assert route_deterministic("the deadline for the project is next week") == "task_manager"

    def test_route_need_to_by(self):
        from main import route_deterministic
        assert route_deterministic("I need to finish the docs by Friday") == "task_manager"

    def test_save_not_hijacked(self):
        """'remember this fact' should still go to archivist, not task_manager."""
        from main import route_deterministic
        assert route_deterministic("remember this important fact about Python") == "archivist"

    def test_search_not_hijacked(self):
        """'what do I know about X' should still go to archivist."""
        from main import route_deterministic
        assert route_deterministic("what did I save about machine learning") == "archivist"


# ── Database CRUD ────────────────────────────────────────────────────

class TestTaskDatabaseCRUD:
    """Test task DB methods with a real (temp) SQLite database."""

    @pytest.fixture(autouse=True)
    def setup_db(self, tmp_path):
        """Create a fresh database for each test."""
        import sqlite3
        self.db_path = str(tmp_path / "test_brain.db")
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                due_date TEXT,
                reminder_at TEXT,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'medium',
                tags TEXT DEFAULT '[]',
                linked_knowledge TEXT DEFAULT '[]',
                recurrence TEXT,
                created_at TEXT,
                completed_at TEXT
            )
        """)
        self.conn.commit()

    def _add_task(self, user_id, title, due_date=None, reminder_at=None, status="pending"):
        import json
        task_id = str(uuid.uuid4())
        self.cursor.execute(
            """INSERT INTO tasks (id, user_id, title, due_date, reminder_at, status, priority, tags, linked_knowledge, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'medium', '[]', '[]', ?)""",
            (task_id, user_id, title, due_date, reminder_at, status, datetime.now().isoformat()),
        )
        self.conn.commit()
        return task_id

    def test_add_and_get_tasks(self):
        uid = "user123"
        tid = self._add_task(uid, "Buy milk", due_date="2026-03-01")
        self.cursor.execute("SELECT * FROM tasks WHERE user_id = ?", (uid,))
        rows = self.cursor.fetchall()
        assert len(rows) == 1
        assert rows[0][2] == "Buy milk"  # title column

    def test_complete_task(self):
        uid = "user123"
        tid = self._add_task(uid, "Do laundry")
        self.cursor.execute(
            "UPDATE tasks SET status = 'done', completed_at = ? WHERE id = ? AND user_id = ?",
            (datetime.now().isoformat(), tid, uid),
        )
        self.conn.commit()
        self.cursor.execute("SELECT status FROM tasks WHERE id = ?", (tid,))
        assert self.cursor.fetchone()[0] == "done"

    def test_get_due_reminders(self):
        uid = "user123"
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        future = (datetime.now() + timedelta(hours=2)).isoformat()
        self._add_task(uid, "Past reminder", reminder_at=past)
        self._add_task(uid, "Future reminder", reminder_at=future)

        now = datetime.now().isoformat()
        self.cursor.execute(
            "SELECT * FROM tasks WHERE status = 'pending' AND reminder_at IS NOT NULL AND reminder_at <= ?",
            (now,),
        )
        due = self.cursor.fetchall()
        assert len(due) == 1
        assert due[0][2] == "Past reminder"

    def test_delete_task(self):
        uid = "user123"
        tid = self._add_task(uid, "Temporary task")
        self.cursor.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (tid, uid))
        self.conn.commit()
        self.cursor.execute("SELECT * FROM tasks WHERE id = ?", (tid,))
        assert self.cursor.fetchone() is None


# ── Complete task matching ───────────────────────────────────────────

class TestCompleteTargetMatching:

    def test_match_by_number(self):
        from agents.task_manager import _extract_complete_target
        tasks = [
            {"id": "aaa", "title": "Buy milk"},
            {"id": "bbb", "title": "Call dentist"},
            {"id": "ccc", "title": "Submit report"},
        ]
        assert _extract_complete_target("done with #2", tasks) == "bbb"

    def test_match_by_number_no_hash(self):
        from agents.task_manager import _extract_complete_target
        tasks = [{"id": "aaa", "title": "Buy milk"}]
        assert _extract_complete_target("done with 1", tasks) == "aaa"

    def test_match_by_keyword(self):
        from agents.task_manager import _extract_complete_target
        tasks = [
            {"id": "aaa", "title": "Buy milk"},
            {"id": "bbb", "title": "Call the dentist"},
        ]
        assert _extract_complete_target("done with dentist", tasks) == "bbb"

    def test_no_match_returns_first(self):
        """If no specific target, default to first task."""
        from agents.task_manager import _extract_complete_target
        tasks = [{"id": "aaa", "title": "Buy milk"}]
        result = _extract_complete_target("done", tasks)
        assert result == "aaa"

    def test_empty_tasks(self):
        from agents.task_manager import _extract_complete_target
        assert _extract_complete_target("done with #1", []) is None


# ── Formatting ───────────────────────────────────────────────────────

class TestTaskListFormatting:

    def test_empty_list(self):
        from agents.task_manager import _format_task_list
        output = _format_task_list([])
        assert "caught up" in output.lower() or "no pending" in output.lower()

    def test_single_task(self):
        from agents.task_manager import _format_task_list
        tasks = [{"title": "Buy milk", "due_date": None, "priority": "medium", "tags": []}]
        output = _format_task_list(tasks)
        assert "1 pending task" in output
        assert "Buy milk" in output

    def test_overdue_task(self):
        from agents.task_manager import _format_task_list
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        tasks = [{"title": "Late task", "due_date": yesterday, "priority": "high", "tags": []}]
        output = _format_task_list(tasks)
        assert "OVERDUE" in output

    def test_due_today(self):
        from agents.task_manager import _format_task_list
        today = datetime.now().strftime("%Y-%m-%d")
        tasks = [{"title": "Urgent task", "due_date": today, "priority": "medium", "tags": []}]
        output = _format_task_list(tasks)
        assert "TODAY" in output


# ── Full agent execute (integration) ─────────────────────────────────

class TestTaskManagerExecute:
    """Integration tests using mocked database."""

    @pytest.fixture(autouse=True)
    def mock_db(self):
        with patch("agents.task_manager.db") as mock:
            mock.add_task.return_value = str(uuid.uuid4())
            mock.get_tasks.return_value = []
            mock.complete_task.return_value = True
            mock.delete_task.return_value = True
            mock.search_clean.return_value = []
            self.mock_db = mock
            yield

    @pytest.mark.asyncio
    async def test_add_task(self):
        from agents.task_manager import execute
        result = await execute({"text": "remind me to buy milk tomorrow", "user_id": "123"})
        assert result.success is True
        assert "Task added" in result.output
        self.mock_db.add_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_tasks_empty(self):
        from agents.task_manager import execute
        result = await execute({"text": "my tasks", "user_id": "123"})
        assert result.success is True
        assert "caught up" in result.output.lower() or "no pending" in result.output.lower()

    @pytest.mark.asyncio
    async def test_list_tasks_with_items(self):
        from agents.task_manager import execute
        self.mock_db.get_tasks.return_value = [
            {"id": "aaa", "title": "Buy milk", "due_date": None, "priority": "medium", "tags": []},
        ]
        result = await execute({"text": "show my tasks", "user_id": "123"})
        assert result.success is True
        assert "Buy milk" in result.output

    @pytest.mark.asyncio
    async def test_complete_task(self):
        from agents.task_manager import execute
        self.mock_db.get_tasks.return_value = [
            {"id": "aaa", "title": "Buy milk", "due_date": None, "priority": "medium", "tags": []},
        ]
        result = await execute({"text": "done with #1", "user_id": "123"})
        assert result.success is True
        assert "Completed" in result.output
        self.mock_db.complete_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_string_payload(self):
        """Agent should accept plain string payload too."""
        from agents.task_manager import execute
        result = await execute("remind me to stretch")
        assert result.success is True
        assert "Task added" in result.output
