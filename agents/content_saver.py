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
    Extract tweet content without Twitter API.
    Uses FxTwitter API (best), Nitter (backup), and Playwright (fallback).
    Handles single tweets and threads.
    """
    try:
        # Parse username and tweet ID
        tweet_match = re.search(r'(?:twitter\.com|x\.com)/([^/]+)/status/(\d+)', url)
        if not tweet_match:
            return "Invalid Twitter/X URL format"

        username = tweet_match.group(1)
        tweet_id = tweet_match.group(2)

        # Try Method 1: FxTwitter API (best - clean JSON, free)
        print("🚀 Trying FxTwitter API...")
        fxtwitter_data = await _extract_from_fxtwitter(username, tweet_id)
        if fxtwitter_data:
            return fxtwitter_data

        # Try Method 2: Nitter (backup)
        print("🐦 FxTwitter failed, trying Nitter...")
        nitter_data = await _extract_from_nitter(username, tweet_id)
        if nitter_data:
            return nitter_data

        # Try Method 3: Playwright (last resort)
        print("🎭 Trying Playwright fallback...")
        playwright_data = await _extract_with_playwright(url)
        if playwright_data:
            return playwright_data

        # Fallback: Basic info
        return f"Tweet by @{username}\nTweet ID: {tweet_id}\nSource: {url}\n\nNote: Could not extract full content. The tweet may be private or deleted."

    except Exception as e:
        return f"Error extracting tweet: {str(e)}"

async def _extract_from_fxtwitter(username: str, tweet_id: str) -> Optional[str]:
    """Extract tweet using FxTwitter API - free, clean JSON"""
    try:
        api_url = f"https://api.fxtwitter.com/{username}/status/{tweet_id}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = await client.get(api_url, headers=headers)

            if response.status_code != 200:
                return None

            data = response.json()

            if data.get('code') != 200:
                return None

            tweet = data.get('tweet', {})
            author = tweet.get('author', {})

            # Extract data
            text = tweet.get('text', '')
            author_name = author.get('name', username)
            author_handle = author.get('screen_name', username)
            created_at = tweet.get('created_at', 'Unknown date')

            # Stats
            likes = tweet.get('likes', 0)
            retweets = tweet.get('retweets', 0)
            replies = tweet.get('replies', 0)
            views = tweet.get('views', 0)

            # Format result
            result = f"**Tweet by @{author_handle}** ({author_name})\n\n"
            result += f"{text}\n\n"

            # Add stats
            stats = []
            if views > 0:
                stats.append(f"👁️ {views:,} views")
            if likes > 0:
                stats.append(f"❤️ {likes:,} likes")
            if retweets > 0:
                stats.append(f"🔁 {retweets:,} retweets")
            if replies > 0:
                stats.append(f"💬 {replies:,} replies")

            if stats:
                result += f"**Stats:** {' · '.join(stats)}\n"

            result += f"**Posted:** {created_at}\n"
            result += f"**Source:** https://twitter.com/{username}/status/{tweet_id}"

            print("✅ Successfully extracted from FxTwitter API")
            return result

    except Exception as e:
        print(f"⚠️  FxTwitter API failed: {e}")
        return None

async def _extract_from_nitter(username: str, tweet_id: str) -> Optional[str]:
    """Extract tweet from Nitter instance"""
    # Try multiple Nitter instances (in case one is down)
    nitter_instances = [
        'nitter.net',
        'nitter.poast.org',
        'nitter.privacydev.net'
    ]

    for instance in nitter_instances:
        try:
            nitter_url = f"https://{instance}/{username}/status/{tweet_id}"

            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = await client.get(nitter_url, headers=headers)

                if response.status_code != 200:
                    continue

                html = response.text

                # Extract tweet content
                # Nitter has clean HTML structure
                tweet_text = ""

                # Extract main tweet text
                tweet_content_match = re.search(r'<div class="tweet-content[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
                if tweet_content_match:
                    tweet_text = tweet_content_match.group(1)
                    # Clean HTML tags
                    tweet_text = re.sub(r'<[^>]+>', ' ', tweet_text)
                    tweet_text = re.sub(r'\s+', ' ', tweet_text).strip()

                # Extract author name
                author_match = re.search(r'<a class="fullname"[^>]*>(.*?)</a>', html)
                author = author_match.group(1) if author_match else username

                # Extract timestamp
                time_match = re.search(r'<span class="tweet-date"[^>]*><a[^>]*title="([^"]*)"', html)
                timestamp = time_match.group(1) if time_match else "Unknown date"

                # Extract stats (retweets, likes)
                stats = []
                retweets_match = re.search(r'<span class="icon-retweet"></span>\s*(\d+)', html)
                if retweets_match:
                    stats.append(f"🔁 {retweets_match.group(1)} retweets")

                likes_match = re.search(r'<span class="icon-heart"></span>\s*(\d+)', html)
                if likes_match:
                    stats.append(f"❤️ {likes_match.group(1)} likes")

                # Check for thread (multiple tweets)
                thread_tweets = re.findall(r'<div class="timeline-item[^"]*".*?<div class="tweet-content[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)

                result = f"**Tweet by @{username}** ({author})\n\n"

                if len(thread_tweets) > 1:
                    result += f"📜 **Thread ({len(thread_tweets)} tweets):**\n\n"
                    for i, thread_tweet in enumerate(thread_tweets[:10], 1):  # Limit to 10 tweets
                        clean_tweet = re.sub(r'<[^>]+>', ' ', thread_tweet)
                        clean_tweet = re.sub(r'\s+', ' ', clean_tweet).strip()
                        result += f"{i}. {clean_tweet}\n\n"
                else:
                    result += f"{tweet_text}\n\n"

                if stats:
                    result += f"**Stats:** {' · '.join(stats)}\n"

                result += f"**Posted:** {timestamp}\n"
                result += f"**Source:** https://twitter.com/{username}/status/{tweet_id}"

                print(f"✅ Successfully extracted from {instance}")
                return result

        except Exception as e:
            print(f"⚠️  {instance} failed: {e}")
            continue

    return None

async def _extract_with_playwright(url: str) -> Optional[str]:
    """Fallback: Extract tweet using Playwright browser automation"""
    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            page = await context.new_page()

            await page.goto(url, wait_until='networkidle', timeout=30000)

            # Wait for tweet to load
            try:
                await page.wait_for_selector('article', timeout=10000)
            except:
                await browser.close()
                return None

            # Extract tweet text
            tweet_texts = await page.locator('[data-testid="tweetText"]').all_text_contents()
            tweet_text = '\n\n'.join(tweet_texts) if tweet_texts else ""

            # Extract author
            try:
                author = await page.locator('[data-testid="User-Name"]').first.inner_text()
            except:
                author = "Unknown"

            await browser.close()

            if tweet_text:
                result = f"**Tweet by {author}**\n\n{tweet_text}\n\n**Source:** {url}"
                print("✅ Successfully extracted with Playwright")
                return result

    except Exception as e:
        print(f"⚠️  Playwright extraction failed: {e}")

    return None

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
