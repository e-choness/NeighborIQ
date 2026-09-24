# Runs shared/tests: analytics, calculator parity fixtures, migrations round-trip.
# Build context is the repository root.
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY shared/requirements.txt shared/requirements.txt
COPY shared/tests/requirements.txt shared/tests/requirements.txt
RUN pip install --no-cache-dir -r shared/tests/requirements.txt

COPY shared ./shared
COPY migrations ./migrations
# Cash-flow fixtures shared with the docs' JavaScript calculator
COPY docs/.vitepress/theme/lib/cashflow.fixtures.json ./docs/.vitepress/theme/lib/cashflow.fixtures.json

ENV PYTHONPATH=/app

CMD ["pytest", "shared/tests", "-v", "--tb=short"]
