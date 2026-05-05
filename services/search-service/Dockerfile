FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Build context is project root
COPY services/search-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared module (modular monolith)
COPY shared ./shared

# Service files
COPY services/search-service/app ./app
COPY services/search-service/main.py ./main.py
COPY services/search-service/tests ./tests
COPY services/search-service/pytest.ini ./pytest.ini

ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
