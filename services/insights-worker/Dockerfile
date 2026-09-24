# Multi-stage build (Phase 7A)
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     libpq-dev     && rm -rf /var/lib/apt/lists/*

COPY shared/requirements.txt ./shared/requirements.txt
COPY services/insights-worker/requirements.txt ./services/insights-worker/requirements.txt
RUN pip install --user --no-cache-dir -r services/insights-worker/requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends     libpq5     curl     && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local

# Copy application code
COPY shared ./shared
COPY services/insights-worker/insights ./insights
COPY services/insights-worker/tasks ./tasks
COPY services/insights-worker/tests ./tests

ENV PYTHONPATH=/app PATH=/root/.local/bin:$PATH

# Celery worker for the insights and narratives queues (no HTTP)
CMD ["celery", "-A", "tasks.celery_app", "worker", "--loglevel=info", "-Q", "insights,narratives"]
