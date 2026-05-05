FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY services/scraper-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared layer (modular monolith — shared models, utils)
COPY shared ./shared

# Scraper service files
COPY services/scraper-service/app ./app
COPY services/scraper-service/scraper ./scraper
COPY services/scraper-service/tasks ./tasks
COPY services/scraper-service/tests ./tests
COPY services/scraper-service/pytest.ini ./pytest.ini

ENV PYTHONPATH=/app
ENV SCRAPY_SETTINGS_MODULE=scraper.settings

# Default: run FastAPI API server
# Override CMD in docker-compose for Celery worker
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005"]
