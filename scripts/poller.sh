#!/usr/bin/env bash
# PT Media Observatory — Pipeline Poller
# Advances the kanban pipeline by polling kanban task statuses
# and spawning next stages when gate conditions are met.
#
# Usage: ./scripts/poller.sh
# Run via cron: */1 * * * * /teamspace/.../poller.sh
set -euo pipefail

INTERNAL_KEY="${INTERNAL_API_KEY:-dev-internal-key}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"

response=$(curl -s -X POST "${BACKEND_URL}/internal/kanban/advance" \
  -H "Content-Type: application/json" \
  -H "X-Internal-Key: ${INTERNAL_KEY}")

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) poller: ${response}"
