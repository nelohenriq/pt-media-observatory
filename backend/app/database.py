"""Database configuration and engine for PT Media Observatory."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Pull DB URL from environment; fallback to local PostgreSQL if not set
import os
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost/pt_media_observatory")

# Create engine - using asyncpg driver for async support (compatible with FastAPI)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10,
    echo=False,  # Set to True for SQL debug logging
)

# SessionLocal for request-scoped sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()