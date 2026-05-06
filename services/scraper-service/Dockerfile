# Multi-stage build
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY services/scraper-service/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

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
COPY services/scraper-service/app ./app
COPY services/scraper-service/scraper ./scraper
COPY services/scraper-service/tasks ./tasks
COPY services/scraper-service/tests ./tests
COPY services/scraper-service/pytest.ini ./pytest.ini

ENV PYTHONPATH=/app PATH=/root/.local/bin:$PATH
ENV SCRAPY_SETTINGS_MODULE=scraper.settings
EXPOSE 8005
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8005/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
