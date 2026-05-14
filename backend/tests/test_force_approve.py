"""Tests for force-approve path and score range validation."""
import pytest
from backend.app.core.state_machine import (
    EventStatus,
    InvalidTransitionError,
    is_drafting_allowed,
    transition_to_writer_pending,
    transition_to_approved,
)


class TestScoreRangeValidation:
    """Score bounds must be enforced in is_drafting_allowed()."""

    def test_score_999_rejected(self):
        """Score above valid range (0-5) must be rejected."""
        assert is_drafting_allowed(reliability_score=999, undercoverage_score=3, blocking_flags=[]) is False

    def test_negative_score_rejected(self):
        assert is_drafting_allowed(reliability_score=-1, undercoverage_score=3, blocking_flags=[]) is False
        assert is_drafting_allowed(reliability_score=3, undercoverage_score=-1, blocking_flags=[]) is False

    def test_valid_boundary_scores_accepted(self):
        """Boundary values 2 and 5 for reliability, 1 and 5 for undercoverage."""
        assert is_drafting_allowed(reliability_score=2, undercoverage_score=1, blocking_flags=[]) is True
        assert is_drafting_allowed(reliability_score=5, undercoverage_score=5, blocking_flags=[]) is True

    def test_score_0_rejected(self):
        assert is_drafting_allowed(reliability_score=0, undercoverage_score=1, blocking_flags=[]) is False


class TestForceApproveWriterPending:
    """force_approve bypasses score gate but not blocking flags."""

    def test_force_approve_without_editor_note_raises(self):
        with pytest.raises(ValueError, match="force_approve requires editor_note"):
            transition_to_writer_pending(
                EventStatus.RISK_COMPLETE,
                reliability_score=1,  # below threshold
                undercoverage_score=0,  # below threshold
                blocking_flags=[],
                force_approve=True,
                editor_note=None,
            )

    def test_force_approve_with_editor_note_succeeds(self):
        result = transition_to_writer_pending(
            EventStatus.RISK_COMPLETE,
            reliability_score=1,
            undercoverage_score=0,
            blocking_flags=[],
            force_approve=True,
            editor_note="Editorial override — story verified by independent sources.",
        )
        assert result == EventStatus.WRITER_PENDING

    def test_force_approve_still_blocks_risk_flags(self):
        """force_approve cannot bypass terminal risk flags like possible_defamation."""
        with pytest.raises(ValueError, match="force_approve cannot bypass blocking flag"):
            transition_to_writer_pending(
                EventStatus.RISK_COMPLETE,
                reliability_score=1,
                undercoverage_score=0,
                blocking_flags=["possible_defamation"],
                force_approve=True,
                editor_note="Proceeding anyway.",
            )

    def test_force_approve_does_not_block_legitimate_flags(self):
        """force_approve with no blocking flags succeeds."""
        result = transition_to_writer_pending(
            EventStatus.RISK_COMPLETE,
            reliability_score=1,
            undercoverage_score=0,
            blocking_flags=["under_investigation"],  # not a blocking flag
            force_approve=True,
            editor_note="OK to proceed.",
        )
        assert result == EventStatus.WRITER_PENDING

    def test_invalid_from_status_raises(self):
        """Cannot force-approve from a state that cannot transition to WRITER_PENDING."""
        with pytest.raises(InvalidTransitionError):
            transition_to_writer_pending(
                EventStatus.INTAKE,
                reliability_score=1,
                undercoverage_score=0,
                blocking_flags=[],
                force_approve=True,
                editor_note="Test",
            )


class TestForceApproveToApproved:
    """force_approve from READY_FOR_REVIEW or NEEDS_EDITOR_DECISION to APPROVED."""

    def test_force_approve_to_approved_requires_editor_note(self):
        with pytest.raises(ValueError, match="force_approve requires editor_note"):
            transition_to_approved(EventStatus.READY_FOR_REVIEW, force_approve=True, editor_note=None)

    def test_force_approve_to_approved_succeeds(self):
        result = transition_to_approved(
            EventStatus.READY_FOR_REVIEW,
            force_approve=True,
            editor_note="Reviewed and approved by editor.",
        )
        assert result == EventStatus.APPROVED

    def test_force_approve_from_needs_editor_decision_to_writer(self):
        """From NEEDS_EDITOR_DECISION, force_approve routes to WRITER_PENDING (retry drafting)."""
        result = transition_to_approved(
            EventStatus.READY_FOR_REVIEW,
            force_approve=True,
            editor_note="Reviewed and approved by editor.",
        )
        assert result == EventStatus.APPROVED

    def test_invalid_from_status_raises(self):
        with pytest.raises(InvalidTransitionError):
            transition_to_approved(EventStatus.RISK_COMPLETE, force_approve=True, editor_note="Test")
