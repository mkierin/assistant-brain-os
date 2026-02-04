"""
Unit tests for AI agents (Archivist, Researcher, Writer)
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from agents.archivist import Archivist
from agents.researcher import Researcher
from agents.writer import Writer
from common.contracts import AgentResponse


class TestArchivist:
    """Test the Archivist agent"""

    @pytest.mark.asyncio
    async def test_archivist_save_success(self):
        """Test saving knowledge successfully"""
        archivist = Archivist()
        payload = {
            "action": "save",
            "text": "Python is a programming language",
            "source": "test"
        }

        with patch('agents.archivist.archivist_agent.run') as mock_run:
            mock_run.return_value = AsyncMock(output="Knowledge saved successfully")

            result = await archivist.execute(payload)

            assert isinstance(result, AgentResponse)
            assert result.success is True
            assert "Knowledge saved" in result.output or result.output != ""
            assert result.error is None

    @pytest.mark.asyncio
    async def test_archivist_search_success(self):
        """Test searching knowledge successfully"""
        archivist = Archivist()
        payload = {
            "action": "search",
            "text": "Python programming",
            "source": "test"
        }

        with patch('agents.archivist.archivist_agent.run') as mock_run:
            mock_run.return_value = AsyncMock(output="Found 3 entries about Python")

            result = await archivist.execute(payload)

            assert isinstance(result, AgentResponse)
            assert result.success is True
            assert result.output != ""
            assert result.error is None

    @pytest.mark.asyncio
    async def test_archivist_error_handling(self):
        """Test archivist error handling"""
        archivist = Archivist()
        payload = {
            "action": "save",
            "text": "Test content",
            "source": "test"
        }

        with patch('agents.archivist.archivist_agent.run') as mock_run:
            mock_run.side_effect = Exception("API Error")

            result = await archivist.execute(payload)

            assert isinstance(result, AgentResponse)
            assert result.success is False
            assert result.error is not None
            assert "API Error" in result.error

    @pytest.mark.asyncio
    async def test_archivist_empty_text(self):
        """Test archivist with empty text"""
        archivist = Archivist()
        payload = {
            "action": "save",
            "text": "",
            "source": "test"
        }

        with patch('agents.archivist.archivist_agent.run') as mock_run:
            mock_run.return_value = AsyncMock(output="Cannot save empty text")

            result = await archivist.execute(payload)

            assert isinstance(result, AgentResponse)
            # Should handle empty text gracefully


class TestResearcher:
    """Test the Researcher agent"""

    @pytest.mark.asyncio
    async def test_researcher_success(self):
        """Test research request successfully"""
        researcher = Researcher()
        payload = {
            "text": "artificial intelligence",
            "source": "test"
        }

        with patch('agents.researcher.researcher_agent.run') as mock_run:
            mock_run.return_value = AsyncMock(
                output="AI is a branch of computer science..."
            )

            result = await researcher.execute(payload)

            assert isinstance(result, AgentResponse)
            assert result.success is True
            assert result.output != ""
            assert result.error is None

    @pytest.mark.asyncio
    async def test_researcher_with_topic(self):
        """Test researcher with topic in payload"""
        researcher = Researcher()
        payload = {
            "topic": "quantum computing",
            "source": "test"
        }

        with patch('agents.researcher.researcher_agent.run') as mock_run:
            mock_run.return_value = AsyncMock(
                output="Quantum computing research results..."
            )

            result = await researcher.execute(payload)

            assert isinstance(result, AgentResponse)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_researcher_error_handling(self):
        """Test researcher error handling"""
        researcher = Researcher()
        payload = {
            "text": "test topic",
            "source": "test"
        }

        with patch('agents.researcher.researcher_agent.run') as mock_run:
            mock_run.side_effect = Exception("Network error")

            result = await researcher.execute(payload)

            assert isinstance(result, AgentResponse)
            assert result.success is False
            assert result.error is not None


class TestWriter:
    """Test the Writer agent"""

    @pytest.mark.asyncio
    async def test_writer_success(self):
        """Test writing content successfully"""
        writer = Writer()
        payload = {
            "text": "Thank you for your help",
            "format": "email",
            "source": "test"
        }

        with patch('agents.writer.writer_agent.run') as mock_run:
            mock_run.return_value = AsyncMock(
                output="Dear colleague,\n\nThank you..."
            )

            result = await writer.execute(payload)

            assert isinstance(result, AgentResponse)
            assert result.success is True
            assert result.output != ""
            assert result.error is None

    @pytest.mark.asyncio
    async def test_writer_with_research_data(self):
        """Test writer with research data"""
        writer = Writer()
        payload = {
            "text": "Summarize this",
            "format": "report",
            "research_data": "AI research findings...",
            "source": "test"
        }

        with patch('agents.writer.writer_agent.run') as mock_run:
            mock_run.return_value = AsyncMock(output="Report summary...")

            result = await writer.execute(payload)

            assert isinstance(result, AgentResponse)
            assert result.success is True

    @pytest.mark.asyncio
    async def test_writer_error_handling(self):
        """Test writer error handling"""
        writer = Writer()
        payload = {
            "text": "test content",
            "source": "test"
        }

        with patch('agents.writer.writer_agent.run') as mock_run:
            mock_run.side_effect = Exception("Generation error")

            result = await writer.execute(payload)

            assert isinstance(result, AgentResponse)
            assert result.success is False
            assert result.error is not None

    @pytest.mark.asyncio
    async def test_writer_default_format(self):
        """Test writer with default format"""
        writer = Writer()
        payload = {
            "text": "Some content",
            "source": "test"
        }

        with patch('agents.writer.writer_agent.run') as mock_run:
            mock_run.return_value = AsyncMock(output="Formatted content...")

            result = await writer.execute(payload)

            assert isinstance(result, AgentResponse)
            assert result.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
