"""
Goal Fulfillment Tracking System.

Tracks whether user requests are actually fulfilled by the agent pipeline.
Uses heuristic evaluation - no LLM calls.

Usage:
    tracker = GoalTracker(db_conn, redis_client)
    tracker.record_goal(job_id, user_id, "telegram", "SEARCH_KNOWLEDGE", "archivist", "what about AI?")
    tracker.evaluate_and_record(job_id, agent_response, duration=5, retry_count=0)
    issues = tracker.get_recent_issues(limit=5)
    stats = tracker.get_stats(days=7)
"""

import json
import re
from enum import Enum
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict


class GoalType(str, Enum):
    SAVE_KNOWLEDGE = "SAVE_KNOWLEDGE"
    SEARCH_KNOWLEDGE = "SEARCH_KNOWLEDGE"
    SAVE_URL = "SAVE_URL"
    SAVE_YOUTUBE = "SAVE_YOUTUBE"
    SAVE_TWEET = "SAVE_TWEET"
    RESEARCH = "RESEARCH"
    WRITE_CONTENT = "WRITE_CONTENT"
    CODE_GENERATION = "CODE_GENERATION"
    UNKNOWN = "UNKNOWN"


# Heuristic rules per goal type.
# success_signals: at least one must appear in output (if list is non-empty)
# failure_signals: if any appear, goal is unfulfilled
# min_output_length: output shorter than this is unfulfilled
FULFILLMENT_RULES = {
    "SAVE_KNOWLEDGE": {
        "success_signals": ["saved", "knowledge saved", "got it", "tagged"],
        "failure_signals": ["too short to save", "not sure what to do"],
        "min_output_length": 20,
    },
    "SEARCH_KNOWLEDGE": {
        "success_signals": ["found", "result"],
        "failure_signals": ["don't have anything", "nothing found", "no relevant knowledge"],
        "min_output_length": 50,
    },
    "SAVE_URL": {
        "success_signals": ["saved", "content saved", "knowledge graph"],
        "failure_signals": ["error extracting", "could not extract", "error saving"],
        "min_output_length": 50,
    },
    "SAVE_YOUTUBE": {
        "success_signals": ["saved that video", "transcript saved", "transcript"],
        "failure_signals": ["doesn't have captions", "blocking", "couldn't get the transcript"],
        "min_output_length": 100,
    },
    "SAVE_TWEET": {
        "success_signals": ["tweet by @", "saved"],
        "failure_signals": ["could not extract", "private or deleted", "invalid twitter"],
        "min_output_length": 50,
    },
    "RESEARCH": {
        "success_signals": [],
        "failure_signals": ["error searching", "no web results", "nothing found in knowledge"],
        "min_output_length": 100,
    },
    "WRITE_CONTENT": {
        "success_signals": [],
        "failure_signals": ["error", "failed"],
        "min_output_length": 50,
    },
    "CODE_GENERATION": {
        "success_signals": ["finalized", "files", "project"],
        "failure_signals": ["error in coding", "could not generate"],
        "min_output_length": 100,
    },
    "UNKNOWN": {
        "success_signals": [],
        "failure_signals": [],
        "min_output_length": 10,
    },
}


class GoalTracker:
    def __init__(self, db_conn, redis_client=None):
        self.conn = db_conn
        self.cursor = db_conn.cursor()
        self.redis = redis_client
        self._init_tables()

    def _init_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS goal_tracking (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                source TEXT DEFAULT 'telegram',
                goal_type TEXT NOT NULL,
                agent TEXT NOT NULL,
                user_input TEXT,
                fulfilled INTEGER DEFAULT 0,
                fulfillment_reason TEXT,
                output_length INTEGER DEFAULT 0,
                duration_seconds INTEGER,
                retry_count INTEGER DEFAULT 0,
                created_at TEXT,
                completed_at TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS goal_issues (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                goal_id TEXT NOT NULL,
                issue_type TEXT NOT NULL,
                details TEXT,
                user_input TEXT,
                agent_output TEXT,
                resolved INTEGER DEFAULT 0,
                created_at TEXT
            )
        """)
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_goal_tracking_fulfilled ON goal_tracking(fulfilled)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_goal_tracking_user_id ON goal_tracking(user_id)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_goal_tracking_created_at ON goal_tracking(created_at)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_goal_tracking_agent ON goal_tracking(agent)")
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_goal_issues_resolved ON goal_issues(resolved)")
        self.conn.commit()

    @staticmethod
    def classify_goal(agent: str, user_text: str) -> str:
        """Derive goal type from the routing decision + user text. No LLM."""
        text_lower = user_text.lower()

        if agent == "archivist":
            # Use the same detection logic as archivist
            from agents.archivist import _detect_action
            action = _detect_action(user_text)
            return GoalType.SEARCH_KNOWLEDGE if action == "search" else GoalType.SAVE_KNOWLEDGE

        if agent == "content_saver":
            if "youtube.com" in text_lower or "youtu.be" in text_lower:
                return GoalType.SAVE_YOUTUBE
            if "twitter.com" in text_lower or "x.com" in text_lower:
                return GoalType.SAVE_TWEET
            return GoalType.SAVE_URL

        if agent == "researcher":
            return GoalType.RESEARCH

        if agent == "writer":
            return GoalType.WRITE_CONTENT

        if agent == "coder":
            return GoalType.CODE_GENERATION

        return GoalType.UNKNOWN

    def record_goal(self, job_id: str, user_id: str, source: str,
                    goal_type: str, agent: str, user_input: str):
        """Record a new goal when a job starts processing."""
        try:
            self.cursor.execute(
                """INSERT OR REPLACE INTO goal_tracking
                   (id, user_id, source, goal_type, agent, user_input, fulfilled, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 0, ?)""",
                (job_id, user_id, source, goal_type, agent,
                 user_input[:500], datetime.now().isoformat())
            )
            self.conn.commit()
        except Exception as e:
            print(f"GoalTracker: Error recording goal: {e}")

    def evaluate_and_record(self, job_id: str, agent_response, duration: int = 0,
                            retry_count: int = 0):
        """Evaluate fulfillment after agent completes and update tracking."""
        try:
            # Get the goal record
            self.cursor.execute(
                "SELECT goal_type, user_input, agent FROM goal_tracking WHERE id = ?",
                (job_id,)
            )
            row = self.cursor.fetchone()
            if not row:
                return

            goal_type, user_input, agent = row
            fulfilled, reason = self.evaluate_fulfillment(goal_type, agent_response)

            # Update tracking record
            self.cursor.execute(
                """UPDATE goal_tracking
                   SET fulfilled = ?, fulfillment_reason = ?, output_length = ?,
                       duration_seconds = ?, retry_count = ?, completed_at = ?
                   WHERE id = ?""",
                (1 if fulfilled else -1, reason, len(agent_response.output),
                 duration, retry_count, datetime.now().isoformat(), job_id)
            )
            self.conn.commit()

            # Log issue if unfulfilled
            if not fulfilled:
                issue_type = self._classify_issue_type(agent_response, reason)
                self._log_issue(
                    goal_id=job_id,
                    issue_type=issue_type,
                    details=json.dumps({
                        "goal_type": goal_type,
                        "agent": agent,
                        "reason": reason,
                        "response_success": agent_response.success,
                        "output_length": len(agent_response.output),
                        "error": agent_response.error,
                        "duration": duration,
                        "retry_count": retry_count,
                    }),
                    user_input=user_input or "",
                    agent_output=agent_response.output[:1000]
                )
                print(f"GoalTracker: UNFULFILLED [{issue_type}] {goal_type} - {reason}")

            # Update Redis daily stats
            if self.redis:
                today = datetime.now().strftime("%Y-%m-%d")
                stats_key = f"goal:stats:daily:{today}"
                self.redis.hincrby(stats_key, "total", 1)
                self.redis.hincrby(stats_key, "fulfilled" if fulfilled else "unfulfilled", 1)
                self.redis.hincrby(stats_key, f"agent:{agent}", 1)
                self.redis.expire(stats_key, 86400 * 30)  # Keep 30 days

        except Exception as e:
            print(f"GoalTracker: Error evaluating goal: {e}")

    @staticmethod
    def evaluate_fulfillment(goal_type: str, agent_response) -> Tuple[bool, str]:
        """Pure heuristic evaluation. Returns (fulfilled, reason)."""
        # Hard failure
        if not agent_response.success:
            return False, f"Agent failure: {agent_response.error or 'unknown error'}"

        output = agent_response.output
        output_lower = output.lower()
        rules = FULFILLMENT_RULES.get(goal_type, FULFILLMENT_RULES["UNKNOWN"])

        # Check failure signals
        for signal in rules.get("failure_signals", []):
            if signal in output_lower:
                return False, f"Failure signal: '{signal}'"

        # Check minimum length
        min_len = rules.get("min_output_length", 10)
        if len(output.strip()) < min_len:
            return False, f"Output too short ({len(output.strip())} < {min_len} chars)"

        # Check success signals (if defined, at least one must match)
        success_signals = rules.get("success_signals", [])
        if success_signals:
            if any(signal in output_lower for signal in success_signals):
                return True, "Success signal matched"
            return False, "No success signal in output"

        # No success signals = any substantial output is success
        return True, "Output meets length threshold"

    @staticmethod
    def _classify_issue_type(agent_response, reason: str) -> str:
        """Classify the issue type from the response and reason."""
        if not agent_response.success:
            return "hard_failure"
        if "too short" in reason.lower() or "length" in reason.lower():
            return "empty_output"
        if "failure signal" in reason.lower():
            return "soft_failure"
        if "no success signal" in reason.lower():
            return "weak_output"
        return "unknown"

    def _log_issue(self, goal_id: str, issue_type: str, details: str,
                   user_input: str, agent_output: str):
        """Write issue to goal_issues table."""
        self.cursor.execute(
            """INSERT INTO goal_issues
               (goal_id, issue_type, details, user_input, agent_output, resolved, created_at)
               VALUES (?, ?, ?, ?, ?, 0, ?)""",
            (goal_id, issue_type, details, user_input[:500],
             agent_output[:1000], datetime.now().isoformat())
        )
        self.conn.commit()

    def get_recent_issues(self, limit: int = 10) -> List[Dict]:
        """Get recent unfulfilled goals with issue details."""
        self.cursor.execute("""
            SELECT gi.id, gi.goal_id, gi.issue_type, gi.details, gi.user_input,
                   gi.agent_output, gi.created_at, gt.agent, gt.goal_type,
                   gt.fulfillment_reason
            FROM goal_issues gi
            JOIN goal_tracking gt ON gi.goal_id = gt.id
            WHERE gi.resolved = 0
            ORDER BY gi.created_at DESC
            LIMIT ?
        """, (limit,))
        rows = self.cursor.fetchall()
        results = []
        for row in rows:
            results.append({
                "issue_id": row[0],
                "goal_id": row[1],
                "issue_type": row[2],
                "details": json.loads(row[3]) if row[3] else {},
                "user_input": row[4],
                "agent_output": row[5],
                "created_at": row[6],
                "agent": row[7],
                "goal_type": row[8],
                "fulfillment_reason": row[9],
            })
        return results

    def get_stats(self, days: int = 7) -> Dict:
        """Get fulfillment statistics for the last N days."""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        self.cursor.execute(
            "SELECT COUNT(*) FROM goal_tracking WHERE created_at >= ?", (cutoff,))
        total = self.cursor.fetchone()[0]

        self.cursor.execute(
            "SELECT COUNT(*) FROM goal_tracking WHERE fulfilled = 1 AND created_at >= ?",
            (cutoff,))
        fulfilled = self.cursor.fetchone()[0]

        self.cursor.execute(
            "SELECT COUNT(*) FROM goal_tracking WHERE fulfilled = -1 AND created_at >= ?",
            (cutoff,))
        unfulfilled = self.cursor.fetchone()[0]

        # Per-agent breakdown
        self.cursor.execute("""
            SELECT agent, COUNT(*) as total,
                   SUM(CASE WHEN fulfilled = 1 THEN 1 ELSE 0 END) as fulfilled
            FROM goal_tracking
            WHERE created_at >= ?
            GROUP BY agent
        """, (cutoff,))
        per_agent = {}
        for row in self.cursor.fetchall():
            agent_total = row[1]
            agent_fulfilled = row[2]
            per_agent[row[0]] = {
                "total": agent_total,
                "fulfilled": agent_fulfilled,
                "rate": agent_fulfilled / agent_total if agent_total > 0 else 0,
            }

        # Common issue types
        self.cursor.execute("""
            SELECT gi.issue_type, COUNT(*)
            FROM goal_issues gi
            JOIN goal_tracking gt ON gi.goal_id = gt.id
            WHERE gt.created_at >= ?
            GROUP BY gi.issue_type
            ORDER BY COUNT(*) DESC
        """, (cutoff,))
        common_issues = {row[0]: row[1] for row in self.cursor.fetchall()}

        return {
            "total": total,
            "fulfilled": fulfilled,
            "unfulfilled": unfulfilled,
            "fulfillment_rate": fulfilled / total if total > 0 else 0,
            "per_agent": per_agent,
            "common_issues": common_issues,
        }

    def get_issues_for_user(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Get recent issues for a specific user."""
        self.cursor.execute("""
            SELECT gi.id, gi.issue_type, gi.user_input, gi.created_at,
                   gt.agent, gt.goal_type, gt.fulfillment_reason
            FROM goal_issues gi
            JOIN goal_tracking gt ON gi.goal_id = gt.id
            WHERE gt.user_id = ? AND gi.resolved = 0
            ORDER BY gi.created_at DESC
            LIMIT ?
        """, (user_id, limit))
        rows = self.cursor.fetchall()
        return [{
            "issue_id": row[0],
            "issue_type": row[1],
            "user_input": row[2],
            "created_at": row[3],
            "agent": row[4],
            "goal_type": row[5],
            "fulfillment_reason": row[6],
        } for row in rows]

    def resolve_issue(self, issue_id: int):
        """Mark an issue as resolved."""
        self.cursor.execute(
            "UPDATE goal_issues SET resolved = 1 WHERE id = ?", (issue_id,))
        self.conn.commit()
