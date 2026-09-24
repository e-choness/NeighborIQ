# Build: install wheels into a virtualenv (no compilers; every dependency ships a wheel)
FROM python:3.14-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN python -m venv /opt/venv
COPY shared/requirements.txt ./shared/requirements.txt
COPY services/insights-worker/requirements.txt ./services/insights-worker/requirements.txt
RUN /opt/venv/bin/pip install --only-binary=:all: -r services/insights-worker/requirements.txt

# Runtime: no extra OS packages, non-root
FROM python:3.14-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY shared ./shared
COPY services/insights-worker/insights ./insights
COPY services/insights-worker/tasks ./tasks
COPY services/insights-worker/tests ./tests
COPY services/insights-worker/pytest.ini ./pytest.ini
# Writable by the service: trained model, Celery beat schedule
RUN mkdir -p /app/models /app/state && chown -R app:app /app/models /app/state

ENV PATH=/opt/venv/bin:$PATH PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER app
# Celery worker for the insights and narratives queues (no HTTP)
CMD ["celery", "-A", "tasks.celery_app", "worker", "--loglevel=info", "-Q", "insights,narratives"]
