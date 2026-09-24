# Multi-stage build
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY shared/requirements.txt ./shared/requirements.txt
COPY services/ingestion-worker/requirements.txt ./services/ingestion-worker/requirements.txt
RUN pip install --user --no-cache-dir -r services/ingestion-worker/requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local

# Copy application code
COPY shared ./shared
COPY services/ingestion-worker/scraper ./scraper
COPY services/ingestion-worker/tasks ./tasks
COPY services/ingestion-worker/ingestion ./ingestion
# Ops image: also runs `alembic upgrade head` (migrate) and the data loaders (bootstrap)
COPY migrations ./migrations
COPY data ./data
COPY services/ingestion-worker/tests ./tests
COPY services/ingestion-worker/pytest.ini ./pytest.ini

ENV PYTHONPATH=/app PATH=/root/.local/bin:$PATH DATA_DIR=/app/data
ENV SCRAPY_SETTINGS_MODULE=scraper.settings
# Celery worker for the scraper queue (no HTTP). The same image runs
# `alembic upgrade head` (migrate) and `python -m ingestion` (bootstrap).
CMD ["celery", "-A", "tasks.celery_app", "worker", "--loglevel=info", "-Q", "scraper"]
