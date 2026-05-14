"""
Internal API endpoints for Hermes Kanban integration.

These endpoints are called by:
- The kanban poller cron job (POST /internal/poller/advance)
- Profile agents (POST /internal/kanban/register-task)
- The curator agent (POST /internal/events/from-curator)

All require X-Internal-Key header (validated against INTERNAL_API_KEY env var).
"""

import logging
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as SASession

from ..config import Settings
from ..database import get_db
from ..models import Event, EventStatus, KanbanTaskSync, StageName, StageStatus
from ..schemas import (
    KanbanTaskRegister,
    KanbanTaskRegisterResponse,
    PollerAdvanceResponse,
    EventKanbanStatus,
    StageNameEnum,
)
from ..services import kanban_sync

logger = logging.getLogger("pt-media-observatory.internal")

router = APIRouter(prefix="/internal", tags=["internal"])


def _check_internal_key(x_internal_key: str = Header(...)) -> None:
    """Validate X-Internal-Key header."""
    settings = Settings()
    if x_internal_key != settings.internal_api_key:
        raise HTTPException(status_code=401, detail="Invalid internal key")


# ------------------------------------------------------------------
# Kanban integration
# ------------------------------------------------------------------

@router.post("/kanban/register-task", response_model=KanbanTaskRegisterResponse)
def register_kanban_task(
    body: KanbanTaskRegister,
    db: SASession = Depends(get_db),
    _=Depends(_check_internal_key),
) -> KanbanTaskRegisterResponse:
    """
    Register a kanban task ID for a pipeline stage.

    Called by profile agents after they create a child kanban task,
    so the backend can track the task and poll its completion.
    """
    sync = kanban_sync.register_task(db, body.event_id, body.stage, body.kanban_task_id)
    return KanbanTaskRegisterResponse(
        id=sync.id,
        event_id=sync.event_id,
        stage=StageNameEnum(sync.stage.value),
        kanban_task_id=sync.kanban_task_id,
        stage_status=sync.stage_status.value,
    )


@router.post("/kanban/advance", response_model=PollerAdvanceResponse)
def advance_pipeline(
    db: SASession = Depends(get_db),
    _=Depends(_check_internal_key),
) -> PollerAdvanceResponse:
    """
    Advance the pipeline for all events with pending kanban tasks.

    This is the main polling endpoint. It:
    1. Finds all events with pending kanban tasks (or in curation_complete)
    2. Polls each task's status on the kanban board
    3. Updates stage status in kanban_task_sync
    4. When gate conditions are met, spawns the next stage's kanban task
    5. When all stages done, marks the event as ready_for_review

    Call this from a cron job every 30–60 seconds.
    """
    result = kanban_sync.advance_all(db)
    return PollerAdvanceResponse(**result)


@router.get("/kanban/status/{event_id}", response_model=EventKanbanStatus)
def event_kanban_status(
    event_id: str,
    db: SASession = Depends(get_db),
    _=Depends(_check_internal_key),
) -> EventKanbanStatus:
    """Return current kanban task status for all stages of an event."""
    try:
        eid = UUID(event_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid event_id")

    event = db.get(Event, eid)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    syncs = db.execute(
        select(KanbanTaskSync).where(KanbanTaskSync.event_id == eid)
    ).scalars().all()

    result = EventKanbanStatus(event_id=eid, title=event.title)
    for s in syncs:
        status_str = s.kanban_status or s.stage_status.value
        if s.stage.value == "curation":
            result.curation = status_str
        elif s.stage.value == "research":
            result.research = status_str
        elif s.stage.value == "coverage":
            result.coverage = status_str
        elif s.stage.value == "risk":
            result.risk = status_str
        elif s.stage.value == "writer":
            result.writer = status_str

    return result


# ------------------------------------------------------------------
# Curator event creation
# ------------------------------------------------------------------

class CuratorEventCreate(BaseModel):
    """Payload from the curator agent after normalising a submission."""
    title: str
    summary_pt: str
    entities: List[str] = []
    date_hint: str = "desconhecida"
    topics: List[str] = []
    claim_core: str = ""
    notes_for_researcher: str = ""


class CuratorEventResponse(BaseModel):
    """Response after curator creates an event."""
    event_id: UUID
    status: str
    spawned: dict = {}  # stage -> kanban_task_id


@router.post("/events/from-curator", response_model=CuratorEventResponse)
def create_event_from_curator(
    body: CuratorEventCreate,
    db: SASession = Depends(get_db),
    _=Depends(_check_internal_key),
) -> CuratorEventResponse:
    """
    Create an event from the curator's normalised output.

    This is called by the curator agent after it completes its investigation.
    The event is created in curation_complete status, which triggers the
    poller to spawn research + coverage tasks.

    The curator should include the event JSON in its task summary output.
    """
    # Create the event
    event = Event(
        title=body.title,
        summary=body.summary_pt,
        status=EventStatus.curation_complete,
        normalized_data={
            "entities": body.entities,
            "date_hint": body.date_hint,
            "topics": body.topics,
            "claim_core": body.claim_core,
            "notes_for_researcher": body.notes_for_researcher,
        },
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    logger.info("Created event %s from curator: %s", event.id, event.title)

    # Immediately spawn research + coverage tasks (curator is already done)
    actions = kanban_sync.advance_event(db, event)

    spawned = {}
    for a in actions:
        if a.get("action") == "spawned":
            spawned[a["stage"]] = a["task_id"]

    return CuratorEventResponse(
        event_id=event.id,
        status=event.status.value,
        spawned=spawned,
    )


# ------------------------------------------------------------------
# Re-trigger a specific stage (manual retry)
# ------------------------------------------------------------------

class RerunStageRequest(BaseModel):
    stage: StageNameEnum


@router.post("/events/{event_id}/rerun-stage")
def rerun_stage(
    event_id: UUID,
    body: RerunStageRequest,
    db: SASession = Depends(get_db),
    _=Depends(_check_internal_key),
) -> dict:
    """
    Manually re-run a failed stage by deleting its kanban_task_sync record
    and triggering the advance logic to re-spawn the task.
    """
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    stage_model = StageName(body.stage.value)

    # Delete existing sync record for this stage
    sync = db.execute(
        select(KanbanTaskSync).where(
            KanbanTaskSync.event_id == event_id,
            KanbanTaskSync.stage == stage_model,
        )
    ).scalar_one_or_none()

    if sync:
        db.delete(sync)
        db.commit()

    # Reset event status to the appropriate pending state
    if stage_model == StageName.research:
        event.status = EventStatus.curation_complete
    elif stage_model == StageName.risk:
        event.status = EventStatus.research_complete
    elif stage_model == StageName.writer:
        event.status = EventStatus.risk_complete
    db.commit()

    # Trigger advance to re-spawn
    actions = kanban_sync.advance_event(db, event)

    return {
        "event_id": str(event_id),
        "rerun_stage": body.stage.value,
        "actions": actions,
    }