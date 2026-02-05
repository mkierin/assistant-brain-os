from pydantic_ai import Agent, RunContext
from common.database import db
from common.contracts import AgentResponse, KnowledgeEntry
from common.config import DEEPSEEK_API_KEY, LLM_PROVIDER
from common.knowledge_graph import knowledge_graph
from pydantic_ai.models.openai import OpenAIModel
from datetime import datetime
import httpx
import re
from typing import Optional
from urllib.parse import urlparse

if LLM_PROVIDER == "deepseek":
    model = OpenAIModel('deepseek-chat', provider='deepseek')
else:
    model = 'openai:gpt-4o-mini'

# Content saver agent for links, tweets, and notes
content_saver_agent = Agent(
    model,
    output_type=str,
    system_prompt="""You are a Content Curator - an Obsidian-style knowledge manager.

Your role:
1. Extract and save content from URLs (articles, tweets, threads)
2. Generate meaningful tags and summaries
3. Identify relationships with existing knowledge
4. Help build a connected knowledge graph

When saving content:
- Extract the main content, title, and key information
- Generate 3-7 relevant tags
- Write a brief 1-2 sentence summary
- Note related topics that could link to other content

Always use your tools to save content properly. Be concise and organized."""
)

@content_saver_agent.tool
async def extract_webpage(ctx: RunContext[None], url: str) -> str:
    """
    Extract content from a webpage URL. Works for articles, blog posts, and general web pages.
    Returns the extracted title and content.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            html = response.text

            # Simple content extraction - look for title and main content
            title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            title = title_match.group(1) if title_match else urlparse(url).netloc

            # Remove scripts and styles
            cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
            cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL | re.IGNORECASE)

            # Extract text from common content containers
            content_patterns = [
                r'<article[^>]*>(.*?)</article>',
                r'<main[^>]*>(.*?)</main>',
                r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
                r'<div[^>]*class="[^"]*post[^"]*"[^>]*>(.*?)</div>',
            ]

            content = ""
            for pattern in content_patterns:
                match = re.search(pattern, cleaned, re.DOTALL | re.IGNORECASE)
                if match:
                    content = match.group(1)
                    break

            # Fallback: get body content
            if not content:
                body_match = re.search(r'<body[^>]*>(.*?)</body>', cleaned, re.DOTALL | re.IGNORECASE)
                content = body_match.group(1) if body_match else cleaned

            # Strip HTML tags
            content = re.sub(r'<[^>]+>', ' ', content)
            # Clean up whitespace
            content = re.sub(r'\s+', ' ', content).strip()

            # Limit content length
            if len(content) > 3000:
                content = content[:3000] + "..."

            return f"Title: {title}\n\nContent:\n{content}\n\nSource: {url}"

    except Exception as e:
        return f"Error extracting webpage: {str(e)}"

@content_saver_agent.tool
async def extract_tweet(ctx: RunContext[None], url: str) -> str:
    """
    Extract information from a Twitter/X URL.
    Note: This is a basic extraction. For full thread support, consider using Twitter API.
    """
    try:
        # Parse tweet ID from URL
        tweet_id_match = re.search(r'/status/(\d+)', url)
        if not tweet_id_match:
            return "Invalid Twitter URL format"

        tweet_id = tweet_id_match.group(1)

        # Basic extraction without API
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            html = response.text

            # Try to extract basic info from HTML
            # Note: Twitter's HTML is complex, this is a basic extraction
            title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
            title = title_match.group(1) if title_match else "Tweet"

            return f"Tweet: {title}\n\nTweet ID: {tweet_id}\nSource: {url}\n\nNote: For full content, consider adding Twitter API integration."

    except Exception as e:
        return f"Error extracting tweet: {str(e)}"

@content_saver_agent.tool
async def save_content(
    ctx: RunContext[None],
    title: str,
    content: str,
    url: Optional[str] = None,
    tags: Optional[str] = None,
    summary: Optional[str] = None
) -> str:
    """
    Save content to the knowledge base with metadata.

    Args:
        title: Title or headline of the content
        content: Main content text
        url: Source URL (if applicable)
        tags: Comma-separated tags (e.g., "ai,machine-learning,research")
        summary: Brief 1-2 sentence summary
    """
    try:
        # Parse tags
        tag_list = [t.strip().lower() for t in (tags or "").split(",") if t.strip()]
        if not tag_list:
            tag_list = ["saved-content"]

        # Build metadata
        metadata = {
            "saved_at": datetime.now().isoformat(),
            "content_type": "webpage" if url else "note"
        }

        if url:
            metadata["url"] = url
            metadata["domain"] = urlparse(url).netloc

        if summary:
            metadata["summary"] = summary

        # Combine into knowledge entry
        full_text = f"# {title}\n\n"
        if summary:
            full_text += f"**Summary:** {summary}\n\n"
        full_text += content
        if url:
            full_text += f"\n\n**Source:** {url}"

        # Save to database (vector store)
        entry = KnowledgeEntry(
            text=full_text,
            tags=tag_list,
            source="content_saver",
            metadata=metadata
        )

        db.add_knowledge(entry)

        # Save to knowledge graph
        node_id = knowledge_graph.add_note(
            title=title,
            content=content,
            tags=tag_list,
            url=url,
            metadata=metadata
        )

        # Get related notes from graph
        related = knowledge_graph.get_related_notes(node_id, max_depth=1)
        connections = f"\n\n🔗 **Auto-linked to {len(related)} related notes**" if related else ""

        return f"✅ Content saved to knowledge graph!\n\nTitle: {title}\nTags: {', '.join(tag_list)}\nSize: {len(content)} characters{connections}"

    except Exception as e:
        return f"Error saving content: {str(e)}"

@content_saver_agent.tool
async def search_related_content(ctx: RunContext[None], query: str, limit: int = 5) -> str:
    """
    Search for related content in the knowledge base.
    Use this to find connections between new content and existing knowledge.
    """
    try:
        results = db.search_knowledge(query, limit=limit)

        if not results['documents'][0]:
            return "No related content found."

        output = "Related content:\n\n"
        for i, doc in enumerate(results['documents'][0][:limit], 1):
            preview = doc[:200] + "..." if len(doc) > 200 else doc
            output += f"{i}. {preview}\n\n"

        return output

    except Exception as e:
        return f"Error searching: {str(e)}"

@content_saver_agent.tool
async def get_graph_stats(ctx: RunContext[None]) -> str:
    """
    Get statistics about the knowledge graph.
    Shows how many notes, connections, and popular tags.
    """
    try:
        stats = knowledge_graph.get_stats()

        output = f"""📊 **Knowledge Graph Stats**

**Nodes:** {stats['total_nodes']} notes
**Connections:** {stats['total_edges']} relationships
**Avg Connections:** {stats['avg_connections']} per note

**Top Tags:**
"""
        for tag, count in list(stats['tags'].items())[:10]:
            output += f"  • {tag}: {count}\n"

        return output

    except Exception as e:
        return f"Error getting stats: {str(e)}"

async def execute(topic: str) -> AgentResponse:
    """
    Main execution function for content saving.
    Handles URLs (web pages, tweets) and plain text notes.
    """
    print(f"💾 Content Saver activated for: {topic}")

    # Detect URL type
    url_match = re.search(r'https?://[^\s]+', topic, re.IGNORECASE)

    if url_match:
        url = url_match.group(0)

        # Determine URL type
        if 'twitter.com' in url or 'x.com' in url:
            print(f"🐦 Detected Twitter/X URL")
            context = f"Extract and save this tweet: {url}"
        else:
            print(f"🌐 Detected webpage URL")
            context = f"Extract and save this webpage: {url}"
    else:
        # Plain text note
        print(f"📝 Saving as plain note")
        context = f"Save this as a note with appropriate tags and summary: {topic}"

    try:
        # Run the agent
        result = await content_saver_agent.run(context)
        output = result.output

        return AgentResponse(
            success=True,
            output=output,
            agent="content_saver"
        )

    except Exception as e:
        error_msg = f"Error in content saver: {str(e)}"
        print(f"❌ {error_msg}")
        return AgentResponse(
            success=False,
            output=error_msg,
            agent="content_saver"
        )
