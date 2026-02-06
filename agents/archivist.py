from pydantic_ai import Agent, RunContext
from common.database import db
from common.contracts import KnowledgeEntry, AgentResponse
from common.config import OPENAI_API_KEY, DEEPSEEK_API_KEY, LLM_PROVIDER
from pydantic_ai.models.openai import OpenAIModel
from typing import List
import re
import uuid

if LLM_PROVIDER == "deepseek":
    model = OpenAIModel('deepseek-chat', provider='deepseek')
else:
    model = 'openai:gpt-4o-mini'

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


async def execute(topic: str) -> AgentResponse:
    """
    Main execution function for the archivist.
    Detects whether to save or search based on the message content.
    """
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
        else:
            # For saves, let the agent handle it (needs LLM for tag generation)
            result = await archivist_agent.run(f"Save this to the knowledge base: {topic}")
            output = result.output

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


class Archivist:
    async def execute(self, payload: dict) -> AgentResponse:
        text = payload.get("text", "")

        # Use explicit action if provided, otherwise detect from text
        action = payload.get("action")
        if not action:
            action = _detect_action(text)

        try:
            if action == "search":
                search_topic = _extract_search_topic(text)
                results = db.search_clean(search_topic, limit=5)
                output = _format_search_results(results, search_topic)
            else:
                result = await archivist_agent.run(f"Save this to the knowledge base: {text}")
                output = result.output

            return AgentResponse(
                success=True,
                output=output,
                next_agent=None,
                data=None,
                error=None
            )
        except Exception as e:
            return AgentResponse(
                success=False,
                output="",
                error=str(e)
            )
