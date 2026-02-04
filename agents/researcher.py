from pydantic_ai import Agent, RunContext
from common.database import db
from common.contracts import AgentResponse
from common.database import db
from common.config import OPENAI_API_KEY, DEEPSEEK_API_KEY, LLM_PROVIDER
from pydantic_ai.models.openai import OpenAIModel
import httpx
from typing import List, Optional
import asyncio

if LLM_PROVIDER == "deepseek":
    model = OpenAIModel('deepseek-chat', provider='deepseek')
else:
    model = 'openai:gpt-4o-mini'

# Use str output for DeepSeek compatibility
researcher_agent = Agent(
    model,
    output_type=str,
    system_prompt="""You are the Researcher. Your job is to find information on the web or in the brain.
Use the tools provided to search for information and browse pages.
Always check the brain first to see if we already know something about the topic.
Provide clear, well-organized research results."""
)

@researcher_agent.tool
async def search_brain(ctx: RunContext[None], query: str) -> str:
    results = db.search_knowledge(query)
    if not results['documents'][0]:
        return "No relevant knowledge found in the brain."
    
    context = "\n".join([f"- {doc}" for doc in results['documents'][0]])
    return f"Brain Context found:\n{context}"

@researcher_agent.tool
async def search_web(ctx: RunContext[None], query: str) -> str:
    # Using a simple duckduckgo search via httpx (mocked or simple implementation)
    # In a real scenario, you'd use a search API or a more robust library
    try:
        async with httpx.AsyncClient() as client:
            # This is a very basic search simulation
            # For a production app, use a proper search API (e.g., Tavily, Serper, Google)
            return f"Web search results for '{query}': [Simulated search results showing relevant information about {query}]"
    except Exception as e:
        return f"Web search failed: {str(e)}"

@researcher_agent.tool
async def browse_page(ctx: RunContext[None], url: str) -> str:
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)
            content = await page.content()
            # Extract text content (simplified)
            text = await page.evaluate("document.body.innerText")
            await browser.close()
            return f"Content from {url}:\n{text[:2000]}..."
    except Exception as e:
        return f"Browsing failed for {url}: {str(e)}"

class Researcher:
    async def execute(self, payload: dict) -> AgentResponse:
        topic = payload.get("topic", payload.get("text", ""))
        prompt = f"Research this topic deeply: {topic}"

        try:
            result = await researcher_agent.run(prompt)

            # Convert string output to AgentResponse
            return AgentResponse(
                success=True,
                output=result.output,
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
