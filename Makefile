# ============================================================
# PT Media Observatory — Convenience Makefile
# ============================================================
# Simulates the CI pipeline locally.
#
# Usage:
#   make test       — run backend + frontend tests
#   make lint       — run all linters
#   make ci         — run lint + test (full CI simulation)
#   make build      — build Docker images
#   make up         — generate certs + start all services via docker compose
#   make down       — stop all services
#   make clean      — remove build artifacts and containers
# ============================================================

.PHONY: test lint ci build up down clean certs install

# ---- Full CI simulation ----
ci: lint test
	@echo "✅ CI simulation complete"

# ---- Testing ----
test: test-backend test-frontend
	@echo "✅ All tests passed"

test-backend:
	@echo "=== Running backend tests ==="
	cd backend && python -m pytest tests/ -v --asyncio-mode=auto $(ARGS)

test-frontend:
	@echo "=== Running frontend e2e tests ==="
	cd frontend && npm run test:e2e $(ARGS)

# ---- Linting ----
lint: lint-backend lint-frontend
	@echo "✅ All linters passed"

lint-backend:
	@echo "=== Linting backend (ruff) ==="
	cd backend && python -m ruff check . && python -m ruff format --check .

lint-backend-types:
	@echo "=== Type checking backend (mypy) ==="
	cd backend && python -m mypy app/ --show-error-codes

lint-frontend:
	@echo "=== Linting frontend (eslint) ==="
	cd frontend && npm run lint

# ---- Docker ----
build: certs
	docker compose build

build-backend:
	docker compose build backend

build-frontend:
	docker compose build frontend

certs:
	@echo "=== Generating self-signed TLS certificates ==="
	mkdir -p certs
	openssl req -x509 -nodes -newkey ec:<(openssl ecparam -name prime256v1) \
		-keyout certs/privkey.pem -out certs/fullchain.pem \
		-days 365 -subj "/CN=localhost" \
		-addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null || \
	openssl req -x509 -nodes -newkey rsa:2048 \
		-keyout certs/privkey.pem -out certs/fullchain.pem \
		-days 365 -subj "/CN=localhost"
	@echo "✅ Self-signed certs generated in ./certs/"

up: certs
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

# ---- Installation ----
install-backend:
	cd backend && pip install -r requirements.txt

install-backend-dev:
	cd backend && pip install -r requirements.txt && pip install pytest pytest-asyncio pytest-cov httpx ruff mypy

install-frontend:
	cd frontend && npm ci

install-playwright:
	cd frontend && npx playwright install --with-deps chromium

install: install-backend-dev install-frontend install-playwright
	@echo "✅ All dependencies installed"

# ---- Cleanup ----
clean:
	docker compose down -v --remove-orphans
	rm -rf frontend/dist frontend/node_modules/.cache
	find backend -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find backend -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Clean complete"
