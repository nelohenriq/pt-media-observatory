-- ============================================================
-- PT Media Observatory V1 — PostgreSQL Schema
-- ============================================================
-- This file contains the complete DDL for the PT Media Observatory
-- database. It can be used directly with psql or as a reference
-- for the Alembic migration system.
--
-- Database: pt_media_observatory
-- PostgreSQL: 16+
-- ============================================================

-- ============================================================
-- Enums
-- ============================================================

-- User roles in the system
CREATE TYPE user_role AS ENUM ('editor', 'admin');

-- Event lifecycle status - finite state machine
CREATE TYPE event_status AS ENUM (
    'intake', 'curation_pending', 'curation_complete',
    'research_pending', 'research_complete',
    'coverage_pending', 'coverage_complete',
    'risk_pending', 'risk_complete',
    'needs_editor_decision', 'writer_pending', 'writer_complete',
    'ready_for_review', 'approved', 'rejected', 'archived',
    'published'
);

-- Pipeline stage names
CREATE TYPE stage_name AS ENUM (
    'curation', 'research', 'coverage', 'risk', 'writer', 'red_team', 'safety'
);

-- Stage execution status
CREATE TYPE stage_status AS ENUM ('pending', 'running', 'succeeded', 'failed', 'cancelled');

-- Review action types
CREATE TYPE review_action_type AS ENUM ('approve', 'reject', 'request_revision', 'force_approve');

-- Draft output formats
CREATE TYPE draft_format AS ENUM ('x_thread', 'site_card', 'newsletter_snippet');

-- ============================================================
-- users table
-- ============================================================
-- System users (editors and admins).
-- Soft deletes via deleted_at for audit compliance.

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'editor',
    hashed_password TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_deleted_at ON users(deleted_at);

-- ============================================================
-- outlets table
-- ============================================================
-- Media outlets (mainstream and independent).
-- Used for coverage comparison tracking.

CREATE TABLE outlets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    website_url TEXT NOT NULL,
    type VARCHAR(100) NOT NULL DEFAULT 'general',
    is_mainstream BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_outlets_name ON outlets(name);
CREATE INDEX idx_outlets_is_mainstream ON outlets(is_mainstream);

-- ============================================================
-- submitted_item table
-- ============================================================
-- Items submitted by users for investigation.
-- Can be a URL, pasted text, or both.

CREATE TABLE submitted_item (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    source_url TEXT,
    text_content TEXT,
    topic_hint TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_submitted_item_user_id ON submitted_item(user_id);
CREATE INDEX idx_submitted_item_created_at ON submitted_item(created_at);

-- ============================================================
-- event table
-- ============================================================
-- Main investigation/event entity.
-- Tracks the full lifecycle from submission to publication.
-- CHECK constraints ensure scores are in valid 0-5 range.

CREATE TABLE event (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submitted_item_id UUID REFERENCES submitted_item(id) ON DELETE SET NULL,
    title TEXT NOT NULL DEFAULT 'Pending normalization',
    summary TEXT,
    status event_status NOT NULL DEFAULT 'intake',
    reliability_score INTEGER,
    undercoverage_score INTEGER,
    risk_flags JSONB NOT NULL DEFAULT '[]',
    normalized_data JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_reliability_score_range CHECK (reliability_score >= 0 AND reliability_score <= 5),
    CONSTRAINT chk_undercoverage_score_range CHECK (undercoverage_score >= 0 AND undercoverage_score <= 5)
);

CREATE INDEX idx_event_status ON event(status);
CREATE INDEX idx_event_submitted_item_id ON event(submitted_item_id);
CREATE INDEX idx_event_created_at ON event(created_at);

-- ============================================================
-- event_stage_run table
-- ============================================================
-- Tracks execution of each pipeline stage for an event.
-- Source of truth for UI progress, retries, errors, model usage.
-- Supports up to 3 retry attempts per stage.

CREATE TABLE event_stage_run (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    stage stage_name NOT NULL,
    status stage_status NOT NULL DEFAULT 'pending',
    attempt INTEGER NOT NULL DEFAULT 0,
    model_used VARCHAR(255),
    input_snapshot JSONB,
    output_snapshot JSONB,
    error_message TEXT,
    kanban_task_id VARCHAR(255),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_stage_run_event ON event_stage_run(event_id);
CREATE INDEX idx_stage_run_status ON event_stage_run(status);
CREATE INDEX idx_stage_run_event_stage ON event_stage_run(event_id, stage);
CREATE INDEX idx_stage_run_created_at ON event_stage_run(created_at);

-- ============================================================
-- evidence_source table
-- ============================================================
-- Evidence sources linked to events.
-- First-class citizens: official docs, social posts, datasets, PDFs, transcripts.
-- JSONB metadata allows flexible per-source-type fields.

CREATE TABLE evidence_source (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    source_type VARCHAR(100) NOT NULL, -- 'official_doc', 'ngo_report', 'article', 'social_post', etc.
    source_url TEXT,
    content_text TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    retrieved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_evidence_event ON evidence_source(event_id);
CREATE INDEX idx_evidence_source_type ON evidence_source(source_type);
CREATE INDEX idx_evidence_created_at ON evidence_source(created_at);

-- ============================================================
-- event_research table
-- ============================================================
-- Research findings for an event.
-- Stores structured findings as JSONB with confidence score.

CREATE TABLE event_research (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    findings JSONB NOT NULL DEFAULT '{}',
    evidence_links TEXT[],
    confidence_score INTEGER,
    model_used VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_confidence_score_range CHECK (confidence_score >= 0 AND confidence_score <= 5)
);

CREATE INDEX idx_research_event ON event_research(event_id);
CREATE INDEX idx_research_created_at ON event_research(created_at);

-- ============================================================
-- event_coverage table
-- ============================================================
-- Coverage analysis comparing event to mainstream outlets.
-- Tracks which outlets covered the story and framing differences.

CREATE TABLE event_coverage (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    outlet_id UUID REFERENCES outlets(id) ON DELETE SET NULL,
    match_confidence FLOAT,
    article_url TEXT,
    article_title TEXT,
    article_date DATE,
    framing_difference TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_match_confidence_range CHECK (match_confidence >= 0 AND match_confidence <= 1)
);

CREATE INDEX idx_coverage_event ON event_coverage(event_id);
CREATE INDEX idx_coverage_outlet ON event_coverage(outlet_id);
CREATE INDEX idx_coverage_created_at ON event_coverage(created_at);

-- ============================================================
-- event_risk table
-- ============================================================
-- Risk assessment for an event.
-- Stores flags, scores, and blocking flags for drafting gate.

CREATE TABLE event_risk (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    flags JSONB NOT NULL DEFAULT '[]',
    reliability_score INTEGER,
    undercoverage_score INTEGER,
    blocking_flags JSONB NOT NULL DEFAULT '[]',
    rationale TEXT,
    model_used VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_risk_reliability_score_range CHECK (reliability_score >= 0 AND reliability_score <= 5),
    CONSTRAINT chk_risk_undercoverage_score_range CHECK (undercoverage_score >= 0 AND undercoverage_score <= 5)
);

CREATE INDEX idx_risk_event ON event_risk(event_id);
CREATE INDEX idx_risk_created_at ON event_risk(created_at);

-- ============================================================
-- event_drafts table
-- ============================================================
-- Generated drafts for events.
-- Stores X threads, site cards, newsletter snippets.

CREATE TABLE event_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    draft_type draft_format NOT NULL,
    content TEXT NOT NULL,
    evidence_references JSONB NOT NULL DEFAULT '[]',
    uncertainty_language TEXT,
    model_used VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_drafts_event ON event_drafts(event_id);
CREATE INDEX idx_drafts_type ON event_drafts(draft_type);
CREATE INDEX idx_drafts_created_at ON event_drafts(created_at);

-- ============================================================
-- event_review_action table
-- ============================================================
-- Review actions (approve/reject/revise) on events.
-- Every editor decision is logged here with rationale.

CREATE TABLE event_review_action (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    action review_action_type NOT NULL,
    editor_user_id UUID NOT NULL REFERENCES users(id),
    revision_request TEXT,
    force_approve BOOLEAN NOT NULL DEFAULT FALSE,
    editor_note TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_review_event ON event_review_action(event_id);
CREATE INDEX idx_review_editor ON event_review_action(editor_user_id);
CREATE INDEX idx_review_created_at ON event_review_action(created_at);

-- ============================================================
-- event_publication table
-- ============================================================
-- Publication records for approved events.
-- Tracks where and when drafts were published.
-- No auto-publishing - manual record creation only.

CREATE TABLE event_publication (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES event(id) ON DELETE CASCADE,
    draft_id UUID REFERENCES event_drafts(id) ON DELETE SET NULL,
    platform VARCHAR(100) NOT NULL,
    published_url TEXT,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_publication_event ON event_publication(event_id);
CREATE INDEX idx_publication_platform ON event_publication(platform);
CREATE INDEX idx_publication_created_at ON event_publication(created_at);

-- ============================================================
-- Schema Comments
-- ============================================================

COMMENT ON TABLE users IS 'System users (editors and admins). Soft deletes via deleted_at.';
COMMENT ON TABLE outlets IS 'Media outlets for coverage comparison.';
COMMENT ON TABLE submitted_item IS 'Items submitted by users for investigation.';
COMMENT ON TABLE event IS 'Main investigation entity - tracks full lifecycle.';
COMMENT ON TABLE event_stage_run IS 'Pipeline stage execution tracking - source of truth for progress.';
COMMENT ON TABLE evidence_source IS 'First-class evidence sources with flexible JSONB metadata.';
COMMENT ON TABLE event_research IS 'Research findings with structured JSONB data.';
COMMENT ON TABLE event_coverage IS 'Coverage analysis comparing to mainstream outlets.';
COMMENT ON TABLE event_risk IS 'Risk assessment with flags and scores for drafting gate.';
COMMENT ON TABLE event_drafts IS 'Generated drafts (X threads, site cards, newsletters).';
COMMENT ON TABLE event_review_action IS 'Editor review actions - all decisions logged.';
COMMENT ON TABLE event_publication IS 'Publication records - manual, no auto-publishing.';

-- ============================================================
-- End of Schema
-- ============================================================
