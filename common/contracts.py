from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid
from datetime import datetime

class JobStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    WAITING_HUMAN = "waiting_human"

class Job(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: JobStatus = JobStatus.PENDING
    current_agent: str
    payload: Dict[str, Any]
    history: List[Dict[str, Any]] = []
    retry_count: int = 0
    max_retries: int = 3
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class KnowledgeEntry(BaseModel):
    text: str
    embedding_id: Optional[str] = None
    tags: List[str] = []
    source: str
    metadata: Dict[str, Any] = {}
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

class AgentResponse(BaseModel):
    success: bool
    output: str
    next_agent: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
