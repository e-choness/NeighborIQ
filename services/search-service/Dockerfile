# Multi-stage build (Phase 7A)
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     libpq-dev     && rm -rf /var/lib/apt/lists/*

COPY services/search-service/requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends     libpq5     curl     && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local

# Copy application code
COPY shared ./shared
COPY services/search-service/app ./app
COPY services/search-service/tests ./tests

ENV PYTHONPATH=/app PATH=/root/.local/bin:$PATH
EXPOSE 8004
HEALTHCHECK --interval=10s --timeout=3s --retries=3     CMD curl -f http://localhost:8004/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004"]
