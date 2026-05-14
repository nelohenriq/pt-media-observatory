"""
PT Media Observatory - SQLAlchemy ORM Models

These models map to the PostgreSQL schema defined in alembic migrations.
All tables use UUID primary keys, soft deletes where appropriate, and JSONB for flexible fields.
"""

from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
import enum


Base = declarative_base()


# ============================================================
# Enums
# ============================================================

class UserRole(str, enum.Enum):
    """User roles in the system."""
    editor = "editor"
    admin = "admin"


class EventStatus(str, enum.Enum):
    """Event lifecycle status - finite state machine."""
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


class StageName(str, enum.Enum):
    """Pipeline stage names."""
    curation = "curation"
    research = "research"
    coverage = "coverage"
    risk = "risk"
    writer = "writer"
    red_team = "red_team"
    safety = "safety"


class StageStatus(str, enum.Enum):
    """Stage execution status."""
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class ReviewActionType(str, enum.Enum):
    """Review action types."""
    approve = "approve"
    reject = "reject"
    request_revision = "request_revision"
    force_approve = "force_approve"


class DraftFormat(str, enum.Enum):
    """Draft output formats."""
    x_thread = "x_thread"
    site_card = "site_card"
    newsletter_snippet = "newsletter_snippet"


# ============================================================
# Users
# ============================================================

class User(Base):
    """System users (editors and admins)."""
    __tablename__ = "users"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    name = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.editor)
    hashed_password = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    review_actions = relationship("EventReviewAction", back_populates="editor")
    submitted_items = relationship("SubmittedItem", back_populates="user")

    __table_args__ = (
        Index("idx_users_email", "email", unique=True),
        Index("idx_users_deleted_at", "deleted_at"),
    )


# ============================================================
# Outlets
# ============================================================

class Outlet(Base):
    """Media outlets (mainstream and independent)."""
    __tablename__ = "outlets"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String(255), nullable=False)
    website_url = Column(Text, nullable=False)
    type = Column(String(100), nullable=False, default="general")
    is_mainstream = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    coverage_articles = relationship("EventCoverage", back_populates="outlet")

    __table_args__ = (
        Index("idx_outlets_name", "name"),
        Index("idx_outlets_is_mainstream", "is_mainstream"),
    )


# ============================================================
# Submitted Items
# ============================================================

class SubmittedItem(Base):
    """Items submitted by users for investigation."""
    __tablename__ = "submitted_item"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    source_url = Column(Text, nullable=True)
    text_content = Column(Text, nullable=True)
    topic_hint = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="submitted_items")
    events = relationship("Event", back_populates="submitted_item")

    __table_args__ = (
        Index("idx_submitted_item_user_id", "user_id"),
        Index("idx_submitted_item_created_at", "created_at"),
    )


# ============================================================
# Events
# ============================================================

class Event(Base):
    """Main investigation/event entity."""
    __tablename__ = "event"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    submitted_item_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("submitted_item.id", ondelete="SET NULL"), nullable=True)
    title = Column(Text, nullable=False, default="Pending normalization")
    summary = Column(Text, nullable=True)
    status = Column(Enum(EventStatus), nullable=False, default=EventStatus.intake)
    reliability_score = Column(Integer, nullable=True)
    undercoverage_score = Column(Integer, nullable=True)
    risk_flags = Column(JSONB, nullable=False, default=list)
    normalized_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint("reliability_score >= 0 AND reliability_score <= 5", name="chk_reliability_score_range"),
        CheckConstraint("undercoverage_score >= 0 AND undercoverage_score <= 5", name="chk_undercoverage_score_range"),
        Index("idx_event_status", "status"),
        Index("idx_event_submitted_item_id", "submitted_item_id"),
        Index("idx_event_created_at", "created_at"),
    )

    # Relationships
    submitted_item = relationship("SubmittedItem", back_populates="events")
    stage_runs = relationship("EventStageRun", back_populates="event", cascade="all, delete-orphan")
    evidence_sources = relationship("EvidenceSource", back_populates="event", cascade="all, delete-orphan")
    research_records = relationship("EventResearch", back_populates="event", cascade="all, delete-orphan")
    coverage_records = relationship("EventCoverage", back_populates="event", cascade="all, delete-orphan")
    risk_records = relationship("EventRisk", back_populates="event", cascade="all, delete-orphan")
    drafts = relationship("EventDraft", back_populates="event", cascade="all, delete-orphan")
    review_actions = relationship("EventReviewAction", back_populates="event", cascade="all, delete-orphan")
    publications = relationship("EventPublication", back_populates="event", cascade="all, delete-orphan")


# ============================================================
# Event Stage Runs
# ============================================================

class EventStageRun(Base):
    """Tracks execution of each pipeline stage for an event."""
    __tablename__ = "event_stage_run"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("event.id", ondelete="CASCADE"), nullable=False)
    stage = Column(Enum(StageName), nullable=False)
    status = Column(Enum(StageStatus), nullable=False, default=StageStatus.pending)
    attempt = Column(Integer, nullable=False, default=0)
    model_used = Column(String(255), nullable=True)
    input_snapshot = Column(JSONB, nullable=True)
    output_snapshot = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    kanban_task_id = Column(String(255), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="stage_runs")

    __table_args__ = (
        Index("idx_stage_run_event", "event_id"),
        Index("idx_stage_run_status", "status"),
        Index("idx_stage_run_event_stage", "event_id", "stage"),
        Index("idx_stage_run_created_at", "created_at"),
    )


# ============================================================
# Evidence Sources
# ============================================================

class EvidenceSource(Base):
    """Evidence sources linked to events."""
    __tablename__ = "evidence_source"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("event.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String(100), nullable=False)  # 'official_doc', 'ngo_report', 'article', 'social_post', etc.
    source_url = Column(Text, nullable=True)
    content_text = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSONB, nullable=False, default=dict)
    retrieved_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="evidence_sources")

    __table_args__ = (
        Index("idx_evidence_event", "event_id"),
        Index("idx_evidence_source_type", "source_type"),
        Index("idx_evidence_created_at", "created_at"),
    )


# ============================================================
# Event Research
# ============================================================

class EventResearch(Base):
    """Research findings for an event."""
    __tablename__ = "event_research"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("event.id", ondelete="CASCADE"), nullable=False)
    findings = Column(JSONB, nullable=False, default=dict)
    evidence_links = Column(Text, nullable=True)  # Array stored as text or use ARRAY type
    confidence_score = Column(Integer, nullable=True)
    model_used = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 5", name="chk_confidence_score_range"),
        Index("idx_research_event", "event_id"),
        Index("idx_research_created_at", "created_at"),
    )

    # Relationships
    event = relationship("Event", back_populates="research_records")


# ============================================================
# Event Coverage
# ============================================================

class EventCoverage(Base):
    """Coverage analysis comparing event to mainstream outlets."""
    __tablename__ = "event_coverage"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("event.id", ondelete="CASCADE"), nullable=False)
    outlet_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("outlets.id", ondelete="SET NULL"), nullable=True)
    match_confidence = Column(Float, nullable=True)
    article_url = Column(Text, nullable=True)
    article_title = Column(Text, nullable=True)
    article_date = Column(Date, nullable=True)
    framing_difference = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint("match_confidence >= 0 AND match_confidence <= 1", name="chk_match_confidence_range"),
        Index("idx_coverage_event", "event_id"),
        Index("idx_coverage_outlet", "outlet_id"),
        Index("idx_coverage_created_at", "created_at"),
    )

    # Relationships
    event = relationship("Event", back_populates="coverage_records")
    outlet = relationship("Outlet", back_populates="coverage_articles")


# ============================================================
# Event Risk
# ============================================================

class EventRisk(Base):
    """Risk assessment for an event."""
    __tablename__ = "event_risk"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("event.id", ondelete="CASCADE"), nullable=False)
    flags = Column(JSONB, nullable=False, default=list)
    reliability_score = Column(Integer, nullable=True)
    undercoverage_score = Column(Integer, nullable=True)
    blocking_flags = Column(JSONB, nullable=False, default=list)
    rationale = Column(Text, nullable=True)
    model_used = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Constraints
    __table_args__ = (
        CheckConstraint("reliability_score >= 0 AND reliability_score <= 5", name="chk_risk_reliability_score_range"),
        CheckConstraint("undercoverage_score >= 0 AND undercoverage_score <= 5", name="chk_risk_undercoverage_score_range"),
        Index("idx_risk_event", "event_id"),
        Index("idx_risk_created_at", "created_at"),
    )

    # Relationships
    event = relationship("Event", back_populates="risk_records")


# ============================================================
# Event Drafts
# ============================================================

class EventDraft(Base):
    """Generated drafts for events."""
    __tablename__ = "event_drafts"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("event.id", ondelete="CASCADE"), nullable=False)
    draft_type = Column(Enum(DraftFormat), nullable=False)
    content = Column(Text, nullable=False)
    evidence_references = Column(JSONB, nullable=False, default=list)
    uncertainty_language = Column(Text, nullable=True)
    model_used = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="drafts")
    publications = relationship("EventPublication", back_populates="draft")

    __table_args__ = (
        Index("idx_drafts_event", "event_id"),
        Index("idx_drafts_type", "draft_type"),
        Index("idx_drafts_created_at", "created_at"),
    )


# ============================================================
# Event Review Actions
# ============================================================

class EventReviewAction(Base):
    """Review actions (approve/reject/revise) on events."""
    __tablename__ = "event_review_action"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("event.id", ondelete="CASCADE"), nullable=False)
    action = Column(Enum(ReviewActionType), nullable=False)
    editor_user_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    revision_request = Column(Text, nullable=True)
    force_approve = Column(Boolean, nullable=False, default=False)
    editor_note = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="review_actions")
    editor = relationship("User", back_populates="review_actions")

    __table_args__ = (
        Index("idx_review_event", "event_id"),
        Index("idx_review_editor", "editor_user_id"),
        Index("idx_review_created_at", "created_at"),
    )


# ============================================================
# Event Publications
# ============================================================

class EventPublication(Base):
    """Publication records for approved events."""
    __tablename__ = "event_publication"

    id = Column(PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("event.id", ondelete="CASCADE"), nullable=False)
    draft_id = Column(PostgreSQLUUID(as_uuid=True), ForeignKey("event_drafts.id", ondelete="SET NULL"), nullable=True)
    platform = Column(String(100), nullable=False)
    published_url = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Relationships
    event = relationship("Event", back_populates="publications")
    draft = relationship("EventDraft", back_populates="publications")

    __table_args__ = (
        Index("idx_publication_event", "event_id"),
        Index("idx_publication_platform", "platform"),
        Index("idx_publication_created_at", "created_at"),
    )
