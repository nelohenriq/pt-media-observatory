# Multi-stage build for FastAPI backend
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install poetry or pip-tools? Use simple pip
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser

# Copy runtime dependencies and code
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin
COPY ./app ./app

# Set environment
ENV PYTHONPATH=/app
ENV UVICORN_WORKERS=2
ENV LOG_LEVEL=info

# Expose port
EXPOSE 8000

# Run as non-root user
USER appuser

# Healthcheck command
HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=5 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Start uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]