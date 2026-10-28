import enum
from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field

class PipelineStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    BUILDING = "BUILDING"
    TESTING = "TESTING"
    FAILED = "FAILED"
    ANALYZING = "ANALYZING"
    PATCHING = "PATCHING"
    RECOVERED_AUTOMATICALLY = "RECOVERED_AUTOMATICALLY"
    REQUIRES_HUMAN_APPROVAL = "REQUIRES_HUMAN_APPROVAL"
    RECOVERY_FAILED_ROLLED_BACK = "RECOVERY_FAILED_ROLLED_BACK"
    SUCCESS = "SUCCESS"

class FailureType(str, enum.Enum):
    SYNTAX_ERROR = "SYNTAX_ERROR"
    IMPORT_DEPENDENCY_ERROR = "IMPORT_DEPENDENCY_ERROR"
    LOGIC_ASSERTION_FAILURE = "LOGIC_ASSERTION_FAILURE"
    CONFIG_WORKFLOW_TYPO = "CONFIG_WORKFLOW_TYPO"
    ENVIRONMENT_MISMATCH = "ENVIRONMENT_MISMATCH"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"

class RiskTier(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class FailureClassification(BaseModel):
    failure_type: FailureType
    failing_file: Optional[str] = None
    failing_line: Optional[int] = None
    failing_symbol: Optional[str] = None
    failing_test_name: Optional[str] = None
    error_message: str
    stack_trace: str = ""

class RiskPrediction(BaseModel):
    risk_score: float  # 0.0 - 1.0 (or percentage 0 - 100)
    risk_tier: RiskTier
    top_risk_factors: list[str] = Field(default_factory=list)
    raw_features: dict[str, Any] = Field(default_factory=dict)
    model_version: str = "rf-commit-v1"

class EvidenceCitation(BaseModel):
    file_path: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    snippet: str
    similarity_score: Optional[float] = None

class RCAAnalysis(BaseModel):
    root_cause_summary: str
    confidence_score: float  # 0.0 - 1.0
    fix_strategy: str
    offending_code: Optional[str] = None
    evidence_citations: list[EvidenceCitation] = Field(default_factory=list)

class FixProposal(BaseModel):
    target_file: str
    original_snippet: str
    replacement_snippet: str
    unified_diff: str
    lines_changed: int
    is_safe: bool = False
    safety_violations: list[str] = Field(default_factory=list)

class HealingAttempt(BaseModel):
    attempt_id: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    rca: Optional[RCAAnalysis] = None
    fix_proposal: Optional[FixProposal] = None
    post_repair_test_passed: bool = False
    action_taken: str = ""
    logs: list[str] = Field(default_factory=list)

class PipelineRun(BaseModel):
    run_id: str
    commit_sha: str
    branch: str = "main"
    author: str = "developer"
    status: PipelineStatus = PipelineStatus.QUEUED
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    risk_prediction: Optional[RiskPrediction] = None
    failure_classification: Optional[FailureClassification] = None
    healing_attempts: list[HealingAttempt] = Field(default_factory=list)
    raw_build_logs: str = ""
    trigger_source: str = "WEB_DASHBOARD"
    commit_message: Optional[str] = None
    run_url: Optional[str] = None
    repository: Optional[str] = None

class AuditRecord(BaseModel):
    event_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    event_type: str
    run_id: Optional[str] = None
    actor: str = "SYSTEM"
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    previous_event_hash: str = "GENESIS"
    event_hash: str = ""
