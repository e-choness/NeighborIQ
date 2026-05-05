FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Build context is project root; copy service-specific requirements
COPY services/house-api-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared module (modular monolith shared layer)
COPY shared ./shared

# Copy migrations so alembic can run inside the container
COPY migrations ./migrations

# Copy service application files
COPY services/house-api-service/app ./app
COPY services/house-api-service/main.py ./main.py
COPY services/house-api-service/tests ./tests
COPY services/house-api-service/pytest.ini ./pytest.ini

# shared/ lives at /app/shared; PYTHONPATH=/app makes `from shared import ...` resolve correctly
ENV PYTHONPATH=/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
