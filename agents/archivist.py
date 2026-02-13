from pydantic_ai import Agent, RunContext
from common.database import db
from common.contracts import KnowledgeEntry, AgentResponse
from common.llm import get_pydantic_ai_model
from typing import List
import re
import uuid

model = get_pydantic_ai_model()

# Agent for saving knowledge (tool-based)
archivist_agent = Agent(
    model,
    output_type=str,
    system_prompt="""You're helping a friend save stuff to their notes. Be casual and helpful.

When they want to save something:
- Use save_knowledge() to store it with good tags
- Pick 3-5 relevant tags for the content
- Confirm what was saved

Response style for saves:
"Got it! Saved that note about X with tags #tag1 #tag2"

NO bold text (**), NO formal language. Just friendly and quick."""
)

@archivist_agent.tool
async def save_knowledge(ctx: RunContext[None], text: str, tags: List[str], source: str) -> str:
    entry = KnowledgeEntry(
        text=text,
        tags=tags,
        source=source,
        embedding_id=str(uuid.uuid4())
    )
    db.add_knowledge(entry)
    return f"Knowledge saved with tags: {', '.join(tags)}"

@archivist_agent.tool
async def search_knowledge(ctx: RunContext[None], query: str) -> str:
    results = db.search_knowledge(query)
    if not results['documents'][0]:
        return "No relevant knowledge found."

    context = "\n".join([f"- {doc}" for doc in results['documents'][0]])
    return f"Relevant knowledge found:\n{context}"


MIN_SAVE_LENGTH = 3  # Minimum character length to save (reject garbage like ".", "..", etc.)

# Common stop words to exclude from auto-tagging
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
    "about", "save", "remember", "note", "store", "keep", "add", "also",
    "like", "just", "much", "many", "well", "now", "still", "already",
    "really", "something", "anything", "everything", "nothing",
}


def _is_meaningful_content(text: str) -> bool:
    """Check if text has enough substance to be worth saving."""
    stripped = text.strip()
    # Too short
    if len(stripped) < MIN_SAVE_LENGTH:
        return False
    # Only punctuation/whitespace
    if not re.search(r'[a-zA-Z0-9]', stripped):
        return False
    return True


def _strip_save_prefix(text: str) -> str:
    """Remove 'save this:', 'remember that:', etc. from the beginning."""
    patterns = [
        r'^save\s+(?:this|that)\s*[:;-]?\s*',
        r'^remember\s+(?:this|that)?\s*[:;-]?\s*',
        r'^note\s*[:;-]\s*',
        r'^note\s+(?:this|that)\s*[:;-]?\s*',
        r'^store\s+(?:this|that)?\s*[:;-]?\s*',
        r'^keep\s+(?:this|that)\s*[:;-]?\s*',
        r'^add\s+(?:this|that|to\s+(?:my\s+)?(?:notes?|brain|knowledge))\s*[:;-]?\s*',
    ]
    cleaned = text
    for pattern in patterns:
        cleaned = re.sub(pattern, '', cleaned, count=1, flags=re.IGNORECASE).strip()
        if cleaned != text:
            break
    return cleaned or text


def _extract_tags(text: str) -> list:
    """Extract tags from text using simple keyword extraction. No LLM."""
    words = re.findall(r'[a-zA-Z]+', text.lower())
    tags = [w for w in words if w not in _STOP_WORDS and len(w) > 2]
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique[:5] or ["general"]


def _detect_action(text: str) -> str:
    """Detect whether the user wants to search or save based on message content."""
    text_lower = text.lower().strip()

    # Search patterns - questions, lookups, retrievals
    search_patterns = [
        r'\bwhat\b.*\b(do|did|have|know|about)\b',
        r'\bfind\b', r'\bsearch\b', r'\blook\s*(up|for)\b',
        r'\bshow\s*me\b', r'\bwhat\s*(did|do)\s*i\b',
        r'\bhave\s*(i|we|you)\b.*\b(about|on|for)\b',
        r'\bdo\s*(you|we|i)\s*(have|know)\b',
        r'\banything\s*(about|on|for)\b',
        r'\btell\s*me\s*(about|what)\b',
        r'^(what|where|when|who|how|which|do|did|is|are|was|can)\b',
    ]
    for pattern in search_patterns:
        if re.search(pattern, text_lower):
            return "search"

    # Save patterns - explicit save/store/remember intent
    save_patterns = [
        r'\bsave\b', r'\bremember\b', r'\bstore\b', r'\bnote\b',
        r'\bkeep\b.*\b(this|that)\b', r'\badd\b.*\b(this|that|to)\b',
    ]
    for pattern in save_patterns:
        if re.search(pattern, text_lower):
            return "save"

    # Default: if it looks like a question or query, search; otherwise save
    if text_lower.endswith('?') or len(text.split()) <= 5:
        return "search"

    return "save"


def _extract_search_topic(text: str) -> str:
    """Extract the core topic from a search question.

    Turns 'what information do you have about OpenClaw?' into 'OpenClaw'.
    """
    text_clean = text.strip().rstrip('?').strip()

    # Try to extract the topic after common phrasing patterns
    extraction_patterns = [
        r'(?:what|which)\s+(?:info|information|stuff|things?|notes?|data)\s+(?:do|did)\s+(?:you|we|i)\s+(?:have|know)\s+(?:about|on|for)\s+(.+)',
        r'(?:what|which)\s+(?:do|did)\s+(?:you|we|i)\s+(?:have|know)\s+(?:about|on|for)\s+(.+)',
        r'(?:do)\s+(?:you|we|i)\s+(?:have|know)\s+(?:anything|something|stuff)\s+(?:about|on|for)\s+(.+)',
        r'(?:tell|show)\s+me\s+(?:about|what\s+(?:you|we|i)\s+(?:have|know)\s+about)\s+(.+)',
        r'(?:find|search|look\s*up)\s+(?:my\s+)?(?:notes?\s+)?(?:about|on|for)?\s*(.+)',
        r'(?:anything|something|everything)\s+(?:about|on|for)\s+(.+)',
        r'(?:what\s+(?:about|is|are))\s+(.+)',
        r'(?:show\s+me)\s+(.+)',
        r'(?:search\s+for)\s+(.+)',
    ]
    text_lower = text_clean.lower()
    for pattern in extraction_patterns:
        match = re.search(pattern, text_lower)
        if match:
            topic = match.group(1).strip()
            # Return with original casing by finding the position in original text
            start_pos = text_lower.find(topic)
            if start_pos >= 0:
                return text_clean[start_pos:start_pos + len(topic)]
            return topic

    # Fallback: return the cleaned text as-is
    return text_clean


def _format_search_results(results: list, search_topic: str) -> str:
    """Format search results directly — no LLM needed, just clean output."""
    if not results:
        return f"Hmm, I don't have anything saved about '{search_topic}' yet."

    output = f"Found {len(results)} result{'s' if len(results) != 1 else ''} about '{search_topic}':\n\n"

    for i, entry in enumerate(results, 1):
        title = entry.get('title', 'Untitled')
        content = entry.get('content', '')
        tags = entry.get('tags', [])
        url = entry.get('url', '')
        source = entry.get('source', '')
        created = entry.get('created_at', '')

        # Clean preview: strip contextual prefix if present, limit length
        if content.startswith('['):
            # Remove the [Document: ...] contextual prefix
            bracket_end = content.find(']\n\n')
            if bracket_end > 0:
                content = content[bracket_end + 3:]

        # Truncate for preview
        preview = content[:300].strip()
        if len(content) > 300:
            preview += "..."

        output += f"{i}. {title}\n"
        output += f"   {preview}\n"

        extras = []
        if tags:
            extras.append(f"tags: {', '.join(tags[:5])}")
        if url:
            extras.append(f"url: {url}")
        if created:
            extras.append(f"saved: {created[:10]}")
        if extras:
            output += f"   ({', '.join(extras)})\n"
        output += "\n"

    return output.strip()


async def execute(payload: dict) -> AgentResponse:
    """
    Main execution function for the archivist.
    Accepts full payload dict with text, user_id, source, etc.
    Detects whether to save or search based on the message content.
    """
    # Support both dict payload (from worker) and plain string (from tests/direct calls)
    if isinstance(payload, str):
        topic = payload
    else:
        topic = payload.get("text", "")

    print(f"📚 Archivist activated for: {topic}")

    action = _detect_action(topic)

    try:
        if action == "search":
            # Direct search: hybrid (BM25 + semantic) → SQLite lookup → format
            # No LLM involved — guaranteed to return actual results
            search_topic = _extract_search_topic(topic)
            print(f"🔍 Searching for: {search_topic}")
            results = db.search_clean(search_topic, limit=5)
            output = _format_search_results(results, search_topic)
        elif action == "save":
            # Validate content before saving
            if not _is_meaningful_content(topic):
                output = "That's too short to save - give me something with a bit more substance!"
            else:
                # Direct save: strip prefix, extract tags, save to DB. No LLM.
                content = _strip_save_prefix(topic)
                tags = _extract_tags(content)

                entry = KnowledgeEntry(
                    text=content,
                    tags=tags,
                    source="archivist",
                    embedding_id=str(uuid.uuid4())
                )
                db.add_knowledge(entry)
                output = f"Saved! Tagged as: {', '.join(f'#{t}' for t in tags)}"
                print(f"💾 Saved directly: {content[:60]}... | Tags: {tags}")
        else:
            output = "I'm not sure what to do with that. Try asking a question or telling me something to save!"

        return AgentResponse(
            success=True,
            output=output,
            agent="archivist"
        )

    except Exception as e:
        error_msg = f"Error in archivist: {str(e)}"
        print(f"❌ {error_msg}")
        return AgentResponse(
            success=False,
            output=error_msg,
            agent="archivist"
        )
