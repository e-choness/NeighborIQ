# Testing Guide

## Testing Philosophy

**All tests must run via Docker Compose.** Never run `pytest` or `uvicorn` directly on your host machine. This ensures:

- ✅ Consistent environment across all developers
- ✅ Tests against real PostgreSQL (not mocks)
- ✅ Integration with Redis and Elasticsearch
- ✅ Proper async/await handling

See [team memory: Docker-only testing policy](../../.claude/projects/D--Projects-NeighborIQ/memory/team/docker-only-testing.md) for rationale.

---

## CI/CD Pipeline Overview

```mermaid
flowchart LR
    Push["Developer pushes<br/>to main or PR"]
    
    Lint["Lint Stage<br/>black, isort, flake8, pylint<br/>Parallel × 7 services"]
    
    Test["Test Stage<br/>pytest + Docker infra<br/>Parallel × 5 services"]
    
    Build["Build Stage<br/>Docker image build<br/>Push to GHCR<br/>Parallel × 7 services"]
    
    Security["Security Scan<br/>Trivy vulnerability<br/>scanning"]
    
    Notify["Notify Completion<br/>Success/Failure summary"]
    
    Push --> Lint
    Lint -->|All pass| Test
    Lint -->|Fail| Notify
    Test -->|All pass| Build
    Test -->|Fail| Notify
    Build -->|All pass| Security
    Build -->|Fail| Notify
    Security --> Notify
    
    style Lint fill:#f0f0f0
    style Test fill:#f0f0f0
    style Build fill:#f0f0f0
    style Security fill:#f0f0f0
```

---

## Test Service Configuration

### Test Profile

Docker Compose test services use the `test` profile. They are **not started** by default — only when explicitly requested:

```bash
# Start test services
docker-compose --profile test up

# List test services
docker-compose config --services | grep test
```

### Test Service Inventory

| Service | Container | Profile | Depends On | Purpose |
|---------|-----------|---------|------------|---------|
| **test-api-gateway** | `api-gateway:latest` | test | — | Unit tests for gateway routing |
| **test-auth-service** | `auth-service:latest` | test | postgres | User auth, JWT generation tests |
| **test-house-api-service** | `house-api-service:latest` | test | postgres | Property CRUD, filtering tests |
| **test-search-service** | `search-service:latest` | test | elasticsearch, redis | ES query, caching tests |
| **test-portfolio-service** | `portfolio-service:latest` | test | postgres | Portfolio CRUD tests |
| **test-ai-insights-service** | `ai-insights-service:latest` | test | postgres, redis | ML model, Celery task tests |
| **test-scraper-service** | `scraper-service:latest` | test | — | Spider, pipeline tests |
| **test-data-layer** | custom | test | postgres, redis, elasticsearch | Database schema, cache, search integration tests |
| **test-frontend-build** | `frontend:latest` | test | — | Nginx config validation |

---

## Lint Tools Reference

All services are linted in parallel via GitHub Actions. Configuration is per-service:

| Tool | Command | Services Checked | Purpose | Config |
|------|---------|------------------|---------|--------|
| **black** | `black --check .` | 7 (all Python) | Code formatting | `pyproject.toml` |
| **isort** | `isort --check-only .` | 7 (all Python) | Import sorting | `pyproject.toml` |
| **flake8** | `flake8 --count --select=E9,F63,F7,F82` | 7 (all Python) | Syntax errors | CLI flags |
| **pylint** | `pylint --exit-zero` | 7 (all Python) | Code quality (warnings) | CLI flags |

### Running Linters Locally

```bash
# Format code with black (changes files)
docker-compose exec auth-service black app/

# Check imports with isort (changes files)
docker-compose exec auth-service isort app/

# Check syntax with flake8 (read-only)
docker-compose exec auth-service flake8 app/ --count --select=E9,F63,F7,F82

# Check quality with pylint (warnings only)
docker-compose exec auth-service pylint app/ --exit-zero
```

---

## Coverage Configuration

### pytest-cov Setup

Coverage is enabled in all test services via `pytest.ini`:

```ini
[pytest]
addopts = --cov=app --cov-report=xml --cov-report=term-missing
testpaths = tests
```

### Viewing Coverage

```bash
# Run tests and generate coverage report
docker-compose --profile test up test-auth-service --abort-on-container-exit

# View report in stdout (shown in logs)
docker-compose logs test-auth-service | grep "TOTAL"

# Example output:
# name                          stmts   miss  cover
# ─────────────────────────────────────────────────
# app/__init__.py                   5      0   100%
# app/main.py                      42      3    93%
# TOTAL                            47      3    94%
```

### Coverage Upload

GitHub Actions uploads coverage to Codecov (if configured):

```yaml
- uses: codecov/codecov-action@v3
  with:
    files: ./services/{service}/coverage.xml
    flags: {service}
```

---

## Running Tests Locally

### Full Test Suite (All Services)

```bash
# Start test containers and run tests until completion or failure
docker-compose --profile test up --abort-on-container-exit

# Exit code: 0 = all pass, 1 = at least one failed
echo "Exit code: $?"
```

### Single Service Test

```bash
# Run tests for one service
docker-compose --profile test up test-auth-service --abort-on-container-exit

# View detailed output
docker-compose logs test-auth-service | tail -100

# Run with verbose pytest output
docker-compose --profile test up test-auth-service -v --abort-on-container-exit
```

### Test in Foreground (Interactive)

```bash
# Start service and see real-time output (useful for debugging)
docker-compose --profile test up test-auth-service

# (Press Ctrl+C to stop; output is visible in real-time)
```

### Specific Test File or Function

```bash
# Run single test file (pass pytest args to container)
docker-compose exec test-auth-service python -m pytest tests/test_auth.py -v

# Run single test function
docker-compose exec test-auth-service python -m pytest tests/test_auth.py::test_login_valid -v

# Run with print statements (don't capture output)
docker-compose exec test-auth-service python -m pytest tests/test_auth.py -s
```

---

## Writing Tests

### Test File Structure

Tests are colocated with services under `tests/` directory:

```
services/auth-service/
├── app/
│   ├── main.py
│   └── ...
├── tests/
│   ├── __init__.py
│   ├── conftest.py      # Shared fixtures
│   ├── test_auth.py     # Login/signup tests
│   ├── test_jwt.py      # Token tests
│   └── ...
├── requirements.txt
└── pytest.ini
```

### Fixture Pattern (conftest.py)

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def db_session():
    """Create an async database session for tests."""
    engine = create_async_engine(
        "postgresql+asyncpg://root:root@postgres:5432/house_discovery_test",
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = AsyncSession(engine)
    yield async_session
    
    await async_session.close()
    await engine.dispose()

@pytest.fixture
async def client(db_session):
    """Create a test HTTP client."""
    from fastapi.testclient import TestClient
    app.dependency_overrides[get_db] = lambda: db_session
    return TestClient(app)
```

### Async Test Pattern

```python
import pytest

@pytest.mark.asyncio
async def test_login_valid(client):
    """Test successful login."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "user@test.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["email"] == "user@test.com"
```

### Database Integration Test Pattern

```python
@pytest.mark.asyncio
async def test_create_user(db_session):
    """Test user creation in database."""
    user = User(
        email="new@test.com",
        hashed_password=hash_password("secret")
    )
    db_session.add(user)
    await db_session.commit()
    
    # Verify user exists
    result = await db_session.execute(
        select(User).where(User.email == "new@test.com")
    )
    assert result.scalar_one().email == "new@test.com"
```

### No Mocks on Database

```python
# ❌ DO NOT MOCK DATABASE
@patch('shared.database.get_db')
def test_get_houses(mock_db):
    # This bypasses the real database — avoid!
    pass

# ✅ USE REAL DATABASE IN DOCKER
async def test_get_houses(db_session):
    # This tests against actual PostgreSQL in Docker
    house = House(title="Test House", city="toronto", price=500000)
    db_session.add(house)
    await db_session.commit()
    # ... test queries against real data
```

---

## CI/CD Triggers

### When Tests Run

| Trigger | Branch | Description |
|---------|--------|-------------|
| `push` | `main` | All commits to main run full pipeline |
| `push` | `echo/*` | All feature branches (e.g., `echo/phase-7`) run full pipeline |
| `pull_request` | `main` | PRs to main run lint + test (not build) |

### GitHub Actions Workflow File

- **Location**: `.github/workflows/ci-cd.yml`
- **Triggers**: Push to `main` or `echo/*`, PR to `main`
- **Jobs**:
  1. **Lint** — Parallel 7 services
  2. **Test** — Parallel 5 services (depends on lint)
  3. **Build** — Parallel 7 services (depends on test)
  4. **Security** — Trivy scanning (depends on build)
  5. **Notify** — Summary notification

---

## Container Registry (GHCR)

### Image Tags

When tests pass and build succeeds, images are pushed to GitHub Container Registry:

```
ghcr.io/e-choness/api-gateway:main
ghcr.io/e-choness/api-gateway:v1.2.3
ghcr.io/e-choness/api-gateway:main-a1b2c3d  (short SHA)
ghcr.io/e-choness/api-gateway:latest        (if main branch)
```

### Image Pull

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USER --password-stdin

# Pull image
docker pull ghcr.io/e-choness/api-gateway:main

# Use in docker-compose.yml
image: ghcr.io/e-choness/api-gateway:main
```

---

## Troubleshooting CI/CD

### Tests Pass Locally, Fail in CI

**Common Cause**: Race condition or timing dependency

**Debugging**:
```bash
# Re-create CI environment exactly
docker-compose down -v  # Clean state
docker-compose --profile test up --abort-on-container-exit

# Check for flaky tests
docker-compose --profile test up --abort-on-container-exit
# (repeat 3 times)
```

### Build Fails with "Base Image Not Found"

**Cause**: CI can't download base image (network timeout)

**Solution**: Retry job manually in GitHub Actions UI

### Coverage Upload Fails

**Cause**: Codecov token missing or expired

**Solution**: Contact repo admin to regenerate Codecov token

### Flaky Elasticsearch Tests

**Cause**: ES takes time to be ready; health check insufficient

**Solution**: Add retry logic in conftest.py:
```python
@pytest.fixture
async def es_client():
    for attempt in range(10):
        try:
            client = AsyncElasticsearch(['http://elasticsearch:9200'])
            await client.info()
            return client
        except:
            await asyncio.sleep(1)
    raise Exception("Elasticsearch not ready")
```

---

## Test Coverage Goals

Target coverage per service (not strict, but aspirational):

| Service | Target Coverage |
|---------|-----------------|
| **auth-service** | 90%+ (critical auth logic) |
| **house-api-service** | 85%+ (CRUD + filtering) |
| **search-service** | 80%+ (ES queries complex) |
| **api-gateway** | 85%+ (routing + auth middleware) |
| **portfolio-service** | 85%+ |
| **ai-insights-service** | 70%+ (ML model hard to test) |
| **scraper-service** | 70%+ (external site dependency) |

Focus on critical paths (auth, data integrity) over edge cases.

---

## See Also

- [**Getting Started Guide**](./getting-started.md) — Local development setup
- [**GitHub Actions Workflow**](../../.github/workflows/ci-cd.yml) — CI configuration
- [pytest Documentation](https://docs.pytest.org/) — Testing framework
