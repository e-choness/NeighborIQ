FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Build context is project root — prefix all paths with service directory
COPY services/ai-insights-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY services/ai-insights-service/app ./app
COPY services/ai-insights-service/tests ./tests

# Copy openapi.json for contract testing
COPY services/ai-insights-service/openapi.json .

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]