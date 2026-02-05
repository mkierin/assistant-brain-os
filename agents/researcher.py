from pydantic_ai import Agent, RunContext
from common.database import db
from common.contracts import AgentResponse
from common.config import DEEPSEEK_API_KEY, LLM_PROVIDER
from pydantic_ai.models.openai import OpenAIModel
from duckduckgo_search import DDGS
from typing import Optional

if LLM_PROVIDER == "deepseek":
    model = OpenAIModel('deepseek-chat', provider='deepseek')
else:
    model = 'openai:gpt-4o-mini'

# Simplified researcher - just basic web search
researcher_agent = Agent(
    model,
    output_type=str,
    system_prompt="""You are a simple Research Assistant for quick web lookups.

Your role:
1. Check the knowledge base first with search_brain()
2. If needed, do a quick web search with search_web()
3. Provide concise, helpful answers

Keep responses short and to the point. For deep content curation, the user should use the content_saver instead."""
)

@researcher_agent.tool
async def search_brain(ctx: RunContext[None], query: str) -> str:
    """
    Search the existing knowledge base for information.
    Always check this first before searching the web.
    """
    try:
        results = db.search_knowledge(query, limit=3)

        if not results['documents'][0]:
            return "Nothing found in knowledge base."

        output = "Found in your knowledge base:\n\n"
        for i, doc in enumerate(results['documents'][0][:3], 1):
            preview = doc[:300] + "..." if len(doc) > 300 else doc
            output += f"{i}. {preview}\n\n"

        return output

    except Exception as e:
        return f"Error searching knowledge base: {str(e)}"

@researcher_agent.tool
async def search_web(ctx: RunContext[None], query: str, max_results: int = 5) -> str:
    """
    Quick web search using DuckDuckGo.
    Returns short summaries and links.
    """
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return "No web results found."

        output = "Web search results:\n\n"
        for i, result in enumerate(results, 1):
            output += f"{i}. **{result['title']}**\n"
            output += f"   {result['body']}\n"
            output += f"   {result['href']}\n\n"

        return output

    except Exception as e:
        return f"Error searching web: {str(e)}"

async def execute(topic: str) -> AgentResponse:
    """
    Simple research execution - check knowledge base, then web if needed.
    """
    print(f"🔍 Researcher activated for: {topic}")

    try:
        # Run the agent
        result = await researcher_agent.run(f"Research this query: {topic}")
        output = result.output

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
