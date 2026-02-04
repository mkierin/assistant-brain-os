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
        assert is_casual_message("hey there") is True
        assert is_casual_message("Hi!") is True
        assert is_casual_message("HELLO") is True

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
        """Test that 'how are you' is detected as casual"""
        from main import is_casual_message

        assert is_casual_message("how are you") is True
        assert is_casual_message("how are you?") is True
        assert is_casual_message("how's it going") is True
        assert is_casual_message("hows it going") is True

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


class TestIntentRouting:
    """Test intent routing logic"""

    @pytest.mark.asyncio
    async def test_route_save_intent(self):
        """Test routing of save/archive intent"""
        from main import route_intent

        with patch('main.client.chat.completions.create') as mock_create:
            mock_create.return_value = Mock(
                choices=[Mock(message=Mock(content='{"agent": "archivist", "payload": {"text": "test"}}'))]
            )

            result = await route_intent("Save this: Test note")

            assert result['agent'] == 'archivist'
            assert 'payload' in result

    @pytest.mark.asyncio
    async def test_route_research_intent(self):
        """Test routing of research intent"""
        from main import route_intent

        with patch('main.client.chat.completions.create') as mock_create:
            mock_create.return_value = Mock(
                choices=[Mock(message=Mock(content='{"agent": "researcher", "payload": {"topic": "AI"}}'))]
            )

            result = await route_intent("Research artificial intelligence")

            assert result['agent'] == 'researcher'
            assert 'payload' in result

    @pytest.mark.asyncio
    async def test_route_write_intent(self):
        """Test routing of writing intent"""
        from main import route_intent

        with patch('main.client.chat.completions.create') as mock_create:
            mock_create.return_value = Mock(
                choices=[Mock(message=Mock(content='{"agent": "writer", "payload": {"text": "email"}}'))]
            )

            result = await route_intent("Write an email")

            assert result['agent'] == 'writer'
            assert 'payload' in result

    @pytest.mark.asyncio
    async def test_route_default_fallback(self):
        """Test default fallback to archivist"""
        from main import route_intent

        with patch('main.client.chat.completions.create') as mock_create:
            mock_create.return_value = Mock(
                choices=[Mock(message=Mock(content='{"agent": "unknown"}'))]
            )

            result = await route_intent("Unclear message")

            # Should have an agent (fallback to archivist if unknown)
            assert 'agent' in result


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
