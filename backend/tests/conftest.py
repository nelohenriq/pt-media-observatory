import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.models import Base

# ----------------------------------------------------------------------
# Test database strategy
# ----------------------------------------------------------------------
# We use an in-memory SQLite database for fast, isolated tests.
# The URL sqlite+pysqlite:///:memory: creates a temporary DB that lives
# only in RAM.  Tables are created fresh for each test run via
# Base.metadata.create_all().  This satisfies the "separate test database"
# requirement while keeping the test suite lightweight and not requiring
# any Docker services.
SQLALCHEMY_TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"

@pytest.fixture(scope="function")
async def async_session():
    """Provide a clean async database session for each test function."""
    test_engine = create_async_engine(
        SQLALCHEMY_TEST_DATABASE_URL, echo=False, future=True
    )
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False,
        autoflush=False, autocommit=False
    )
    # Create all tables defined in app.models
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        yield session
        # Any changes made by the test are rolled back to keep the DB clean
        await session.rollback()
    await test_engine.dispose()

@pytest.fixture
async def async_client():
    """HTTP client that runs in-process against the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client

@pytest.fixture
def auth_headers():
    """Return a dict containing a Bearer token for the test user."""
    token = "test_jwt_token"
    return {"Authorization": f"Bearer {token}"}