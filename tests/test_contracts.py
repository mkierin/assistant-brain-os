"""
Unit tests for data contracts and models
"""
import pytest
from common.contracts import Job, JobStatus, KnowledgeEntry, AgentResponse
from pydantic import ValidationError


class TestJob:
    """Test Job model"""

    def test_job_creation_with_defaults(self):
        """Test creating a job with default values"""
        job = Job(
            current_agent="archivist",
            payload={"text": "test"}
        )

        assert job.status == JobStatus.PENDING
        assert job.retry_count == 0
        assert job.max_retries == 3
        assert len(job.history) == 0
        assert job.id is not None
        assert job.created_at is not None

    def test_job_creation_with_custom_values(self):
        """Test creating a job with custom values"""
        job = Job(
            current_agent="researcher",
            payload={"topic": "AI"},
            max_retries=5,
            retry_count=2
        )

        assert job.current_agent == "researcher"
        assert job.max_retries == 5
        assert job.retry_count == 2

    def test_job_status_enum(self):
        """Test job status enumeration"""
        job = Job(current_agent="archivist", payload={})

        job.status = JobStatus.IN_PROGRESS
        assert job.status == JobStatus.IN_PROGRESS

        job.status = JobStatus.COMPLETED
        assert job.status == JobStatus.COMPLETED

        job.status = JobStatus.FAILED
        assert job.status == JobStatus.FAILED

    def test_job_validation(self):
        """Test job validation"""
        # Missing required field should raise error
        with pytest.raises(ValidationError):
            Job(payload={"text": "test"})  # Missing current_agent

        with pytest.raises(ValidationError):
            Job(current_agent="archivist")  # Missing payload

    def test_job_history_append(self):
        """Test appending to job history"""
        job = Job(current_agent="archivist", payload={"text": "test"})

        job.history.append({"agent": "archivist", "output": "success"})
        assert len(job.history) == 1
        assert job.history[0]["agent"] == "archivist"

    def test_job_serialization(self):
        """Test job serialization to JSON"""
        job = Job(
            current_agent="archivist",
            payload={"text": "test"}
        )

        json_data = job.model_dump_json()
        assert isinstance(json_data, str)
        assert "archivist" in json_data


class TestKnowledgeEntry:
    """Test KnowledgeEntry model"""

    def test_knowledge_entry_creation(self):
        """Test creating a knowledge entry"""
        entry = KnowledgeEntry(
            text="Python is great",
            tags=["programming", "python"],
            source="test"
        )

        assert entry.text == "Python is great"
        assert len(entry.tags) == 2
        assert entry.source == "test"
        assert entry.created_at is not None

    def test_knowledge_entry_with_metadata(self):
        """Test knowledge entry with metadata"""
        entry = KnowledgeEntry(
            text="Test entry",
            tags=["test"],
            source="test",
            metadata={"importance": "high", "category": "work"}
        )

        assert entry.metadata["importance"] == "high"
        assert entry.metadata["category"] == "work"

    def test_knowledge_entry_validation(self):
        """Test knowledge entry validation"""
        # Missing required fields
        with pytest.raises(ValidationError):
            KnowledgeEntry(tags=["test"])  # Missing text and source

        with pytest.raises(ValidationError):
            KnowledgeEntry(text="test")  # Missing source

    def test_knowledge_entry_empty_tags(self):
        """Test knowledge entry with empty tags"""
        entry = KnowledgeEntry(
            text="Test",
            source="test"
        )

        assert entry.tags == []


class TestAgentResponse:
    """Test AgentResponse model"""

    def test_agent_response_success(self):
        """Test successful agent response"""
        response = AgentResponse(
            success=True,
            output="Task completed successfully"
        )

        assert response.success is True
        assert response.output == "Task completed successfully"
        assert response.error is None
        assert response.next_agent is None

    def test_agent_response_failure(self):
        """Test failed agent response"""
        response = AgentResponse(
            success=False,
            output="",
            error="API Error occurred"
        )

        assert response.success is False
        assert response.error == "API Error occurred"

    def test_agent_response_with_next_agent(self):
        """Test agent response with chaining"""
        response = AgentResponse(
            success=True,
            output="Research completed",
            next_agent="writer"
        )

        assert response.next_agent == "writer"

    def test_agent_response_with_data(self):
        """Test agent response with additional data"""
        response = AgentResponse(
            success=True,
            output="Result",
            data={"tokens": 100, "time": 5.2}
        )

        assert response.data["tokens"] == 100
        assert response.data["time"] == 5.2

    def test_agent_response_validation(self):
        """Test agent response validation"""
        # Missing required fields
        with pytest.raises(ValidationError):
            AgentResponse(output="test")  # Missing success

        with pytest.raises(ValidationError):
            AgentResponse(success=True)  # Missing output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
