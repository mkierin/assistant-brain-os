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

class FailureDetail(BaseModel):
    """Detailed information about a task failure"""
    timestamp: str
    attempt: int
    agent: str
    error_message: str
    stack_trace: Optional[str] = None
    input_payload: Dict[str, Any]

class RescueContext(BaseModel):
    """Complete context for rescue agent to diagnose and fix"""
    job_id: str
    workflow_goal: str
    failed_agent: str
    failure_count: int
    failure_history: List[FailureDetail]
    original_payload: Dict[str, Any]
    agent_code: Optional[str] = None
    worker_logs: Optional[str] = None

class RecoveryStrategy(str, Enum):
    RETRY_WITH_MODIFICATION = "retry_with_modification"
    ROUTE_TO_DIFFERENT_AGENT = "route_to_different_agent"
    APPLY_CODE_PATCH = "apply_code_patch"
    ESCALATE_TO_HUMAN = "escalate_to_human"
    SKIP_STEP = "skip_step"

class RescueDiagnosis(BaseModel):
    """AI diagnosis and recovery plan"""
    root_cause: str
    can_auto_fix: bool
    recovery_strategy: RecoveryStrategy
    actions: List[Dict[str, Any]]
    confidence: float  # 0.0 to 1.0
    explanation: str
    pr_summary: Optional[str] = None

class SkillMeta(BaseModel):
    """Metadata parsed from skill file YAML frontmatter"""
    name: str
    domain: str
    version: str = "1.0"
    description: str = ""
    tags: List[str] = []
    keywords: List[str] = []
    output_types: List[str] = []
    author: str = ""
    file_path: str = ""

class Skill(BaseModel):
    """Complete skill: metadata + body content"""
    meta: SkillMeta
    body: str

class ProjectManifest(BaseModel):
    """Manifest of all files generated for a coding project"""
    project_id: str
    task: str = ""
    files: List[Dict[str, Any]] = []
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None

class PRIssueSummary(BaseModel):
    """PR-ready issue report"""
    issue_id: str
    title: str
    summary: str
    root_cause: str
    reproduction_steps: List[str]
    error_logs: str
    suggested_fix: str
    impact: str
    related_files: List[str]
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
