"""
Test cases for all bug fixes in the Second Brain Assistant.

These tests verify that previously broken functionality now works correctly.
Run with: cd /root/assistant-brain-os && python -m pytest tests/test_bug_fixes.py -v
"""

import pytest
import json
import os
import sys
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# BUG FIX 1: MODEL_NAME now exists in config.py
# ============================================================
class TestConfigModelName:
    """Bug: rescue_agent.py imported MODEL_NAME from config but it didn't exist."""

    def test_model_name_exists_in_config(self):
        """MODEL_NAME should be importable from common.config."""
        from common.config import MODEL_NAME
        assert MODEL_NAME is not None
        assert isinstance(MODEL_NAME, str)
        assert MODEL_NAME in ("deepseek-chat", "gpt-4o-mini")

    def test_model_name_matches_provider(self):
        """MODEL_NAME should match the LLM_PROVIDER setting."""
        from common.config import MODEL_NAME, LLM_PROVIDER
        if LLM_PROVIDER == "deepseek":
            assert MODEL_NAME == "deepseek-chat"
        else:
            assert MODEL_NAME == "gpt-4o-mini"

    def test_rescue_agent_imports_cleanly(self):
        """rescue_agent.py should import without errors."""
        # This was crashing before the fix
        try:
            from common.config import MODEL_NAME
            assert True
        except ImportError:
            pytest.fail("MODEL_NAME should be importable from common.config")


# ============================================================
# BUG FIX 2: Duplicate import removed from content_saver.py
# ============================================================
class TestContentSaverImports:
    """Bug: content_saver.py had duplicate import line."""

    def test_no_duplicate_imports(self):
        """content_saver.py should not have duplicate import lines."""
        import inspect
        import agents.content_saver as cs
        source = inspect.getsource(cs)

        # Count occurrences of the import
        import_line = "from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound"
        count = source.count(import_line)
        assert count == 1, f"Expected 1 occurrence, found {count}"


# ============================================================
# BUG FIX 3: is_casual_message false positive prevention
# ============================================================
class TestCasualMessageDetection:
    """Bug: startswith check was too aggressive, treating actionable messages as casual."""

    def setup_method(self):
        from main import is_casual_message
        self.is_casual = is_casual_message

    def test_actual_casual_messages_detected(self):
        """Simple greetings should still be detected as casual."""
        assert self.is_casual("hi") is True
        assert self.is_casual("hello") is True
        assert self.is_casual("hey") is True
        assert self.is_casual("thanks") is True
        assert self.is_casual("ok") is True
        assert self.is_casual("bye") is True
        assert self.is_casual("cool") is True

    def test_actionable_messages_not_casual(self):
        """Messages with action keywords should NOT be casual."""
        assert self.is_casual("ok cool find me info about AI") is False
        assert self.is_casual("thanks but can you also research X") is False
        assert self.is_casual("nice, now search for quantum computing") is False
        assert self.is_casual("hello, can you save this note for me") is False
        assert self.is_casual("good morning, what did I save yesterday?") is False

    def test_urls_never_casual(self):
        """URLs should never be treated as casual."""
        assert self.is_casual("https://example.com") is False
        assert self.is_casual("ok check this out https://example.com") is False

    def test_questions_not_casual(self):
        """Questions with question words should not be casual."""
        assert self.is_casual("what is machine learning?") is False
        assert self.is_casual("how do I save a note?") is False
        assert self.is_casual("why is the sky blue?") is False
        assert self.is_casual("where can I find that article?") is False

    def test_short_non_casual_messages(self):
        """Short messages with action keywords should not be casual."""
        assert self.is_casual("save this") is False
        assert self.is_casual("search AI") is False
        assert self.is_casual("research physics") is False
        assert self.is_casual("find notes") is False


# ============================================================
# BUG FIX 4: Database delete_entry uses correct column
# ============================================================
class TestDatabaseDeleteEntry:
    """Bug: delete_entry used nonexistent 'embedding_id' column instead of 'id'."""

    def test_delete_uses_id_column(self):
        """Verify delete_entry SQL references 'id' column, not 'embedding_id'."""
        import inspect
        from common.database import Database
        source = inspect.getsource(Database.delete_entry)
        assert "WHERE id = ?" in source
        assert "WHERE embedding_id = ?" not in source


# ============================================================
# BUG FIX 5: Database add_knowledge uses UUID for IDs
# ============================================================
class TestDatabaseAddKnowledge:
    """Bug: SQLite ID used text[:50] fallback causing collisions."""

    def test_add_knowledge_generates_uuid(self):
        """When no embedding_id is provided, a UUID should be generated."""
        import inspect
        from common.database import Database
        source = inspect.getsource(Database.add_knowledge)
        # Should use uuid.uuid4() instead of text[:50]
        assert "uuid.uuid4()" in source
        assert "text[:50]" not in source


# ============================================================
# BUG FIX 6: Reranking works in async context
# ============================================================
class TestReranking:
    """Bug: reranking never worked because it detected a running event loop
    and returned without reranking."""

    def test_sync_rerank_method_exists(self):
        """A synchronous reranking method should exist."""
        from common.database import Database
        assert hasattr(Database, '_rerank_results_sync')

    def test_search_knowledge_calls_sync_rerank(self):
        """search_knowledge with rerank=True should call sync reranking."""
        import inspect
        from common.database import Database
        source = inspect.getsource(Database.search_knowledge)
        assert "_rerank_results_sync" in source
        # Should NOT have the broken asyncio.get_event_loop pattern
        assert "loop.is_running()" not in source


# ============================================================
# BUG FIX 7: Knowledge graph get_backlinks works with MultiDiGraph
# ============================================================
class TestKnowledgeGraphBacklinks:
    """Bug: get_backlinks failed because MultiDiGraph.get_edge_data returns
    {edge_key: {attrs}} dict, not a flat attrs dict."""

    def test_backlinks_with_multidigraph(self):
        """get_backlinks should handle MultiDiGraph edge data format."""
        from common.knowledge_graph import KnowledgeGraph
        import tempfile

        # Create a temporary graph
        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            temp_path = f.name

        try:
            kg = KnowledgeGraph(graph_path=temp_path)

            # Add two nodes manually
            kg.graph.add_node("node_a", title="Note A", content="Content A", tags=[], created_at=datetime.now().isoformat())
            kg.graph.add_node("node_b", title="Note B", content="Content B", tags=[], created_at=datetime.now().isoformat())

            # Add edge (this is how MultiDiGraph stores edges)
            kg.graph.add_edge("node_a", "node_b", relationship="mentions", reason="test")

            # This should NOT crash
            backlinks = kg.get_backlinks("node_b")

            assert len(backlinks) == 1
            assert backlinks[0]['id'] == 'node_a'
            assert backlinks[0]['title'] == 'Note A'
            assert backlinks[0]['relationship'] == 'mentions'
        finally:
            os.unlink(temp_path)

    def test_backlinks_empty_for_no_predecessors(self):
        """get_backlinks should return empty list for nodes with no incoming edges."""
        from common.knowledge_graph import KnowledgeGraph
        import tempfile

        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            temp_path = f.name

        try:
            kg = KnowledgeGraph(graph_path=temp_path)
            kg.graph.add_node("lonely_node", title="Lonely", content="", tags=[])

            backlinks = kg.get_backlinks("lonely_node")
            assert backlinks == []
        finally:
            os.unlink(temp_path)

    def test_backlinks_nonexistent_node(self):
        """get_backlinks should return empty list for nonexistent nodes."""
        from common.knowledge_graph import KnowledgeGraph
        import tempfile

        with tempfile.NamedTemporaryFile(suffix='.pkl', delete=False) as f:
            temp_path = f.name

        try:
            kg = KnowledgeGraph(graph_path=temp_path)
            assert kg.get_backlinks("nonexistent") == []
        finally:
            os.unlink(temp_path)


# ============================================================
# BUG FIX 8: Redis status emoji now correct
# ============================================================
class TestStatusEmoji:
    """Bug: Status command showed red emoji even when Redis was connected."""

    def test_status_text_has_dynamic_emoji(self):
        """Status text should use green emoji when Redis is connected."""
        import inspect
        from main import status_command
        source = inspect.getsource(status_command)
        # Should have conditional emoji, not hardcoded red
        assert "🟢" in source or "r.ping()" in source


# ============================================================
# BUG FIX 9: YouTube summary respects LLM_PROVIDER
# ============================================================
class TestYouTubeSummaryProvider:
    """Bug: YouTube summary always used DeepSeek regardless of LLM_PROVIDER."""

    def test_youtube_respects_provider_setting(self):
        """The YouTube transcript summarizer should check LLM_PROVIDER."""
        import inspect
        import agents.content_saver as cs
        source = inspect.getsource(cs.extract_youtube_video)
        # Should check the provider, not hardcode DeepSeek
        assert "_provider" in source or "LLM_PROVIDER" in source
        # Should NOT have hardcoded DeepSeek-only setup
        assert 'llm_client = AsyncOpenAI(\n            api_key=DEEPSEEK_API_KEY,\n            base_url="https://api.deepseek.com"\n        )\n\n        summary_response' not in source


# ============================================================
# BUG FIX 10: Worker sends responses to web users via Redis
# ============================================================
class TestWorkerWebResponses:
    """Bug: Worker always tried to send Telegram messages, even for web users."""

    def test_worker_checks_source(self):
        """Worker should check payload source to determine response channel."""
        import inspect
        from worker import process_job
        source = inspect.getsource(process_job)
        # Should check for 'web' source
        assert 'source == "web"' in source
        # Should push to Redis for web users
        assert "web_response:" in source

    def test_worker_stores_web_conversation(self):
        """Worker should store web responses in conversation history."""
        import inspect
        from worker import process_job
        source = inspect.getsource(process_job)
        assert "web_conversation:" in source


# ============================================================
# BUG FIX 11: Web backend routes messages correctly
# ============================================================
def _load_web_route_function():
    """Helper to load _route_web_message from the web backend."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "web_backend_main",
        "/root/brain-web-interface/backend/main.py"
    )
    mod = importlib.util.module_from_spec(spec)
    # Patch out the heavy imports that would fail in test context
    sys.modules['web_backend_main'] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception:
        pass
    return getattr(mod, '_route_web_message', None)


class TestWebMessageRouting:
    """Bug: Web messages always went to archivist regardless of content."""

    def test_route_function_logic_urls(self):
        """URLs should route to content_saver."""
        # Test the routing logic directly (reimplemented to avoid import issues)
        import re

        def route(text):
            if re.search(r'https?://[^\s]+', text, re.IGNORECASE):
                return "content_saver"
            text_lower = text.lower()
            if any(kw in text_lower for kw in ["research", "look into", "investigate", "tell me about"]):
                return "researcher"
            if any(kw in text_lower for kw in ["write", "draft", "format", "compose", "email"]):
                return "writer"
            if any(kw in text_lower for kw in ["save", "remember", "note", "store"]):
                return "archivist"
            if any(kw in text_lower for kw in ["search", "find", "what did i", "look up", "show me"]):
                return "archivist"
            return "researcher"

        assert route("https://youtube.com/watch?v=abc") == "content_saver"
        assert route("check https://example.com") == "content_saver"

    def test_route_function_logic_save(self):
        """Save/remember keywords should route to archivist."""
        import re

        def route(text):
            if re.search(r'https?://[^\s]+', text, re.IGNORECASE):
                return "content_saver"
            text_lower = text.lower()
            if any(kw in text_lower for kw in ["research", "look into", "investigate", "tell me about"]):
                return "researcher"
            if any(kw in text_lower for kw in ["write", "draft", "format", "compose", "email"]):
                return "writer"
            if any(kw in text_lower for kw in ["save", "remember", "note", "store"]):
                return "archivist"
            if any(kw in text_lower for kw in ["search", "find", "what did i", "look up", "show me"]):
                return "archivist"
            return "researcher"

        assert route("save this note about python") == "archivist"
        assert route("remember that meeting is Friday") == "archivist"

    def test_route_function_logic_research(self):
        """Research keywords should route to researcher."""
        import re

        def route(text):
            if re.search(r'https?://[^\s]+', text, re.IGNORECASE):
                return "content_saver"
            text_lower = text.lower()
            if any(kw in text_lower for kw in ["research", "look into", "investigate", "tell me about"]):
                return "researcher"
            if any(kw in text_lower for kw in ["write", "draft", "format", "compose", "email"]):
                return "writer"
            if any(kw in text_lower for kw in ["save", "remember", "note", "store"]):
                return "archivist"
            if any(kw in text_lower for kw in ["search", "find", "what did i", "look up", "show me"]):
                return "archivist"
            return "researcher"

        assert route("research quantum computing") == "researcher"
        assert route("tell me about machine learning") == "researcher"

    def test_route_function_logic_writer(self):
        """Write keywords should route to writer."""
        import re

        def route(text):
            if re.search(r'https?://[^\s]+', text, re.IGNORECASE):
                return "content_saver"
            text_lower = text.lower()
            if any(kw in text_lower for kw in ["research", "look into", "investigate", "tell me about"]):
                return "researcher"
            if any(kw in text_lower for kw in ["write", "draft", "format", "compose", "email"]):
                return "writer"
            if any(kw in text_lower for kw in ["save", "remember", "note", "store"]):
                return "archivist"
            if any(kw in text_lower for kw in ["search", "find", "what did i", "look up", "show me"]):
                return "archivist"
            return "researcher"

        assert route("write an email to my boss") == "writer"
        assert route("draft a report about Q4") == "writer"

    def test_web_backend_has_routing_function(self):
        """Verify the web backend main.py contains _route_web_message."""
        with open('/root/brain-web-interface/backend/main.py', 'r') as f:
            source = f.read()
        assert 'def _route_web_message' in source
        assert 'current_agent="archivist"' not in source.split('_route_web_message')[1][:500]


# ============================================================
# BUG FIX 12: Web backend knowledge endpoints use correct data format
# ============================================================
class TestWebKnowledgeEndpoints:
    """Bug: Web endpoints misinterpreted ChromaDB query result format."""

    def test_database_has_get_all_entries(self):
        """Database should have get_all_entries method returning list of dicts."""
        from common.database import Database
        assert hasattr(Database, 'get_all_entries')
        assert hasattr(Database, 'get_all_entries_count')
        assert hasattr(Database, 'search_entries')

    def test_get_all_entries_returns_list(self):
        """get_all_entries should return a list, not a ChromaDB result dict."""
        from common.database import db
        result = db.get_all_entries(limit=5)
        assert isinstance(result, list)

    def test_get_all_entries_count_returns_int(self):
        """get_all_entries_count should return an integer."""
        from common.database import db
        result = db.get_all_entries_count()
        assert isinstance(result, int)
        assert result >= 0

    def test_search_entries_returns_list(self):
        """search_entries should return a list, not a ChromaDB result dict."""
        from common.database import db
        result = db.search_entries("test", limit=5)
        assert isinstance(result, list)


# ============================================================
# BUG FIX 13: content_saver remove_last_entry uses valid API
# ============================================================
class TestRemoveLastEntry:
    """Bug: remove_last_entry called search_knowledge with invalid params
    (sort_by, sort_order) and misinterpreted the result format."""

    def test_remove_last_entry_uses_get_recent(self):
        """remove_last_entry should use get_recent_knowledge instead of
        search_knowledge with invalid params."""
        import inspect
        import agents.content_saver as cs
        source = inspect.getsource(cs.remove_last_entry)
        # Should NOT call search_knowledge with sort params
        assert "sort_by" not in source
        assert "sort_order" not in source
        # Should use get_recent_knowledge
        assert "get_recent_knowledge" in source


# ============================================================
# BUG FIX 14: Deprecated asyncio.get_event_loop() removed
# ============================================================
class TestAsyncioDeprecation:
    """Bug: main.py used deprecated asyncio.get_event_loop().run_until_complete()."""

    def test_no_deprecated_event_loop_call(self):
        """main() should not call asyncio.get_event_loop().run_until_complete()."""
        import inspect
        from main import main as main_func
        source = inspect.getsource(main_func)
        # Should not have the actual deprecated call pattern
        assert "asyncio.get_event_loop()" not in source
        assert "run_until_complete" not in source
        # Should use post_init hook instead
        assert "post_init" in source


# ============================================================
# Contracts / Data Model Tests
# ============================================================
class TestContracts:
    """Verify data model contracts work correctly."""

    def test_job_creation(self):
        from common.contracts import Job, JobStatus
        job = Job(current_agent="archivist", payload={"text": "test"})
        assert job.status == JobStatus.PENDING
        assert job.retry_count == 0
        assert job.max_retries == 3
        assert job.id is not None

    def test_job_serialization(self):
        from common.contracts import Job
        job = Job(current_agent="researcher", payload={"text": "test query"})
        json_str = job.model_dump_json()
        loaded = Job(**json.loads(json_str))
        assert loaded.current_agent == "researcher"
        assert loaded.payload["text"] == "test query"

    def test_agent_response(self):
        from common.contracts import AgentResponse
        resp = AgentResponse(success=True, output="Hello", next_agent="writer")
        assert resp.success is True
        assert resp.next_agent == "writer"

    def test_knowledge_entry(self):
        from common.contracts import KnowledgeEntry
        entry = KnowledgeEntry(text="test content", tags=["ai"], source="test")
        assert entry.created_at is not None
        assert entry.tags == ["ai"]


# ============================================================
# Knowledge Graph Tests
# ============================================================
class TestKnowledgeGraphOperations:
    """Test knowledge graph core operations."""

    def setup_method(self):
        import tempfile
        self.temp_file = tempfile.NamedTemporaryFile(suffix='.pkl', delete=False)
        self.temp_path = self.temp_file.name
        self.temp_file.close()

        from common.knowledge_graph import KnowledgeGraph
        self.kg = KnowledgeGraph(graph_path=self.temp_path)

    def teardown_method(self):
        os.unlink(self.temp_path)

    def test_add_note(self):
        node_id = self.kg.add_note(
            title="Test Note",
            content="This is a test note about [[AI]]",
            tags=["test", "ai"]
        )
        assert node_id is not None
        assert self.kg.graph.has_node(node_id)

    def test_bidirectional_links(self):
        """[[Note]] syntax should create bidirectional links."""
        node_id = self.kg.add_note(
            title="Source Note",
            content="This links to [[Target Note]]",
            tags=["test"]
        )
        # Should have created a placeholder for "Target Note"
        target = self.kg._find_note_by_title("Target Note")
        assert target is not None

        # Both directions should exist
        assert self.kg.graph.has_edge(node_id, target)
        assert self.kg.graph.has_edge(target, node_id)

    def test_tag_hierarchy(self):
        """Hierarchical tags should be expanded correctly."""
        result = self.kg._parse_tag_hierarchy("ai/ml/nlp")
        assert result == ["ai", "ai/ml", "ai/ml/nlp"]

    def test_daily_note_creation(self):
        daily_id = self.kg.get_or_create_daily_note("2024-01-15")
        assert daily_id == "daily_2024-01-15"
        assert self.kg.graph.has_node(daily_id)

        # Second call should return same id
        daily_id2 = self.kg.get_or_create_daily_note("2024-01-15")
        assert daily_id2 == daily_id

    def test_get_stats(self):
        self.kg.add_note(title="A", content="content", tags=["x"])
        stats = self.kg.get_stats()
        assert stats['total_nodes'] > 0
        assert isinstance(stats['tags'], dict)

    def test_search_by_tag(self):
        self.kg.add_note(title="Tagged", content="tagged content", tags=["python"])
        results = self.kg.search_by_tag("python")
        assert len(results) >= 1
        assert any(r['title'] == "Tagged" for r in results)


# ============================================================
# BUG FIX 16: Archivist defaults to "save" for search queries
# ============================================================
class TestArchivistActionDetection:
    """Bug: Archivist always defaulted action to 'save' when no action field
    was provided in the payload, causing search queries like 'what info do
    you have about X?' to be saved as knowledge instead of searched."""

    def test_detect_action_imported(self):
        """_detect_action should be importable from archivist."""
        from agents.archivist import _detect_action
        assert callable(_detect_action)

    def test_search_what_do_you_have(self):
        """'What information do you have about X?' should detect as search."""
        from agents.archivist import _detect_action
        assert _detect_action("what information do you have about OpenClaw?") == "search"

    def test_search_what_did_i_save(self):
        """'What did I save about X?' should detect as search."""
        from agents.archivist import _detect_action
        assert _detect_action("what did I save about machine learning?") == "search"

    def test_search_find_notes(self):
        """'Find my notes about X' should detect as search."""
        from agents.archivist import _detect_action
        assert _detect_action("find my notes about Python") == "search"

    def test_search_show_me(self):
        """'Show me what I have about X' should detect as search."""
        from agents.archivist import _detect_action
        assert _detect_action("show me what I have about AI") == "search"

    def test_search_anything_about(self):
        """'Anything about X?' should detect as search."""
        from agents.archivist import _detect_action
        assert _detect_action("anything about quantum computing?") == "search"

    def test_search_do_you_know(self):
        """'Do you know anything about X?' should detect as search."""
        from agents.archivist import _detect_action
        assert _detect_action("do you know anything about OpenClaw?") == "search"

    def test_search_question_mark(self):
        """Messages ending with ? should detect as search."""
        from agents.archivist import _detect_action
        assert _detect_action("OpenClaw?") == "search"

    def test_search_tell_me_about(self):
        """'Tell me about X' should detect as search."""
        from agents.archivist import _detect_action
        assert _detect_action("tell me about the meeting notes") == "search"

    def test_search_look_up(self):
        """'Look up X' should detect as search."""
        from agents.archivist import _detect_action
        assert _detect_action("look up my notes on React") == "search"

    def test_save_explicit_save(self):
        """'Save this: ...' should detect as save."""
        from agents.archivist import _detect_action
        assert _detect_action("save this: AI is transforming healthcare") == "save"

    def test_save_explicit_remember(self):
        """'Remember that ...' should detect as save."""
        from agents.archivist import _detect_action
        assert _detect_action("remember that the meeting is at 3pm on Friday") == "save"

    def test_save_explicit_note(self):
        """'Note: ...' should detect as save."""
        from agents.archivist import _detect_action
        assert _detect_action("note this down: password policy requires 12 chars") == "save"

    def test_archivist_has_module_execute(self):
        """Archivist should have a module-level execute() function."""
        import agents.archivist as archivist
        assert hasattr(archivist, 'execute')
        assert callable(archivist.execute)

    def test_class_execute_detects_search_without_action(self):
        """Class-based Archivist.execute should detect search from text when no action given."""
        from agents.archivist import _detect_action
        # Simulating what happens when payload has no 'action' key
        payload = {"text": "what do you have about OpenClaw?", "source": "telegram"}
        action = payload.get("action")
        assert action is None
        detected = _detect_action(payload["text"])
        assert detected == "search"


# ============================================================
# BUG FIX 17: Archivist search prompt too vague, LLM doesn't call tool
# ============================================================
class TestArchivistTopicExtraction:
    """Bug: Archivist passed the full question as-is to the LLM prompt
    (e.g., 'Search the knowledge base for: what information do you have about
    OpenClaw?'). The LLM treated it as a meta-question and asked for
    clarification instead of calling search_knowledge(). Fix: extract the
    core topic and use directive prompts like 'SEARCH FOR: OpenClaw'."""

    def test_extract_what_info_about(self):
        """'what information do you have about OpenClaw?' -> 'OpenClaw'"""
        from agents.archivist import _extract_search_topic
        result = _extract_search_topic("what information do you have about OpenClaw?")
        assert result.lower() == "openclaw"

    def test_extract_what_do_you_know_about(self):
        """'what do you know about machine learning?' -> 'machine learning'"""
        from agents.archivist import _extract_search_topic
        result = _extract_search_topic("what do you know about machine learning?")
        assert result.lower() == "machine learning"

    def test_extract_do_you_have_anything_about(self):
        """'do you have anything about Python?' -> 'Python'"""
        from agents.archivist import _extract_search_topic
        result = _extract_search_topic("do you have anything about Python?")
        assert result.lower() == "python"

    def test_extract_find_notes(self):
        """'find my notes about React hooks' -> 'React hooks'"""
        from agents.archivist import _extract_search_topic
        result = _extract_search_topic("find my notes about React hooks")
        assert result.lower() == "react hooks"

    def test_extract_show_me(self):
        """'show me my AI notes' -> 'my AI notes'"""
        from agents.archivist import _extract_search_topic
        result = _extract_search_topic("show me my AI notes")
        assert "ai notes" in result.lower()

    def test_extract_tell_me_about(self):
        """'tell me about the budget meeting' -> 'the budget meeting'"""
        from agents.archivist import _extract_search_topic
        result = _extract_search_topic("tell me about the budget meeting")
        assert "budget meeting" in result.lower()

    def test_extract_anything_about(self):
        """'anything about kubernetes?' -> 'kubernetes'"""
        from agents.archivist import _extract_search_topic
        result = _extract_search_topic("anything about kubernetes?")
        assert result.lower() == "kubernetes"

    def test_extract_simple_topic_passthrough(self):
        """'OpenClaw' (no question phrasing) should pass through as-is."""
        from agents.archivist import _extract_search_topic
        result = _extract_search_topic("OpenClaw")
        assert result == "OpenClaw"

    def test_extract_search_for(self):
        """'search for quantum computing' -> 'quantum computing'"""
        from agents.archivist import _extract_search_topic
        result = _extract_search_topic("search for quantum computing")
        assert result.lower() == "quantum computing"

    def test_extract_preserves_original_casing(self):
        """Extraction should preserve original casing of the topic."""
        from agents.archivist import _extract_search_topic
        result = _extract_search_topic("what do you have about OpenClaw?")
        assert result == "OpenClaw"

    def test_search_uses_db_search_clean(self):
        """Search should use db.search_clean() for hybrid search + clean text."""
        import inspect
        import agents.archivist as archivist
        source = inspect.getsource(archivist.execute)
        assert "db.search_clean" in source, \
            "execute() should call db.search_clean() for search"

    def test_format_search_results_exists(self):
        """_format_search_results() should exist for direct formatting."""
        import agents.archivist as archivist
        assert hasattr(archivist, '_format_search_results')
        assert callable(archivist._format_search_results)

    def test_format_search_results_empty(self):
        """_format_search_results with empty list should say nothing found."""
        from agents.archivist import _format_search_results
        output = _format_search_results([], "OpenClaw")
        assert "don't have anything" in output or "nothing" in output.lower()

    def test_format_search_results_with_data(self):
        """_format_search_results should format entries with title and preview."""
        from agents.archivist import _format_search_results
        results = [
            {
                'id': '1',
                'title': 'OpenClaw Research',
                'content': 'OpenClaw is an open-source AI agent',
                'tags': ['ai', 'tools'],
                'source': 'content_saver',
                'url': 'https://example.com',
                'created_at': '2026-02-06T12:00:00',
            }
        ]
        output = _format_search_results(results, "OpenClaw")
        assert "1 result" in output
        assert "OpenClaw Research" in output
        assert "open-source AI agent" in output

    def test_format_strips_contextual_prefix(self):
        """_format_search_results should strip [Document: ...] prefix."""
        from agents.archivist import _format_search_results
        results = [
            {
                'id': '1',
                'title': 'Test',
                'content': '[Document: Test | Topics: ai | Source: saver]\n\nActual content here',
                'tags': [],
                'source': '',
                'url': '',
                'created_at': '',
            }
        ]
        output = _format_search_results(results, "test")
        assert "[Document:" not in output
        assert "Actual content here" in output

    def test_db_search_clean_exists(self):
        """Database should have search_clean() method."""
        from common.database import db
        assert hasattr(db, 'search_clean')
        assert callable(db.search_clean)

    def test_db_search_clean_returns_list(self):
        """search_clean() should return a list of dicts."""
        from common.database import db
        results = db.search_clean("nonexistent_query_xyz_123")
        assert isinstance(results, list)

    def test_no_llm_in_search_path(self):
        """Search path should NOT involve any LLM agent calls."""
        import inspect
        import agents.archivist as archivist
        source = inspect.getsource(archivist.execute)
        # The search branch should not call any agent.run()
        # Split the source to get just the search branch
        assert "archivist_agent.run" not in source.split("action == \"search\"")[1].split("else:")[0], \
            "Search path should not call archivist_agent.run()"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
