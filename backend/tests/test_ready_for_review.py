from backend.app.core.state_machine import EventStatus, can_transition, transition


class TestReadyForReviewTransitions:
    def test_ready_for_review_to_approved(self):
        assert can_transition(EventStatus.READY_FOR_REVIEW, EventStatus.APPROVED)
        assert transition(EventStatus.READY_FOR_REVIEW, EventStatus.APPROVED) == EventStatus.APPROVED

    def test_approved_to_published(self):
        assert can_transition(EventStatus.APPROVED, EventStatus.PUBLISHED)
        assert transition(EventStatus.APPROVED, EventStatus.PUBLISHED) == EventStatus.PUBLISHED

    def test_ready_for_review_to_rejected(self):
        assert can_transition(EventStatus.READY_FOR_REVIEW, EventStatus.REJECTED)
        assert transition(EventStatus.READY_FOR_REVIEW, EventStatus.REJECTED) == EventStatus.REJECTED

    def test_rejected_no_further_transitions(self):
        # REJECTED is a terminal state; no outgoing transitions allowed
        assert not can_transition(EventStatus.REJECTED, EventStatus.APPROVED)
        assert not can_transition(EventStatus.REJECTED, EventStatus.PUBLISHED)
        assert not can_transition(EventStatus.REJECTED, EventStatus.WRITER_PENDING)
        assert not can_transition(EventStatus.REJECTED, EventStatus.WRITER_COMPLETE)
        assert not can_transition(EventStatus.REJECTED, EventStatus.READY_FOR_REVIEW)