# House API Service

## Introduction

The House API Service owns the **property and community data model**. It provides CRUD operations, advanced filtering, pagination, and price history tracking for all real estate listings in the NeighborIQ platform.

All queries are fully async (`asyncpg` + SQLAlchemy 2.0) and all responses are paginated to support efficient browsing of large datasets.

---

## Data Model Class Diagram

```mermaid
classDiagram
    class House {
        int id PK
        str title
        str community
        str city
        str region
        str street
        int price
        float area
        int rooms
        int floor
        str decoration
        int age
        float latitude
        float longitude
        str url
        str images JSON
        bool is_active
        datetime created_at
        datetime updated_at
        
        methods:
        + get_by_id(id)
        + list(filters, page, page_size)
        + search_by_location(lat, lon, radius)
    }
    
    class Community {
        int id PK
        str city
        str region
        str street
        float median_price
        int house_count
        datetime updated_at
    }
    
    class HousePriceHistory {
        int id PK
        int house_id FK
        int price
        datetime recorded_at
    }
    
    class PriceRange {
        int min_price
        int max_price
    }
    
    House "1" --> "0..*" HousePriceHistory : tracks price changes
    House "*" --> "1" Community : belongs to
    House "*" --> "1" PriceRange : filtered by
```

---

## API Endpoints

### List Houses

```http
GET /api/v1/houses?city=toronto&price_min=300000&price_max=800000&page=1&page_size=50
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `city` | string | — | Filter by city (e.g., `toronto`, `vancouver`) |
| `region` | string | — | Filter by region/district |
| `street` | string | — | Filter by street address |
| `community` | string | — | Filter by neighborhood |
| `price_min` | int | — | Minimum price in CAD |
| `price_max` | int | — | Maximum price in CAD |
| `rooms_min` | int | — | Minimum bedrooms |
| `rooms_max` | int | — | Maximum bedrooms |
| `area_min` | float | — | Minimum area in m² |
| `area_max` | float | — | Maximum area in m² |
| `page` | int | 1 | Page number (1-indexed) |
| `page_size` | int | 50 | Results per page (1-100) |
| `sort` | string | `created_at` | Sort field: `price`, `created_at`, `area`, `rooms` |
| `order` | string | `desc` | Sort order: `asc` or `desc` |

**Response**:
```json
{
  "houses": [
    {
      "id": 1,
      "title": "4-BR House in Downtown Toronto",
      "community": "King West",
      "city": "toronto",
      "region": "Downtown",
      "street": "King St W",
      "price": 650000,
      "area": 250.5,
      "rooms": 4,
      "floor": 3,
      "decoration": "精装",
      "age": 5,
      "latitude": 43.6452,
      "longitude": -79.3807,
      "url": "https://...",
      "created_at": "2025-11-20T10:30:00Z",
      "updated_at": "2025-12-06T15:45:00Z"
    }
  ],
  "total_count": 1234,
  "page": 1,
  "page_size": 50,
  "total_pages": 25
}
```

### Get Single House

```http
GET /api/v1/houses/{id}
```

**Response**: Single house object (same schema as above)

### Create House (Admin/Scraper Only)

```http
POST /api/v1/houses
Content-Type: application/json

{
  "title": "New Property",
  "community": "Downtown",
  "city": "toronto",
  "region": "Core",
  "price": 550000,
  "area": 200,
  "rooms": 3,
  "latitude": 43.6452,
  "longitude": -79.3807,
  "url": "https://..."
}
```

**Response**: Created house object (201 Created)

### Update House

```http
PUT /api/v1/houses/{id}
Content-Type: application/json

{
  "price": 575000
}
```

**Response**: Updated house object

### Delete House

```http
DELETE /api/v1/houses/{id}
```

**Response**: `204 No Content`

### List Communities

```http
GET /api/v1/communities?city=toronto&region=downtown
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `city` | string | Filter by city |
| `region` | string | Filter by region |
| `page` | int | Pagination |
| `page_size` | int | Results per page |

**Response**:
```json
{
  "communities": [
    {
      "id": 1,
      "city": "toronto",
      "region": "Downtown",
      "median_price": 625000,
      "house_count": 234,
      "updated_at": "2025-12-06T00:00:00Z"
    }
  ],
  "total_count": 45,
  "page": 1,
  "page_size": 50,
  "total_pages": 1
}
```

---

## Query Filter Parameters Detailed Reference

| Filter | Type | Range | SQL Operator | Example |
|--------|------|-------|--------------|---------|
| `city` | string | — | LIKE or exact | `city=toronto` |
| `region` | string | — | LIKE or exact | `region=downtown` |
| `street` | string | — | LIKE | `street=king` |
| `community` | string | — | LIKE | `community=king west` |
| `price_min` | int | 0 - 999,999,999 CAD | `price >= X` | `price_min=300000` |
| `price_max` | int | 0 - 999,999,999 CAD | `price <= X` | `price_max=800000` |
| `rooms_min` | int | 1-10 | `rooms >= X` | `rooms_min=2` |
| `rooms_max` | int | 1-10 | `rooms <= X` | `rooms_max=5` |
| `area_min` | float | 1-1000 m² | `area >= X` | `area_min=100` |
| `area_max` | float | 1-1000 m² | `area <= X` | `area_max=500` |

**Combined Filters** are AND-ed together:
```
GET /api/v1/houses?city=toronto&price_min=300000&price_max=800000&rooms_min=3
# WHERE city='toronto' AND price >= 300000 AND price <= 800000 AND rooms >= 3
```

---

## Pagination Implementation

- **Default page size**: 50 results
- **Max page size**: 100 results
- **Page numbering**: 1-indexed (page=1 is first page)
- **Total count**: Returned in response for frontend pagination UI

**Example Request**:
```http
GET /api/v1/houses?city=toronto&page=2&page_size=25
```

**Calculated Offset**:
```
offset = (page - 1) * page_size = (2 - 1) * 25 = 25
SQL: OFFSET 25 LIMIT 25
```

**Response** includes:
- `houses` — array of house objects
- `total_count` — total matching houses across all pages
- `page`, `page_size`, `total_pages` — pagination metadata

---

## Price History Tracking

When a house's price changes, the old price is automatically recorded in `house_price_history`:

```sql
INSERT INTO house_price_history (house_id, price, recorded_at)
VALUES (?, ?, NOW());
```

### Get Price History

```http
GET /api/v1/houses/{id}/price-history
```

**Response**:
```json
{
  "price_history": [
    { "price": 650000, "recorded_at": "2025-12-06T10:00:00Z" },
    { "price": 640000, "recorded_at": "2025-11-20T15:30:00Z" },
    { "price": 630000, "recorded_at": "2025-10-15T09:00:00Z" }
  ]
}
```

This enables price trend analysis and negotiation context.

---

## Indexes for Performance

| Index | Columns | Rationale |
|-------|---------|-----------|
| `idx_house_houses_city_region` | (city, region) | Common filter combination |
| `idx_house_houses_price` | (price) | Price range queries |
| `idx_house_houses_location` | (latitude, longitude) | Geo-spatial queries |
| `idx_house_houses_url` | (url) | Uniqueness constraint |
| `idx_house_houses_community` | (community) | Filter by neighborhood |

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql+asyncpg://root:root@localhost:5432/house_discovery` | Async Postgres connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis cache (optional) |

---

## Caching Strategy

House objects can be cached in Redis:
- **Key**: `house:{id}`
- **TTL**: 24 hours
- **Invalidation**: On any PUT/DELETE operation

List responses are not cached due to high dimensionality of filter combinations.

---

## Troubleshooting

### Query Timeout (response takes >5 seconds)

**Root Cause**: Large dataset without proper filtering or indexes

**Solution**:
```bash
# Check index usage
docker-compose exec postgres psql -U root -d house_discovery -c \
  "EXPLAIN ANALYZE SELECT * FROM house_houses WHERE city='toronto' AND price > 300000;"

# Add missing index if needed
docker-compose exec postgres psql -U root -d house_discovery -c \
  "CREATE INDEX idx_city_price ON house_houses(city, price);"
```

### Empty Results Despite Data Existing

**Root Cause**: Case sensitivity in string filters (PostgreSQL case-sensitive by default)

**Solution**: Use ILIKE for case-insensitive search:
```http
GET /api/v1/houses?city=TORONTO  # May return 0 results if data is 'toronto'
```

The service should normalize city values to lowercase on insert and query.

---

## See Also

- [**System Architecture**](../architecture/overview.md) — Database schema context
- [**Data Models**](../architecture/data-models.md) — Full ER diagram and field descriptions
- [**Search Service**](./search-service.md) — For full-text search on house data
