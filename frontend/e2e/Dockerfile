# Browser tests (Playwright + Chromium). Build context: repository root.
#   docker compose --profile test run --rm test-frontend-e2e
FROM mcr.microsoft.com/playwright:v1.63.0-noble
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
ENV CI=1
CMD ["npx", "playwright", "test"]
