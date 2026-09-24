# Runs shared/tests: analytics, calculator parity fixtures, migrations round-trip.
# Build context is the repository root.
FROM python:3.14-slim
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app
COPY shared/requirements.txt shared/requirements.txt
COPY shared/tests/requirements.txt shared/tests/requirements.txt
RUN pip install --only-binary=:all: -r shared/tests/requirements.txt

COPY shared ./shared
COPY migrations ./migrations
# Cash-flow fixtures shared with the docs' JavaScript calculator
COPY docs/.vitepress/theme/lib/cashflow.fixtures.json ./docs/.vitepress/theme/lib/cashflow.fixtures.json

ENV PYTHONPATH=/app
CMD ["pytest", "shared/tests", "-v", "--tb=short", "-p", "no:cacheprovider"]
