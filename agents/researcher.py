from common.database import db
from common.contracts import AgentResponse
from common.llm import get_async_client, get_model_name
from duckduckgo_search import DDGS


def _search_brain_direct(query: str, limit: int = 8) -> list:
    """Search knowledge base directly. Returns list of dicts or empty list."""
    try:
        return db.search_clean(query, limit=limit)
    except Exception as e:
        print(f"⚠️ Brain search error: {e}")
        return []


def _search_web_direct(query: str, max_results: int = 5) -> list:
    """Search web via DuckDuckGo directly. Returns list of dicts or empty list."""
    try:
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))
    except Exception as e:
        print(f"⚠️ Web search error: {e}")
        return []


async def _synthesize_answer(topic: str, brain_results: list, web_results: list, conversation_history: list = None) -> str:
    """Use LLM to synthesize a nice answer from raw search results.
    This is the ONLY LLM call — used for formatting, not decision-making.
    """
    client = get_async_client()
    model = get_model_name()

    # Build context from raw results
    context = ""
    if brain_results:
        context += "From the user's knowledge base:\n"
        for r in brain_results:
            title = r.get('title', 'Untitled')
            content = r.get('content', '')[:600]
            tags = r.get('tags', [])
            tag_str = f" [tags: {', '.join(tags)}]" if tags else ""
            context += f"- {title}{tag_str}: {content}\n"
        context += "\n"

    if web_results:
        context += "From the web:\n"
        for r in web_results:
            context += f"- {r.get('title', '')}: {r.get('body', '')}\n"
            context += f"  Source: {r.get('href', '')}\n"

    # Include conversation history for context-aware responses
    if conversation_history:
        context += "\nRecent conversation:\n"
        for msg in conversation_history[-6:]:
            role = "User" if msg.get("sender") == "user" else "Assistant"
            context += f"{role}: {msg.get('message', '')[:200]}\n"

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": (
                "You are a helpful research assistant. Synthesize a clear, comprehensive answer "
                "from the search results provided. Be casual and friendly, like texting a knowledgeable friend. "
                "PRIORITIZE the user's knowledge base results — those are their personal notes and saved content. "
                "Mention what came from their knowledge base vs the web. "
                "Include relevant source links. If the user has saved multiple things on this topic, "
                "connect the dots and summarize the themes. Keep it under 400 words. "
                "If there's conversation history, take it into account for follow-up questions."
            )},
            {"role": "user", "content": f"Question: {topic}\n\n{context}"}
        ],
        temperature=0.3,
        max_tokens=800
    )
    return response.choices[0].message.content.strip()


def _format_raw_results(topic: str, brain_results: list, web_results: list) -> str:
    """Fallback: format results without LLM if synthesis fails."""
    output = ""

    if brain_results:
        output += f"From your knowledge base ({len(brain_results)} results):\n\n"
        for i, r in enumerate(brain_results, 1):
            title = r.get('title', 'Untitled')
            content = r.get('content', '')[:400]
            tags = r.get('tags', [])
            output += f"{i}. {title}\n   {content}\n"
            if tags:
                output += f"   Tags: {', '.join(tags[:5])}\n"
            output += "\n"

    if web_results:
        output += "From the web:\n\n"
        for i, r in enumerate(web_results, 1):
            output += f"{i}. {r.get('title', 'No title')}\n"
            output += f"   {r.get('body', '')}\n"
            output += f"   {r.get('href', '')}\n\n"

    if not output:
        output = f"I couldn't find anything about '{topic}'. Try rephrasing your question."

    return output.strip()


async def execute(payload) -> AgentResponse:
    """
    Research execution: search brain + web directly, then synthesize.
    LLM is used ONLY for formatting the answer — searches always happen.
    """
    topic = payload.get("text", "") if isinstance(payload, dict) else payload
    print(f"🔍 Researcher activated for: {topic}")

    try:
        # Step 1: Always search both sources (no LLM deciding whether to search)
        brain_results = _search_brain_direct(topic)
        web_results = _search_web_direct(topic)

        has_results = bool(brain_results or web_results)

        if brain_results:
            print(f"🧠 Found {len(brain_results)} brain results")
        if web_results:
            print(f"🌐 Found {len(web_results)} web results")

        if not has_results:
            return AgentResponse(
                success=True,
                output=f"I searched your knowledge base and the web but couldn't find anything about '{topic}'. Try rephrasing or being more specific.",
                agent="researcher"
            )

        # Step 2: Try LLM synthesis (the ONLY LLM call — for formatting, not decision-making)
        conversation_history = payload.get("conversation_history") if isinstance(payload, dict) else None
        try:
            output = await _synthesize_answer(topic, brain_results, web_results, conversation_history)
        except Exception as synth_err:
            print(f"⚠️ LLM synthesis failed ({synth_err}), using raw format")
            output = _format_raw_results(topic, brain_results, web_results)

        return AgentResponse(
            success=True,
            output=output,
            agent="researcher"
        )

    except Exception as e:
        error_msg = f"Error in researcher: {str(e)}"
        print(f"❌ {error_msg}")
        return AgentResponse(
            success=False,
            output=error_msg,
            agent="researcher"
        )
