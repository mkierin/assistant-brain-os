"""
Tests for the journal agent: action detection, topic extraction, mood detection,
prefix stripping, routing, knowledge graph linking, and integration.

Run with: cd /root/assistant-brain-os && python -m pytest tests/test_journal.py -v
"""

import pytest
import sys
import os
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ── Action detection ─────────────────────────────────────────────────

class TestJournalActionDetection:

    def test_save_default(self):
        from agents.journal import _detect_action
        assert _detect_action("today I worked on the project") == "save"

    def test_save_journal_prefix(self):
        from agents.journal import _detect_action
        assert _detect_action("journal: had a great day") == "save"

    def test_view_show_journal(self):
        from agents.journal import _detect_action
        assert _detect_action("show my journal") == "view"

    def test_view_recent_entries(self):
        from agents.journal import _detect_action
        assert _detect_action("my journal entries") == "view"

    def test_view_last_diary(self):
        from agents.journal import _detect_action
        assert _detect_action("last diary entries") == "view"

    def test_view_journal_history(self):
        from agents.journal import _detect_action
        assert _detect_action("journal history") == "view"

    def test_view_what_did_i_journal(self):
        from agents.journal import _detect_action
        assert _detect_action("what did I journal yesterday") == "view"


# ── Prefix stripping ────────────────────────────────────────────────

class TestJournalPrefixStripping:

    def test_strip_journal_colon(self):
        from agents.journal import _strip_journal_prefix
        assert _strip_journal_prefix("journal: had a great day") == "had a great day"

    def test_strip_diary_entry(self):
        from agents.journal import _strip_journal_prefix
        assert _strip_journal_prefix("diary entry: met with the team") == "met with the team"

    def test_strip_daily_log(self):
        from agents.journal import _strip_journal_prefix
        assert _strip_journal_prefix("daily log: finished the feature") == "finished the feature"

    def test_strip_journal_dash(self):
        from agents.journal import _strip_journal_prefix
        assert _strip_journal_prefix("journal - busy day at work") == "busy day at work"

    def test_no_prefix(self):
        from agents.journal import _strip_journal_prefix
        assert _strip_journal_prefix("today I worked on the project") == "today I worked on the project"

    def test_strip_log_colon(self):
        from agents.journal import _strip_journal_prefix
        assert _strip_journal_prefix("log: shipped the new release") == "shipped the new release"


# ── Topic extraction ─────────────────────────────────────────────────

class TestTopicExtraction:

    def test_extracts_meaningful_words(self):
        from agents.journal import _extract_topics
        topics = _extract_topics("Today I had a meeting about machine learning and neural networks")
        assert "meeting" in topics
        assert "machine" in topics
        assert "learning" in topics or "neural" in topics

    def test_filters_stop_words(self):
        from agents.journal import _extract_topics
        topics = _extract_topics("I went to the store and bought some things")
        assert "the" not in topics
        assert "and" not in topics
        assert "some" not in topics

    def test_limits_to_7_topics(self):
        from agents.journal import _extract_topics
        topics = _extract_topics("Python JavaScript TypeScript React Angular Vue Svelte Django Flask FastAPI PostgreSQL Redis")
        assert len(topics) <= 7

    def test_short_words_filtered(self):
        from agents.journal import _extract_topics
        topics = _extract_topics("I am ok")
        # All filtered, should get fallback
        assert topics == ["journal"]

    def test_deduplicates(self):
        from agents.journal import _extract_topics
        topics = _extract_topics("meeting about meeting notes from the meeting")
        assert topics.count("meeting") == 1


# ── Mood detection ───────────────────────────────────────────────────

class TestMoodDetection:

    def test_positive_happy(self):
        from agents.journal import _detect_mood
        assert _detect_mood("I'm really happy today") == "positive"

    def test_positive_productive(self):
        from agents.journal import _detect_mood
        assert _detect_mood("Had a productive day at work") == "positive"

    def test_negative_frustrated(self):
        from agents.journal import _detect_mood
        assert _detect_mood("Feeling frustrated with the bugs") == "negative"

    def test_negative_stressed(self):
        from agents.journal import _detect_mood
        assert _detect_mood("I'm stressed about the deadline") == "negative"

    def test_neutral(self):
        from agents.journal import _detect_mood
        assert _detect_mood("It was a normal day at the office") == "neutral"

    def test_no_mood(self):
        from agents.journal import _detect_mood
        assert _detect_mood("Shipped the new feature") is None

    def test_positive_grateful(self):
        from agents.journal import _detect_mood
        assert _detect_mood("Feeling grateful for the team") == "positive"


# ── Title generation ─────────────────────────────────────────────────

class TestTitleGeneration:

    def test_short_content(self):
        from agents.journal import _generate_title
        title = _generate_title("Met with the team about Q3 goals", "2026-02-08")
        assert "2026-02-08" in title
        assert "Met with the team" in title

    def test_long_content_truncated(self):
        from agents.journal import _generate_title
        long_text = "A" * 100 + " and more stuff"
        title = _generate_title(long_text, "2026-02-08")
        assert len(title) <= 80
        assert "..." in title

    def test_empty_content_fallback(self):
        from agents.journal import _generate_title
        title = _generate_title("", "2026-02-08")
        assert "2026-02-08" in title
        assert "Journal Entry" in title


# ── Routing from main.py ────────────────────────────────────────────

class TestJournalRouting:

    def test_route_journal_prefix(self):
        from main import route_deterministic
        assert route_deterministic("journal: had a great day today") == "journal"

    def test_route_diary_prefix(self):
        from main import route_deterministic
        assert route_deterministic("diary: worked on the project all morning") == "journal"

    def test_route_daily_log(self):
        from main import route_deterministic
        assert route_deterministic("daily log: shipped the release") == "journal"

    def test_route_show_journal(self):
        from main import route_deterministic
        assert route_deterministic("show my journal") == "journal"

    def test_route_journal_entries(self):
        from main import route_deterministic
        assert route_deterministic("my journal entries") == "journal"

    def test_route_view_diary(self):
        from main import route_deterministic
        assert route_deterministic("view diary entries") == "journal"

    def test_save_not_hijacked(self):
        """'save this fact' should still go to archivist."""
        from main import route_deterministic
        assert route_deterministic("save this important fact about Python") == "archivist"

    def test_remind_me_not_hijacked(self):
        """'remind me' should still go to task_manager."""
        from main import route_deterministic
        assert route_deterministic("remind me to call John tomorrow") == "task_manager"

    def test_question_not_hijacked(self):
        """Questions should still go to researcher."""
        from main import route_deterministic
        assert route_deterministic("what is machine learning?") == "researcher"


# ── Formatting ───────────────────────────────────────────────────────

class TestJournalListFormatting:

    def test_empty_list(self):
        from agents.journal import _format_journal_list
        output = _format_journal_list([])
        assert "no journal entries" in output.lower() or "start journaling" in output.lower()

    def test_single_entry(self):
        from agents.journal import _format_journal_list
        entries = [{
            'content': 'Had a productive day working on the new feature',
            'tags': ['journal', 'productive', 'feature'],
            'created_at': '2026-02-08T10:30:00',
        }]
        output = _format_journal_list(entries)
        assert "productive" in output
        assert "2026-02-08" in output

    def test_multiple_entries(self):
        from agents.journal import _format_journal_list
        entries = [
            {'content': 'Morning standup', 'tags': ['journal'], 'created_at': '2026-02-08T09:00:00'},
            {'content': 'Afternoon coding session', 'tags': ['journal', 'coding'], 'created_at': '2026-02-07T14:00:00'},
        ]
        output = _format_journal_list(entries)
        assert "1." in output
        assert "2." in output

    def test_long_content_truncated(self):
        from agents.journal import _format_journal_list
        entries = [{'content': 'A' * 300, 'tags': ['journal'], 'created_at': '2026-02-08'}]
        output = _format_journal_list(entries)
        assert "..." in output


# ── Full agent execute (integration) ─────────────────────────────────

class TestJournalExecute:

    @pytest.fixture(autouse=True)
    def mock_deps(self):
        with patch("agents.journal.db") as mock_db, \
             patch("agents.journal.knowledge_graph") as mock_kg:
            mock_db.search_clean.return_value = []
            mock_db.get_journal_entries.return_value = []
            mock_kg.add_note.return_value = "node_123"
            mock_kg._find_note_by_title.return_value = None
            self.mock_db = mock_db
            self.mock_kg = mock_kg
            yield

    @pytest.mark.asyncio
    async def test_save_journal_entry(self):
        from agents.journal import execute
        result = await execute({
            "text": "journal: Today I had a great meeting with the team about our Q3 roadmap",
            "user_id": "123",
            "input_type": "text",
        })
        assert result.success is True
        assert "Journal entry saved" in result.output
        self.mock_db.add_knowledge.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_captures_mood(self):
        from agents.journal import execute
        result = await execute({
            "text": "journal: Feeling really happy and productive today",
            "user_id": "123",
        })
        assert result.success is True
        assert "positive" in result.output.lower()

    @pytest.mark.asyncio
    async def test_save_extracts_topics(self):
        from agents.journal import execute
        result = await execute({
            "text": "journal: Worked on the Python backend and fixed database queries",
            "user_id": "123",
        })
        assert result.success is True
        assert "Topics:" in result.output

    @pytest.mark.asyncio
    async def test_save_with_related_notes(self):
        from agents.journal import execute
        self.mock_db.search_clean.return_value = [
            {'id': 'abc', 'title': 'Python Notes', 'source': 'archivist'},
        ]
        self.mock_kg._find_note_by_title.return_value = "node_abc"
        result = await execute({
            "text": "journal: Today I studied Python decorators and context managers",
            "user_id": "123",
        })
        assert result.success is True
        assert "Linked to" in result.output

    @pytest.mark.asyncio
    async def test_save_rejects_too_short(self):
        from agents.journal import execute
        result = await execute({"text": "hi", "user_id": "123"})
        assert result.success is False
        assert "too short" in result.output.lower()

    @pytest.mark.asyncio
    async def test_view_journal(self):
        from agents.journal import execute
        self.mock_db.get_journal_entries.return_value = [
            {'content': 'Great day', 'tags': ['journal'], 'created_at': '2026-02-08'},
        ]
        result = await execute({"text": "show my journal", "user_id": "123"})
        assert result.success is True
        assert "Great day" in result.output

    @pytest.mark.asyncio
    async def test_string_payload(self):
        from agents.journal import execute
        result = await execute("journal: Today was an interesting day at the office with lots of meetings")
        assert result.success is True

    @pytest.mark.asyncio
    async def test_voice_input_type_in_metadata(self):
        from agents.journal import execute
        result = await execute({
            "text": "Today I had a productive day working on the new feature and fixing bugs",
            "user_id": "123",
            "input_type": "voice",
        })
        assert result.success is True
        # Check the metadata passed to add_knowledge
        call_args = self.mock_db.add_knowledge.call_args
        entry = call_args[0][0]  # First positional arg (KnowledgeEntry)
        assert entry.metadata.get("input_source") == "voice"

    @pytest.mark.asyncio
    async def test_knowledge_graph_called(self):
        from agents.journal import execute
        result = await execute({
            "text": "journal: Discussed the new architecture with the engineering team today",
            "user_id": "123",
        })
        assert result.success is True
        self.mock_kg.add_note.assert_called_once()

    @pytest.mark.asyncio
    async def test_journal_tags_include_date(self):
        from agents.journal import execute
        result = await execute({
            "text": "journal: Worked on machine learning models today",
            "user_id": "123",
        })
        assert result.success is True
        call_args = self.mock_db.add_knowledge.call_args
        entry = call_args[0][0]
        today = datetime.now().strftime("%Y-%m-%d")
        assert "journal" in entry.tags
        assert today in entry.tags
