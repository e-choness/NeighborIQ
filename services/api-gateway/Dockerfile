FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Build context is project root; copy service-specific requirements
COPY services/api-gateway/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module (modular monolith shared layer)
COPY shared ./shared

# Copy service application files
COPY services/api-gateway/app ./app
COPY services/api-gateway/main.py ./main.py
COPY services/api-gateway/tests ./tests

# shared/ lives at /app/shared; PYTHONPATH=/app makes `from shared import ...` resolve correctly
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
