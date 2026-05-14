"""Celery stage runner — executes pipeline stages as async tasks."""
import json
import logging
from uuid import UUID
from celery import Celery
from kombu import Exchange, Queue

from .llm_client import LLMClient
from ..core.state_machine import EventStatus, transition, is_drafting_allowed, can_transition
from ..database import SessionLocal
from .. import models as m

logger = logging.getLogger(__name__)

app = Celery("pt_observatory")
app.conf.update(
    broker_url="redis://localhost:6379/0",
    result_backend="redis://localhost:6379/0",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=600,
    task_soft_time_limit=540,
    worker_prefetch_multiplier=1,
    task_queues=[Queue("default", Exchange("default"), routing_key="default")],
)


def _get_event(event_id: UUID):
    db = SessionLocal()
    try:
        event = db.query(m.Event).filter(m.Event.id == event_id).first()
        if not event:
            raise ValueError(f"Event {event_id} not found")
        return event, db
    except:
        db.close()
        raise


def _transition_and_log(event_id: UUID, to_status: EventStatus, db):
    event = db.query(m.Event).filter(m.Event.id == event_id).first()
    old_status = EventStatus(event.status)
    new_status = transition(old_status, to_status)
    event.status = new_status.value
    db.commit()


@app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_curation(self, event_id: UUID, input_data: dict):
    """Normalize submission data."""
    llm = LLMClient()
    try:
        prompt = f"Normalize this submission into a structured event: {json.dumps(input_data)}"
        result = llm.chat([{"role": "user", "content": prompt}], json_mode=True)
        event, db = _get_event(event_id)
        if can_transition(EventStatus(event.status), EventStatus.CURATION_COMPLETE):
            _transition_and_log(event_id, EventStatus.CURATION_COMPLETE, db)
        return json.loads(result)
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        db.close()


@app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_research(self, event_id: UUID, input_data: dict):
    """Research a submission — search web, extract evidence."""
    llm = LLMClient()
    try:
        prompt = f"Research this event thoroughly. Find official documents, NGO reports, and articles. Return structured findings with evidence links: {json.dumps(input_data)}"
        result = llm.chat([{"role": "user", "content": prompt}], json_mode=True)
        event, db = _get_event(event_id)
        research = m.EventResearch(
            event_id=event_id,
            findings=json.loads(result),
            model_used=llm.model,
        )
        db.add(research)
        if can_transition(EventStatus(event.status), EventStatus.RESEARCH_COMPLETE):
            _transition_and_log(event_id, EventStatus.RESEARCH_COMPLETE, db)
        db.commit()
        return json.loads(result)
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        db.close()


@app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_coverage(self, event_id: UUID, input_data: dict):
    """Compare event against mainstream outlet coverage."""
    llm = LLMClient()
    try:
        prompt = f"Analyze mainstream Portuguese media coverage for this event. Identify which outlets covered it, with what framing, and any delays. Return structured data: {json.dumps(input_data)}"
        result = llm.chat([{"role": "user", "content": prompt}], json_mode=True)
        event, db = _get_event(event_id)
        if can_transition(EventStatus(event.status), EventStatus.COVERAGE_COMPLETE):
            _transition_and_log(event_id, EventStatus.COVERAGE_COMPLETE, db)
        db.commit()
        return json.loads(result)
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        db.close()


@app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_risk(self, event_id: UUID, input_data: dict):
    """Assess risk flags and scores for drafting gate."""
    llm = LLMClient()
    try:
        prompt = f"""Assess risk for this event. Return JSON with:
- reliability_score (0-5)
- undercoverage_score (0-5)
- flags: list of risk flags found
- blocking_flags: list of blocking risk flags
- rationale: explanation
Data: {json.dumps(input_data)}"""
        result = llm.chat([{"role": "user", "content": prompt}], json_mode=True)
        data = json.loads(result)
        event, db = _get_event(event_id)
        risk = m.EventRisk(
            event_id=event_id,
            flags=data.get("flags", []),
            reliability_score=data.get("reliability_score"),
            undercoverage_score=data.get("undercoverage_score"),
            blocking_flags=data.get("blocking_flags", []),
            rationale=data.get("rationale"),
            model_used=llm.model,
        )
        db.add(risk)

        if can_transition(EventStatus(event.status), EventStatus.RISK_COMPLETE):
            _transition_and_log(event_id, EventStatus.RISK_COMPLETE, db)

        if is_drafting_allowed(
            data.get("reliability_score"),
            data.get("undercoverage_score"),
            data.get("blocking_flags"),
        ):
            if can_transition(EventStatus.RISK_COMPLETE, EventStatus.WRITER_PENDING):
                _transition_and_log(event_id, EventStatus.WRITER_PENDING, db)
        else:
            if can_transition(EventStatus.RISK_COMPLETE, EventStatus.NEEDS_EDITOR_DECISION):
                _transition_and_log(event_id, EventStatus.NEEDS_EDITOR_DECISION, db)

        db.commit()
        return data
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        db.close()


@app.task(bind=True, max_retries=3, default_retry_delay=30)
def run_writer(self, event_id: UUID, input_data: dict):
    """Generate drafts (X thread, site card, newsletter)."""
    llm = LLMClient()
    try:
        prompt = f"Generate 3 draft formats for this event (x_thread, site_card, newsletter_snippet) with evidence references and uncertainty language: {json.dumps(input_data)}"
        result = llm.chat([{"role": "user", "content": prompt}], json_mode=True)
        data = json.loads(result)
        event, db = _get_event(event_id)
        for fmt in ["x_thread", "site_card", "newsletter_snippet"]:
            if fmt in data:
                draft = m.EventDraft(
                    event_id=event_id,
                    draft_type=fmt,
                    content=data[fmt].get("content", ""),
                    evidence_references=data[fmt].get("evidence_references", []),
                    uncertainty_language=data[fmt].get("uncertainty_language"),
                    model_used=llm.model,
                )
                db.add(draft)

        if can_transition(EventStatus(event.status), EventStatus.WRITER_COMPLETE):
            _transition_and_log(event_id, EventStatus.WRITER_COMPLETE, db)
        if can_transition(EventStatus.WRITER_COMPLETE, EventStatus.READY_FOR_REVIEW):
            _transition_and_log(event_id, EventStatus.READY_FOR_REVIEW, db)
        db.commit()
        return data
    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        db.close()