"""
Tests for the Goal Fulfillment Tracking System.

These are REAL integration tests that:
- Create actual SQLite tables and insert/query data
- Evaluate realistic agent outputs against fulfillment heuristics
- Test the full record → evaluate → query cycle
- Verify stats aggregation

Run with: cd /root/assistant-brain-os && python -m pytest tests/test_goal_tracker.py -v
"""

import pytest
import os
import sys
import json
import sqlite3
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.goal_tracker import GoalTracker, GoalType, FULFILLMENT_RULES
from common.contracts import AgentResponse


# ============================================================
# Fixture: in-memory SQLite database for each test
# ============================================================
@pytest.fixture
def tracker():
    """Create a GoalTracker with a fresh in-memory SQLite database."""
    conn = sqlite3.connect(":memory:")
    t = GoalTracker(conn, redis_client=None)
    yield t
    conn.close()


# ============================================================
# Goal Classification Tests
# ============================================================
class TestGoalClassification:
    """Test that classify_goal() correctly derives goal types from agent + text."""

    def test_archivist_search_question(self):
        result = GoalTracker.classify_goal("archivist", "what do you know about Python?")
        assert result == GoalType.SEARCH_KNOWLEDGE

    def test_archivist_save_explicit(self):
        result = GoalTracker.classify_goal("archivist", "save this: AI is transforming healthcare")
        assert result == GoalType.SAVE_KNOWLEDGE

    def test_archivist_search_find(self):
        result = GoalTracker.classify_goal("archivist", "find my notes about Docker")
        assert result == GoalType.SEARCH_KNOWLEDGE

    def test_content_saver_youtube(self):
        result = GoalTracker.classify_goal("content_saver", "https://youtube.com/watch?v=abc123")
        assert result == GoalType.SAVE_YOUTUBE

    def test_content_saver_twitter(self):
        result = GoalTracker.classify_goal("content_saver", "https://twitter.com/user/status/123")
        assert result == GoalType.SAVE_TWEET

    def test_content_saver_x_dot_com(self):
        result = GoalTracker.classify_goal("content_saver", "https://x.com/user/status/123")
        assert result == GoalType.SAVE_TWEET

    def test_content_saver_generic_url(self):
        result = GoalTracker.classify_goal("content_saver", "https://example.com/article")
        assert result == GoalType.SAVE_URL

    def test_researcher(self):
        result = GoalTracker.classify_goal("researcher", "research quantum computing")
        assert result == GoalType.RESEARCH

    def test_writer(self):
        result = GoalTracker.classify_goal("writer", "write an email to my team")
        assert result == GoalType.WRITE_CONTENT

    def test_coder(self):
        result = GoalTracker.classify_goal("coder", "create a data model for e-commerce")
        assert result == GoalType.CODE_GENERATION

    def test_unknown_agent(self):
        result = GoalTracker.classify_goal("nonexistent", "some text")
        assert result == GoalType.UNKNOWN


# ============================================================
# Fulfillment Evaluation Tests (with realistic agent outputs)
# ============================================================
class TestFulfillmentEvaluation:
    """Test evaluate_fulfillment() with outputs that match real agent behavior."""

    def test_search_found_results(self):
        """Archivist search that finds results should be fulfilled."""
        response = AgentResponse(
            success=True,
            output="Found 3 results about 'OpenClaw':\n\n1. OpenClaw Research Report\n   OpenClaw is a free, open-source AI agent...\n   (tags: ai, tools, saved: 2026-02-06)\n\n2. Installation Guide\n   How to install OpenClaw safely...\n   (tags: setup, saved: 2026-02-06)"
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("SEARCH_KNOWLEDGE", response)
        assert fulfilled is True
        assert "success signal" in reason.lower()

    def test_search_no_results(self):
        """Archivist search with no results should be unfulfilled."""
        response = AgentResponse(
            success=True,
            output="Hmm, I don't have anything saved about 'quantum computing' yet."
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("SEARCH_KNOWLEDGE", response)
        assert fulfilled is False
        assert "failure signal" in reason.lower()

    def test_save_success(self):
        """Archivist save confirmation should be fulfilled."""
        response = AgentResponse(
            success=True,
            output="Got it! Saved that note about machine learning with tags #ai #ml #deep-learning"
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("SAVE_KNOWLEDGE", response)
        assert fulfilled is True

    def test_save_rejected_garbage(self):
        """Archivist rejecting garbage input should be unfulfilled."""
        response = AgentResponse(
            success=True,
            output="That's too short to save - give me something with a bit more substance!"
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("SAVE_KNOWLEDGE", response)
        assert fulfilled is False

    def test_youtube_success(self):
        """YouTube extraction with transcript should be fulfilled."""
        response = AgentResponse(
            success=True,
            output="Got it! Saved that video.\n\nHow to Build AI Agents\nby TechChannel • 15:30\n\nTL;DR: This video covers building AI agents with Python...\n\nFull transcript saved (5000 chars). You can search for it anytime!"
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("SAVE_YOUTUBE", response)
        assert fulfilled is True

    def test_youtube_no_captions(self):
        """YouTube video without captions should be unfulfilled."""
        response = AgentResponse(
            success=True,
            output="Hmm, that video doesn't have captions available, so I can't extract the transcript."
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("SAVE_YOUTUBE", response)
        assert fulfilled is False

    def test_youtube_blocked(self):
        """YouTube blocking transcript access should be unfulfilled."""
        response = AgentResponse(
            success=True,
            output="YouTube's blocking the transcript extraction right now (happens sometimes with automated tools)."
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("SAVE_YOUTUBE", response)
        assert fulfilled is False

    def test_research_substantive(self):
        """Research with substantial output should be fulfilled."""
        response = AgentResponse(
            success=True,
            output="Here's what I found about quantum computing:\n\n1. Quantum Basics - Quantum computing uses qubits instead of classical bits. " * 3
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("RESEARCH", response)
        assert fulfilled is True

    def test_research_empty(self):
        """Research with tiny output should be unfulfilled."""
        response = AgentResponse(
            success=True,
            output="No results."
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("RESEARCH", response)
        assert fulfilled is False

    def test_hard_failure(self):
        """Any agent with success=False should be unfulfilled."""
        response = AgentResponse(
            success=False,
            output="",
            error="Connection timeout to OpenAI API"
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("RESEARCH", response)
        assert fulfilled is False
        assert "agent failure" in reason.lower()

    def test_code_generation_success(self):
        """Coder agent producing files should be fulfilled."""
        response = AgentResponse(
            success=True,
            output="Project finalized! Created 5 files in output/projects/20260206_143022/:\n- fact_orders.qvs\n- dim_customers.qvs\n- README.md"
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("CODE_GENERATION", response)
        assert fulfilled is True

    def test_tweet_success(self):
        """Tweet extraction with content should be fulfilled."""
        response = AgentResponse(
            success=True,
            output="Got it! Saved that tweet.\n\nTweet by @elonmusk (Elon Musk)\n\nExciting day for AI! The future is here.\n\nStats: 50,000 likes · 10,000 retweets"
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("SAVE_TWEET", response)
        assert fulfilled is True

    def test_tweet_private(self):
        """Private/deleted tweet should be unfulfilled."""
        response = AgentResponse(
            success=True,
            output="Tweet by @user. Could not extract full content. The tweet may be private or deleted."
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("SAVE_TWEET", response)
        assert fulfilled is False

    def test_url_save_success(self):
        """URL content extraction should be fulfilled."""
        response = AgentResponse(
            success=True,
            output="Content saved to knowledge graph!\n\nTitle: How AI is Changing Healthcare\nTags: ai, healthcare\nSize: 3500 characters"
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("SAVE_URL", response)
        assert fulfilled is True

    def test_url_extraction_error(self):
        """URL extraction failure should be unfulfilled."""
        response = AgentResponse(
            success=True,
            output="Error extracting webpage: 403 Forbidden"
        )
        fulfilled, reason = GoalTracker.evaluate_fulfillment("SAVE_URL", response)
        assert fulfilled is False


# ============================================================
# Full Lifecycle Tests (record → evaluate → query)
# ============================================================
class TestGoalTrackingLifecycle:
    """Test the complete lifecycle: record a goal, evaluate it, query results."""

    def test_record_and_evaluate_fulfilled(self, tracker):
        """Record a goal, evaluate as fulfilled, verify in DB."""
        tracker.record_goal("job-1", "user-42", "telegram",
                           "SEARCH_KNOWLEDGE", "archivist",
                           "what do you know about Python?")

        response = AgentResponse(
            success=True,
            output="Found 2 results about 'Python':\n\n1. Python Tutorial\n   Learn Python basics..."
        )
        tracker.evaluate_and_record("job-1", response, duration=3, retry_count=0)

        # Verify in DB
        tracker.cursor.execute("SELECT fulfilled, fulfillment_reason, duration_seconds FROM goal_tracking WHERE id = ?", ("job-1",))
        row = tracker.cursor.fetchone()
        assert row[0] == 1  # fulfilled
        assert "success signal" in row[1].lower()
        assert row[2] == 3

    def test_record_and_evaluate_unfulfilled_logs_issue(self, tracker):
        """Unfulfilled goal should create an issue in goal_issues table."""
        tracker.record_goal("job-2", "user-42", "telegram",
                           "SEARCH_KNOWLEDGE", "archivist",
                           "what do you know about quantum computing?")

        response = AgentResponse(
            success=True,
            output="Hmm, I don't have anything saved about 'quantum computing' yet."
        )
        tracker.evaluate_and_record("job-2", response, duration=2, retry_count=0)

        # Verify issue was logged
        tracker.cursor.execute("SELECT issue_type, user_input, agent_output FROM goal_issues WHERE goal_id = ?", ("job-2",))
        row = tracker.cursor.fetchone()
        assert row is not None
        assert row[0] == "soft_failure"
        assert "quantum computing" in row[1]
        assert "don't have anything" in row[2]

    def test_hard_failure_logs_issue(self, tracker):
        """Hard failure (success=False) should log issue with hard_failure type."""
        tracker.record_goal("job-3", "user-42", "telegram",
                           "RESEARCH", "researcher",
                           "research AI safety")

        response = AgentResponse(
            success=False, output="", error="OpenAI API timeout"
        )
        tracker.evaluate_and_record("job-3", response, duration=30, retry_count=3)

        tracker.cursor.execute("SELECT issue_type FROM goal_issues WHERE goal_id = ?", ("job-3",))
        row = tracker.cursor.fetchone()
        assert row[0] == "hard_failure"

    def test_get_recent_issues(self, tracker):
        """get_recent_issues should return issues joined with goal tracking data."""
        # Create 2 unfulfilled goals
        for i, (text, output) in enumerate([
            ("what about AI?", "Hmm, I don't have anything saved about 'AI' yet."),
            ("find notes on Docker", "Hmm, I don't have anything saved about 'Docker' yet."),
        ], 1):
            tracker.record_goal(f"job-{i}", "user-42", "telegram",
                               "SEARCH_KNOWLEDGE", "archivist", text)
            tracker.evaluate_and_record(
                f"job-{i}",
                AgentResponse(success=True, output=output),
                duration=2
            )

        issues = tracker.get_recent_issues(limit=10)
        assert len(issues) == 2
        assert issues[0]["agent"] == "archivist"
        assert issues[0]["goal_type"] == "SEARCH_KNOWLEDGE"
        assert "issue_type" in issues[0]

    def test_fulfilled_goals_do_not_create_issues(self, tracker):
        """Fulfilled goals should NOT appear in issues."""
        tracker.record_goal("job-ok", "user-42", "telegram",
                           "SAVE_KNOWLEDGE", "archivist",
                           "save this: AI is great")
        tracker.evaluate_and_record(
            "job-ok",
            AgentResponse(success=True, output="Got it! Saved that note with tags #ai"),
            duration=1
        )

        issues = tracker.get_recent_issues(limit=10)
        assert len(issues) == 0


# ============================================================
# Stats Tests
# ============================================================
class TestGoalStats:
    """Test the stats aggregation."""

    def test_stats_empty_db(self, tracker):
        """Stats on empty DB should return zeros."""
        stats = tracker.get_stats(days=7)
        assert stats["total"] == 0
        assert stats["fulfilled"] == 0
        assert stats["unfulfilled"] == 0
        assert stats["fulfillment_rate"] == 0
        assert stats["per_agent"] == {}
        assert stats["common_issues"] == {}

    def test_stats_with_data(self, tracker):
        """Stats should correctly aggregate fulfilled and unfulfilled goals."""
        # 3 fulfilled searches
        for i in range(3):
            tracker.record_goal(f"ok-{i}", "user-1", "telegram",
                               "SEARCH_KNOWLEDGE", "archivist", f"search {i}")
            tracker.evaluate_and_record(
                f"ok-{i}",
                AgentResponse(success=True, output=f"Found 1 result about '{i}':\n\n1. Result content here with enough text to pass threshold"),
                duration=2
            )

        # 2 unfulfilled saves
        for i in range(2):
            tracker.record_goal(f"fail-{i}", "user-1", "telegram",
                               "SAVE_KNOWLEDGE", "archivist", ".")
            tracker.evaluate_and_record(
                f"fail-{i}",
                AgentResponse(success=True, output="That's too short to save"),
                duration=1
            )

        stats = tracker.get_stats(days=7)
        assert stats["total"] == 5
        assert stats["fulfilled"] == 3
        assert stats["unfulfilled"] == 2
        assert stats["fulfillment_rate"] == 0.6

        # Per-agent
        assert "archivist" in stats["per_agent"]
        assert stats["per_agent"]["archivist"]["total"] == 5
        assert stats["per_agent"]["archivist"]["fulfilled"] == 3

        # Common issues
        assert len(stats["common_issues"]) > 0

    def test_stats_respects_date_range(self, tracker):
        """Stats should only include goals within the date range."""
        # Insert a goal with old date
        tracker.cursor.execute(
            """INSERT INTO goal_tracking (id, user_id, source, goal_type, agent, user_input, fulfilled, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 1, ?)""",
            ("old-1", "user-1", "telegram", "RESEARCH", "researcher",
             "old query", (datetime.now() - timedelta(days=30)).isoformat())
        )
        tracker.conn.commit()

        # Insert a recent goal
        tracker.record_goal("new-1", "user-1", "telegram",
                           "RESEARCH", "researcher", "new query")
        tracker.evaluate_and_record(
            "new-1",
            AgentResponse(success=True, output="Here are the results of my research " * 10),
            duration=5
        )

        stats = tracker.get_stats(days=7)
        assert stats["total"] == 1  # Only the recent one


# ============================================================
# Issue Management Tests
# ============================================================
class TestIssueManagement:
    """Test issue querying and resolution."""

    def test_resolve_issue(self, tracker):
        """resolve_issue should mark an issue as resolved."""
        tracker.record_goal("job-r", "user-1", "telegram",
                           "SEARCH_KNOWLEDGE", "archivist", "find stuff")
        tracker.evaluate_and_record(
            "job-r",
            AgentResponse(success=True, output="Hmm, I don't have anything saved about 'stuff' yet."),
            duration=1
        )

        issues = tracker.get_recent_issues()
        assert len(issues) == 1

        tracker.resolve_issue(issues[0]["issue_id"])

        # Should no longer appear in unresolved issues
        issues_after = tracker.get_recent_issues()
        assert len(issues_after) == 0

    def test_get_issues_for_user(self, tracker):
        """Should only return issues for the specified user."""
        # User A issue
        tracker.record_goal("job-a", "user-A", "telegram",
                           "RESEARCH", "researcher", "research cats")
        tracker.evaluate_and_record(
            "job-a",
            AgentResponse(success=True, output="No web results found."),
            duration=5
        )

        # User B issue
        tracker.record_goal("job-b", "user-B", "telegram",
                           "RESEARCH", "researcher", "research dogs")
        tracker.evaluate_and_record(
            "job-b",
            AgentResponse(success=True, output="No web results found."),
            duration=5
        )

        user_a_issues = tracker.get_issues_for_user("user-A")
        assert len(user_a_issues) == 1
        assert user_a_issues[0]["user_input"] == "research cats"


# ============================================================
# Issue Type Classification
# ============================================================
class TestIssueTypeClassification:
    """Test that issues are classified into the right types."""

    def test_hard_failure_type(self):
        response = AgentResponse(success=False, output="", error="timeout")
        issue_type = GoalTracker._classify_issue_type(response, "Agent failure: timeout")
        assert issue_type == "hard_failure"

    def test_soft_failure_type(self):
        response = AgentResponse(success=True, output="nothing found")
        issue_type = GoalTracker._classify_issue_type(response, "Failure signal: 'nothing found'")
        assert issue_type == "soft_failure"

    def test_empty_output_type(self):
        response = AgentResponse(success=True, output="ok")
        issue_type = GoalTracker._classify_issue_type(response, "Output too short (2 < 50 chars)")
        assert issue_type == "empty_output"

    def test_weak_output_type(self):
        response = AgentResponse(success=True, output="something happened")
        issue_type = GoalTracker._classify_issue_type(response, "No success signal in output")
        assert issue_type == "weak_output"


# ============================================================
# Fulfillment Rules Consistency
# ============================================================
class TestFulfillmentRules:
    """Test that all goal types have rules defined."""

    def test_all_goal_types_have_rules(self):
        """Every GoalType should have a corresponding entry in FULFILLMENT_RULES."""
        for goal_type in GoalType:
            assert goal_type.value in FULFILLMENT_RULES, \
                f"Missing fulfillment rules for {goal_type.value}"

    def test_rules_have_required_keys(self):
        """Each rule should have success_signals, failure_signals, min_output_length."""
        for goal_type, rules in FULFILLMENT_RULES.items():
            assert "success_signals" in rules, f"{goal_type} missing success_signals"
            assert "failure_signals" in rules, f"{goal_type} missing failure_signals"
            assert "min_output_length" in rules, f"{goal_type} missing min_output_length"
            assert isinstance(rules["success_signals"], list)
            assert isinstance(rules["failure_signals"], list)
            assert isinstance(rules["min_output_length"], int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
