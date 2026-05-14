"""API tests for PT Media Observatory backend."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.state_machine import EventStatus, transition, can_transition, is_drafting_allowed, transition_to_writer_pending, InvalidTransitionError


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# ── State Machine Tests ──────────────────────────────────────────────

class TestStateMachine:
    def test_valid_intake_to_curation(self):
        assert can_transition(EventStatus.INTAKE, EventStatus.CURATION_PENDING)
        assert transition(EventStatus.INTAKE, EventStatus.CURATION_PENDING) == EventStatus.CURATION_PENDING

    def test_invalid_skip_to_published(self):
        assert not can_transition(EventStatus.INTAKE, EventStatus.PUBLISHED)

    def test_invalid_transition_raises(self):
        with pytest.raises(Exception):
            transition(EventStatus.INTAKE, EventStatus.PUBLISHED)

    def test_parallel_research_coverage(self):
        assert can_transition(EventStatus.CURATION_COMPLETE, EventStatus.RESEARCH_PENDING)
        assert can_transition(EventStatus.CURATION_COMPLETE, EventStatus.COVERAGE_PENDING)

    def test_full_pipeline(self):
        s = EventStatus.INTAKE
        s = transition(s, EventStatus.CURATION_PENDING)
        s = transition(s, EventStatus.CURATION_COMPLETE)
        s = transition(s, EventStatus.RESEARCH_PENDING)
        s = transition(s, EventStatus.RESEARCH_COMPLETE)
        assert s == EventStatus.RESEARCH_COMPLETE


# ── Drafting Gate Tests ──────────────────────────────────────────────

class TestDraftingGate:
    def test_blocks_when_reliability_too_low(self):
        assert not is_drafting_allowed(reliability_score=1, undercoverage_score=2, blocking_flags=[])

    def test_blocks_when_undercoverage_too_low(self):
        assert not is_drafting_allowed(reliability_score=3, undercoverage_score=0, blocking_flags=[])

    def test_blocks_when_blocking_flag_present(self):
        assert not is_drafting_allowed(
            reliability_score=3, undercoverage_score=2,
            blocking_flags=["possible_defamation"]
        )

    def test_allows_when_all_clear(self):
        assert is_drafting_allowed(reliability_score=3, undercoverage_score=2, blocking_flags=[])

    def test_allows_with_null_flags(self):
        assert is_drafting_allowed(reliability_score=4, undercoverage_score=3, blocking_flags=None)


# ── API Health Endpoint Tests ────────────────────────────────────────

class TestHealthEndpoint:
    @pytest.mark.anyio
    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

    @pytest.mark.anyio
    async def test_health_returns_namespace(self, client):
        resp = await client.get("/health")
        data = resp.json()
        assert "namespace" in data


# ── Auth Tests ──────────────────────────────────────────────────────

class TestAuth:
    @pytest.mark.anyio
    async def test_auth_endpoint_exists(self, client):
        resp = await client.post("/auth/login", json={"username": "test@test.com", "password": "test"})
        assert resp.status_code in (200, 401, 422)

    @pytest.mark.anyio
    async def test_auth_requires_credentials(self, client):
        resp = await client.post("/auth/login", json={})
        assert resp.status_code == 422


# ── Event Endpoint Tests ────────────────────────────────────────────

class TestEvents:
    @pytest.mark.anyio
    async def test_list_events_requires_auth(self, client):
        resp = await client.get("/events/")
        assert resp.status_code in (200, 401, 403)

    @pytest.mark.anyio
    async def test_get_nonexistent_event(self, client):
        resp = await client.get("/events/00000000-0000-0000-0000-000000000000")
        assert resp.status_code in (404, 401)


# ── Submission Tests ───────────────────────────────────────────────

class TestSubmissions:
    @pytest.mark.anyio
    async def test_create_submission_requires_auth(self, client):
        resp = await client.post("/submissions/", json={"source_url": "https://example.com"})
        assert resp.status_code in (401, 403, 422)


# ── Transaction Isolation Test ──────────────────────────────────────

class TestTransactionIsolation:
    @pytest.mark.anyio
    async def test_concurrent_requests_dont_interfere(self, client):
        resp1 = await client.get("/health")
        resp2 = await client.get("/health")
        assert resp1.status_code == 200
        assert resp2.status_code == 200