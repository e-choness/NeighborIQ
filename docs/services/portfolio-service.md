# Portfolio Service

## Introduction

The Portfolio Service manages **user-saved houses** (watchlist / portfolio). It provides auth-gated CRUD operations for the `SavedHouse` model, allowing users to track and organize properties of interest.

The service is lightweight and focuses on fast retrieval of a user's saved houses. All operations require JWT authentication (enforced by API Gateway).

---

## Data Model

```mermaid
erDiagram
    USERS ||--o{ SAVED_HOUSES : creates
    HOUSES ||--o{ SAVED_HOUSES : "is_saved_in"
    
    USERS {
        uuid id PK
        string email UK
        string hashed_password
        string role
        datetime created_at
    }
    
    HOUSES {
        int id PK
        string title
        string city
        int price
        float area
        datetime created_at
    }
    
    SAVED_HOUSES {
        int id PK
        uuid user_id FK
        int house_id FK
        datetime saved_at
    }
```

**Constraints**:
- Composite unique index on (user_id, house_id) — prevents duplicate saves
- Foreign keys with CASCADE DELETE — remove from portfolio when user/house is deleted

---

## API Endpoints

### List User's Saved Houses

```http
GET /api/v1/portfolio
Authorization: Bearer {access_token}
```

**Response**:
```json
{
  "houses": [
    {
      "id": 1,
      "title": "4-BR House near High Park",
      "community": "King West",
      "city": "toronto",
      "region": "Downtown",
      "price": 650000,
      "area": 250.5,
      "rooms": 4,
      "floor": 3,
      "decoration": "精装",
      "age": 5,
      "latitude": 43.6452,
      "longitude": -79.3807,
      "saved_at": "2025-12-01T10:30:00Z"
    }
  ],
  "total_count": 12,
  "page": 1,
  "page_size": 50,
  "total_pages": 1
}
```

**Query Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | int | 1 | Pagination page |
| `page_size` | int | 50 | Results per page (1-100) |
| `sort` | string | `saved_at` | Sort by: `saved_at`, `price`, `area` |
| `order` | string | `desc` | Sort order: `asc` or `desc` |

### Save a House

```http
POST /api/v1/portfolio
Authorization: Bearer {access_token}
Content-Type: application/json

{
  "house_id": 1
}
```

**Response** (201 Created):
```json
{
  "id": 123,
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "house_id": 1,
  "saved_at": "2025-12-06T15:45:00Z"
}
```

**Errors**:
- `400` — Invalid house_id or already saved
- `404` — House not found
- `401` — Unauthorized (missing token)

### Remove from Portfolio

```http
DELETE /api/v1/portfolio/{house_id}
Authorization: Bearer {access_token}
```

**Response**:
- `204 No Content` — Successfully removed
- `404` — Not in portfolio
- `401` — Unauthorized

### Health Check

```http
GET /health
```

**Response**:
```json
{
  "status": "ok",
  "service": "portfolio-service",
  "version": "0.1.0",
  "timestamp": "2025-12-06T15:45:00Z"
}
```

---

## Authentication Requirements

All endpoints except `/health` require a **valid JWT access token** in one of two places:

1. **Authorization Header**:
   ```http
   Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

2. **HttpOnly Cookie**:
   ```http
   Cookie: access_token=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
   ```

The **API Gateway** validates the JWT and injects `X-User-ID` header, which the Portfolio Service uses to scope operations to the authenticated user.

### Token Format

- **Type**: RS256 JWT
- **Payload**: `{sub: user_id, email, role, exp, ...}`
- **TTL**: 15 minutes
- **Refresh**: Via `/api/v1/auth/refresh`

---

## SavedHouse Model Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | int | ✗ | Record identifier |
| `user_id` | UUID | ✗ | User who saved (from JWT) |
| `house_id` | int | ✗ | Property ID |
| `saved_at` | datetime | ✗ | Timestamp (auto-populated) |

---

## Caching Strategy

Saved house lists are cacheable in Redis:
- **Key**: `portfolio:{user_id}:page:{page_num}` (per user, per page)
- **TTL**: 1 hour
- **Invalidation**: On POST/DELETE to portfolio

**Rationale**: User's portfolio rarely changes; caching improves list performance.

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://root:root@localhost:5432/house_discovery` | Async Postgres connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis cache (optional) |

---

## Troubleshooting

### 401 Unauthorized

**Symptom**: All requests return `401 Unauthorized`

**Root Cause**: Missing or expired access token

**Solution**:
1. Ensure token is in Authorization header or `access_token` cookie
2. Token may be expired — refresh via `POST /auth/refresh`
3. Check browser DevTools Network tab to confirm token is being sent

### 400 Bad Request (Duplicate Save)

**Symptom**: `POST /portfolio` with same house_id returns `400`

**Root Cause**: House already in user's portfolio

**Solution**: Check if house is already saved before re-saving, or delete first then re-add

### 404 Not Found

**Symptom**: `GET /portfolio/{house_id}` returns `404`

**Root Cause**: House not in user's portfolio, or house_id doesn't exist

**Solution**: Verify house_id exists in house API service first

---

## Use Cases

### Browse Saved Houses

User visits "My Portfolio" page:
```javascript
const response = await fetch('/api/v1/portfolio?sort=saved_at&order=desc', {
  credentials: 'include'  // Include auth cookies
})
const { houses } = await response.json()
// Display houses in UI
```

### Quick-Save a House

User clicks heart icon on search results:
```javascript
await fetch('/api/v1/portfolio', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({ house_id: 1 })
})
```

### Remove from Portfolio

User clicks "Remove" button:
```javascript
await fetch(`/api/v1/portfolio/${house_id}`, {
  method: 'DELETE',
  credentials: 'include'
})
```

---

## See Also

- [**Data Models**](../architecture/data-models.md) — SavedHouse schema
- [**System Architecture**](../architecture/overview.md) — Service topology
