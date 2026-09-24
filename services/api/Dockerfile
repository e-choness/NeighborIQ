# Multi-stage build
FROM python:3.11-slim AS builder

WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY shared/requirements.txt ./shared/requirements.txt
COPY services/api/requirements.txt ./services/api/requirements.txt
RUN pip install --user --no-cache-dir -r services/api/requirements.txt

FROM python:3.11-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /root/.local /root/.local

COPY shared ./shared
COPY services/api/app ./app
COPY services/api/tests ./tests
COPY services/api/pytest.ini ./pytest.ini

ENV PYTHONPATH=/app PATH=/root/.local/bin:$PATH
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
