"""
Integration tests for end-to-end workflows
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from common.contracts import Job, AgentResponse


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows"""

    @pytest.mark.asyncio
    async def test_save_and_search_workflow(self):
        """Test saving knowledge and then searching for it"""
        from agents.archivist import Archivist

        archivist = Archivist()

        # Step 1: Save knowledge
        with patch('agents.archivist.archivist_agent.run') as mock_run:
            mock_run.return_value = AsyncMock(output="Knowledge saved with tags: python, programming")

            save_result = await archivist.execute({
                "action": "save",
                "text": "Python is a programming language",
                "source": "test"
            })

            assert save_result.success is True

        # Step 2: Search for saved knowledge
        with patch('agents.archivist.archivist_agent.run') as mock_run:
            mock_run.return_value = AsyncMock(
                output="Found: Python is a programming language"
            )

            search_result = await archivist.execute({
                "action": "search",
                "text": "Python",
                "source": "test"
            })

            assert search_result.success is True

    @pytest.mark.asyncio
    async def test_research_and_write_workflow(self):
        """Test researching a topic and then writing about it"""
        from agents.researcher import Researcher
        from agents.writer import Writer

        researcher = Researcher()
        writer = Writer()

        # Step 1: Research
        with patch('agents.researcher.researcher_agent.run') as mock_run:
            mock_run.return_value = AsyncMock(
                output="AI is a branch of computer science..."
            )

            research_result = await researcher.execute({
                "text": "artificial intelligence",
                "source": "test"
            })

            assert research_result.success is True
            research_data = research_result.output

        # Step 2: Write based on research
        with patch('agents.writer.writer_agent.run') as mock_run:
            mock_run.return_value = AsyncMock(
                output="Comprehensive article about AI..."
            )

            write_result = await writer.execute({
                "text": "Write an article",
                "research_data": research_data,
                "source": "test"
            })

            assert write_result.success is True


class TestErrorRecovery:
    """Test error recovery and resilience"""

    @pytest.mark.asyncio
    async def test_agent_failure_recovery(self):
        """Test that failed agents return proper error response"""
        from agents.archivist import Archivist

        archivist = Archivist()

        with patch('agents.archivist.archivist_agent.run') as mock_run:
            mock_run.side_effect = Exception("Network timeout")

            result = await archivist.execute({
                "action": "save",
                "text": "test",
                "source": "test"
            })

            # Should not crash, should return error response
            assert isinstance(result, AgentResponse)
            assert result.success is False
            assert "Network timeout" in result.error

    @pytest.mark.asyncio
    async def test_malformed_payload_handling(self):
        """Test handling of malformed payloads"""
        from agents.archivist import Archivist

        archivist = Archivist()

        # Missing expected fields
        with patch('agents.archivist.archivist_agent.run') as mock_run:
            mock_run.return_value = AsyncMock(output="Handled missing fields")

            result = await archivist.execute({})

            # Should handle gracefully
            assert isinstance(result, AgentResponse)


class TestConcurrency:
    """Test concurrent operations"""

    @pytest.mark.asyncio
    async def test_multiple_agents_parallel(self):
        """Test running multiple agents in parallel"""
        from agents.archivist import Archivist
        from agents.researcher import Researcher

        archivist = Archivist()
        researcher = Researcher()

        with patch('agents.archivist.archivist_agent.run') as mock_arch_run, \
             patch('agents.researcher.researcher_agent.run') as mock_res_run:

            mock_arch_run.return_value = AsyncMock(output="Saved")
            mock_res_run.return_value = AsyncMock(output="Research results")

            # Run both in parallel
            import asyncio
            results = await asyncio.gather(
                archivist.execute({"action": "save", "text": "test", "source": "test"}),
                researcher.execute({"text": "test topic", "source": "test"})
            )

            assert len(results) == 2
            assert all(r.success for r in results)


class TestDataPersistence:
    """Test data persistence and consistency"""

    def test_job_serialization_deserialization(self):
        """Test job can be serialized and deserialized"""
        from common.contracts import Job
        import json

        original_job = Job(
            current_agent="archivist",
            payload={"text": "test", "user_id": 12345}
        )

        # Serialize
        json_str = original_job.model_dump_json()

        # Deserialize
        job_dict = json.loads(json_str)
        restored_job = Job(**job_dict)

        assert restored_job.current_agent == original_job.current_agent
        assert restored_job.payload == original_job.payload
        assert restored_job.id == original_job.id

    def test_agent_response_serialization(self):
        """Test agent response serialization"""
        from common.contracts import AgentResponse
        import json

        response = AgentResponse(
            success=True,
            output="Test output",
            data={"key": "value"}
        )

        # Should be serializable
        json_str = response.model_dump_json()
        restored = AgentResponse(**json.loads(json_str))

        assert restored.success == response.success
        assert restored.output == response.output
        assert restored.data == response.data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
