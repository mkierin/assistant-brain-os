from pydantic_ai import Agent, RunContext
from common.database import db
from common.contracts import AgentResponse
from common.config import DEEPSEEK_API_KEY, TAVILY_API_KEY, BRAVE_API_KEY, LLM_PROVIDER
from pydantic_ai.models.openai import OpenAIModel
from duckduckgo_search import DDGS
from tavily import TavilyClient
from typing import List, Optional
import asyncio
import hashlib
import json
import httpx

if LLM_PROVIDER == "deepseek":
    model = OpenAIModel('deepseek-chat', provider='deepseek')
else:
    model = 'openai:gpt-4o-mini'

# Initialize Tavily client
tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

# Simple cache using ChromaDB
def get_cache_key(query: str) -> str:
    """Generate cache key from query"""
    return hashlib.md5(query.lower().encode()).hexdigest()

# Enhanced researcher agent with query analysis and multi-source search
researcher_agent = Agent(
    model,
    output_type=str,
    system_prompt="""You are an advanced Research Agent with access to multiple search engines and tools.

Your research process:

1. **Analyze the Query**: Use analyze_query() to break complex questions into 2-4 focused sub-questions. For simple queries, skip this step.

2. **Search Multiple Sources**: Use ALL available search tools to gather comprehensive information:
   - search_brain() - Check existing knowledge first
   - search_tavily() - Best for AI-optimized, summarized research (HIGHLY RECOMMENDED)
   - search_web_ddg() - Good for general web search
   - search_brave() - Comprehensive search results (if available)

3. **Deep Dive (Optional)**: If needed, use browse_page() to get full content from 1-2 key sources.

4. **Synthesize**: Combine all findings into a comprehensive, well-organized response that:
   - Presents information clearly and conversationally
   - Highlights key points from multiple sources
   - Mentions sources when relevant
   - Is factual and informative

IMPORTANT: Actually USE the tools. Never say "I can help research" - DO the research by calling the search functions!

For best results on important topics, use analyze_query() first, then search each sub-question with tavily."""
)

@researcher_agent.tool
async def analyze_query(ctx: RunContext[None], query: str) -> str:
    """
    Analyze a complex query and break it down into 2-4 focused sub-questions.
    Use this for complex topics to get better research results.

    Returns a JSON list of sub-questions.
    """
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com"
    )

    prompt = f"""Analyze this research query and break it into 2-4 focused sub-questions that together would comprehensively answer the main question.

Query: {query}

Return ONLY a JSON array of strings (sub-questions), nothing else.
Example: ["What is X?", "How does Y work?", "What are the benefits of Z?"]"""

    try:
        response = await client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        sub_questions = json.loads(response.choices[0].message.content)
        formatted = "Query breakdown:\n" + "\n".join([f"{i+1}. {q}" for i, q in enumerate(sub_questions)])
        return formatted
    except Exception as e:
        return f"Query analysis skipped: {str(e)}"

@researcher_agent.tool
async def search_brain(ctx: RunContext[None], query: str) -> str:
    """Search existing knowledge base for relevant cached information"""
    results = db.search_knowledge(query, limit=5)
    if not results['documents'][0]:
        return "No relevant knowledge found in the brain."

    context = "\n".join([f"- {doc}" for doc in results['documents'][0][:5]])
    return f"Knowledge base results:\n{context}"

@researcher_agent.tool
async def search_tavily(ctx: RunContext[None], query: str, max_results: int = 5) -> str:
    """
    Search using Tavily API - PURPOSE-BUILT FOR AI RESEARCH.
    Returns AI-optimized, high-quality results with summaries.
    RECOMMENDED for most research queries.
    """
    if not tavily_client:
        return "Tavily API not configured"

    try:
        # Check cache first
        cache_key = f"tavily_{get_cache_key(query)}"
        cached = db.search_knowledge(cache_key, limit=1)
        if cached['documents'][0]:
            return f"[Cached] Tavily results:\n{cached['documents'][0][0]}"

        # Search with Tavily
        response = tavily_client.search(
            query=query,
            max_results=max_results,
            include_answer=True,  # Get AI-generated answer
            include_raw_content=False  # Save tokens
        )

        # Format results
        formatted = f"Tavily search for '{query}':\n\n"

        # Include AI answer if available
        if response.get('answer'):
            formatted += f"AI Summary: {response['answer']}\n\n"

        # Add source results
        formatted += "Sources:\n"
        for i, result in enumerate(response.get('results', []), 1):
            title = result.get('title', 'No title')
            content = result.get('content', 'No description')
            url = result.get('url', '')
            formatted += f"{i}. **{title}**\n   {content}\n   Source: {url}\n\n"

        # Cache results
        try:
            db.add_knowledge({
                "text": formatted,
                "tags": [cache_key, "tavily_cache"],
                "source": "tavily"
            })
        except:
            pass

        return formatted.strip()

    except Exception as e:
        return f"Tavily search failed: {str(e)}"

@researcher_agent.tool
async def search_web_ddg(ctx: RunContext[None], query: str, max_results: int = 5) -> str:
    """
    Search using DuckDuckGo (free, privacy-focused).
    Good for general web search.
    """
    try:
        # Check cache
        cache_key = f"ddg_{get_cache_key(query)}"
        cached = db.search_knowledge(cache_key, limit=1)
        if cached['documents'][0]:
            return f"[Cached] DuckDuckGo results:\n{cached['documents'][0][0]}"

        # Search with DuckDuckGo
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No DuckDuckGo results found for '{query}'"

        # Format results
        formatted = f"DuckDuckGo search for '{query}':\n\n"
        for i, result in enumerate(results, 1):
            title = result.get('title', 'No title')
            body = result.get('body', 'No description')
            url = result.get('href', '')
            formatted += f"{i}. **{title}**\n   {body}\n   Source: {url}\n\n"

        # Cache results
        try:
            db.add_knowledge({
                "text": formatted,
                "tags": [cache_key, "ddg_cache"],
                "source": "duckduckgo"
            })
        except:
            pass

        return formatted.strip()

    except Exception as e:
        return f"DuckDuckGo search failed: {str(e)}"

@researcher_agent.tool
async def search_brave(ctx: RunContext[None], query: str, max_results: int = 5) -> str:
    """
    Search using Brave Search API (requires API key).
    Comprehensive search results with good quality.
    """
    if not BRAVE_API_KEY:
        return "Brave Search API key not configured (optional)"

    try:
        # Check cache
        cache_key = f"brave_{get_cache_key(query)}"
        cached = db.search_knowledge(cache_key, limit=1)
        if cached['documents'][0]:
            return f"[Cached] Brave results:\n{cached['documents'][0][0]}"

        # Search with Brave
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={"q": query, "count": max_results},
                headers={"X-Subscription-Token": BRAVE_API_KEY},
                timeout=10.0
            )

            if response.status_code != 200:
                return f"Brave search returned status {response.status_code}"

            data = response.json()
            results = data.get('web', {}).get('results', [])

            if not results:
                return f"No Brave results found for '{query}'"

            # Format results
            formatted = f"Brave search for '{query}':\n\n"
            for i, result in enumerate(results[:max_results], 1):
                title = result.get('title', 'No title')
                description = result.get('description', 'No description')
                url = result.get('url', '')
                formatted += f"{i}. **{title}**\n   {description}\n   Source: {url}\n\n"

            # Cache results
            try:
                db.add_knowledge({
                    "text": formatted,
                    "tags": [cache_key, "brave_cache"],
                    "source": "brave"
                })
            except:
                pass

            return formatted.strip()

    except Exception as e:
        return f"Brave search failed: {str(e)}"

@researcher_agent.tool
async def browse_page(ctx: RunContext[None], url: str) -> str:
    """
    Fetch full content from a specific webpage using Playwright.
    Use sparingly - only when you need detailed info from a specific source.
    """
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, timeout=30000)

            # Extract text content
            text = await page.evaluate("document.body.innerText")
            await browser.close()

            # Limit to 4000 chars
            return f"Content from {url}:\n\n{text[:4000]}..."
    except Exception as e:
        return f"Failed to browse {url}: {str(e)}"

class Researcher:
    async def execute(self, payload: dict) -> AgentResponse:
        topic = payload.get("topic", payload.get("text", ""))

        # Check if user wants fresh/new information
        fresh_keywords = ['new', 'fresh', 'latest', 'updated', 'recent', 'current', 'now']
        wants_fresh = any(keyword in topic.lower() for keyword in fresh_keywords)

        # Check if we already have research on this topic (unless asking for fresh)
        if not wants_fresh:
            print(f"🔍 Checking for existing research on: {topic}")
            cached_research = db.search_knowledge(f"RESEARCH: {topic}", limit=3)

            if cached_research['documents'][0]:
                # Found previous research
                cached_result = cached_research['documents'][0][0]
                print(f"✅ Found cached research ({len(cached_result)} chars)")

                # Check if it's comprehensive enough (>500 chars)
                if len(cached_result) > 500:
                    return AgentResponse(
                        success=True,
                        output=f"{cached_result}\n\n💡 This is from previous research. Ask for 'latest' or 'fresh' info if you want updated results.",
                        next_agent=None,
                        data=None,
                        error=None
                    )

        print(f"🔬 Conducting {'fresh' if wants_fresh else 'new'} research on: {topic}")

        # Enhanced research prompt with multi-source strategy
        prompt = f"""Research this topic comprehensively: {topic}

RESEARCH STRATEGY:

1. If this is a complex topic, start with analyze_query() to break it down into sub-questions.

2. Search multiple sources for the best coverage:
   - search_brain() - Check existing knowledge
   - search_tavily() - AI-optimized research (HIGHLY RECOMMENDED - use this!)
   - search_web_ddg() - General web search
   - search_brave() - If available, provides additional coverage

3. For complex topics: Search each sub-question separately using tavily or ddg.

4. Optionally use browse_page() if you need detailed content from a specific source (1-2 pages max).

5. SYNTHESIZE everything into a comprehensive response that:
   - Combines insights from multiple sources
   - Presents information clearly and conversationally
   - Highlights the most important findings
   - Mentions key sources
   - Is well-organized and informative

Remember: USE THE TOOLS! Actually search and gather information. Don't just say you can help - DO the research!"""

        try:
            result = await researcher_agent.run(prompt)

            # Verify we got actual content
            output = result.output
            if len(output) < 150 or any(phrase in output.lower() for phrase in ["happy to", "i can help", "i'd be glad"]):
                return AgentResponse(
                    success=False,
                    output="",
                    error="Research agent failed to execute tools properly"
                )

            # Save successful research to knowledge base for future reuse
            try:
                from datetime import datetime
                from common.contracts import KnowledgeEntry

                # Extract key topics from the query for tags
                query_words = [word.strip('?.,!') for word in topic.lower().split() if len(word) > 3]
                tags = list(set(query_words[:5]))  # Top 5 unique keywords as tags
                tags.append("research")
                tags.append("auto-saved")

                # Create knowledge entry
                entry = KnowledgeEntry(
                    text=f"RESEARCH: {topic}\n\n{output}",
                    tags=tags,
                    source="researcher_agent",
                    metadata={
                        "query": topic,
                        "researched_at": datetime.now().isoformat(),
                        "output_length": len(output)
                    }
                )

                db.add_knowledge(entry)
                print(f"💾 Research saved to knowledge base: {len(output)} chars, tags: {tags[:3]}")

            except Exception as save_error:
                print(f"⚠️  Failed to save research (non-critical): {save_error}")
                # Don't fail the whole request if saving fails

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
