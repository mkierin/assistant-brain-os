"""
Task Manager agent — deterministic task/reminder CRUD. Zero LLM calls.

Handles:
  - Adding tasks & reminders with natural-language dates
  - Listing pending/upcoming tasks
  - Completing tasks (by index or keyword)
  - Linking tasks to existing knowledge entries
"""

import re
import uuid
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict

import dateparser

from common.database import db
from common.contracts import AgentResponse


# ── Action detection ─────────────────────────────────────────────────

def _detect_action(text: str) -> str:
    """Classify intent: 'add', 'list', 'complete', or 'delete'.

    Pure regex — no LLM.
    """
    t = text.lower().strip()

    # Complete / done
    complete_patterns = [
        r'\b(done|finished|completed?|check\s*off|mark\s*done)\b',
        r'\bcross\s*off\b',
    ]
    for p in complete_patterns:
        if re.search(p, t):
            return "complete"

    # Delete / cancel
    delete_patterns = [
        r'\b(delete|remove|cancel)\s+(task|todo|reminder)\b',
    ]
    for p in delete_patterns:
        if re.search(p, t):
            return "delete"

    # List / show
    list_patterns = [
        r'\b(my|show|list|view|see|pending|upcoming)\s*(tasks?|todos?|to-?dos?|reminders?)\b',
        r'\b(tasks?|todos?|to-?dos?|reminders?)\s*(list|pending|upcoming|due)\b',
        r'\bwhat\b.*\b(tasks?|todos?|to-?dos?|reminders?)\b',
        r'\bwhat\s+(do\s+)?i\s+(have|need)\s+to\s+do\b',
    ]
    for p in list_patterns:
        if re.search(p, t):
            return "list"

    # Default: add
    return "add"


# ── Date extraction ──────────────────────────────────────────────────

# Patterns that clearly separate "date part" from "task part"
_DATE_PREFIX_PATTERNS = [
    # "on Tuesday do X", "by Friday submit report"
    r'^(?:on|by)\s+(.+?)\s*(?:,\s*|\s+)(?:i\s+(?:need|have|want|must)\s+to\s+|(?:do|finish|complete|submit|send|call|meet|prepare|deliver)\s+)',
    # "next monday remind me to X"
    r'^((?:next|this)\s+\w+)\s+remind\s+me\s+(?:to\s+)?',
]

_DATE_SUFFIX_PATTERNS = [
    # "X on Tuesday", "X by next Friday", "X before March 15"
    r'\b(?:on|by|before|until|due)\s+(.+?)$',
    # "X next Tuesday"
    r'\b((?:next|this)\s+(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday))$',
    # "X tomorrow", "X today"
    r'\b(today|tomorrow|tonight)$',
]

_REMINDER_TIME_PATTERNS = [
    # "at 3pm", "at 14:00"
    r'\bat\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b',
    # "in 2 hours", "in 30 minutes"
    r'\b(in\s+\d+\s+(?:hour|minute|min|hr)s?)\b',
]


def _extract_date_and_task(text: str) -> Tuple[Optional[str], Optional[str], str]:
    """Extract due_date, reminder_at, and clean task title from text.

    Returns: (due_date ISO str or None, reminder_at ISO str or None, task_title)
    """
    cleaned = _strip_task_prefix(text)
    raw_date_str = None
    task_title = cleaned

    # Try prefix date patterns
    for pattern in _DATE_PREFIX_PATTERNS:
        m = re.search(pattern, cleaned, re.IGNORECASE)
        if m:
            raw_date_str = m.group(1).strip()
            # Task is everything after the date part
            task_title = cleaned[m.end():].strip()
            break

    # Try suffix date patterns
    if not raw_date_str:
        for pattern in _DATE_SUFFIX_PATTERNS:
            m = re.search(pattern, cleaned, re.IGNORECASE)
            if m:
                raw_date_str = m.group(1).strip()
                task_title = cleaned[:m.start()].strip()
                break

    # Try to extract a reminder time
    reminder_time_str = None
    for pattern in _REMINDER_TIME_PATTERNS:
        m = re.search(pattern, cleaned, re.IGNORECASE)
        if m:
            reminder_time_str = m.group(1).strip()
            # Remove time from task title
            task_title = re.sub(pattern, '', task_title, flags=re.IGNORECASE).strip()
            break

    # Parse the date with dateparser
    due_date = None
    reminder_at = None

    if raw_date_str:
        parsed = dateparser.parse(
            raw_date_str,
            settings={
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': datetime.now(),
            }
        )
        if parsed:
            due_date = parsed.strftime("%Y-%m-%d")

    # If no explicit date found, try to find a date anywhere in the text
    if not due_date:
        parsed_anywhere = dateparser.parse(
            cleaned,
            settings={
                'PREFER_DATES_FROM': 'future',
                'RELATIVE_BASE': datetime.now(),
            }
        )
        # Only accept if dateparser found something that isn't "now"
        if parsed_anywhere:
            delta = abs((parsed_anywhere - datetime.now()).total_seconds())
            if delta > 3600:  # More than 1 hour from now → it's a real date
                due_date = parsed_anywhere.strftime("%Y-%m-%d")

    # Build reminder_at
    if due_date:
        if reminder_time_str:
            time_parsed = dateparser.parse(
                reminder_time_str,
                settings={'PREFER_DATES_FROM': 'future'},
            )
            if time_parsed:
                reminder_at = f"{due_date}T{time_parsed.strftime('%H:%M:%S')}"
        else:
            # Default reminder: 9 AM on the due date
            reminder_at = f"{due_date}T09:00:00"

    # Clean up task title
    task_title = _clean_task_title(task_title)
    if not task_title:
        task_title = cleaned  # Fallback to full cleaned text

    return due_date, reminder_at, task_title


def _strip_task_prefix(text: str) -> str:
    """Remove 'remind me to', 'todo:', 'task:', etc."""
    patterns = [
        r'^remind\s+me\s+(?:to\s+)?',
        r'^(?:add\s+)?(?:a\s+)?(?:todo|to-?do|task|reminder)\s*[:;-]?\s*',
        r'^(?:i\s+)?(?:need|have|want|must)\s+to\s+',
        r'^don\'?t\s+(?:let\s+me\s+)?forget\s+(?:to\s+)?',
        r'^set\s+(?:a\s+)?reminder\s*(?:to|for)?\s*',
    ]
    result = text
    for p in patterns:
        result = re.sub(p, '', result, count=1, flags=re.IGNORECASE).strip()
        if result != text:
            break
    return result or text


def _clean_task_title(title: str) -> str:
    """Remove leftover date fragments and clean up the title."""
    # Remove dangling prepositions at start/end
    title = re.sub(r'^(?:on|by|before|until|due|at)\s+', '', title, flags=re.IGNORECASE).strip()
    title = re.sub(r'\s+(?:on|by|before)$', '', title, flags=re.IGNORECASE).strip()
    # Remove trailing punctuation noise
    title = title.strip(' ,;:-')
    # Capitalize first letter
    if title:
        title = title[0].upper() + title[1:]
    return title


# ── Priority extraction ──────────────────────────────────────────────

def _extract_priority(text: str) -> str:
    """Extract priority from text. Returns 'low', 'medium', or 'high'."""
    t = text.lower()
    if re.search(r'\b(urgent|asap|critical|important|high\s*priority)\b', t):
        return "high"
    if re.search(r'\b(low\s*priority|whenever|no\s*rush|someday)\b', t):
        return "low"
    return "medium"


# ── Tag extraction ───────────────────────────────────────────────────

_TASK_STOP_WORDS = {
    "the", "a", "an", "is", "are", "to", "of", "in", "for", "on", "with",
    "at", "by", "from", "i", "me", "my", "need", "have", "want", "must",
    "do", "will", "would", "should", "can", "could", "task", "todo",
    "remind", "reminder", "don", "let", "forget", "set", "add",
}


def _extract_task_tags(text: str) -> List[str]:
    """Extract 2-3 tags from task text."""
    words = re.findall(r'[a-zA-Z]+', text.lower())
    tags = [w for w in words if w not in _TASK_STOP_WORDS and len(w) > 2]
    seen = set()
    unique = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:3] or ["task"]


# ── Complete task matching ───────────────────────────────────────────

def _extract_complete_target(text: str, tasks: List[Dict]) -> Optional[str]:
    """Find which task the user wants to complete.

    Matches by:
      1. Task number (#1, #2, etc.)
      2. Keyword overlap with task titles
    """
    t = text.lower().strip()

    # Try to find a number reference: "done with #2", "complete task 3"
    num_match = re.search(r'#?(\d+)', t)
    if num_match:
        idx = int(num_match.group(1)) - 1  # 1-indexed for users
        if 0 <= idx < len(tasks):
            return tasks[idx]['id']

    # Keyword match: find the task with the most word overlap
    # Remove action words first
    cleaned = re.sub(r'\b(done|finished|completed?|check|off|mark|with|task|todo)\b', '', t).strip()
    if not cleaned:
        return tasks[0]['id'] if tasks else None

    query_words = set(cleaned.split())
    best_id = None
    best_overlap = 0

    for task in tasks:
        title_words = set(task['title'].lower().split())
        overlap = len(query_words & title_words)
        if overlap > best_overlap:
            best_overlap = overlap
            best_id = task['id']

    return best_id


# ── Formatting ───────────────────────────────────────────────────────

def _format_task_list(tasks: List[Dict]) -> str:
    """Format task list for display."""
    if not tasks:
        return "No pending tasks! You're all caught up."

    output = f"You have {len(tasks)} pending task{'s' if len(tasks) != 1 else ''}:\n\n"

    for i, task in enumerate(tasks, 1):
        title = task['title']
        due = task.get('due_date')
        priority = task.get('priority', 'medium')
        tags = task.get('tags', [])

        # Priority indicator
        pri_icon = {"high": "!!", "medium": "", "low": "~"}.get(priority, "")
        if pri_icon:
            pri_icon = f" [{pri_icon}]"

        output += f"  {i}. {title}{pri_icon}\n"

        details = []
        if due:
            # Calculate days until due (compare dates, not datetimes)
            try:
                due_dt = datetime.strptime(due, "%Y-%m-%d").date()
                today = datetime.now().date()
                delta = (due_dt - today).days
                if delta == 0:
                    details.append("due TODAY")
                elif delta == 1:
                    details.append("due tomorrow")
                elif delta < 0:
                    details.append(f"OVERDUE by {abs(delta)} day{'s' if abs(delta) != 1 else ''}")
                else:
                    details.append(f"due {due} ({delta} days)")
            except ValueError:
                details.append(f"due {due}")
        if tags:
            details.append(f"tags: {', '.join(tags)}")
        if details:
            output += f"     ({', '.join(details)})\n"

    output += "\nSay 'done with #N' to complete a task."
    return output


def _find_related_knowledge(task_title: str, limit: int = 3) -> List[str]:
    """Find knowledge entries related to this task. Returns list of IDs."""
    try:
        results = db.search_clean(task_title, limit=limit)
        return [r['id'] for r in results if r.get('id')]
    except Exception:
        return []


# ── Main execute ─────────────────────────────────────────────────────

async def execute(payload) -> AgentResponse:
    """Task manager entry point. Deterministic — no LLM calls."""
    if isinstance(payload, str):
        text = payload
        user_id = "default"
    else:
        text = payload.get("text", "")
        user_id = str(payload.get("user_id", "default"))

    print(f"Task manager activated for: {text}")

    action = _detect_action(text)

    try:
        if action == "add":
            return _handle_add(text, user_id)
        elif action == "list":
            return _handle_list(user_id)
        elif action == "complete":
            return _handle_complete(text, user_id)
        elif action == "delete":
            return _handle_delete(text, user_id)
        else:
            return AgentResponse(
                success=True,
                output="Not sure what to do with that. Try 'add a task', 'my tasks', or 'done with #1'.",
            )
    except Exception as e:
        error_msg = f"Error in task manager: {str(e)}"
        print(f"{error_msg}")
        return AgentResponse(success=False, output=error_msg, error=str(e))


def _handle_add(text: str, user_id: str) -> AgentResponse:
    """Add a new task/reminder."""
    due_date, reminder_at, title = _extract_date_and_task(text)
    priority = _extract_priority(text)
    tags = _extract_task_tags(title)

    # Find related knowledge
    linked = _find_related_knowledge(title)

    task_id = db.add_task(
        user_id=user_id,
        title=title,
        due_date=due_date,
        reminder_at=reminder_at,
        priority=priority,
        tags=tags,
        linked_knowledge=linked,
    )

    # Build confirmation message
    parts = [f"Task added: {title}"]
    if due_date:
        parts.append(f"Due: {due_date}")
    if reminder_at:
        parts.append(f"Reminder set: {reminder_at}")
    if priority != "medium":
        parts.append(f"Priority: {priority}")
    if linked:
        parts.append(f"Linked to {len(linked)} related note{'s' if len(linked) != 1 else ''}")

    return AgentResponse(success=True, output="\n".join(parts))


def _handle_list(user_id: str) -> AgentResponse:
    """List pending tasks."""
    tasks = db.get_tasks(user_id, status="pending")
    output = _format_task_list(tasks)
    return AgentResponse(success=True, output=output)


def _handle_complete(text: str, user_id: str) -> AgentResponse:
    """Complete a task by number or keyword."""
    tasks = db.get_tasks(user_id, status="pending")
    if not tasks:
        return AgentResponse(success=True, output="No pending tasks to complete!")

    target_id = _extract_complete_target(text, tasks)
    if not target_id:
        return AgentResponse(
            success=False,
            output="Couldn't figure out which task you mean. Try 'done with #1' or 'done with <task name>'.",
        )

    success = db.complete_task(target_id, user_id)
    if success:
        # Find the task title for confirmation
        task_title = next((t['title'] for t in tasks if t['id'] == target_id), "task")
        remaining = len(tasks) - 1
        msg = f"Done! Completed: {task_title}"
        if remaining > 0:
            msg += f"\n{remaining} task{'s' if remaining != 1 else ''} remaining."
        else:
            msg += "\nAll tasks done! You're all caught up."
        return AgentResponse(success=True, output=msg)
    else:
        return AgentResponse(success=False, output="Couldn't find that task. Try 'my tasks' to see the list.")


def _handle_delete(text: str, user_id: str) -> AgentResponse:
    """Delete a task by number or keyword."""
    tasks = db.get_tasks(user_id, status="pending")
    if not tasks:
        return AgentResponse(success=True, output="No pending tasks to delete!")

    target_id = _extract_complete_target(text, tasks)  # Reuse matching logic
    if not target_id:
        return AgentResponse(
            success=False,
            output="Couldn't figure out which task to delete. Try 'delete task #1'.",
        )

    success = db.delete_task(target_id, user_id)
    if success:
        task_title = next((t['title'] for t in tasks if t['id'] == target_id), "task")
        return AgentResponse(success=True, output=f"Deleted: {task_title}")
    else:
        return AgentResponse(success=False, output="Couldn't find that task.")
