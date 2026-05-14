"""
PT Media Observatory - Pydantic Schemas

These schemas define the request/response models for the FastAPI application.
They provide validation, serialization, and OpenAPI documentation generation.
"""

from datetime import datetime, date
from typing import Optional, List, Any, Dict
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator


# ============================================================
# Enums (matching SQLAlchemy models)
# ============================================================

class UserRole(str, Enum):
    editor = "editor"
    admin = "admin"


class EventStatus(str, Enum):
    intake = "intake"
    curation_pending = "curation_pending"
    curation_complete = "curation_complete"
    research_pending = "research_pending"
    research_complete = "research_complete"
    coverage_pending = "coverage_pending"
    coverage_complete = "coverage_complete"
    risk_pending = "risk_pending"
    risk_complete = "risk_complete"
    needs_editor_decision = "needs_editor_decision"
    writer_pending = "writer_pending"
    writer_complete = "writer_complete"
    ready_for_review = "ready_for_review"
    approved = "approved"
    rejected = "rejected"
    archived = "archived"
    published = "published"


class StageName(str, Enum):
    curation = "curation"
    research = "research"
    coverage = "coverage"
    risk = "risk"
    writer = "writer"
    red_team = "red_team"
    safety = "safety"


class StageStatus(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class ReviewActionType(str, Enum):
    approve = "approve"
    reject = "reject"
    request_revision = "request_revision"
    force_approve = "force_approve"


class DraftFormat(str, Enum):
    x_thread = "x_thread"
    site_card = "site_card"
    newsletter_snippet = "newsletter_snippet"


# ============================================================
# Common Response Fields
# ============================================================

class BaseResponse(BaseModel):
    """Base response with common fields."""
    class Config:
        from_attributes = True


# ============================================================
# User Schemas
# ============================================================

class UserCreate(BaseModel):
    """Request to create a new user."""
    email: str = Field(..., min_length=1, max_length=255, description="User email address")
    name: str = Field(..., min_length=1, max_length=255, description="User full name")
    password: str = Field(..., min_length=12, description="Password (min 12 chars)")
    role: UserRole = Field(default=UserRole.editor, description="User role")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        if '@' not in v:
            raise ValueError('Email must contain @')
        return v


class UserResponse(BaseModel):
    """User data response."""
    id: UUID
    email: str
    name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Authentication Schemas
# ============================================================

class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded JWT token data."""
    user_id: Optional[str] = None
    exp: Optional[int] = None


class LoginRequest(BaseModel):
    """Login request with credentials."""
    username: str = Field(..., description="Email or username")
    password: str


# ============================================================
# Submission Schemas
# ============================================================

class SubmittedItemCreate(BaseModel):
    """Request to submit a new item for investigation."""
    source_url: Optional[HttpUrl] = Field(None, description="URL of the source")
    text_content: Optional[str] = Field(None, description="Pasted text content")
    topic_hint: Optional[str] = Field(None, description="Optional topic hint")
    notes: Optional[str] = Field(None, description="Additional notes from submitter")

    @model_validator(mode='after')
    def check_either_url_or_text(self) -> 'SubmittedItemCreate':
        if not self.source_url and not self.text_content:
            raise ValueError("Either source_url or text_content must be provided")
        return self


class SubmittedItemResponse(BaseModel):
    """Submitted item response with linked event."""
    id: UUID
    user_id: UUID
    source_url: Optional[str]
    text_content: Optional[str]
    topic_hint: Optional[str]
    notes: Optional[str]
    created_at: datetime
    event_id: Optional[UUID] = None
    event_status: Optional[EventStatus] = None

    class Config:
        from_attributes = True


# ============================================================
# Event Schemas
# ============================================================

class EventResponse(BaseModel):
    """Event response with full details."""
    id: UUID
    submitted_item_id: Optional[UUID]
    title: str
    summary: Optional[str]
    status: EventStatus
    reliability_score: Optional[int] = Field(None, ge=0, le=5)
    undercoverage_score: Optional[int] = Field(None, ge=0, le=5)
    risk_flags: List[str]
    normalized_data: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EventListResponse(BaseModel):
    """Paginated list of events."""
    items: List[EventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class EventUpdate(BaseModel):
    """Request to update event fields (curator only)."""
    title: Optional[str] = None
    summary: Optional[str] = None
    normalized_data: Optional[Dict[str, Any]] = None


# ============================================================
# Stage Run Schemas
# ============================================================

class StageRunResponse(BaseModel):
    """Stage run details."""
    id: UUID
    event_id: UUID
    stage: StageName
    status: StageStatus
    attempt: int
    model_used: Optional[str]
    input_snapshot: Optional[Dict[str, Any]]
    output_snapshot: Optional[Dict[str, Any]]
    error_message: Optional[str]
    kanban_task_id: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class StageRetryRequest(BaseModel):
    """Request to retry a failed stage."""
    pass  # No body needed, just triggers retry


# ============================================================
# Evidence Schemas
# ============================================================

class EvidenceSourceResponse(BaseModel):
    """Evidence source details."""
    id: UUID
    event_id: UUID
    source_type: str
    source_url: Optional[str]
    content_text: Optional[str]
    metadata: Dict[str, Any]
    retrieved_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Research Schemas
# ============================================================

class EventResearchResponse(BaseModel):
    """Research findings response."""
    id: UUID
    event_id: UUID
    findings: Dict[str, Any]
    evidence_links: Optional[List[str]]
    confidence_score: Optional[int] = Field(None, ge=0, le=5)
    model_used: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Coverage Schemas
# ============================================================

class EventCoverageResponse(BaseModel):
    """Coverage analysis response."""
    id: UUID
    event_id: UUID
    outlet_id: Optional[UUID]
    outlet_name: Optional[str]
    match_confidence: Optional[float] = Field(None, ge=0, le=1)
    article_url: Optional[str]
    article_title: Optional[str]
    article_date: Optional[date]
    framing_difference: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Risk Schemas
# ============================================================

class EventRiskResponse(BaseModel):
    """Risk assessment response."""
    id: UUID
    event_id: UUID
    flags: List[str]
    reliability_score: Optional[int] = Field(None, ge=0, le=5)
    undercoverage_score: Optional[int] = Field(None, ge=0, le=5)
    blocking_flags: List[str]
    rationale: Optional[str]
    model_used: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Draft Schemas
# ============================================================

class DraftResponse(BaseModel):
    """Draft content response."""
    id: UUID
    event_id: UUID
    draft_type: DraftFormat
    content: str
    evidence_references: List[Any]
    uncertainty_language: Optional[str]
    model_used: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Review Action Schemas
# ============================================================

class ReviewActionCreate(BaseModel):
    """Request to create a review action."""
    action: ReviewActionType
    force_approve: bool = Field(default=False, description="Force approval despite blocking flags")
    editor_note: Optional[str] = Field(None, description="Required for force_approve or reject")
    revision_request: Optional[str] = Field(None, description="Required for request_revision")

    @model_validator(mode='after')
    def validate_action_requirements(self) -> 'ReviewActionCreate':
        if self.action == 'force_approve' and not self.editor_note:
            raise ValueError("force_approve requires editor_note")
        if self.action == 'reject' and not self.editor_note:
            raise ValueError("reject requires editor_note")
        if self.action == 'request_revision' and not self.revision_request:
            raise ValueError("request_revision requires revision_request")
        return self


class ReviewActionResponse(BaseModel):
    """Review action response."""
    id: UUID
    event_id: UUID
    action: ReviewActionType
    editor_user_id: UUID
    editor_name: Optional[str]
    revision_request: Optional[str]
    force_approve: bool
    editor_note: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Publication Schemas
# ============================================================

class PublicationCreate(BaseModel):
    """Request to record a publication."""
    draft_id: Optional[UUID] = None
    platform: str = Field(..., description="Platform name (e.g., 'x_thread', 'newsletter')")
    published_url: Optional[HttpUrl] = None


class PublicationResponse(BaseModel):
    """Publication record response."""
    id: UUID
    event_id: UUID
    draft_id: Optional[UUID]
    platform: str
    published_url: Optional[str]
    published_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================
# Pagination Schemas
# ============================================================

class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper."""
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================
# Error Schemas (RFC 7807)
# ============================================================

class ErrorDetail(BaseModel):
    """Individual error detail."""
    field: str
    message: str


class ErrorResponse(BaseModel):
    """RFC 7807 compliant error response."""
    type: str = Field(..., description="URI identifying the error type")
    title: str = Field(..., description="Short summary of the error")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Detailed error message")
    instance: Optional[str] = Field(None, description="URI of the request")
    errors: Optional[List[ErrorDetail]] = Field(None, description="Field-level validation errors")


# ============================================================
# Health Check
# ============================================================

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    database: str
    timestamp: datetime


# ============================================================
# Aliases for API compatibility
# ============================================================

UserRead = UserResponse
SubmissionRead = SubmittedItemResponse
SubmissionCreate = SubmittedItemCreate
SubmissionUpdate = SubmittedItemCreate
EventRead = EventResponse
EventCreate = EventResponse
DraftRead = DraftResponse
PublicationRead = PublicationResponse
StageRunRead = StageRunResponse
ResearchRead = EventResearchResponse
CoverageRead = EventCoverageResponse
RiskRead = EventRiskResponse
EvidenceSourceRead = EvidenceSourceResponse


# ============================================================
# Internal / Kanban Poller Schemas
# ============================================================

class StageNameEnum(str, Enum):
    curation = "curation"
    research = "research"
    coverage = "coverage"
    risk = "risk"
    writer = "writer"


class StageStatusEnum(str, Enum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class KanbanTaskRegister(BaseModel):
    """Register a kanban task ID for a pipeline stage."""
    event_id: UUID
    stage: StageNameEnum
    kanban_task_id: str


class KanbanTaskRegisterResponse(BaseModel):
    id: UUID
    event_id: UUID
    stage: StageNameEnum
    kanban_task_id: str
    stage_status: StageStatusEnum


class PollerAdvanceResponse(BaseModel):
    """Result of one poller advance cycle."""
    events_checked: int
    tasks_spawned: List[dict] = []
    events_advanced: List[dict] = []
    errors: List[str] = []


class EventKanbanStatus(BaseModel):
    """Current kanban status for an event's pipeline stages."""
    event_id: UUID
    title: str
    curation: Optional[str] = None
    research: Optional[str] = None
    coverage: Optional[str] = None
    risk: Optional[str] = None
    writer: Optional[str] = None
