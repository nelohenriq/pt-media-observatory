#!/bin/bash
# PT Media Observatory — Start all services
# Usage: ./scripts/start-all.sh

set -e
cd /teamspace/studios/this_studio/workspace/pt-media-observatory

echo "=== Starting PostgreSQL ==="
docker run -d \
  --name ptmedia-postgres \
  --restart unless-stopped \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=examplepassword \
  -e POSTGRES_DB=ptmedia \
  -p 127.0.0.1:5432:5432 \
  -v ptmedia_pgdata:/var/lib/postgresql/data \
  postgres:16-alpine

# Wait for postgres to be ready
echo "Waiting for PostgreSQL..."
for i in $(seq 1 30); do
  if docker exec ptmedia-postgres pg_isready -U postgres >/dev/null 2>&1; then
    echo "PostgreSQL ready"
    break
  fi
  sleep 1
done

echo "=== Starting backend ==="
DATABASE_URL=postgresql://postgres:examplepassword@localhost:5432/ptmedia \
JWT_SECRET=test-secret-key \
INTERNAL_API_KEY=dev-internal-key \
python3 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

echo "Backend PID: $BACKEND_PID"
sleep 5

# Verify
if curl -sf http://localhost:8000/health >/dev/null; then
  echo "Backend ready at http://localhost:8000"
else
  echo "WARNING: Backend may not be ready"
fi

echo "=== Ready ==="
echo "Backend: http://localhost:8000"
echo "Health:  curl http://localhost:8000/health"
echo "Poll:    curl -X POST http://localhost:8000/internal/kanban/advance -H 'X-Internal-Key: dev-internal-key'"