"""Submission API endpoints for PT Media Observatory."""

from uuid import UUID
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from ..database import SessionLocal
from .. import models, schemas, security

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/submissions/", response_model=schemas.SubmissionRead, status_code=status.HTTP_201_CREATED)
async def create_submission(
    sub_in: schemas.SubmissionCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(security.get_current_user),
):
    """Create a new submission linked to the authenticated user."""
    # Create submission record
    db_submission = models.SubmittedItem(
        user_id=current_user["sub"],
        url=sub_in.url,
        text_content=sub_in.text_content,
        topic_hint=sub_in.topic_hint,
        notes=sub_in.notes,
    )
    db.add(db_submission)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Unable to create submission"
        )
    db.refresh(db_submission)
    return db_submission


@router.get("/submissions/", response_model=List[schemas.SubmissionRead])
async def list_submissions(
    db: Session = Depends(get_db),
    current_user: dict = Depends(security.get_current_user),
):
    """List all submissions for the authenticated user."""
    return (
        db.query(models.SubmittedItem)
        .filter(models.SubmittedItem.user_id == current_user["sub"])
        .all()
    )


@router.get("/submissions/{sub_id}", response_model=schemas.SubmissionRead)
async def get_submission(
    sub_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(security.get_current_user),
):
    """Get a specific submission by ID."""
    db_submission = (
        db.query(models.SubmittedItem)
        .filter(models.SubmittedItem.id == sub_id)
        .first()
    )
    if not db_submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    return db_submission


@router.put("/submissions/{sub_id}", response_model=schemas.SubmissionRead)
async def update_submission(
    sub_id: UUID,
    sub_in: schemas.SubmissionUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(security.get_current_user),
):
    """Update a submission."""
    db_submission = (
        db.query(models.SubmittedItem)
        .filter(models.SubmittedItem.id == sub_id)
        .first()
    )
    if not db_submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    # Optional: enforce ownership check here
    for field, value in sub_in.dict(exclude_unset=True).items():
        setattr(db_submission, field, value)
    db.commit()
    db.refresh(db_submission)
    return db_submission


@router.delete("/submissions/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_submission(
    sub_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(security.get_current_user),
):
    """Delete a submission."""
    db_submission = (
        db.query(models.SubmittedItem)
        .filter(models.SubmittedItem.id == sub_id)
        .first()
    )
    if not db_submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Submission not found")
    db.delete(db_submission)
    db.commit()
    return  # 204 No Content