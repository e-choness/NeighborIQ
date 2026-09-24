# Build: install wheels into a virtualenv (no compilers; every dependency ships a wheel)
FROM python:3.14-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1
RUN python -m venv /opt/venv
COPY shared/requirements.txt ./shared/requirements.txt
COPY services/api/requirements.txt ./services/api/requirements.txt
RUN /opt/venv/bin/pip install --only-binary=:all: -r services/api/requirements.txt

# Runtime: no extra OS packages, non-root
FROM python:3.14-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY shared ./shared
COPY services/api/app ./app
COPY services/api/tests ./tests
COPY services/api/pytest.ini ./pytest.ini

ENV PATH=/opt/venv/bin:$PATH PYTHONPATH=/app PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER app
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
