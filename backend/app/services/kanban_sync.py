"""
Kanban synchronisation service.

This module bridges the Hermes Kanban board with the PT Media Observatory
pipeline stages. It:

1. Tracks kanban task IDs per event/stage via KanbanTaskSync
2. Polls the kanban board for task status
3. Advances events through the pipeline when stages complete
4. Spawns the next kanban task when gate conditions are met

The canonical pipeline flow (matching pt-media-kanban-wiring.md §3):

    submission → curator task
                     ↓ event.status = curation_complete
              ┌──────┴──────┐
              ↓             ↓
       research task  coverage task    (created by backend on curation_complete)
              ↓             ↓
         both done     both done
              └──────┬──────┘
                     ↓
              risk task
                     ↓
               risk done
                     ↓
             writer task
                     ↓
              writer done
                     ↓
          event.status = ready_for_review
                     ↓
               human reviews
"""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session as SASession
from uuid import UUID

from ..models import (
    Base,
    Event,
    EventStatus,
    KanbanTaskSync,
    StageName,
    StageStatus,
)
from ..schemas import StageNameEnum, StageStatusEnum

logger = logging.getLogger("pt-media-observatory.kanban_sync")


# ------------------------------------------------------------------
# Hermes Kanban CLI wrappers
# ------------------------------------------------------------------

def _run_hermes(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Run a hermes kanban CLI command. Returns (exit_code, stdout, stderr)."""
    cmd = ["hermes", "kanban"] + args
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except FileNotFoundError:
        return -1, "", "hermes CLI not found"


def get_task_status(kanban_task_id: str) -> Optional[str]:
    """
    Query a single task's status from the kanban board.

    Returns one of: 'ready' | 'running' | 'done' | 'blocked' | 'archived' | None
    """
    code, stdout, _ = _run_hermes(["show", kanban_task_id, "--json"])
    if code != 0:
        return None
    try:
        data = json.loads(stdout)
        # Status lives at data["task"]["status"] for the --json output
        return data.get("task", {}).get("status")
    except (json.JSONDecodeError, KeyError):
        return None


def create_kanban_task(
    title: str,
    assignee: str,
    body: dict,
    parent_task_id: Optional[str] = None,
) -> Optional[str]:
    """
    Create a task on the kanban board and return its task_id.

    Returns None on failure.
    """
    cmd = [
        "create", title,
        "--body", json.dumps(body),
        "--assignee", assignee,
        "--max-runtime", "600",
        "--json",
    ]
    if parent_task_id:
        cmd.extend(["--parent", parent_task_id])

    code, stdout, stderr = _run_hermes(cmd, timeout=15)
    if code != 0:
        logger.warning("kanban create failed: %s", stderr.strip())
        return None
    try:
        data = json.loads(stdout)
        return data.get("id")
    except (json.JSONDecodeError, KeyError):
        return None


def get_curator_task_id(event_id: UUID) -> Optional[str]:
    """Find the curator kanban task for a given event by looking for a task body containing the event_id."""
    code, stdout, _ = _run_hermes(["list", "--json"])
    if code != 0:
        return None
    try:
        tasks = json.loads(stdout)
        for task in tasks:
            body = task.get("body", "")
            if str(event_id) in body and task.get("assignee") == "curator":
                return task.get("id")
    except (json.JSONDecodeError, KeyError):
        pass
    return None


# ------------------------------------------------------------------
# Stage gate logic
# ------------------------------------------------------------------

def _stage_from_str(s: str) -> StageName:
    """Convert schema StageNameEnum to model StageName."""
    mapping = {
        StageNameEnum.curation: StageName.curation,
        StageNameEnum.research: StageName.research,
        StageNameEnum.coverage: StageName.coverage,
        StageNameEnum.risk: StageName.risk,
        StageNameEnum.writer: StageName.writer,
    }
    return mapping.get(StageName(s), StageName.research)


def _status_from_kanban(kanban_status: str) -> StageStatus:
    """Map kanban task status to StageStatus."""
    mapping = {
        "done": StageStatus.succeeded,
        "ready": StageStatus.pending,
        "running": StageStatus.running,
        "blocked": StageStatus.pending,
        "archived": StageStatus.cancelled,
    }
    return mapping.get(kanban_status, StageStatus.pending)


def advance_event(db: SASession, event: Event) -> list[dict]:
    """
    Check and advance a single event through the pipeline.

    Returns a list of dicts describing what was done.
    """
    actions: list[dict] = []

    # ── 1. Curation complete → spawn research + coverage ──────────────────
    if event.status == EventStatus.curation_complete:
        research_sync = _get_sync(db, event.id, StageName.research)
        coverage_sync = _get_sync(db, event.id, StageName.coverage)

        spawned = False
        if research_sync is None:
            curator_tid = get_curator_task_id(event.id)
            rid = create_kanban_task(
                title=f"Research: {event.title[:80]}",
                assignee="researcher_pt",
                body={"event_id": str(event.id), "stage": "research"},
                parent_task_id=curator_tid,
            )
            if rid:
                _upsert_sync(db, event.id, StageName.research, rid, StageStatus.pending)
                actions.append({"action": "spawned", "stage": "research", "task_id": rid})
                logger.info("Spawned research task %s for event %s", rid, event.id)
                spawned = True

        if coverage_sync is None:
            curator_tid = curator_tid or get_curator_task_id(event.id)
            cid = create_kanban_task(
                title=f"Coverage check: {event.title[:80]}",
                assignee="coverage_analyzer",
                body={"event_id": str(event.id), "stage": "coverage"},
                parent_task_id=curator_tid,
            )
            if cid:
                _upsert_sync(db, event.id, StageName.coverage, cid, StageStatus.pending)
                actions.append({"action": "spawned", "stage": "coverage", "task_id": cid})
                logger.info("Spawned coverage task %s for event %s", cid, event.id)
                spawned = True

        if spawned:
            event.status = EventStatus.research_pending
            db.commit()
        elif research_sync and coverage_sync:
            # Tasks already exist — check if both are done
            if research_sync.stage_status == StageStatus.succeeded and \
               coverage_sync.stage_status == StageStatus.succeeded:
                # Both done — advance to allow risk stage to be triggered
                event.status = EventStatus.research_complete
                db.commit()
                _check_and_spawn_risk(db, event, actions)
                return actions  # risk check is done, don't re-poll

    # ── 2. Poll running stages and advance when done ───────────────────────
    all_syncs = _get_all_syncs(db, event.id)

    for sync in all_syncs:
        if sync.stage_status in (StageStatus.succeeded, StageStatus.failed):
            continue  # already terminal

        kanban_status = get_task_status(sync.kanban_task_id)
        if kanban_status is None:
            continue

        sync.kanban_status = kanban_status
        new_stage_status = _status_from_kanban(kanban_status)
        sync.stage_status = new_stage_status

        if new_stage_status == StageStatus.succeeded:
            _advance_event_on_stage_done(db, event, sync.stage, actions)
            db.commit()
            # Don't return — keep processing other syncs in case both research
            # and coverage just completed in the same cycle (risk needs both)

        elif new_stage_status == StageStatus.cancelled:
            # Task was archived — re-spawn it so the pipeline continues
            # (e.g. task timed out and was archived; we need a replacement)
            if sync.stage == StageName.risk:
                # Reset sync to pending and spawn replacement risk task
                sync.stage_status = StageStatus.pending
                db.flush()
                rid = create_kanban_task(
                    title=f"Risk review: {event.title[:80]}",
                    assignee="risk_reviewer",
                    body={"event_id": str(event.id), "stage": "risk"},
                )
                if rid:
                    sync.kanban_task_id = rid
                    sync.stage_status = StageStatus.pending
                    sync.kanban_status = None
                    actions.append({"action": "respawned", "stage": "risk", "task_id": rid})
                    logger.info("Respawned risk task %s for event %s after archive", rid, event.id)
                db.commit()

    # After polling all syncs, do a final check to spawn risk if both research
    # and coverage just completed (handles the case where the second stage
    # finished and this poll cycle is the first to notice both are done).
    # This also handles events stuck in coverage_complete because the
    # early-return in _advance_event_on_stage_done prevented risk spawning.
    research_sync = _get_sync(db, event.id, StageName.research)
    coverage_sync = _get_sync(db, event.id, StageName.coverage)
    if research_sync and coverage_sync:
        if research_sync.stage_status == StageStatus.succeeded and \
           coverage_sync.stage_status == StageStatus.succeeded:
            # Update event status to research_complete and spawn risk
            event.status = EventStatus.research_complete
            _check_and_spawn_risk(db, event, actions)
            db.commit()

    db.commit()
    return actions


def _advance_event_on_stage_done(
    db: SASession,
    event: Event,
    completed_stage: StageName,
    actions: list[dict],
) -> None:
    """Update event status and spawn the next stage after `completed_stage` finishes."""

    if completed_stage == StageName.research:
        event.status = EventStatus.research_complete
        _check_and_spawn_risk(db, event, actions)

    elif completed_stage == StageName.coverage:
        event.status = EventStatus.coverage_complete
        _check_and_spawn_risk(db, event, actions)

    elif completed_stage == StageName.risk:
        event.status = EventStatus.risk_complete
        _check_and_spawn_writer(db, event, actions)

    elif completed_stage == StageName.writer:
        event.status = EventStatus.ready_for_review
        actions.append({"action": "event_ready", "event_id": str(event.id)})
        logger.info("Event %s is ready for review", event.id)


def _check_and_spawn_risk(db: SASession, event: Event, actions: list[dict]) -> None:
    """Both research + coverage done → spawn risk_reviewer task."""
    research_sync = _get_sync(db, event.id, StageName.research)
    coverage_sync = _get_sync(db, event.id, StageName.coverage)

    if research_sync and coverage_sync:
        if research_sync.stage_status == StageStatus.succeeded and \
           coverage_sync.stage_status == StageStatus.succeeded:

            # Check risk not already spawned
            if _get_sync(db, event.id, StageName.risk) is None:
                rid = create_kanban_task(
                    title=f"Risk review: {event.title[:80]}",
                    assignee="risk_reviewer",
                    body={"event_id": str(event.id), "stage": "risk"},
                )
                if rid:
                    _upsert_sync(db, event.id, StageName.risk, rid, StageStatus.pending)
                    actions.append({"action": "spawned", "stage": "risk", "task_id": rid})
                    logger.info("Spawned risk task %s for event %s", rid, event.id)


def _check_and_spawn_writer(db: SASession, event: Event, actions: list[dict]) -> None:
    """Risk done → spawn writer_pt task."""
    risk_sync = _get_sync(db, event.id, StageName.risk)

    if risk_sync and risk_sync.stage_status == StageStatus.succeeded:
        if _get_sync(db, event.id, StageName.writer) is None:
            wid = create_kanban_task(
                title=f"Draft outputs: {event.title[:80]}",
                assignee="writer_pt",
                body={"event_id": str(event.id), "stage": "writer"},
            )
            if wid:
                _upsert_sync(db, event.id, StageName.writer, wid, StageStatus.pending)
                actions.append({"action": "spawned", "stage": "writer", "task_id": wid})
                logger.info("Spawned writer task %s for event %s", wid, event.id)


# ------------------------------------------------------------------
# DB helpers
# ------------------------------------------------------------------

def _get_sync(db: SASession, event_id: UUID, stage: StageName) -> Optional[KanbanTaskSync]:
    return db.execute(
        select(KanbanTaskSync).where(
            KanbanTaskSync.event_id == event_id,
            KanbanTaskSync.stage == stage,
        )
    ).scalar_one_or_none()


def _get_all_syncs(db: SASession, event_id: UUID) -> list[KanbanTaskSync]:
    return list(db.execute(
        select(KanbanTaskSync).where(KanbanTaskSync.event_id == event_id)
    ).scalars().all())


def _upsert_sync(
    db: SASession,
    event_id: UUID,
    stage: StageName,
    kanban_task_id: str,
    stage_status: StageStatus,
) -> KanbanTaskSync:
    existing = _get_sync(db, event_id, stage)
    if existing:
        existing.kanban_task_id = kanban_task_id
        existing.stage_status = stage_status
        db.commit()
        return existing
    sync = KanbanTaskSync(
        event_id=event_id,
        stage=stage,
        kanban_task_id=kanban_task_id,
        stage_status=stage_status,
    )
    db.add(sync)
    db.commit()
    db.refresh(sync)
    return sync


# ------------------------------------------------------------------
# Public API (called by the internal router)
# ------------------------------------------------------------------

def register_task(
    db: SASession,
    event_id: UUID,
    stage: StageNameEnum,
    kanban_task_id: str,
    stage_status: Optional[StageStatus] = None,
) -> KanbanTaskSync:
    """Register (or update) a kanban task ID for a pipeline stage.

    When stage_status is passed as 'succeeded', immediately advance the
    pipeline so downstream stages are triggered without waiting for the
    next poll cycle.
    """
    stage_model = _stage_from_str(stage.value)
    status = stage_status or StageStatus.pending
    sync = _upsert_sync(db, event_id, stage_model, kanban_task_id, status)
    logger.info(
        "Registered kanban task %s for event %s stage %s (status=%s)",
        kanban_task_id, event_id, stage.value, status.value,
    )

    # Immediately trigger pipeline advancement when a stage completes,
    # so next stages are spawned in the same API call that marks them done.
    if status == StageStatus.succeeded:
        event = db.get(Event, event_id)
        if event:
            actions: list[dict] = []
            _advance_event_on_stage_done(db, event, stage_model, actions)
            logger.info(
                "Stage %s completed for event %s — advanced to %s",
                stage.value, event_id, event.status,
            )
            db.commit()

    return sync


def advance_all(db: SASession) -> dict:
    """
    Poll all events that have pending kanban tasks and advance them.

    Called by POST /internal/poller/advance
    """
    # Find events that have kanban_task_sync records with non-terminal status
    pending_syncs = db.execute(
        select(KanbanTaskSync.stage_status, KanbanTaskSync.event_id)
        .where(KanbanTaskSync.stage_status.in_([StageStatus.pending, StageStatus.running]))
    ).all()

    event_ids = list(set(s.event_id for s in pending_syncs))

    # Also poll events in any non-terminal pipeline state —
    # the polling loop handles each status correctly, so we include all
    # intermediate states (research_pending, coverage_complete, risk_pending, etc.)
    non_terminal_statuses = [
        EventStatus.curation_complete,
        EventStatus.research_pending,
        EventStatus.coverage_complete,
        EventStatus.research_complete,
        EventStatus.risk_pending,
        EventStatus.risk_complete,
        # ready_for_review is terminal for the pipeline — skip it
    ]
    pipeline_events = db.execute(
        select(Event).where(Event.status.in_(non_terminal_statuses))
    ).scalars().all()
    event_ids.extend(e.id for e in pipeline_events)

    events_checked = 0
    all_actions: list[dict] = []
    errors: list[str] = []

    for event_id in event_ids:
        try:
            event = db.get(Event, event_id)
            if event is None:
                continue
            events_checked += 1
            actions = advance_event(db, event)
            all_actions.extend(actions)
        except Exception as e:
            logger.exception("Error advancing event %s", event_id)
            errors.append(f"event {event_id}: {str(e)}")

    return {
        "events_checked": events_checked,
        "tasks_spawned": [a for a in all_actions if a.get("action") == "spawned"],
        "events_advanced": [a for a in all_actions if a.get("action") != "spawned"],
        "errors": errors,
    }