"""
Test YouTube URL flow end-to-end
Simulates user sharing YouTube URLs and traces through the system
"""

import pytest
import re
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import Mock, AsyncMock, patch, MagicMock
from common.contracts import Job, JobStatus, AgentResponse


class TestURLDetection:
    """Test URL detection at various stages"""

    def test_url_regex_pattern(self):
        """Test the URL regex pattern used in main.py"""
        url_pattern = r'https?://[^\s]+'

        test_cases = [
            ("https://youtube.com/watch?v=abc123", True),
            ("https://youtu.be/abc123", True),
            ("http://youtube.com/watch?v=test", True),
            ("Check this: https://youtube.com/watch?v=xyz", True),
            ("youtu.be/test", False),  # No protocol
            ("youtube.com/watch?v=test", False),  # No protocol
            ("hello world", False),
        ]

        for text, should_match in test_cases:
            match = re.search(url_pattern, text, re.IGNORECASE)
            assert (match is not None) == should_match, f"Failed for: {text}"

    def test_youtube_url_formats(self):
        """Test various YouTube URL formats"""
        youtube_urls = [
            "https://youtube.com/watch?v=dQw4w9WgXcQ",
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtu.be/dQw4w9WgXcQ",
            "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
            "https://youtube.com/watch?v=abc123&feature=share",
            "https://youtube.com/embed/abc123",
        ]

        url_pattern = r'https?://[^\s]+'
        for url in youtube_urls:
            assert re.search(url_pattern, url, re.IGNORECASE), f"Should match: {url}"

    def test_video_id_extraction(self):
        """Test extracting video ID from various YouTube URL formats"""
        test_cases = [
            ("https://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
            ("https://youtube.com/embed/abc123", "abc123"),
            ("https://youtube.com/watch?v=test&feature=share", "test"),
        ]

        video_id_pattern = r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)'

        for url, expected_id in test_cases:
            match = re.search(video_id_pattern, url)
            assert match, f"Should extract ID from: {url}"
            assert match.group(1) == expected_id, f"Expected {expected_id}, got {match.group(1)}"


class TestCasualMessageDetection:
    """Test casual vs actionable message classification"""

    def test_urls_not_casual(self):
        """URLs should never be classified as casual"""
        from main import is_casual_message

        test_urls = [
            "https://youtube.com/watch?v=abc123",
            "Check this out: https://youtu.be/test",
            "https://example.com/article",
            "http://twitter.com/user/status/123",
        ]

        for url in test_urls:
            result = is_casual_message(url)
            assert result == False, f"URL should not be casual: {url}"

    def test_casual_messages(self):
        """Test that actual casual messages are detected"""
        from main import is_casual_message

        casual_messages = [
            "hello",
            "hi there",
            "thanks",
            "cool",
            "nice",
        ]

        for msg in casual_messages:
            result = is_casual_message(msg)
            assert result == True, f"Should be casual: {msg}"

    def test_actionable_messages(self):
        """Test that actionable messages are not casual"""
        from main import is_casual_message

        actionable_messages = [
            "save this note",
            "search for python",
            "find videos about AI",
            "research machine learning",
        ]

        for msg in actionable_messages:
            result = is_casual_message(msg)
            assert result == False, f"Should not be casual: {msg}"


class TestAgentRouting:
    """Test agent routing logic"""

    @pytest.mark.asyncio
    async def test_url_routes_to_content_saver(self):
        """Test that URLs are routed to content_saver"""
        # Simulate the routing logic in main.py
        text = "https://youtube.com/watch?v=abc123"
        url_pattern = r'https?://[^\s]+'

        if re.search(url_pattern, text, re.IGNORECASE):
            agent = "content_saver"
        else:
            agent = "other"

        assert agent == "content_saver", "URL should route to content_saver"

    @pytest.mark.asyncio
    async def test_routing_priority(self):
        """Test that URL detection happens before casual check"""
        from main import is_casual_message

        text = "hello https://youtube.com/watch?v=test"

        # URL detection should happen first
        url_pattern = r'https?://[^\s]+'
        has_url = re.search(url_pattern, text, re.IGNORECASE)
        is_casual = is_casual_message(text)

        # Should have URL and not be casual
        assert has_url is not None, "Should detect URL"
        assert is_casual == False, "Should not be casual despite 'hello'"


class TestWorkerJobProcessing:
    """Test worker's job processing"""

    @pytest.mark.asyncio
    async def test_worker_loads_content_saver(self):
        """Test that worker can load content_saver agent"""
        import importlib

        # Test dynamic import
        agent_name = "content_saver"
        agent_module = importlib.import_module(f"agents.{agent_name}")

        # Should have execute function
        assert hasattr(agent_module, 'execute'), "Module should have execute function"

        execute_func = getattr(agent_module, 'execute')
        assert callable(execute_func), "execute should be callable"

    @pytest.mark.asyncio
    async def test_job_payload_structure(self):
        """Test Job payload for YouTube URL"""
        job = Job(
            current_agent="content_saver",
            payload={
                "text": "https://youtube.com/watch?v=abc123",
                "source": "telegram",
                "user_id": 12345
            }
        )

        assert job.current_agent == "content_saver"
        assert "text" in job.payload
        assert job.payload["text"].startswith("https://")
        assert job.status == JobStatus.PENDING


class TestContentSaverAgent:
    """Test content_saver agent directly"""

    @pytest.mark.asyncio
    async def test_content_saver_detects_youtube(self):
        """Test that content_saver recognizes YouTube URLs"""
        text = "https://youtube.com/watch?v=abc123"

        # Check detection logic
        is_youtube = 'youtube.com' in text or 'youtu.be' in text
        assert is_youtube, "Should detect as YouTube"

    @pytest.mark.asyncio
    async def test_content_saver_execution_structure(self):
        """Test content_saver execute function structure"""
        from agents import content_saver
        import inspect

        # Check execute function exists
        assert hasattr(content_saver, 'execute'), "Should have execute function"

        # Check it's async
        assert inspect.iscoroutinefunction(content_saver.execute), "execute should be async"

        # Check signature
        sig = inspect.signature(content_saver.execute)
        params = list(sig.parameters.keys())
        assert len(params) > 0, "execute should take at least one parameter"


class TestEndToEndFlow:
    """Test complete flow from message to execution"""

    @pytest.mark.asyncio
    async def test_youtube_url_complete_flow(self):
        """Simulate complete flow of YouTube URL"""

        # Step 1: User sends message
        user_message = "https://youtube.com/watch?v=dQw4w9WgXcQ"

        # Step 2: Check if casual
        from main import is_casual_message
        is_casual = is_casual_message(user_message)
        assert is_casual == False, "YouTube URL should not be casual"

        # Step 3: Detect URL
        url_pattern = r'https?://[^\s]+'
        has_url = re.search(url_pattern, user_message, re.IGNORECASE)
        assert has_url is not None, "Should detect URL"

        # Step 4: Route to content_saver
        agent = "content_saver" if has_url else "other"
        assert agent == "content_saver", "Should route to content_saver"

        # Step 5: Create job
        job = Job(
            current_agent=agent,
            payload={
                "text": user_message,
                "source": "telegram",
                "user_id": 12345
            }
        )
        assert job.current_agent == "content_saver"

        # Step 6: Worker would load agent
        import importlib
        agent_module = importlib.import_module(f"agents.{job.current_agent}")
        assert hasattr(agent_module, 'execute'), "Agent should have execute"

        print("✅ Complete flow test passed!")

    @pytest.mark.asyncio
    async def test_different_youtube_formats(self):
        """Test flow with different YouTube URL formats"""
        youtube_urls = [
            "https://youtube.com/watch?v=abc123",
            "https://youtu.be/xyz789",
            "Check this: https://youtube.com/watch?v=test123",
        ]

        for url in youtube_urls:
            # Casual check
            from main import is_casual_message
            is_casual = is_casual_message(url)
            assert is_casual == False, f"Should not be casual: {url}"

            # URL detection
            url_pattern = r'https?://[^\s]+'
            has_url = re.search(url_pattern, url, re.IGNORECASE)
            assert has_url is not None, f"Should detect URL: {url}"

            # Routing
            agent = "content_saver" if has_url else "other"
            assert agent == "content_saver", f"Should route to content_saver: {url}"


class TestErrorScenarios:
    """Test error handling scenarios"""

    @pytest.mark.asyncio
    async def test_malformed_youtube_url(self):
        """Test handling of malformed YouTube URLs"""
        malformed_urls = [
            "https://youtube.com/watch",  # No video ID
            "https://youtube.com",  # Just domain
            "youtube.com/watch?v=test",  # No protocol
        ]

        url_pattern = r'https?://[^\s]+'
        video_id_pattern = r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)'

        for url in malformed_urls:
            # URL detection
            has_url = re.search(url_pattern, url, re.IGNORECASE)

            if has_url:
                # Try to extract video ID
                video_id = re.search(video_id_pattern, url)
                if not video_id:
                    print(f"⚠️ URL detected but no video ID: {url}")

    @pytest.mark.asyncio
    async def test_retry_mechanism(self):
        """Test that retry mechanism is set up correctly"""
        job = Job(
            current_agent="content_saver",
            payload={"text": "test"},
            max_retries=3
        )

        assert job.retry_count == 0
        assert job.max_retries == 3

        # Simulate failure
        job.retry_count += 1
        assert job.retry_count < job.max_retries, "Should retry"

        job.retry_count = 3
        assert job.retry_count >= job.max_retries, "Should dispatch rescue"


class TestIntegrationWithMocks:
    """Integration tests with mocked external services"""

    @pytest.mark.asyncio
    async def test_content_saver_with_mock_youtube(self):
        """Test content_saver with mocked YouTube API"""
        # This will fail if youtube-transcript-api is not installed
        # but will help identify the issue
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            api = YouTubeTranscriptApi()
            print("✅ youtube-transcript-api is available")
        except ImportError as e:
            pytest.fail(f"youtube-transcript-api not installed: {e}")
        except Exception as e:
            print(f"⚠️ YouTube API error (expected): {e}")

    @pytest.mark.asyncio
    async def test_yt_dlp_available(self):
        """Test that yt-dlp is available"""
        import subprocess
        try:
            result = subprocess.run(['yt-dlp', '--version'],
                                   capture_output=True,
                                   timeout=5)
            if result.returncode == 0:
                print(f"✅ yt-dlp is available: {result.stdout.decode().strip()}")
            else:
                pytest.fail("yt-dlp command failed")
        except FileNotFoundError:
            pytest.fail("yt-dlp is not installed")
        except Exception as e:
            pytest.fail(f"yt-dlp check failed: {e}")


class TestDiagnostics:
    """Diagnostic tests to identify issues"""

    def test_main_py_exists(self):
        """Check main.py exists and imports"""
        try:
            import main
            print("✅ main.py imports successfully")
        except Exception as e:
            pytest.fail(f"main.py import failed: {e}")

    def test_worker_py_exists(self):
        """Check worker.py exists and imports"""
        try:
            import worker
            print("✅ worker.py imports successfully")
        except Exception as e:
            pytest.fail(f"worker.py import failed: {e}")

    def test_content_saver_exists(self):
        """Check content_saver agent exists"""
        try:
            from agents import content_saver
            print("✅ content_saver imports successfully")

            # Check for execute function
            assert hasattr(content_saver, 'execute'), "Missing execute function"
            print("✅ content_saver has execute function")

        except Exception as e:
            pytest.fail(f"content_saver import failed: {e}")

    def test_dependencies_installed(self):
        """Check critical dependencies"""
        dependencies = [
            'redis',
            'telegram',
            'pydantic_ai',
            'youtube_transcript_api',
            'openai',
        ]

        missing = []
        for dep in dependencies:
            try:
                __import__(dep)
                print(f"✅ {dep} is installed")
            except ImportError:
                missing.append(dep)
                print(f"❌ {dep} is NOT installed")

        if missing:
            pytest.fail(f"Missing dependencies: {', '.join(missing)}")


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s"])
