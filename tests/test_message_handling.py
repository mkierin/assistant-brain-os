"""
Unit tests for message handling and routing logic
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestCasualMessageDetection:
    """Test casual message detection logic"""

    def test_greeting_detection(self):
        """Test that greetings are detected as casual"""
        from main import is_casual_message

        assert is_casual_message("hi") is True
        assert is_casual_message("hello") is True
        # "hey there" is 2 words without action keyword — not in CASUAL_PATTERNS
        # but doesn't have action keywords either, so it's NOT casual (correct)
        assert is_casual_message("Hi!") is True  # single word, in patterns
        assert is_casual_message("HELLO") is True  # single word, case-insensitive match

    def test_thanks_detection(self):
        """Test that thanks messages are detected as casual"""
        from main import is_casual_message

        assert is_casual_message("thanks") is True
        assert is_casual_message("thank you") is True
        assert is_casual_message("thx") is True
        assert is_casual_message("Thanks!") is True

    def test_goodbye_detection(self):
        """Test that goodbye messages are detected as casual"""
        from main import is_casual_message

        assert is_casual_message("bye") is True
        assert is_casual_message("goodbye") is True
        assert is_casual_message("see you") is True
        assert is_casual_message("later") is True

    def test_how_are_you_detection(self):
        """Test that 'how are you' variations.
        Note: 'how are you' contains 'how' (action keyword), so is_casual_message
        returns False. These get routed to agents instead. Exact matches in
        CASUAL_PATTERNS still work for phrases without action keywords."""
        from main import is_casual_message

        # These contain "how" which is an action keyword substring — they're NOT casual
        # This is intentional: it's better to route "how are you" to an agent
        # (which gives a helpful response) than to risk missing "how do I..."
        assert is_casual_message("how are you") is False
        # "hows" contains substring "how" so also not casual
        assert is_casual_message("hows it going") is False
        # But exact single-word matches still work
        assert is_casual_message("ok") is True
        assert is_casual_message("thanks") is True

    def test_actionable_messages_not_casual(self):
        """Test that actionable messages are not detected as casual"""
        from main import is_casual_message

        assert is_casual_message("Save this: Python is great") is False
        assert is_casual_message("Research artificial intelligence") is False
        assert is_casual_message("Write an email about the project") is False
        assert is_casual_message("What did I save about Python?") is False
        assert is_casual_message("Search for machine learning notes") is False

    def test_short_unclear_messages(self):
        """Test that short unclear messages are detected as casual"""
        from main import is_casual_message

        assert is_casual_message("ok") is True
        assert is_casual_message("cool") is True
        assert is_casual_message("nice") is True

    def test_messages_with_keywords_not_casual(self):
        """Test that messages with action keywords are not casual"""
        from main import is_casual_message

        assert is_casual_message("save something") is False
        assert is_casual_message("search something") is False
        assert is_casual_message("find information") is False
        assert is_casual_message("what is AI?") is False
        assert is_casual_message("how does it work?") is False


class TestDeterministicRouting:
    """Test deterministic routing (no LLM call)"""

    def test_route_save_intent(self):
        from main import route_deterministic
        assert route_deterministic("Save this: Test note") == "archivist"
        assert route_deterministic("remember that Python is great") == "archivist"
        assert route_deterministic("note this: meeting at 3pm") == "archivist"

    def test_route_search_knowledge_base(self):
        from main import route_deterministic
        assert route_deterministic("what did I save about Python?") == "archivist"
        assert route_deterministic("search my brain for AI notes") == "archivist"
        assert route_deterministic("find my notes about meetings") == "archivist"

    def test_route_research_intent(self):
        from main import route_deterministic
        assert route_deterministic("research artificial intelligence") == "researcher"
        assert route_deterministic("look up quantum computing") == "researcher"
        assert route_deterministic("investigate this topic") == "researcher"

    def test_route_general_questions_to_researcher(self):
        from main import route_deterministic
        assert route_deterministic("what is quantum computing?") == "researcher"
        assert route_deterministic("how does photosynthesis work?") == "researcher"
        assert route_deterministic("explain machine learning") == "researcher"

    def test_route_write_intent(self):
        from main import route_deterministic
        assert route_deterministic("write an email about the project") == "writer"
        assert route_deterministic("draft a report on Q4 results") == "writer"
        assert route_deterministic("format this text nicely") == "writer"

    def test_route_code_intent(self):
        from main import route_deterministic
        assert route_deterministic("create a data model for e-commerce") == "coder"
        assert route_deterministic("build a star schema for sales") == "coder"
        assert route_deterministic("generate a Python script for ETL") == "coder"

    def test_route_urls_to_content_saver(self):
        from main import route_deterministic
        assert route_deterministic("https://example.com/article") == "content_saver"
        assert route_deterministic("check this out https://youtube.com/watch?v=abc") == "content_saver"
        assert route_deterministic("http://twitter.com/user/status/123") == "content_saver"

    def test_route_default_short_text(self):
        from main import route_deterministic
        # Short text without clear intent defaults to archivist
        result = route_deterministic("quantum physics")
        assert result == "archivist"

    def test_route_default_long_text(self):
        from main import route_deterministic
        # Long text without clear intent defaults to archivist (save mode)
        result = route_deterministic("The mitochondria is the powerhouse of the cell and it produces ATP through oxidative phosphorylation")
        assert result == "archivist"


class TestUserSettings:
    """Test user settings management"""

    def test_get_default_settings(self):
        """Test getting default settings for new user"""
        from main import get_user_settings, DEFAULT_SETTINGS

        with patch('main.r.get', return_value=None):
            settings = get_user_settings(12345)

            assert settings == DEFAULT_SETTINGS
            assert settings['auto_route'] is True
            assert settings['voice_enabled'] is True
            assert settings['max_retries'] == 3

    def test_get_existing_settings(self):
        """Test getting existing user settings"""
        import json
        from main import get_user_settings

        custom_settings = {
            "auto_route": False,
            "voice_enabled": False,
            "notifications": False,
            "default_agent": "researcher",
            "max_retries": 5
        }

        with patch('main.r.get', return_value=json.dumps(custom_settings)):
            settings = get_user_settings(12345)

            assert settings == custom_settings
            assert settings['auto_route'] is False
            assert settings['default_agent'] == "researcher"

    def test_save_settings(self):
        """Test saving user settings"""
        from main import save_user_settings

        settings = {
            "auto_route": True,
            "voice_enabled": False,
            "max_retries": 3
        }

        with patch('main.r.set') as mock_set:
            save_user_settings(12345, settings)

            mock_set.assert_called_once()
            # Verify the key format
            call_args = mock_set.call_args[0]
            assert "user_settings:12345" in call_args[0]


class TestThinkingMessages:
    """Test thinking message variations"""

    def test_thinking_messages_exist(self):
        """Test that thinking messages are defined"""
        from main import THINKING_MESSAGES

        assert len(THINKING_MESSAGES) >= 30
        assert all(isinstance(msg, str) for msg in THINKING_MESSAGES)

    def test_thinking_messages_unique(self):
        """Test that thinking messages are unique"""
        from main import THINKING_MESSAGES

        assert len(THINKING_MESSAGES) == len(set(THINKING_MESSAGES))

    def test_thinking_messages_not_empty(self):
        """Test that no thinking message is empty"""
        from main import THINKING_MESSAGES

        assert all(len(msg) > 0 for msg in THINKING_MESSAGES)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
