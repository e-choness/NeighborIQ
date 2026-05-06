# NeighborIQ

[![build](https://img.shields.io/github/actions/workflow/status/e-choness/neighboriq/ci-cd.yml?branch=main&style=flat-square)](https://github.com/e-choness/neighboriq/actions/workflows/ci-cd.yml)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/Python-3.11+-blue.svg?style=flat-square)](https://www.python.org/downloads/release/python-3110/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED.svg?style=flat-square)](https://docs.docker.com/compose/)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen.svg?style=flat-square)](CONTRIBUTING.md)

**NeighborIQ** is an AI-powered Canadian real estate intelligence platform. It combines microservices architecture with machine learning to deliver actionable neighborhood insights, price predictions, and investment analytics for Canadian residential markets.

![banner](./images/banner-wide.jpeg)

## At a Glance

- **🏘️ Data-Driven Insights** — Scrapy-powered data pipeline ingests listings from Canadian real estate markets into a unified database
- **🧠 ML-Powered Predictions** — XGBoost models predict property prices and rental yields with confidence intervals
- **🔍 Full-Text + Geo Search** — Elasticsearch indexes properties for multi-dimensional search (location, price, community); results cached in Redis
- **🔐 Enterprise Auth** — RS256 JWT tokens with refresh rotation, cookie-based session management, JWKS-aware middleware

## System Architecture

```mermaid
flowchart TD
    Frontend[Vue 3 Frontend<br/>Port 80]
    Nginx[Nginx Reverse Proxy]
    
    subgraph Services["API Services (FastAPI)"]
        Gateway["API Gateway<br/>Port 8000<br/>JWT Middleware + Rate Limit"]
        Auth["Auth Service<br/>Port 8001<br/>JWT + User Mgmt"]
        House["House API Service<br/>Port 8002<br/>Property CRUD"]
        Search["Search Service<br/>Port 8004<br/>ES + Caching"]
        Portfolio["Portfolio Service<br/>Port 8006<br/>Saved Houses"]
        AI["AI Insights Service<br/>Port 8003<br/>ML + Celery"]
        Scraper["Scraper Service<br/>Port 8005<br/>Data Ingestion"]
    end
    
    subgraph Data["Data & Infrastructure"]
        Postgres["PostgreSQL 15<br/>house_discovery<br/>+PostGIS"]
        Redis["Redis 7<br/>Caching + Celery"]
        ES["Elasticsearch 8.11<br/>Full-Text Index"]
    end
    
    subgraph Workers["Async Jobs"]
        CeleryWorker["Celery Worker<br/>Scrape + Insights"]
        CeleryBeat["Celery Beat<br/>Scheduler"]
    end
    
    Frontend --> Nginx
    Nginx --> Gateway
    Gateway --> Auth & House & Search & AI & Portfolio & Scraper
    
    Auth --> Postgres & Redis
    House --> Postgres & Redis
    Search --> ES & Redis
    AI --> Postgres & Redis
    Scraper --> Postgres
    Portfolio --> Postgres & Redis
    
    Scraper --> CeleryWorker
    AI --> CeleryWorker
    Scraper --> CeleryBeat
    AI --> CeleryBeat
    CeleryWorker --> Redis
    CeleryBeat --> Redis
    CeleryWorker --> Postgres & ES
```

## Technology Stack

```mermaid
mindmap
  root((NeighborIQ))
    Backend
      FastAPI 0.104+
      Python 3.11
      SQLAlchemy 2.0
      Pydantic V2
      asyncpg
    Infrastructure
      PostgreSQL 15
      PostGIS 3.4
      Redis 7
      Elasticsearch 8.11
      Nginx
    Data Pipeline
      Scrapy 2.10
      Celery 5.3
      XGBoost
      scikit-learn
    Frontend
      Vue 3
      TypeScript
      Tailwind CSS
      Pinia
      OpenLayers
      Vite
    DevOps
      Docker & Docker Compose
      GitHub Actions
      Trivy Security Scanning
```

## Quick Start

### Prerequisites

- Docker Desktop (or Docker + Docker Compose v2)
- Git
- ~15 min setup time

### Start the Full Stack

```bash
git clone https://github.com/e-choness/neighboriq.git
cd NeighborIQ

# Start all services (database, Redis, Elasticsearch, all APIs, frontend)
docker-compose up -d

# Wait for services to be healthy (~30-60 seconds)
docker-compose ps

# Tail logs to see startup progress
docker-compose logs -f
```

### Access the Application

- **Frontend (Vue SPA)** — http://localhost
- **API Gateway** — http://localhost:8000/docs (Swagger UI)
- **Auth Service** — http://localhost:8001/docs
- **House API Service** — http://localhost:8002/docs
- **Search Service** — http://localhost:8004/docs

### Run Tests

```bash
# Run the full test suite via Docker
docker-compose --profile test up --abort-on-container-exit
```

## Service Port Map

| Service | Port | Description |
|---------|------|-------------|
| **API Gateway** | 8000 | Request boundary, JWT middleware, rate limiting |
| **Auth Service** | 8001 | User registration/login, RS256 JWT, JWKS |
| **House API Service** | 8002 | Property/community CRUD, filtering, pagination |
| **AI Insights Service** | 8003 | ML price prediction, rental yield, Celery worker |
| **Search Service** | 8004 | Elasticsearch full-text + geo-spatial search |
| **Scraper Service** | 8005 | Data ingestion control API, Scrapy pipeline |
| **Portfolio Service** | 8006 | User saved houses / watchlist |
| **Frontend (Nginx)** | 80 | Vue 3 SPA |

## Documentation

Comprehensive documentation is available in the `/docs` directory:

### Architecture & Design
- [**System Architecture**](docs/architecture/overview.md) — Microservices topology, request lifecycle, service responsibilities
- [**Data Models**](docs/architecture/data-models.md) — Database schema (ER diagram), SQLAlchemy ORM models

### Service Documentation
- [**API Gateway**](docs/services/api-gateway.md) — JWT middleware, JWKS caching, rate limiting, routing
- [**Auth Service**](docs/services/auth-service.md) — User authentication, RS256 token generation, cookie strategy
- [**House API Service**](docs/services/house-api-service.md) — Property API, filtering, pagination, price history
- [**Search Service**](docs/services/search-service.md) — Elasticsearch indexing, geo-spatial search, Redis caching
- [**AI Insights Service**](docs/services/ai-insights-service.md) — ML pipeline (XGBoost), Celery tasks, narrative generation
- [**Scraper Service**](docs/services/scraper-service.md) — Scrapy spiders, pipeline stages, task scheduling
- [**Portfolio Service**](docs/services/portfolio-service.md) — Saved houses, watchlist management

### Frontend & Development
- [**Frontend Overview**](docs/frontend/overview.md) — Vue 3 SPA architecture, routing, components, state management
- [**Getting Started Guide**](docs/development/getting-started.md) — Docker Compose setup, environment variables, common commands
- [**Testing Guide**](docs/development/testing.md) — Docker-based testing strategy, CI/CD pipeline, test profiles

## Development Workflow

### Local Development

```bash
# Start the stack in development mode
docker-compose up -d

# View logs for a service
docker-compose logs -f auth-service

# Run migrations (if needed)
docker-compose exec api-gateway python -m alembic upgrade head

# Execute commands in a container
docker-compose exec auth-service python -m pytest -v
```

### Important Note on Testing

⚠️ **All tests must run via Docker Compose.** Never run `pytest` or `uvicorn` directly on your host machine. Use:

```bash
# Correct: Docker-based testing
docker-compose --profile test up --abort-on-container-exit

# Incorrect: Do not run locally
# pytest services/auth-service/tests/  ❌
# uvicorn services/auth-service.main  ❌
```

### Code Style

This project uses **Black** for formatting and **isort** for imports. The CI pipeline enforces these checks.

```bash
# Format code (runs in service container via Docker)
docker-compose exec auth-service black app/
docker-compose exec auth-service isort app/
```

## Architecture Highlights

### Single Responsibility Microservices

Each service owns its domain and data:

- **Auth Service** — user identity, tokens
- **House API Service** — property catalog
- **Search Service** — search indexing and retrieval
- **AI Insights Service** — price predictions, rental analysis
- **Scraper Service** — data ingestion
- **Portfolio Service** — user saved houses
- **API Gateway** — security boundary (authentication, authorization, rate limiting)

### Shared Infrastructure

All services connect to a single PostgreSQL database (`house_discovery`) with domain-prefixed tables (`house_*`, `auth_*`, `portfolio_*`). This design avoids the operational complexity of database-per-service while maintaining clear boundaries.

### Async-First Backend

FastAPI with `asyncpg` enables high concurrency. Celery workers handle long-running tasks (ML inference, scraping).

### Production-Ready Authentication

RS256 JWT tokens with JWKS endpoint. Gateway caches JWKS for 5 minutes to avoid per-request calls to auth service. Refresh token rotation prevents token reuse.

### Intelligent Caching

Redis caches are layered:
- Search results (30-min TTL, query-hashed keys)
- User sessions (via refresh tokens)
- Celery task results

## Deployment

NeighborIQ is designed for containerized deployment. See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for production configuration and scaling guidance.

## Contributing

Contributions are welcome! Please open an issue or PR. Follow the code style guidelines (Black formatting, Pydantic schema validation, async/await patterns).

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) file for details.

## Support

For questions, issues, or feature requests, please use [GitHub Issues](https://github.com/e-choness/neighboriq/issues).
