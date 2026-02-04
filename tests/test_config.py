"""
Unit tests for configuration and environment
"""
import pytest
import os
from unittest.mock import patch


class TestConfiguration:
    """Test configuration loading"""

    def test_config_loads_required_vars(self):
        """Test that required config vars are loaded"""
        # Mock environment variables
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'test-key-1',
            'DEEPSEEK_API_KEY': 'test-key-2',
            'TELEGRAM_TOKEN': 'test-token',
            'LLM_PROVIDER': 'deepseek',
            'REDIS_URL': 'redis://localhost:6379'
        }):
            # Reimport to get new env vars
            import importlib
            import common.config as config
            importlib.reload(config)

            assert config.OPENAI_API_KEY == 'test-key-1'
            assert config.DEEPSEEK_API_KEY == 'test-key-2'
            assert config.TELEGRAM_TOKEN == 'test-token'
            assert config.LLM_PROVIDER == 'deepseek'
            assert config.REDIS_URL == 'redis://localhost:6379'

    def test_config_defaults(self):
        """Test configuration defaults"""
        from common.config import TASK_QUEUE, MAX_RETRIES

        assert TASK_QUEUE == "task_queue"
        assert MAX_RETRIES == 3

    def test_database_paths(self):
        """Test database path configuration"""
        with patch.dict(os.environ, {
            'DATABASE_PATH': 'test_data/brain.db',
            'CHROMA_PATH': 'test_data/chroma'
        }):
            import importlib
            import common.config as config
            importlib.reload(config)

            assert 'test_data' in config.DATABASE_PATH
            assert 'test_data' in config.CHROMA_PATH


class TestEnvironmentValidation:
    """Test environment validation"""

    def test_missing_required_vars(self):
        """Test handling of missing required environment variables"""
        # This should be handled gracefully by config
        # or raise appropriate errors
        pass  # Implementation depends on error handling strategy

    def test_invalid_llm_provider(self):
        """Test handling of invalid LLM provider"""
        # Validate that only 'openai' or 'deepseek' are accepted
        pass  # Implementation depends on validation strategy


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
