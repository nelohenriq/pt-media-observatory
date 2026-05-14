"""Database configuration and engine for PT Media Observatory."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import Base from models so all tables are registered on the same Base instance.
# models.py does NOT import from database.py, so this is safe (no circular import).
from .models import Base

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/ptmedia",
)

# Create engine
_engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


def get_db():
    """FastAPI dependency that yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables() -> None:
    """
    Create all tables registered on Base.

    This imports models (registering their tables on Base.metadata) then
    creates any tables that don't exist yet.
    """
    # Import all models to ensure they are registered on Base.metadata
    from . import models  # noqa: F401
    Base.metadata.create_all(bind=_engine)