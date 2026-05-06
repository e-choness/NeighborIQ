# NeighborIQ Deployment Guide — Phase 7

Complete deployment and operational procedures for NeighborIQ microservices on Docker Compose.

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Local Development](#local-development)
3. [Production Deployment](#production-deployment)
4. [Health Checks & Monitoring](#health-checks--monitoring)
5. [Scaling & Performance](#scaling--performance)
6. [Troubleshooting](#troubleshooting)
7. [Rollback Procedures](#rollback-procedures)

---

## Pre-Deployment Checklist

Before deploying to production:

- [ ] All unit tests passing: `docker-compose --profile test run --rm test-*-service`
- [ ] All integration tests passing
- [ ] Code coverage > 80%: `pytest --cov=app`
- [ ] No security vulnerabilities: `trivy fs .`
- [ ] Docker images built and tagged: `docker-compose build`
- [ ] Environment variables set in `.env.prod`
- [ ] SSL certificates prepared (if HTTPS required)
- [ ] Database backups configured
- [ ] Monitoring & logging configured
- [ ] Disaster recovery plan documented

---

## Local Development

### Initial Setup

```bash
# Clone repository
git clone https://github.com/yourusername/neighboriq.git
cd neighboriq

# Build all services
docker-compose build

# Start all services
docker-compose up -d

# Verify all services are healthy
docker-compose ps
```

### Running Tests

```bash
# Run tests for all services
docker-compose --profile test run --rm test-api-gateway
docker-compose --profile test run --rm test-auth-service
docker-compose --profile test run --rm test-house-api-service
# ... etc

# Run with coverage report
docker-compose --profile test run --rm test-api-gateway pytest --cov=app --cov-report=html
```

### Viewing Logs

```bash
# View logs from all services
docker-compose logs -f

# View logs from specific service
docker-compose logs -f api-gateway

# View last 100 lines
docker-compose logs --tail=100 auth-service
```

### Stopping Services

```bash
# Stop all services (data persists)
docker-compose down

# Stop and remove volumes (WARNING: deletes data)
docker-compose down -v
```

---

## Production Deployment

### Prerequisites

- VPS with Docker and Docker Compose installed
- PostgreSQL 15+, Redis 7+, Elasticsearch 8.11.0
- Nginx for reverse proxy and SSL termination
- Domain name with DNS pointing to VPS
- SSL certificates (Let's Encrypt recommended)
- Backups of PostgreSQL and Redis data

### Deployment Steps

#### Step 1: Prepare Environment

```bash
# SSH to production VPS
ssh user@prod.neighboriq.com

# Create app directory
mkdir -p /app/neighboriq
cd /app/neighboriq

# Clone repository (or update existing)
git clone https://github.com/yourusername/neighboriq.git .

# Create .env.prod with production secrets
cat > .env.prod << 'EOF'
# Database
DATABASE_URL=postgresql+asyncpg://prod_user:STRONG_PASSWORD@postgres:5432/house_discovery

# Redis
REDIS_URL=redis://redis:6379/0

# Elasticsearch
ELASTICSEARCH_URL=http://elasticsearch:9200

# JWT Keys (generate new pair)
JWT_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----
JWT_PUBLIC_KEY=-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----

# API Gateway
AUTH_SERVICE_URL=http://auth-service:8000
HOUSE_SERVICE_URL=http://house-api-service:8000
SEARCH_SERVICE_URL=http://search-service:8000
PORTFOLIO_SERVICE_URL=http://portfolio-service:8000
AI_INSIGHTS_SERVICE_URL=http://ai-insights-service:8000

# CORS
CORS_ORIGINS=https://neighboriq.com,https://www.neighboriq.com

# Secrets
SECRET_KEY=generate_strong_random_string

# Azure OpenAI (if using AI insights)
OPENAI_API_KEY=sk-...
OPENAI_API_ENDPOINT=https://...openai.azure.com/
EOF

# Set restrictive permissions
chmod 600 .env.prod
```

#### Step 2: Configure SSL

```bash
# Generate self-signed certificate for development
# (Use Let's Encrypt for production)
mkdir -p certs
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem -days 365 -nodes

# Or use certbot for Let's Encrypt
sudo apt-get install certbot python3-certbot-nginx
sudo certbot certonly --standalone -d neighboriq.com -d www.neighboriq.com
sudo cp /etc/letsencrypt/live/neighboriq.com/fullchain.pem certs/cert.pem
sudo cp /etc/letsencrypt/live/neighboriq.com/privkey.pem certs/key.pem
```

#### Step 3: Initialize Databases

```bash
# Start database services only
docker-compose up -d postgres redis elasticsearch

# Wait for databases to be ready
sleep 30

# Run database migrations
docker-compose run --rm api-gateway python -m alembic upgrade head

# Verify database connectivity
docker-compose exec postgres psql -U root -d house_discovery -c "SELECT 1;"
```

#### Step 4: Deploy Services

```bash
# Build all services
docker-compose build

# Pull latest images (if using registry)
docker-compose pull

# Start all services with production overrides
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify all services started
docker-compose ps
```

#### Step 5: Health Checks

```bash
# Check all service health endpoints
curl http://localhost:8000/health  # API Gateway
curl http://localhost:8001/health  # Auth Service
curl http://localhost:8002/health  # House API
curl http://localhost:8004/health  # Search Service
curl http://localhost:8003/api/v1/health  # AI Insights
curl http://localhost:8006/health  # Portfolio Service
curl http://localhost:8005/health  # Scraper Service

# All should return 200 OK with status
curl -s http://localhost/health | jq .
```

#### Step 6: Verify Frontend

```bash
# Test frontend is accessible through Nginx
curl http://localhost/
# Should return HTML content from Vue 3 frontend

# Test API routing through Nginx
curl http://localhost/api/v1/houses
# Should return house listings or 401 if auth required
```

---

## Health Checks & Monitoring

### Service Health Endpoints

All services expose `/health` endpoints (except AI Insights which uses `/api/v1/health`):

| Service | Endpoint | Port | Health Check Frequency |
|---------|----------|------|------------------------|
| API Gateway | `GET /health` | 8000 | 10s |
| Auth Service | `GET /health` | 8001 | 10s |
| House API | `GET /health` | 8002 | 10s |
| Search Service | `GET /health` | 8004 | 10s |
| AI Insights | `GET /api/v1/health` | 8003 | 60s |
| Portfolio Service | `GET /health` | 8006 | 10s |
| Scraper Service | `GET /health` | 8005 | 60s |
| Frontend | HTTP 200 | 80 | 30s |
| Nginx | `GET /health` | 80 | 30s |

### Docker Health Status

```bash
# View health status of all containers
docker-compose ps

# Output example:
# NAME                        STATUS
# postgres                    Up 5 minutes (healthy)
# redis                       Up 5 minutes (healthy)
# elasticsearch               Up 5 minutes (healthy)
# api-gateway                 Up 2 minutes (healthy)
# auth-service                Up 2 minutes (healthy)
# house-api-service           Up 2 minutes (healthy)
```

### Manual Health Check Script

```bash
#!/bin/bash
# health-check.sh

SERVICES=(
    "localhost:8000:/health"
    "localhost:8001:/health"
    "localhost:8002:/health"
    "localhost:8004:/health"
    "localhost:8003:/api/v1/health"
    "localhost:8006:/health"
    "localhost:8005:/health"
)

for service in "${SERVICES[@]}"; do
    IFS=':' read -r host port path <<< "$service"
    if curl -f http://$host$path > /dev/null 2>&1; then
        echo "✓ $host$path"
    else
        echo "✗ $host$path"
    fi
done
```

### Monitoring & Alerting

#### Docker Stats

```bash
# Monitor CPU/memory usage
docker stats

# With output to file
docker stats > /var/log/docker-stats.log
```

#### Log Aggregation

```bash
# View aggregated logs
docker-compose logs -f --tail=100

# Filter by service
docker-compose logs -f api-gateway

# Tail specific timestamp
docker-compose logs --since 2026-05-06T10:00:00 --until 2026-05-06T11:00:00
```

#### Prometheus Integration (Future)

```yaml
# Add to docker-compose.prod.yml when ready
prometheus:
  image: prom/prometheus:latest
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
```

---

## Scaling & Performance

### Horizontal Scaling (Future — Kubernetes)

For now, Docker Compose deployment is single-node. When scaling is needed:

```bash
# Scale Celery workers (horizontal)
docker-compose up -d --scale ai-insights-worker=3 --scale scraper-worker=2

# Scale API services (requires load balancer)
docker-compose up -d --scale auth-service=2 --scale house-api-service=2
```

### Performance Tuning

#### Database Connection Pooling

Set in docker-compose.yml:

```yaml
environment:
  - DATABASE_POOL_SIZE=20
  - DATABASE_MAX_OVERFLOW=10
  - DATABASE_POOL_RECYCLE=3600
```

#### Redis Eviction Policy

```bash
docker-compose exec redis redis-cli CONFIG SET maxmemory-policy allkeys-lru
```

#### Elasticsearch Sharding

```bash
# Create index with shards for faster queries
curl -X PUT "localhost:9200/houses?pretty" -H 'Content-Type: application/json' -d'{
  "settings": {
    "number_of_shards": 5,
    "number_of_replicas": 1
  }
}'
```

---

## Troubleshooting

### Service won't start

```bash
# Check logs
docker-compose logs service-name

# Check if port is in use
lsof -i :8000

# Rebuild image
docker-compose build --no-cache service-name
docker-compose up -d service-name
```

### Database connection errors

```bash
# Verify database is running and healthy
docker-compose ps postgres

# Test connection
docker-compose exec postgres psql -U root -d house_discovery -c "SELECT 1;"

# Check DATABASE_URL environment variable
docker-compose config | grep DATABASE_URL
```

### High memory usage

```bash
# Check memory usage
docker stats

# Reduce JVM memory for Elasticsearch
docker-compose.yml: ES_JAVA_OPTS=-Xms256m -Xmx256m
```

### API timeouts

```bash
# Check API Gateway logs
docker-compose logs -f api-gateway

# Verify downstream services are responding
curl http://auth-service:8000/health
curl http://house-api-service:8000/health

# Check network
docker-compose exec api-gateway curl http://auth-service:8000/health
```

---

## Rollback Procedures

### Quick Rollback (Same-Day)

```bash
# If deployment introduced critical bugs:

# 1. Get previous image tags
docker image ls | grep neighboriq

# 2. Update docker-compose.yml with previous image tags
# Example:
#   api-gateway:
#     image: ghcr.io/yourusername/api-gateway:main-abc123def456

# 3. Restart services with previous version
docker-compose down
docker-compose up -d

# 4. Run smoke tests
./health-check.sh
pytest smoke_tests/
```

### Full Rollback (Database Migrations)

```bash
# If migration caused data issues:

# 1. Restore from backup
docker-compose down
docker exec neighboriq_postgres pg_restore -d house_discovery < backup.sql

# 2. Rollback migration
docker-compose run --rm api-gateway python -m alembic downgrade -1

# 3. Redeploy previous services
docker-compose down
# Update image tags in docker-compose.yml
docker-compose up -d

# 4. Verify data integrity
docker-compose exec postgres psql -d house_discovery -c "SELECT COUNT(*) FROM houses;"
```

### Blue-Green Deployment (Zero-Downtime)

For production environments requiring zero downtime:

```bash
# 1. Start "green" (new) services on separate ports
docker-compose -f docker-compose.blue.yml up -d

# 2. Run smoke tests on green
curl http://localhost:8100/health

# 3. Switch Nginx to point to green
# Edit nginx.conf: upstream api_gateway { server api-gateway-green:8000; }
# Reload Nginx
docker-compose exec nginx nginx -s reload

# 4. Monitor error rates
docker-compose logs -f

# 5. If rollback needed, switch Nginx back to blue
# Edit nginx.conf: upstream api_gateway { server api-gateway:8000; }
docker-compose exec nginx nginx -s reload

# 6. Stop green services
docker-compose -f docker-compose.blue.yml down
```

---

## Disaster Recovery

### Backup Strategy

```bash
# Daily PostgreSQL backups
docker-compose exec postgres pg_dump -U root -d house_discovery > backup-$(date +%Y%m%d).sql

# Backup Redis
docker-compose exec redis redis-cli BGSAVE
docker cp neighboriq_redis_1:/data/dump.rdb ./redis-backup-$(date +%Y%m%d).rdb

# Upload to S3
aws s3 cp backup-*.sql s3://neighboriq-backups/postgres/
aws s3 cp redis-backup-*.rdb s3://neighboriq-backups/redis/
```

### Recovery

```bash
# Restore PostgreSQL
docker-compose exec postgres psql -U root < backup-20260506.sql

# Restore Redis
docker cp redis-backup-20260506.rdb neighboriq_redis_1:/data/dump.rdb
docker-compose restart redis
```

---

## Security Hardening Checklist

- [ ] All environment secrets stored in `.env.prod` (NOT in git)
- [ ] SSL/TLS certificates configured and auto-renewing
- [ ] API rate limiting enabled
- [ ] JWT token validation working
- [ ] CORS origins restricted to frontend domain
- [ ] Database credentials strong and rotated regularly
- [ ] Docker images scanned for vulnerabilities (Trivy)
- [ ] Firewall rules configured (port 80, 443 only)
- [ ] Regular security audits scheduled
- [ ] Incident response plan documented

---

## Support & Escalation

- **Issue:** Services not starting → Check logs, rebuild
- **Issue:** High latency → Check Docker stats, scale workers
- **Issue:** Data inconsistency → Restore from backup, reapply migrations
- **Issue:** Security incident → Implement rollback, rotate secrets
- **Escalation:** Contact infrastructure team for VPS issues, database issues, security incidents

---

## References

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Nginx Documentation](https://nginx.org/en/docs/)
- [PostgreSQL Backup & Restore](https://www.postgresql.org/docs/current/backup.html)
- [Let's Encrypt](https://letsencrypt.org/)
