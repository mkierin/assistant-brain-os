"""
Journal agent — saves diary/journal entries with rich metadata and
auto-links them to the knowledge graph and existing notes.

Zero LLM calls. All deterministic.

Flow:
  1. Strip journal prefix ("journal:", "diary:", "today I...", etc.)
  2. Extract date (defaults to today)
  3. Extract topics via keyword extraction
  4. Save to SQLite + ChromaDB with content_type="journal" metadata
  5. Add to knowledge graph → link to daily note
  6. Cross-link: search existing knowledge for related notes, create edges
"""

import re
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Tuple

from common.database import db
from common.contracts import KnowledgeEntry, AgentResponse
from common.knowledge_graph import knowledge_graph


# ── Prefix stripping ────────────────────────────────────────────────

_JOURNAL_PREFIXES = [
    r'^journal\s*(?:entry)?\s*[:;-]?\s*',
    r'^diary\s*(?:entry)?\s*[:;-]?\s*',
    r'^daily\s*(?:log|note|entry)\s*[:;-]?\s*',
    r'^log\s*[:;-]\s*',
]


def _strip_journal_prefix(text: str) -> str:
    """Remove 'journal:', 'diary entry:', etc."""
    result = text
    for p in _JOURNAL_PREFIXES:
        result = re.sub(p, '', result, count=1, flags=re.IGNORECASE).strip()
        if result != text:
            break
    return result or text


# ── Topic extraction ─────────────────────────────────────────────────

_STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "to", "of", "in",
    "for", "on", "with", "at", "by", "from", "as", "into", "through",
    "during", "before", "after", "above", "below", "between", "under",
    "again", "then", "once", "here", "there", "when", "where", "why",
    "how", "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "just", "because", "but", "and", "or", "if",
    "while", "this", "that", "these", "those", "i", "me", "my", "myself",
    "we", "our", "ours", "you", "your", "he", "him", "his", "she", "her",
    "it", "its", "they", "them", "their", "what", "which", "who", "whom",
    "about", "also", "like", "much", "many", "well", "now", "still",
    "already", "really", "something", "anything", "everything", "nothing",
    "today", "yesterday", "tomorrow", "morning", "evening", "night",
    "went", "got", "get", "going", "think", "thought", "know", "knew",
    "feel", "feeling", "felt", "thing", "things", "made", "make",
    "day", "time", "lot", "lots", "bit", "way",
}


def _extract_topics(text: str) -> List[str]:
    """Extract meaningful topics/tags from journal text. No LLM."""
    words = re.findall(r'[a-zA-Z]+', text.lower())
    # Filter: not a stop word, length > 2
    topics = [w for w in words if w not in _STOP_WORDS and len(w) > 2]
    # Deduplicate preserving order
    seen = set()
    unique = []
    for t in topics:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:7] or ["journal"]


# ── Mood detection (simple, no LLM) ─────────────────────────────────

_MOOD_PATTERNS = {
    "positive": [
        r'\b(happy|excited|great|wonderful|amazing|productive|grateful|glad|love|enjoyed|fun|proud|accomplished)\b',
    ],
    "negative": [
        r'\b(sad|frustrated|angry|stressed|tired|exhausted|disappointed|worried|anxious|overwhelmed|annoyed)\b',
    ],
    "neutral": [
        r'\b(okay|fine|normal|usual|regular|typical|standard)\b',
    ],
}


def _detect_mood(text: str) -> Optional[str]:
    """Simple mood detection from journal text. Returns mood or None."""
    t = text.lower()
    for mood, patterns in _MOOD_PATTERNS.items():
        for p in patterns:
            if re.search(p, t):
                return mood
    return None


# ── Cross-linking ────────────────────────────────────────────────────

def _find_related_knowledge(text: str, topics: List[str], limit: int = 3) -> List[Dict]:
    """Search existing knowledge base for entries related to this journal entry.

    Returns list of dicts with id, title for linking.
    """
    # Use the most specific topics as search queries
    query = " ".join(topics[:4])
    if not query.strip():
        return []

    try:
        results = db.search_clean(query, limit=limit)
        # Filter out other journal entries to avoid self-linking noise
        return [
            r for r in results
            if r.get('source') != 'journal'
        ]
    except Exception:
        return []


def _link_to_knowledge_graph(
    entry_id: str,
    title: str,
    content: str,
    tags: List[str],
    related: List[Dict],
):
    """Add journal entry to knowledge graph and cross-link to related notes."""
    try:
        # Add the journal node
        node_id = knowledge_graph.add_note(
            title=title,
            content=content,
            tags=tags,
        )

        # Cross-link to related knowledge entries
        for related_entry in related:
            related_title = related_entry.get('title', '')
            # Find or create the related node in the graph
            target_id = knowledge_graph._find_note_by_title(related_title)
            if target_id and target_id != node_id:
                knowledge_graph.add_relationship(
                    node_id,
                    target_id,
                    relationship='related-to',
                    metadata={'reason': 'Journal cross-link', 'source': 'journal'},
                )

        return node_id
    except Exception as e:
        print(f"Knowledge graph linking failed: {e}")
        return None


# ── Title generation ─────────────────────────────────────────────────

def _generate_title(text: str, date: str) -> str:
    """Generate a title for the journal entry from content."""
    # Use first sentence or first 60 chars
    first_line = text.split('.')[0].split('\n')[0].strip()
    if len(first_line) > 60:
        first_line = first_line[:57] + "..."
    if first_line:
        return f"Journal {date}: {first_line}"
    return f"Journal Entry - {date}"


# ── Formatting ───────────────────────────────────────────────────────

def _format_journal_list(entries: List[Dict]) -> str:
    """Format journal entries for display."""
    if not entries:
        return "No journal entries yet. Send a voice or text message to start journaling!"

    output = f"Your last {len(entries)} journal entries:\n\n"
    for i, entry in enumerate(entries, 1):
        created = entry.get('created_at', '')[:10]
        content = entry.get('content', '')
        tags = entry.get('tags', [])

        # Preview: first 150 chars
        preview = content[:150].strip()
        if len(content) > 150:
            preview += "..."

        output += f"{i}. [{created}] {preview}\n"
        if tags:
            tag_str = ", ".join(f"#{t}" for t in tags[:5] if t not in ('journal', 'diary'))
            if tag_str:
                output += f"   {tag_str}\n"
        output += "\n"

    return output.strip()


# ── Action detection ─────────────────────────────────────────────────

def _detect_action(text: str) -> str:
    """Detect whether user wants to view journal or write an entry."""
    t = text.lower().strip()

    view_patterns = [
        r'\b(?:my|show|view|read|list|see|recent|last)\s*(?:journal|diary|entries|logs?)\b',
        r'\b(?:journal|diary)\s*(?:entries|history|list|log)\b',
        r'\bwhat\s+did\s+i\s+(?:write|journal|log|note)\b',
    ]
    for p in view_patterns:
        if re.search(p, t):
            return "view"

    return "save"


# ── Main execute ─────────────────────────────────────────────────────

async def execute(payload) -> AgentResponse:
    """Journal agent entry point. Deterministic — no LLM calls."""
    if isinstance(payload, str):
        text = payload
        user_id = "default"
        source = "text"
    else:
        text = payload.get("text", "")
        user_id = str(payload.get("user_id", "default"))
        source = payload.get("input_type", "text")

    print(f"Journal agent activated for: {text[:80]}")

    action = _detect_action(text)

    try:
        if action == "view":
            return _handle_view()
        else:
            return _handle_save(text, user_id, source)
    except Exception as e:
        error_msg = f"Error in journal: {str(e)}"
        print(f"{error_msg}")
        return AgentResponse(success=False, output=error_msg, error=str(e))


def _handle_view() -> AgentResponse:
    """Show recent journal entries."""
    entries = db.get_journal_entries(limit=7)
    output = _format_journal_list(entries)
    return AgentResponse(success=True, output=output)


def _handle_save(text: str, user_id: str, source: str) -> AgentResponse:
    """Save a journal entry with metadata and cross-linking."""
    today = datetime.now().strftime("%Y-%m-%d")

    # Clean the text
    content = _strip_journal_prefix(text)

    # Validate
    if len(content.strip()) < 5 or not re.search(r'[a-zA-Z]', content):
        return AgentResponse(
            success=False,
            output="That's too short for a journal entry. Tell me more about your day!",
        )

    # Extract metadata
    topics = _extract_topics(content)
    mood = _detect_mood(content)
    title = _generate_title(content, today)

    # Build tags: always include journal + date + topics
    tags = ["journal", today] + [t for t in topics if t != "journal"]

    # Build metadata
    metadata = {
        "content_type": "journal",
        "date": today,
        "input_source": source,
        "user_id": user_id,
    }
    if mood:
        metadata["mood"] = mood

    # Save to DB
    entry_id = str(uuid.uuid4())
    entry = KnowledgeEntry(
        text=content,
        tags=tags,
        source="journal",
        metadata=metadata,
        embedding_id=entry_id,
    )
    db.add_knowledge(entry)

    # Cross-link with existing knowledge
    related = _find_related_knowledge(content, topics)
    related_ids = [r['id'] for r in related if r.get('id')]

    # Add to knowledge graph
    _link_to_knowledge_graph(entry_id, title, content, tags, related)

    # Build confirmation
    parts = [f"Journal entry saved for {today}."]
    if mood:
        parts.append(f"Mood: {mood}")
    parts.append(f"Topics: {', '.join(f'#{t}' for t in topics[:5])}")

    if related:
        related_titles = [r.get('title', 'Untitled')[:40] for r in related[:3]]
        parts.append(f"Linked to {len(related)} related note{'s' if len(related) != 1 else ''}: {', '.join(related_titles)}")

    return AgentResponse(success=True, output="\n".join(parts))
