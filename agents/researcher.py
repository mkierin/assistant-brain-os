from common.database import db
from common.contracts import AgentResponse
from common.config import DEEPSEEK_API_KEY, LLM_PROVIDER, OPENAI_API_KEY, MODEL_NAME
from duckduckgo_search import DDGS


def _search_brain_direct(query: str, limit: int = 3) -> list:
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


async def _synthesize_answer(topic: str, brain_results: list, web_results: list) -> str:
    """Use LLM to synthesize a nice answer from raw search results.
    This is the ONLY LLM call — used for formatting, not decision-making.
    """
    from openai import AsyncOpenAI

    if LLM_PROVIDER == "deepseek":
        client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
        model = "deepseek-chat"
    else:
        client = AsyncOpenAI(api_key=OPENAI_API_KEY)
        model = MODEL_NAME

    # Build context from raw results
    context = ""
    if brain_results:
        context += "From the user's knowledge base:\n"
        for r in brain_results:
            title = r.get('title', 'Untitled')
            content = r.get('content', '')[:300]
            context += f"- {title}: {content}\n"
        context += "\n"

    if web_results:
        context += "From the web:\n"
        for r in web_results:
            context += f"- {r.get('title', '')}: {r.get('body', '')}\n"
            context += f"  Source: {r.get('href', '')}\n"

    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": (
                "You are a helpful research assistant. Synthesize a clear, concise answer "
                "from the search results provided. Be casual and friendly. "
                "Mention if info came from the user's knowledge base vs the web. "
                "Include relevant source links. Keep it under 300 words."
            )},
            {"role": "user", "content": f"Question: {topic}\n\n{context}"}
        ],
        temperature=0.3,
        max_tokens=600
    )
    return response.choices[0].message.content.strip()


def _format_raw_results(topic: str, brain_results: list, web_results: list) -> str:
    """Fallback: format results without LLM if synthesis fails."""
    output = ""

    if brain_results:
        output += "From your knowledge base:\n\n"
        for i, r in enumerate(brain_results, 1):
            title = r.get('title', 'Untitled')
            content = r.get('content', '')[:200]
            output += f"{i}. {title}\n   {content}\n\n"

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
        try:
            output = await _synthesize_answer(topic, brain_results, web_results)
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
