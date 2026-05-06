# Getting Started Guide

## Prerequisites

Ensure you have the following installed:

- **Docker Desktop** (includes Docker and Docker Compose v2) or **Docker + Docker Compose v2.20+**
- **Git** (version 2.40+)
- **Browser** (Firefox, Chrome, or Safari for testing frontend)

For detailed setup, visit:
- [Docker Install](https://docs.docker.com/get-docker/)
- [Docker Compose Install](https://docs.docker.com/compose/install/)

---

## Repository Clone & Initial Setup

```bash
# Clone the repository
git clone https://github.com/e-choness/neighboriq.git
cd NeighborIQ

# Verify Docker is running
docker --version
docker-compose --version

# Create .env file (optional — uses defaults if omitted)
# See Environment Variables section below
```

---

## Directory Structure Overview

```
NeighborIQ/
├── services/                  # 7 FastAPI services
│   ├── api-gateway/
│   ├── auth-service/
│   ├── house-api-service/
│   ├── search-service/
│   ├── ai-insights-service/
│   ├── scraper-service/
│   └── portfolio-service/
├── frontend/                  # Vue 3 SPA
│   ├── src/
│   ├── public/
│   ├── index.html
│   └── vite.config.ts
├── shared/                    # Shared Python library
│   ├── database/
│   ├── models/
│   ├── cache/
│   └── utils/
├── migrations/                # Alembic DB migrations
├── docker-compose.yml         # Development configuration
├── docker-compose.prod.yml    # Production (optional overlay)
├── README.md
└── docs/                      # Documentation
```

---

## Infrastructure Services

These services are infrastructure dependencies (no custom code):

| Service | Image | Port | Purpose | Health Check |
|---------|-------|------|---------|--------------|
| **postgres** | `postgis/postgis:15-3.4-alpine` | 5432 | Primary database with geo-spatial support | `pg_isready -U root` |
| **redis** | `redis:7-alpine` | 6379 | Cache & Celery broker | `redis-cli ping` |
| **elasticsearch** | `docker.elastic.co/elasticsearch/elasticsearch:8.11.0` | 9200 | Full-text search index | `curl -f http://localhost:9200/_cluster/health` |
| **nginx** | (frontend only) | 80 | Static file serving & reverse proxy | HTTP 200 response |

---

## Application Services Port Map

| Service | Container Port | Host Port | Description |
|---------|----------------|-----------|-------------|
| **api-gateway** | 8000 | 8000 | Request boundary, JWT auth, rate limiting |
| **auth-service** | 8000 | 8001 | User registration/login, JWT generation |
| **house-api-service** | 8000 | 8002 | Property CRUD, filtering, pagination |
| **ai-insights-service** | 8000 | 8003 | ML predictions, Celery worker tasks |
| **search-service** | 8000 | 8004 | Elasticsearch full-text search |
| **scraper-service** | 8005 | 8005 | Data ingestion control API |
| **portfolio-service** | 8000 | 8006 | User saved houses / watchlist |
| **frontend** | 80 | 80 | Vue 3 SPA (Nginx) |

---

## Starting the Full Stack

### Option 1: Start Everything (Recommended for First Run)

```bash
# Start all services and wait for health checks
docker-compose up -d

# Watch startup progress
docker-compose logs -f

# Verify all services are healthy
docker-compose ps
```

Expected output:
```
NAME                    STATUS
postgres                healthy
redis                   healthy
elasticsearch           healthy
api-gateway             running
auth-service            running
house-api-service       running
search-service          running
ai-insights-service     running
scraper-service         running
portfolio-service       running
scraper-worker          running
scraper-beat            running
ai-insights-worker      running
ai-insights-beat        running
frontend                running
```

### Option 2: Start with Dependencies Only (For Backend Development)

```bash
# Start only infrastructure (database, cache, search)
docker-compose up -d postgres redis elasticsearch

# Then start individual services as needed
docker-compose up -d api-gateway auth-service house-api-service
```

---

## Access the Application

Once all services are healthy:

- **Frontend (Vue SPA)** — http://localhost/ (or http://localhost:80)
- **API Gateway Swagger** — http://localhost:8000/docs
- **Auth Service API** — http://localhost:8001/docs
- **House API** — http://localhost:8002/docs
- **Search API** — http://localhost:8004/docs
- **Elasticsearch** — http://localhost:9200 (raw JSON API)
- **Redis CLI** — `docker-compose exec redis redis-cli`

---

## Environment Variables Reference

Create a `.env` file in the project root to override defaults. All services read from this file.

### Shared Environment Variables

```env
# Database (all services use this)
DATABASE_URL=postgresql+asyncpg://root:root@postgres:5432/house_discovery
REDIS_URL=redis://redis:6379/0

# Frontend (Nginx)
VITE_API_BASE_URL=http://localhost:8000
```

### Service-Specific

#### API Gateway (port 8000)
```env
AUTH_SERVICE_URL=http://auth-service:8000
HOUSE_SERVICE_URL=http://house-api-service:8000
SEARCH_SERVICE_URL=http://search-service:8000
PORTFOLIO_SERVICE_URL=http://portfolio-service:8000
AI_INSIGHTS_SERVICE_URL=http://ai-insights-service:8000
CORS_ORIGINS=http://localhost:5173,http://localhost:80
```

#### Auth Service (port 8001)
```env
SECURE_COOKIES=0  # Set to 1 for production (HTTPS required)
```

#### AI Insights Service (port 8003)
```env
SCRAPER_DATABASE_URL=postgresql://root:root@postgres:5432/house_discovery
CELERY_BROKER_URL=redis://redis:6379/2
NARRATIVE_PROVIDER=local  # or openai, azure
MODEL_PATH=/app/models/price_prediction.joblib
```

#### Scraper Service (port 8005)
```env
CELERY_BROKER_URL=redis://redis:6379/2
SCRAPY_SETTINGS_MODULE=scraper.settings
```

#### Search Service (port 8004)
```env
ELASTICSEARCH_URL=http://elasticsearch:9200
```

---

## Database Migrations

Alembic manages schema migrations. Migrations run automatically on service startup, but you can run them manually:

```bash
# View migration history
docker-compose exec api-gateway python -m alembic history

# Upgrade to latest revision
docker-compose exec api-gateway python -m alembic upgrade head

# Create a new migration (if you modify shared/models/*.py)
docker-compose exec api-gateway python -m alembic revision --autogenerate -m "add new column"

# Downgrade to previous revision (rarely needed)
docker-compose exec api-gateway python -m alembic downgrade -1
```

---

## Frontend Development (Vite Dev Server)

For frontend development with hot module reloading:

### Option 1: Via Docker (Recommended)

```bash
# Terminal 1: Start backend services
docker-compose up -d api-gateway auth-service

# Terminal 2: Start Vite dev server in frontend container
docker-compose exec frontend npm run dev

# Frontend accessible at http://localhost:5173
```

### Option 2: Locally (Node.js Required)

```bash
# Install dependencies
cd frontend
npm install

# Start dev server (auto-proxies /api to http://localhost:8000)
npm run dev

# Accessible at http://localhost:5173
```

---

## Useful Docker Compose Commands

### Viewing Logs

```bash
# Tail logs from all services
docker-compose logs -f

# Tail logs from one service
docker-compose logs -f auth-service

# View last 100 lines
docker-compose logs --tail=100 auth-service

# Watch specific container in real-time
docker-compose logs -f --follow auth-service
```

### Executing Commands in Containers

```bash
# Run Python interactively in a service
docker-compose exec auth-service python

# Run a test in a service
docker-compose exec auth-service python -m pytest tests/ -v

# Connect to database
docker-compose exec postgres psql -U root -d house_discovery

# Access Redis CLI
docker-compose exec redis redis-cli
```

### Stopping & Restarting

```bash
# Stop all services (preserves data)
docker-compose down

# Stop and remove volumes (destroys data)
docker-compose down -v

# Restart one service
docker-compose restart auth-service

# Rebuild a service image (after code changes)
docker-compose up -d --build auth-service
```

### Cleanup

```bash
# Remove unused Docker images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove all containers, images, volumes (total reset)
docker system prune -a --volumes
```

---

## Running Tests

**Important**: All tests must run via Docker. Never run `pytest` locally on your host machine.

```bash
# Run full test suite (all services with test profile)
docker-compose --profile test up --abort-on-container-exit

# Run tests for specific service
docker-compose --profile test up test-auth-service --abort-on-container-exit

# Run with verbose output
docker-compose --profile test up -f docker-compose.yml test-house-api-service

# After tests, view coverage
docker-compose logs test-auth-service | grep coverage
```

**Test Services Available** (with `--profile test`):
- `test-api-gateway`
- `test-auth-service`
- `test-house-api-service`
- `test-search-service`
- `test-portfolio-service`
- `test-ai-insights-service`
- `test-scraper-service`
- `test-data-layer`
- `test-frontend-build`

---

## Production Compose (Optional)

For production-like deployments, overlay `docker-compose.prod.yml`:

```bash
# Start with production settings
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Environment changes:
# - SECURE_COOKIES=1 (HTTPS required)
# - Multiple API Gateway instances for load balancing
# - Nginx reverse proxy with TLS termination
```

---

## Common Development Workflows

### Adding a New Database Column

```bash
# 1. Modify the SQLAlchemy model (shared/models/*.py)
# 2. Create a migration
docker-compose exec api-gateway python -m alembic revision --autogenerate -m "add user_status column"

# 3. Review the migration file
vi migrations/alembic/versions/*.py

# 4. Apply it
docker-compose exec api-gateway python -m alembic upgrade head

# 5. Verify in database
docker-compose exec postgres psql -U root -d house_discovery -c "\d auth_users"
```

### Testing a Service in Isolation

```bash
# Start only the service and its dependencies
docker-compose up -d postgres redis api-gateway auth-service

# Run tests
docker-compose exec auth-service python -m pytest tests/test_auth.py -v

# Tail logs
docker-compose logs -f auth-service
```

### Debugging a Crashing Service

```bash
# Check why it crashed
docker-compose logs auth-service

# Look for last error message and traceback
# Common issues: missing env var, DB connection fail, missing import

# Restart with verbose output
docker-compose up auth-service  # (don't use -d to see real-time output)
```

---

## Troubleshooting

### Port Already in Use

**Error**: `bind: address already in use`

**Solution**:
```bash
# Find process using port 8000
lsof -i :8000

# Kill process
kill -9 <PID>

# Or use a different port in docker-compose.yml
```

### Postgres Healthcheck Timeout

**Error**: `postgres: service "postgres" lacks a healthcheck`

**Solution**: Wait longer or check Postgres logs:
```bash
docker-compose logs postgres

# Usually: "ERROR: role "root" does not exist"
# Reset database: docker-compose down -v && docker-compose up -d
```

### Elasticsearch Out of Memory

**Error**: `exception [out_of_memory_heap_space]`

**Solution**: Increase JVM heap in docker-compose.yml:
```yaml
elasticsearch:
  environment:
    - ES_JAVA_OPTS=-Xms1g -Xmx1g  # Increase from default 512m
```

---

## Next Steps

- **Backend Development**: See individual service docs in `/docs/services/`
- **Frontend Development**: See [Frontend Overview](../frontend/overview.md)
- **Testing**: See [Testing Guide](./testing.md)
- **Production Deployment**: See [DEPLOYMENT.md](../DEPLOYMENT.md)
