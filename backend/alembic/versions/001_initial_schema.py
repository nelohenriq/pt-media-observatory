"""Initial schema - PT Media Observatory V1

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-05-13

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ============================================================
    # Create enums
    # ============================================================
    
    # User roles
    op.execute("CREATE TYPE user_role AS ENUM ('editor', 'admin')")
    
    # Event status - finite state machine
    op.execute("""
        CREATE TYPE event_status AS ENUM (
            'intake', 'curation_pending', 'curation_complete',
            'research_pending', 'research_complete',
            'coverage_pending', 'coverage_complete',
            'risk_pending', 'risk_complete',
            'needs_editor_decision', 'writer_pending', 'writer_complete',
            'ready_for_review', 'approved', 'rejected', 'archived',
            'published'
        )
    """)
    
    # Stage names
    op.execute("""
        CREATE TYPE stage_name AS ENUM (
            'curation', 'research', 'coverage', 'risk', 'writer', 'red_team', 'safety'
        )
    """)
    
    # Stage status
    op.execute("CREATE TYPE stage_status AS ENUM ('pending', 'running', 'succeeded', 'failed', 'cancelled')")
    
    # Review action types
    op.execute("CREATE TYPE review_action_type AS ENUM ('approve', 'reject', 'request_revision', 'force_approve')")
    
    # Draft formats
    op.execute("CREATE TYPE draft_format AS ENUM ('x_thread', 'site_card', 'newsletter_snippet')")
    
    # ============================================================
    # users table
    # ============================================================
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('role', sa.Enum('editor', 'admin', name='user_role'), nullable=False, default='editor'),
        sa.Column('hashed_password', sa.Text, nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
    op.create_index('idx_users_email', 'users', ['email'], unique=True)
    op.create_index('idx_users_deleted_at', 'users', ['deleted_at'])
    
    # ============================================================
    # outlets table
    # ============================================================
    op.create_table(
        'outlets',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('website_url', sa.Text, nullable=False),
        sa.Column('type', sa.String(100), nullable=False, default='general'),
        sa.Column('is_mainstream', sa.Boolean, nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
    )
    op.create_index('idx_outlets_name', 'outlets', ['name'])
    op.create_index('idx_outlets_is_mainstream', 'outlets', ['is_mainstream'])
    
    # ============================================================
    # submitted_item table
    # ============================================================
    op.create_table(
        'submitted_item',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=False),
        sa.Column('source_url', sa.Text, nullable=True),
        sa.Column('text_content', sa.Text, nullable=True),
        sa.Column('topic_hint', sa.Text, nullable=True),
        sa.Column('notes', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
    )
    op.create_index('idx_submitted_item_user_id', 'submitted_item', ['user_id'])
    op.create_index('idx_submitted_item_created_at', 'submitted_item', ['created_at'])
    
    # ============================================================
    # event table
    # ============================================================
    op.create_table(
        'event',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('submitted_item_id', UUID(as_uuid=True), sa.ForeignKey('submitted_item.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.Text, nullable=False, default='Pending normalization'),
        sa.Column('summary', sa.Text, nullable=True),
        sa.Column('status', sa.Enum('intake', 'curation_pending', 'curation_complete',
                                     'research_pending', 'research_complete',
                                     'coverage_pending', 'coverage_complete',
                                     'risk_pending', 'risk_complete',
                                     'needs_editor_decision', 'writer_pending', 'writer_complete',
                                     'ready_for_review', 'approved', 'rejected', 'archived',
                                     'published', name='event_status'), nullable=False, default='intake'),
        sa.Column('reliability_score', sa.Integer, nullable=True),
        sa.Column('undercoverage_score', sa.Integer, nullable=True),
        sa.Column('risk_flags', JSONB, nullable=False, default=sa.text("'[]'::jsonb")),
        sa.Column('normalized_data', JSONB, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
    )
    # CHECK constraints for score ranges
    op.execute('ALTER TABLE event ADD CONSTRAINT chk_reliability_score_range CHECK (reliability_score >= 0 AND reliability_score <= 5)')
    op.execute('ALTER TABLE event ADD CONSTRAINT chk_undercoverage_score_range CHECK (undercoverage_score >= 0 AND undercoverage_score <= 5)')
    op.create_index('idx_event_status', 'event', ['status'])
    op.create_index('idx_event_submitted_item_id', 'event', ['submitted_item_id'])
    op.create_index('idx_event_created_at', 'event', ['created_at'])
    
    # ============================================================
    # event_stage_run table
    # ============================================================
    op.create_table(
        'event_stage_run',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey('event.id', ondelete='CASCADE'), nullable=False),
        sa.Column('stage', sa.Enum('curation', 'research', 'coverage', 'risk', 'writer', 'red_team', 'safety', name='stage_name'), nullable=False),
        sa.Column('status', sa.Enum('pending', 'running', 'succeeded', 'failed', 'cancelled', name='stage_status'), nullable=False, default='pending'),
        sa.Column('attempt', sa.Integer, nullable=False, default=0),
        sa.Column('model_used', sa.String(255), nullable=True),
        sa.Column('input_snapshot', JSONB, nullable=True),
        sa.Column('output_snapshot', JSONB, nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('kanban_task_id', sa.String(255), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
    )
    op.create_index('idx_stage_run_event', 'event_stage_run', ['event_id'])
    op.create_index('idx_stage_run_status', 'event_stage_run', ['status'])
    op.create_index('idx_stage_run_event_stage', 'event_stage_run', ['event_id', 'stage'])
    op.create_index('idx_stage_run_created_at', 'event_stage_run', ['created_at'])
    
    # ============================================================
    # evidence_source table
    # ============================================================
    op.create_table(
        'evidence_source',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey('event.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_type', sa.String(100), nullable=False),
        sa.Column('source_url', sa.Text, nullable=True),
        sa.Column('content_text', sa.Text, nullable=True),
        sa.Column('metadata', JSONB, nullable=False, default=sa.text("'{}'::jsonb")),
        sa.Column('retrieved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
    )
    op.create_index('idx_evidence_event', 'evidence_source', ['event_id'])
    op.create_index('idx_evidence_source_type', 'evidence_source', ['source_type'])
    op.create_index('idx_evidence_created_at', 'evidence_source', ['created_at'])
    
    # ============================================================
    # event_research table
    # ============================================================
    op.create_table(
        'event_research',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey('event.id', ondelete='CASCADE'), nullable=False),
        sa.Column('findings', JSONB, nullable=False, default=sa.text("'{}'::jsonb")),
        sa.Column('evidence_links', sa.Text, nullable=True),
        sa.Column('confidence_score', sa.Integer, nullable=True),
        sa.Column('model_used', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
    )
    op.execute('ALTER TABLE event_research ADD CONSTRAINT chk_confidence_score_range CHECK (confidence_score >= 0 AND confidence_score <= 5)')
    op.create_index('idx_research_event', 'event_research', ['event_id'])
    op.create_index('idx_research_created_at', 'event_research', ['created_at'])
    
    # ============================================================
    # event_coverage table
    # ============================================================
    op.create_table(
        'event_coverage',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey('event.id', ondelete='CASCADE'), nullable=False),
        sa.Column('outlet_id', UUID(as_uuid=True), sa.ForeignKey('outlets.id', ondelete='SET NULL'), nullable=True),
        sa.Column('match_confidence', sa.Float, nullable=True),
        sa.Column('article_url', sa.Text, nullable=True),
        sa.Column('article_title', sa.Text, nullable=True),
        sa.Column('article_date', sa.Date, nullable=True),
        sa.Column('framing_difference', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
    )
    op.execute('ALTER TABLE event_coverage ADD CONSTRAINT chk_match_confidence_range CHECK (match_confidence >= 0 AND match_confidence <= 1)')
    op.create_index('idx_coverage_event', 'event_coverage', ['event_id'])
    op.create_index('idx_coverage_outlet', 'event_coverage', ['outlet_id'])
    op.create_index('idx_coverage_created_at', 'event_coverage', ['created_at'])
    
    # ============================================================
    # event_risk table
    # ============================================================
    op.create_table(
        'event_risk',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey('event.id', ondelete='CASCADE'), nullable=False),
        sa.Column('flags', JSONB, nullable=False, default=sa.text("'[]'::jsonb")),
        sa.Column('reliability_score', sa.Integer, nullable=True),
        sa.Column('undercoverage_score', sa.Integer, nullable=True),
        sa.Column('blocking_flags', JSONB, nullable=False, default=sa.text("'[]'::jsonb")),
        sa.Column('rationale', sa.Text, nullable=True),
        sa.Column('model_used', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
    )
    op.execute('ALTER TABLE event_risk ADD CONSTRAINT chk_risk_reliability_score_range CHECK (reliability_score >= 0 AND reliability_score <= 5)')
    op.execute('ALTER TABLE event_risk ADD CONSTRAINT chk_risk_undercoverage_score_range CHECK (undercoverage_score >= 0 AND undercoverage_score <= 5)')
    op.create_index('idx_risk_event', 'event_risk', ['event_id'])
    op.create_index('idx_risk_created_at', 'event_risk', ['created_at'])
    
    # ============================================================
    # event_drafts table
    # ============================================================
    op.create_table(
        'event_drafts',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey('event.id', ondelete='CASCADE'), nullable=False),
        sa.Column('draft_type', sa.Enum('x_thread', 'site_card', 'newsletter_snippet', name='draft_format'), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('evidence_references', JSONB, nullable=False, default=sa.text("'[]'::jsonb")),
        sa.Column('uncertainty_language', sa.Text, nullable=True),
        sa.Column('model_used', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
    )
    op.create_index('idx_drafts_event', 'event_drafts', ['event_id'])
    op.create_index('idx_drafts_type', 'event_drafts', ['draft_type'])
    op.create_index('idx_drafts_created_at', 'event_drafts', ['created_at'])
    
    # ============================================================
    # event_review_action table
    # ============================================================
    op.create_table(
        'event_review_action',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey('event.id', ondelete='CASCADE'), nullable=False),
        sa.Column('action', sa.Enum('approve', 'reject', 'request_revision', 'force_approve', name='review_action_type'), nullable=False),
        sa.Column('editor_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('revision_request', sa.Text, nullable=True),
        sa.Column('force_approve', sa.Boolean, nullable=False, default=False),
        sa.Column('editor_note', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
    )
    op.create_index('idx_review_event', 'event_review_action', ['event_id'])
    op.create_index('idx_review_editor', 'event_review_action', ['editor_user_id'])
    op.create_index('idx_review_created_at', 'event_review_action', ['created_at'])
    
    # ============================================================
    # event_publication table
    # ============================================================
    op.create_table(
        'event_publication',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('event_id', UUID(as_uuid=True), sa.ForeignKey('event.id', ondelete='CASCADE'), nullable=False),
        sa.Column('draft_id', UUID(as_uuid=True), sa.ForeignKey('event_drafts.id', ondelete='SET NULL'), nullable=True),
        sa.Column('platform', sa.String(100), nullable=False),
        sa.Column('published_url', sa.Text, nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, default=sa.text('NOW()')),
    )
    op.create_index('idx_publication_event', 'event_publication', ['event_id'])
    op.create_index('idx_publication_platform', 'event_publication', ['platform'])
    op.create_index('idx_publication_created_at', 'event_publication', ['created_at'])


def downgrade():
    # Drop tables in reverse order (respecting foreign keys)
    op.drop_table('event_publication')
    op.drop_table('event_review_action')
    op.drop_table('event_drafts')
    op.drop_table('event_risk')
    op.drop_table('event_coverage')
    op.drop_table('event_research')
    op.drop_table('evidence_source')
    op.drop_table('event_stage_run')
    op.drop_table('event')
    op.drop_table('submitted_item')
    op.drop_table('outlets')
    op.drop_table('users')
    
    # Drop enums
    op.execute("DROP TYPE draft_format")
    op.execute("DROP TYPE review_action_type")
    op.execute("DROP TYPE stage_status")
    op.execute("DROP TYPE stage_name")
    op.execute("DROP TYPE event_status")
    op.execute("DROP TYPE user_role")
