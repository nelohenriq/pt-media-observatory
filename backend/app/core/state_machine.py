"""Event state machine — finite state machine with guards."""
from enum import Enum
from typing import Optional, List


class EventStatus(str, Enum):
    INTAKE = "intake"
    CURATION_PENDING = "curation_pending"
    CURATION_COMPLETE = "curation_complete"
    RESEARCH_PENDING = "research_pending"
    RESEARCH_COMPLETE = "research_complete"
    COVERAGE_PENDING = "coverage_pending"
    COVERAGE_COMPLETE = "coverage_complete"
    RISK_PENDING = "risk_pending"
    RISK_COMPLETE = "risk_complete"
    NEEDS_EDITOR_DECISION = "needs_editor_decision"
    WRITER_PENDING = "writer_pending"
    WRITER_COMPLETE = "writer_complete"
    READY_FOR_REVIEW = "ready_for_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ARCHIVED = "archived"
    PUBLISHED = "published"


class InvalidTransitionError(Exception):
    def __init__(self, from_status: EventStatus, to_status: EventStatus):
        self.from_status = from_status
        self.to_status = to_status
        super().__init__(f"Cannot transition from {from_status.value} to {to_status.value}")


# Valid transition map
_VALID_TRANSITIONS: dict[EventStatus, list[EventStatus]] = {
    EventStatus.INTAKE: [EventStatus.CURATION_PENDING],
    EventStatus.CURATION_PENDING: [EventStatus.CURATION_COMPLETE],
    EventStatus.CURATION_COMPLETE: [EventStatus.RESEARCH_PENDING, EventStatus.COVERAGE_PENDING],
    EventStatus.RESEARCH_PENDING: [EventStatus.RESEARCH_COMPLETE],
    EventStatus.RESEARCH_COMPLETE: [EventStatus.RISK_PENDING],
    EventStatus.COVERAGE_PENDING: [EventStatus.COVERAGE_COMPLETE],
    EventStatus.COVERAGE_COMPLETE: [EventStatus.RISK_PENDING],
    EventStatus.RISK_PENDING: [EventStatus.RISK_COMPLETE],
    EventStatus.RISK_COMPLETE: [EventStatus.NEEDS_EDITOR_DECISION, EventStatus.WRITER_PENDING],
    EventStatus.NEEDS_EDITOR_DECISION: [EventStatus.WRITER_PENDING, EventStatus.REJECTED, EventStatus.ARCHIVED],
    EventStatus.WRITER_PENDING: [EventStatus.WRITER_COMPLETE],
    EventStatus.WRITER_COMPLETE: [EventStatus.READY_FOR_REVIEW],
    EventStatus.READY_FOR_REVIEW: [EventStatus.APPROVED, EventStatus.REJECTED, EventStatus.NEEDS_EDITOR_DECISION],
    EventStatus.APPROVED: [EventStatus.PUBLISHED],
    EventStatus.REJECTED: [],
    EventStatus.ARCHIVED: [],
    EventStatus.PUBLISHED: [],
}


BLOCKING_RISK_FLAGS = frozenset({
    "serious_accusation_weak_evidence",
    "single_anonymous_source",
    "possible_defamation",
    "identity_or_private_life_risk",
    "manipulated_or_unverified_media",
    "private_person_harm_risk",
    "missing_primary_source_for_serious_claim",
})


def can_transition(from_status: EventStatus, to_status: EventStatus) -> bool:
    return to_status in _VALID_TRANSITIONS.get(from_status, [])


def transition(from_status: EventStatus, to_status: EventStatus) -> EventStatus:
    if not can_transition(from_status, to_status):
        raise InvalidTransitionError(from_status, to_status)
    return to_status

def transition_to_writer_pending(
    from_status: EventStatus,
    reliability_score: Optional[int],
    undercoverage_score: Optional[int],
    blocking_flags: Optional[List[str]] = None,
    force_approve: bool = False,
    editor_note: Optional[str] = None,
) -> EventStatus:
    """
    Transition to writer_pending after enforcing drafting gate constraints.

    If force_approve=True, bypasses score-based gate (reliability ≥ 2, undercoverage ≥ 1)
    but still enforces blocking risk flags and requires editor_note.

    Raises InvalidTransitionError if:
      - transition is not structurally valid
      - force_approve=True but editor_note is missing
      - any blocking risk flag is present (force_approve still blocks these)
    """
    if not can_transition(from_status, EventStatus.WRITER_PENDING):
        raise InvalidTransitionError(from_status, EventStatus.WRITER_PENDING)

    if not is_drafting_allowed(
        reliability_score=reliability_score,
        undercoverage_score=undercoverage_score,
        blocking_flags=blocking_flags,
    ):
        if force_approve:
            if not editor_note:
                raise ValueError("force_approve requires editor_note")
            # Still enforce blocking flags even for force-approve
            flags = blocking_flags or []
            for flag in flags:
                if flag in BLOCKING_RISK_FLAGS:
                    raise ValueError(f"force_approve cannot bypass blocking flag: {flag}")
        else:
            raise InvalidTransitionError(from_status, EventStatus.WRITER_PENDING)

    return transition(from_status, EventStatus.WRITER_PENDING)


def transition_to_approved(
    from_status: EventStatus,
    force_approve: bool = False,
    editor_note: Optional[str] = None,
) -> EventStatus:
    """
    Transition to APPROVED (ready for publication).

    Available from READY_FOR_REVIEW or NEEDS_EDITOR_DECISION.
    force_approve allows bypassing the normal review gate with editor_note.
    """
    if not can_transition(from_status, EventStatus.APPROVED):
        raise InvalidTransitionError(from_status, EventStatus.APPROVED)

    if force_approve:
        if not editor_note:
            raise ValueError("force_approve requires editor_note")
        # Note: blocking flags already evaluated at RISK_COMPLETE stage;
        # force_approve from here is an editorial override, not a safety bypass

    return transition(from_status, EventStatus.APPROVED)


def is_drafting_allowed(
    reliability_score: Optional[int],
    undercoverage_score: Optional[int],
    blocking_flags: Optional[List[str]] = None,
) -> bool:
    """Drafting gate: check if event can proceed to writer stage."""
    if reliability_score is None or not (2 <= reliability_score <= 5):
        return False
    if undercoverage_score is None or not (1 <= undercoverage_score <= 5):
        return False
    flags = blocking_flags or []
    for flag in flags:
        if flag in BLOCKING_RISK_FLAGS:
            return False
    return True