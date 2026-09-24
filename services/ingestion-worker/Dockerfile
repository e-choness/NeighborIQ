# Build: install wheels into a virtualenv (no compilers; every dependency ships a wheel)
FROM python:3.14-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN python -m venv /opt/venv
COPY shared/requirements.txt ./shared/requirements.txt
COPY services/ingestion-worker/requirements.txt ./services/ingestion-worker/requirements.txt
RUN /opt/venv/bin/pip install --only-binary=:all: -r services/ingestion-worker/requirements.txt

# Runtime: no extra OS packages, non-root
FROM python:3.14-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY shared ./shared
COPY services/ingestion-worker/scraper ./scraper
COPY services/ingestion-worker/tasks ./tasks
COPY services/ingestion-worker/ingestion ./ingestion
# Ops image: also runs `alembic upgrade head` (migrate) and the data loaders (bootstrap)
COPY migrations ./migrations
COPY data ./data
COPY services/ingestion-worker/tests ./tests
COPY services/ingestion-worker/pytest.ini ./pytest.ini
# Writable by the service: open-data download cache, Celery beat schedule
RUN mkdir -p /app/data/cache /app/state && chown -R app:app /app/data/cache /app/state

ENV PATH=/opt/venv/bin:$PATH PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data SCRAPY_SETTINGS_MODULE=scraper.settings
USER app
# Celery worker for the scraper queue (no HTTP). The same image runs
# `alembic upgrade head` (migrate) and `python -m ingestion` (bootstrap).
CMD ["celery", "-A", "tasks.celery_app", "worker", "--loglevel=info", "-Q", "scraper"]
