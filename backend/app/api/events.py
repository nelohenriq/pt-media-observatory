"""Event API endpoints for PT Media Observatory."""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..database import SessionLocal
from .. import models, schemas, security

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/events/", response_model=schemas.EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    event_in: schemas.EventCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(security.get_current_user),
):
    """Create a new event linked to a submitted item."""
    # Verify submission item exists
    submission = db.query(models.SubmittedItem).get(event_in.submitted_item_id)
    if not submission:
        raise HTTPException(status_code=404, detail="SubmittedItem not found")
    # Create event record
    db_event = models.Event(
        submitted_item_id=event_in.submitted_item_id,
        title=event_in.title,
        summary=event_in.summary,
        status=event_in.status,
        reliability_score=event_in.reliability_score or 0,
        undercoverage_score=event_in.undercoverage_score or 0,
        risk_flags=event_in.risk_flags or [],
        normalized_data=event_in.normalized_data,
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


@router.get("/events/", response_model=List[schemas.EventRead])
async def list_events(
    db: Session = Depends(get_db),
    current_user: dict = Depends(security.get_current_user),
):
    """List all events (public read-only for now)."""
    return db.query(models.Event).all()


@router.get("/events/{event_id}", response_model=schemas.EventRead)
async def get_event(
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(security.get_current_user),
):
    """Get a specific event by ID."""
    db_event = db.query(models.Event).get(event_id)
    if not db_event:
        raise HTTPException(status_code=404, detail="Event not found")
    return db_event