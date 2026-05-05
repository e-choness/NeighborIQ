FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Build context is project root
COPY services/test-data-layer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared layer and tests
COPY shared ./shared
COPY shared/tests ./tests
COPY migrations ./migrations
COPY services/test-data-layer/pytest.ini ./pytest.ini

ENV PYTHONPATH=/app

CMD ["pytest", "tests/", "-v", "--tb=short"]
