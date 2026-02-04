"""
Unit tests for worker job processing
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from common.contracts import Job, JobStatus, AgentResponse


class TestJobProcessing:
    """Test worker job processing logic"""

    @pytest.mark.asyncio
    async def test_successful_job_processing(self):
        """Test processing a job successfully"""
        from worker import process_job

        job_data = Job(
            current_agent="archivist",
            payload={"text": "test", "user_id": 12345}
        ).model_dump_json()

        mock_agent = Mock()
        mock_agent.execute = AsyncMock(return_value=AgentResponse(
            success=True,
            output="Job completed successfully"
        ))

        with patch('worker.importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.Archivist = Mock(return_value=mock_agent)
            mock_import.return_value = mock_module

            with patch('worker.bot.send_message', new_callable=AsyncMock) as mock_send:
                with patch('worker.r') as mock_redis:
                    await process_job(job_data)

                    # Should send success message to user
                    mock_send.assert_called_once()
                    call_args = mock_send.call_args
                    assert call_args[1]['chat_id'] == 12345
                    assert "✅ Task Completed!" in call_args[1]['text']

    @pytest.mark.asyncio
    async def test_failed_job_with_retry(self):
        """Test job failure triggers retry"""
        from worker import process_job

        job = Job(
            current_agent="archivist",
            payload={"text": "test", "user_id": 12345},
            max_retries=3,
            retry_count=0
        )

        mock_agent = Mock()
        mock_agent.execute = AsyncMock(side_effect=Exception("API Error"))

        with patch('worker.importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.Archivist = Mock(return_value=mock_agent)
            mock_import.return_value = mock_module

            with patch('worker.r') as mock_redis:
                await process_job(job.model_dump_json())

                # Should push back to queue for retry
                mock_redis.lpush.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test job fails after max retries"""
        from worker import process_job

        job = Job(
            current_agent="archivist",
            payload={"text": "test", "user_id": 12345},
            max_retries=3,
            retry_count=3  # Already at max
        )

        mock_agent = Mock()
        mock_agent.execute = AsyncMock(side_effect=Exception("API Error"))

        with patch('worker.importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.Archivist = Mock(return_value=mock_agent)
            mock_import.return_value = mock_module

            with patch('worker.bot.send_message', new_callable=AsyncMock) as mock_send:
                with patch('worker.r') as mock_redis:
                    await process_job(job.model_dump_json())

                    # Should send failure message
                    mock_send.assert_called_once()
                    call_args = mock_send.call_args
                    assert "⚠️ Task Failed after" in call_args[1]['text']

    @pytest.mark.asyncio
    async def test_agent_chaining(self):
        """Test agent chaining with next_agent"""
        from worker import process_job

        job = Job(
            current_agent="researcher",
            payload={"text": "test", "user_id": 12345}
        )

        mock_agent = Mock()
        mock_agent.execute = AsyncMock(return_value=AgentResponse(
            success=True,
            output="Research complete",
            next_agent="writer"
        ))

        with patch('worker.importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_module.Researcher = Mock(return_value=mock_agent)
            mock_import.return_value = mock_module

            with patch('worker.bot.send_message', new_callable=AsyncMock):
                with patch('worker.r') as mock_redis:
                    await process_job(job.model_dump_json())

                    # Should queue next agent
                    mock_redis.lpush.assert_called_once()
                    queued_job = json.loads(mock_redis.lpush.call_args[0][1])
                    assert queued_job['current_agent'] == 'writer'


class TestDynamicAgentLoading:
    """Test dynamic agent loading"""

    @pytest.mark.asyncio
    async def test_load_archivist(self):
        """Test loading archivist agent"""
        from worker import process_job

        job = Job(
            current_agent="archivist",
            payload={"text": "test", "user_id": 12345}
        )

        with patch('worker.importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_agent = Mock()
            mock_agent.execute = AsyncMock(return_value=AgentResponse(
                success=True, output="Success"
            ))
            mock_module.Archivist = Mock(return_value=mock_agent)
            mock_import.return_value = mock_module

            with patch('worker.bot.send_message', new_callable=AsyncMock):
                with patch('worker.r'):
                    await process_job(job.model_dump_json())

                    # Verify correct agent module was imported
                    mock_import.assert_called_with('agents.archivist')

    @pytest.mark.asyncio
    async def test_load_researcher(self):
        """Test loading researcher agent"""
        from worker import process_job

        job = Job(
            current_agent="researcher",
            payload={"text": "test", "user_id": 12345}
        )

        with patch('worker.importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_agent = Mock()
            mock_agent.execute = AsyncMock(return_value=AgentResponse(
                success=True, output="Success"
            ))
            mock_module.Researcher = Mock(return_value=mock_agent)
            mock_import.return_value = mock_module

            with patch('worker.bot.send_message', new_callable=AsyncMock):
                with patch('worker.r'):
                    await process_job(job.model_dump_json())

                    mock_import.assert_called_with('agents.researcher')

    @pytest.mark.asyncio
    async def test_load_writer(self):
        """Test loading writer agent"""
        from worker import process_job

        job = Job(
            current_agent="writer",
            payload={"text": "test", "user_id": 12345}
        )

        with patch('worker.importlib.import_module') as mock_import:
            mock_module = Mock()
            mock_agent = Mock()
            mock_agent.execute = AsyncMock(return_value=AgentResponse(
                success=True, output="Success"
            ))
            mock_module.Writer = Mock(return_value=mock_agent)
            mock_import.return_value = mock_module

            with patch('worker.bot.send_message', new_callable=AsyncMock):
                with patch('worker.r'):
                    await process_job(job.model_dump_json())

                    mock_import.assert_called_with('agents.writer')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
