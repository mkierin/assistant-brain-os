from common.database import db
from common.contracts import AgentResponse, KnowledgeEntry
from common.config import DEEPSEEK_API_KEY, LLM_PROVIDER, OPENAI_API_KEY, MODEL_NAME
from common.knowledge_graph import knowledge_graph
from datetime import datetime
import httpx
import re
import json
import subprocess
import uuid
from typing import Optional, List
from urllib.parse import urlparse
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound


# ---------------------------------------------------------------------------
# Standalone extraction functions (no RunContext, directly callable)
# ---------------------------------------------------------------------------

async def _extract_webpage_content(url: str) -> str:
    """Extract content from a webpage URL. Returns extracted text or error string."""
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = await client.get(url, headers=headers)
            response.raise_for_status()

            html = response.text

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

            if not content:
                body_match = re.search(r'<body[^>]*>(.*?)</body>', cleaned, re.DOTALL | re.IGNORECASE)
                content = body_match.group(1) if body_match else cleaned

            content = re.sub(r'<[^>]+>', ' ', content)
            content = re.sub(r'\s+', ' ', content).strip()

            if len(content) > 3000:
                content = content[:3000] + "..."

            return f"Title: {title}\n\nContent:\n{content}\n\nSource: {url}"

    except Exception as e:
        return f"Error extracting webpage: {str(e)}"


async def _extract_tweet_content(url: str) -> str:
    """Extract tweet content. Tries FxTwitter → Nitter → Playwright."""
    try:
        tweet_match = re.search(r'(?:twitter\.com|x\.com)/([^/]+)/status/(\d+)', url)
        if not tweet_match:
            return "Invalid Twitter/X URL format"

        username = tweet_match.group(1)
        tweet_id = tweet_match.group(2)

        # Try FxTwitter API
        print("🚀 Trying FxTwitter API...")
        fxtwitter_data = await _extract_from_fxtwitter(username, tweet_id)
        if fxtwitter_data:
            return fxtwitter_data

        # Try Nitter
        print("🐦 FxTwitter failed, trying Nitter...")
        nitter_data = await _extract_from_nitter(username, tweet_id)
        if nitter_data:
            return nitter_data

        # Try Playwright
        print("🎭 Trying Playwright fallback...")
        playwright_data = await _extract_with_playwright(url)
        if playwright_data:
            return playwright_data

        return f"Tweet by @{username}\nTweet ID: {tweet_id}\nSource: {url}\n\nNote: Could not extract full content. The tweet may be private or deleted."

    except Exception as e:
        return f"Error extracting tweet: {str(e)}"


async def _extract_from_fxtwitter(username: str, tweet_id: str) -> Optional[str]:
    """Extract tweet using FxTwitter API"""
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
            text = tweet.get('text', '')
            author_name = author.get('name', username)
            author_handle = author.get('screen_name', username)
            created_at = tweet.get('created_at', 'Unknown date')

            likes = tweet.get('likes', 0)
            retweets = tweet.get('retweets', 0)
            replies = tweet.get('replies', 0)
            views = tweet.get('views', 0)

            result = f"Tweet by @{author_handle} ({author_name})\n\n"
            result += f"{text}\n\n"

            stats = []
            if views > 0:
                stats.append(f"{views:,} views")
            if likes > 0:
                stats.append(f"{likes:,} likes")
            if retweets > 0:
                stats.append(f"{retweets:,} retweets")
            if replies > 0:
                stats.append(f"{replies:,} replies")

            if stats:
                result += f"Stats: {' | '.join(stats)}\n"

            result += f"Posted: {created_at}\n"
            result += f"Source: https://twitter.com/{username}/status/{tweet_id}"

            print("✅ Successfully extracted from FxTwitter API")
            return result

    except Exception as e:
        print(f"⚠️ FxTwitter API failed: {e}")
        return None


async def _extract_from_nitter(username: str, tweet_id: str) -> Optional[str]:
    """Extract tweet from Nitter instance"""
    nitter_instances = ['nitter.net', 'nitter.poast.org', 'nitter.privacydev.net']

    for instance in nitter_instances:
        try:
            nitter_url = f"https://{instance}/{username}/status/{tweet_id}"
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                response = await client.get(nitter_url, headers=headers)
                if response.status_code != 200:
                    continue

                html = response.text
                tweet_content_match = re.search(r'<div class="tweet-content[^"]*"[^>]*>(.*?)</div>', html, re.DOTALL)
                if tweet_content_match:
                    tweet_text = tweet_content_match.group(1)
                    tweet_text = re.sub(r'<[^>]+>', ' ', tweet_text)
                    tweet_text = re.sub(r'\s+', ' ', tweet_text).strip()
                else:
                    continue

                author_match = re.search(r'<a class="fullname"[^>]*>(.*?)</a>', html)
                author = author_match.group(1) if author_match else username

                result = f"Tweet by @{username} ({author})\n\n{tweet_text}\n\nSource: https://twitter.com/{username}/status/{tweet_id}"
                print(f"✅ Successfully extracted from {instance}")
                return result

        except Exception as e:
            print(f"⚠️ {instance} failed: {e}")
            continue

    return None


async def _extract_with_playwright(url: str) -> Optional[str]:
    """Fallback: Extract tweet using Playwright"""
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            page = await context.new_page()
            await page.goto(url, wait_until='networkidle', timeout=30000)
            try:
                await page.wait_for_selector('article', timeout=10000)
            except:
                await browser.close()
                return None

            tweet_texts = await page.locator('[data-testid="tweetText"]').all_text_contents()
            tweet_text = '\n\n'.join(tweet_texts) if tweet_texts else ""
            try:
                author = await page.locator('[data-testid="User-Name"]').first.inner_text()
            except:
                author = "Unknown"
            await browser.close()

            if tweet_text:
                result = f"Tweet by {author}\n\n{tweet_text}\n\nSource: {url}"
                print("✅ Successfully extracted with Playwright")
                return result
    except Exception as e:
        print(f"⚠️ Playwright extraction failed: {e}")
    return None


async def _extract_youtube_content(url: str) -> str:
    """Extract transcript and metadata from a YouTube video."""
    try:
        video_id_match = re.search(r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)', url)
        if not video_id_match:
            return "Invalid YouTube URL format"

        video_id = video_id_match.group(1)
        print(f"🎥 Extracting YouTube video: {video_id}")

        # Get transcript
        try:
            api = YouTubeTranscriptApi()
            fetched = api.fetch(video_id, languages=['en'])
            transcript_text = " ".join([snippet.text for snippet in fetched.snippets])
            print(f"✅ Got transcript: {len(transcript_text)} characters")
        except (TranscriptsDisabled, NoTranscriptFound):
            return "That video doesn't have captions available, so I can't extract the transcript.\n\nWant to share the key points with me? I'll save those instead!"
        except Exception as e:
            error_msg = str(e).lower()
            if 'block' in error_msg or 'forbidden' in error_msg or '403' in error_msg:
                return "YouTube's blocking the transcript extraction right now (happens sometimes). Try again in a bit, or tell me the main points and I'll save those."
            return f"Couldn't get the transcript - {str(e)}"

        # Get video metadata via yt-dlp
        title = "YouTube Video"
        channel = "Unknown"
        duration = 0
        description = ""

        try:
            result = subprocess.run(
                ['yt-dlp', '--dump-json', '--no-download', f'https://youtube.com/watch?v={video_id}'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                metadata = json.loads(result.stdout)
                title = metadata.get('title', title)
                channel = metadata.get('uploader', metadata.get('channel', channel))
                duration = metadata.get('duration', 0)
                description = metadata.get('description', '')
        except Exception as e:
            print(f"⚠️ Metadata extraction failed: {e}")

        duration_str = f"{duration // 60}:{duration % 60:02d}" if duration else "Unknown"

        # Create summary using LLM (LLM used for formatting only — transcript was already extracted)
        summary = ""
        try:
            from openai import AsyncOpenAI
            if LLM_PROVIDER == "deepseek":
                llm_client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
                summary_model = "deepseek-chat"
            else:
                llm_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
                summary_model = MODEL_NAME

            summary_response = await llm_client.chat.completions.create(
                model=summary_model,
                messages=[{"role": "user", "content": f"Summarize this YouTube video transcript in 5-7 key points:\n\nTitle: {title}\nChannel: {channel}\n\nTranscript:\n{transcript_text[:3000]}"}],
                temperature=0.3,
                max_tokens=500
            )
            summary = summary_response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ Summary generation failed: {e}")
            summary = transcript_text[:500] + "..."

        # Build output
        output = f"{title}\nby {channel} | {duration_str}\n\n"
        output += f"{summary}\n\n"

        # Chapters from description
        if description:
            chapter_matches = re.findall(r'(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+?)(?:\n|$)', description)
            if chapter_matches:
                output += "Chapters:\n"
                for time, chapter_title in chapter_matches[:5]:
                    output += f"- {time} {chapter_title.strip()}\n"
                output += "\n"

        output += f"Full transcript saved ({len(transcript_text)} chars)."
        return output

    except Exception as e:
        return f"Error extracting YouTube video: {str(e)}"


# ---------------------------------------------------------------------------
# Direct save helper
# ---------------------------------------------------------------------------

def _auto_tags(content: str, url: str) -> List[str]:
    """Auto-generate tags from content and URL."""
    tags = []

    # URL-based tags
    if 'youtube.com' in url or 'youtu.be' in url:
        tags.append('youtube')
    elif 'twitter.com' in url or 'x.com' in url:
        tags.append('tweet')
    elif 'github.com' in url:
        tags.append('github')
    else:
        domain = urlparse(url).netloc.replace('www.', '')
        short = domain.split('.')[0]
        if short and len(short) > 1:
            tags.append(short)

    # Content-based: extract a few keyword-like words
    words = re.findall(r'[a-zA-Z]{4,}', content[:500].lower())
    stop = {"this", "that", "with", "from", "have", "been", "they", "their",
            "about", "which", "when", "will", "more", "also", "than", "into",
            "some", "them", "then", "could", "would", "there", "these", "your",
            "what", "each", "make", "like", "just", "over", "such", "take",
            "other", "very", "after", "most", "only", "come", "made", "find",
            "here", "thing", "many", "well", "content", "title", "source",
            "error", "none", "http", "https", "tweet"}
    for w in words:
        if w not in stop and w not in tags:
            tags.append(w)
        if len(tags) >= 5:
            break

    tags.append("saved-content")
    return tags


def _extract_title_from_content(extracted: str, url: str) -> str:
    """Extract a title from the extracted content string."""
    # Check for "Title: ..." pattern (from webpage extraction)
    title_match = re.match(r'^Title:\s*(.+?)(?:\n|$)', extracted)
    if title_match:
        return title_match.group(1).strip()[:120]

    # Check for first line as title (YouTube/tweet format)
    first_line = extracted.split('\n')[0].strip()
    if first_line and len(first_line) > 3:
        return first_line[:120]

    # Fallback to domain
    return urlparse(url).netloc


def _save_content_to_db(title: str, content: str, url: str, tags: List[str]) -> int:
    """Save extracted content directly to DB + knowledge graph. Returns related count."""
    metadata = {
        "saved_at": datetime.now().isoformat(),
        "content_type": _content_type(url),
        "url": url,
        "domain": urlparse(url).netloc,
        "title": title,
    }

    full_text = f"# {title}\n\n{content}"
    if url:
        full_text += f"\n\nSource: {url}"

    entry = KnowledgeEntry(
        text=full_text,
        tags=tags,
        source="content_saver",
        metadata=metadata,
        embedding_id=str(uuid.uuid4()),
    )
    db.add_knowledge(entry)

    # Knowledge graph
    try:
        node_id = knowledge_graph.add_note(
            title=title, content=content[:3000], tags=tags, url=url, metadata=metadata
        )
        related = knowledge_graph.get_related_notes(node_id, max_depth=1)
        return len(related)
    except Exception as e:
        print(f"⚠️ Knowledge graph error: {e}")
        return 0


def _content_type(url: str) -> str:
    if 'youtube.com' in url or 'youtu.be' in url:
        return "youtube"
    if 'twitter.com' in url or 'x.com' in url:
        return "tweet"
    return "webpage"


def _is_extraction_error(text: str) -> bool:
    """Check if extraction result is an error message."""
    error_starts = ("Error", "Invalid", "That video doesn't", "YouTube's blocking",
                    "Couldn't get", "Could not extract")
    return any(text.startswith(prefix) for prefix in error_starts)


# ---------------------------------------------------------------------------
# Main execute — direct extraction + direct save, no LLM tool-calling gamble
# ---------------------------------------------------------------------------

async def execute(payload) -> AgentResponse:
    """
    Content saving: extract content directly, save directly.
    LLM used ONLY for YouTube summary (and it's optional with fallback).
    """
    topic = payload.get("text", "") if isinstance(payload, dict) else payload
    print(f"💾 Content Saver activated for: {topic}")

    # Find URL in the message
    url_match = re.search(r'https?://[^\s]+', topic, re.IGNORECASE)

    if not url_match:
        # No URL — shouldn't normally reach here, but handle gracefully
        return AgentResponse(
            success=True,
            output="I didn't find a URL in your message. To save text notes, just tell me to 'save' or 'remember' something.",
            agent="content_saver"
        )

    url = url_match.group(0)

    try:
        # Step 1: Extract content directly (no LLM deciding which tool to call)
        if 'youtube.com' in url or 'youtu.be' in url:
            print(f"🎥 YouTube video detected")
            extracted = await _extract_youtube_content(url)
        elif 'twitter.com' in url or 'x.com' in url:
            print(f"🐦 Twitter/X URL detected")
            extracted = await _extract_tweet_content(url)
        else:
            print(f"🌐 Webpage detected")
            extracted = await _extract_webpage_content(url)

        # Step 2: Check for extraction errors
        if _is_extraction_error(extracted):
            return AgentResponse(success=True, output=extracted, agent="content_saver")

        # Step 3: Auto-generate title and tags
        title = _extract_title_from_content(extracted, url)
        tags = _auto_tags(extracted, url)

        # Step 4: Save directly to DB + knowledge graph
        related_count = _save_content_to_db(title, extracted, url, tags)

        # Step 5: Build response
        output = f"Saved! {title}\n"
        output += f"Tags: {', '.join(f'#{t}' for t in tags[:5])}\n"
        if related_count:
            output += f"Connected to {related_count} related notes\n"
        output += f"\n{extracted[:2000]}"

        print(f"✅ Content saved: {title}")
        return AgentResponse(success=True, output=output, agent="content_saver")

    except Exception as e:
        error_msg = f"Error in content saver: {str(e)}"
        print(f"❌ {error_msg}")
        return AgentResponse(success=False, output=error_msg, agent="content_saver")
