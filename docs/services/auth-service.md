# Auth Service

## Introduction & Responsibilities

The Auth Service is the **identity boundary** for NeighborIQ. It exclusively owns:

- **User Registration** — email + password signup
- **User Login** — email + password validation
- **JWT Generation** — RS256 access and refresh tokens
- **Token Refresh** — refresh token rotation for token expiry
- **JWKS Endpoint** — public key distribution for other services to verify JWTs
- **Session Management** — HttpOnly cookie management, refresh token revocation

All password hashing is bcrypt; all tokens are RS256 with rotating key pairs. The service acts as a true OAuth 2.0-like boundary, never exposing private keys.

---

## Login Flow Sequence

```mermaid
sequenceDiagram
    participant Client as Browser
    participant Gateway as API Gateway
    participant AuthSvc as Auth Service
    participant DB as PostgreSQL
    
    Client->>+Gateway: POST /api/v1/auth/login (email, password)
    
    Note over Gateway: No JWT required (public endpoint)
    
    Gateway->>+AuthSvc: POST /api/v1/auth/login (email, password)
    
    AuthSvc->>+DB: SELECT * FROM auth_users WHERE email='user@example.com'
    DB-->>-AuthSvc: User row (with hashed_password)
    
    AuthSvc->>AuthSvc: bcrypt.verify(password, user.hashed_password)
    
    alt Password matches
        AuthSvc->>DB: Query auth_jwt_key_pairs (SELECT latest key)
        DB-->>AuthSvc: RSA key pair
        
        AuthSvc->>AuthSvc: Generate access token<br>Payload: sub=user.id, email, role, exp=15m<br>Sign with RS256
        
        AuthSvc->>AuthSvc: Generate refresh token<br>Payload: jti=uuid, exp=7d
        
        AuthSvc->>DB: INSERT INTO auth_refresh_tokens (user_id, token_hash, expires_at)
        DB-->>AuthSvc: OK
        
        AuthSvc-->>Gateway: Response with tokens<br>Set-Cookie: access_token=... (HttpOnly)<br>Set-Cookie: refresh_token=... (HttpOnly)
        
    else Password wrong
        AuthSvc-->>Gateway: 401 Invalid credentials
    end
    %% Explicitly deactivate AuthSvc after the conditional block ends
    deactivate AuthSvc
    
    Gateway-->>-Client: (same response as Auth Service)
    
    Note over Client: Browser stores cookies<br>(HttpOnly means JS can't access)
```

---

## Token Refresh Flow

```mermaid
sequenceDiagram
    participant Client as Browser
    participant Gateway as API Gateway
    participant AuthSvc as Auth Service
    participant DB as PostgreSQL
    
    Note over Client: Access token near expiry<br>or already expired
    
    Client->>+Gateway: POST /api/v1/auth/refresh (Cookie: refresh_token=eyJh...)
    
    Note over Gateway: No access token required (public refresh endpoint)
    
    Gateway->>+AuthSvc: POST /api/v1/auth/refresh (refresh_token in cookie)
    
    AuthSvc->>AuthSvc: Decode refresh token (no signature check, token was signed by us)
    
    AuthSvc->>DB: SELECT * FROM auth_refresh_tokens WHERE token_hash = bcrypt(token) AND NOT revoked AND expires_at greater than now
    
    alt Token found and valid
        AuthSvc->>AuthSvc: Generate new access token<br>Payload: sub=user.id
        
        AuthSvc->>AuthSvc: (Optional) Rotate refresh token<br>Generate new refresh_token
        
        AuthSvc->>DB: DELETE old refresh_tokens, INSERT new refresh_token
        DB-->>AuthSvc: OK
        
        AuthSvc-->>Gateway: Response with new tokens (Set-Cookie: access_token=..., refresh_token=...)
        
    else Token not found or expired
        AuthSvc-->>Gateway: 401 Refresh token invalid or expired
        
        Note over Client: User must log in again
    end
    %% Cleanly deactivate AuthSvc after the conditional block ends
    deactivate AuthSvc
    
    Gateway-->>-Client: (response)
```

---

## Token Lifecycle State Diagram

```mermaid
stateDiagram-v2
    [*] --> Created: POST /login<br/>or /refresh
    
    Created --> Active: Token signed<br/>cookies set
    
    Active --> Valid: Middleware<br/>verifies signature<br/>& expiry
    
    Valid --> Expired: 15 min<br/>elapses
    
    Expired --> Refreshable: Refresh token<br/>still valid
    
    Refreshable --> Active: POST /refresh<br/>new access token
    
    Valid --> Revoked: POST /logout<br/>delete refresh_token
    
    Revoked --> [*]: Blacklisted
    
    Expired --> [*]: Can't refresh<br/>Expired too
```

---

## RS256 Key Generation & Management

**RSA Key Pair Storage**:

Keys are stored in `auth_jwt_key_pairs` table:
- `kid` — Key ID (used in JWT header to identify which key signed it)
- `public_key` — PEM format, shared via JWKS endpoint
- `private_key` — PEM format, never exposed outside Auth Service

**JWKS Endpoint** — `GET /.well-known/jwks.json`:

```json
{
  "keys": [
    {
      "kty": "RSA",
      "kid": "2024-01",
      "use": "sig",
      "n": "xnK82...",
      "e": "AQAB"
    },
    {
      "kty": "RSA",
      "kid": "2024-02",
      "use": "sig",
      "n": "z0Xz...",
      "e": "AQAB"
    }
  ]
}
```

The API Gateway caches this for 5 minutes; other services fetch it to verify JWT signatures.

**Key Rotation Strategy**:
- Generate new RSA key pair periodically (e.g., monthly)
- Keep 2-3 keys active in the database
- API Gateway JWKS cache TTL (5 min) allows gradual transition
- Clients (API Gateway, other services) try all keys in JWKS until one verifies

---

## Cookie Strategy

### Access Token Cookie

| Property | Value | Rationale |
|----------|-------|-----------|
| **Name** | `access_token` | — |
| **Value** | JWT string | Signed RS256 token |
| **HttpOnly** | ✓ | Prevent XSS attacks from stealing token |
| **Secure** | ✓ (prod only) | HTTPS only; set via `SECURE_COOKIES=1` env var |
| **SameSite** | `Lax` | Prevent CSRF; allow same-site form submissions |
| **Path** | `/` | Available to all routes |
| **Domain** | (same-site) | Set by browser automatically |
| **Max-Age** | 900 (15 min) | Expires in 15 minutes |

### Refresh Token Cookie

| Property | Value | Rationale |
|----------|-------|-----------|
| **Name** | `refresh_token` | — |
| **Value** | JWT string | Longer-lived token for obtaining new access tokens |
| **HttpOnly** | ✓ | Prevent XSS |
| **Secure** | ✓ (prod only) | HTTPS only |
| **SameSite** | `Lax` | Prevent CSRF |
| **Max-Age** | 604800 (7 days) | Expires in 7 days |

### Why HttpOnly?

Prevents JavaScript (including malicious injected code) from accessing tokens via `document.cookie`. Tokens are only sent by the browser in HTTP requests (where `SameSite` and `Secure` provide additional protection).

### Dev vs. Prod Security

**Development** (`SECURE_COOKIES=0`):
- Cookies sent over HTTP (for `localhost` testing)
- Allows insecure local development

**Production** (`SECURE_COOKIES=1`):
- Cookies only sent over HTTPS
- Requires valid TLS certificate
- Set in `docker-compose.prod.yml`

---

## API Endpoints

| Method | Path | Auth | Request Body | Response | Purpose |
|--------|------|------|--------------|----------|---------|
| POST | `/api/v1/auth/signup` | ✗ | {email, password} | {user: {id, email, role}} | Register new user |
| POST | `/api/v1/auth/login` | ✗ | {email, password} | {user: {id, email, role}} | Login existing user |
| POST | `/api/v1/auth/refresh` | ✗ | — (refresh cookie) | {user: {id, email}} | Refresh access token |
| POST | `/api/v1/auth/logout` | ✓ | — | {status: "ok"} | Revoke refresh token |
| GET | `/api/v1/auth/me` | ✓ | — | {user: {id, email, role}} | Get current user |
| GET | `/.well-known/jwks.json` | ✗ | — | {keys: [...]} | JWKS endpoint (public) |
| GET | `/health` | ✗ | — | {status: "ok"} | Health check |

---

## Pydantic Models

**Request/Response Schemas**:

```python
class UserCreate(BaseModel):
    email: str  # Must be unique
    password: str  # Min 8 characters

class UserLogin(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: UUID
    email: str
    role: str  # "user" or "admin"
    created_at: datetime

class HealthResponse(BaseModel):
    status: str  # "ok"
    service: str  # "auth-service"
    version: str
    timestamp: datetime
```

---

## Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `postgresql://root:root@localhost:5432/house_discovery` | Async Postgres connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis for session cache (optional) |
| `SECURE_COOKIES` | `1` | If `1`, set Secure flag on cookies (HTTPS only). Set to `0` for local dev. |

---

## Troubleshooting

### Key Not Found Error

**Symptom**: `401 Unable to extract signing key`

**Root Cause**: JWKS endpoint returned empty key list or malformed JWK

**Solution**:
```bash
# Check key pairs are in database
docker-compose exec postgres psql -U root -d house_discovery -c \
  "SELECT kid, LENGTH(public_key) FROM auth_jwt_key_pairs;"

# If empty, restart auth service to trigger key generation
docker-compose restart auth-service
```

### Token Refresh Fails with "Refresh Token Invalid"

**Symptom**: `POST /refresh` returns `401 Refresh token invalid or expired`

**Root Cause**: Refresh token was revoked, expired, or corrupted

**Solution**:
- User must log in again via `/login`
- Check `REDIS_URL` is configured correctly if using Redis session cache

### Cookie Not Sent from Browser

**Symptom**: Auth works in Postman but fails in browser; cookies not appearing in requests

**Root Cause**: 
- Cross-origin request without `credentials: 'include'`
- Or frontend not configured with correct API base URL

**Solution** (frontend):
```javascript
// Axios configuration
const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true,  // Include cookies
  headers: {
    'Content-Type': 'application/json',
  }
})
```

### CORS Error: "Cookie from disallowed origin"

**Symptom**: Browser console: `Cross-Origin Request Blocked`

**Root Cause**: API Gateway `CORS_ORIGINS` env var doesn't include frontend origin

**Solution**:
```bash
# Update API Gateway config
export CORS_ORIGINS="http://localhost:5173,https://myapp.com"
docker-compose up -d api-gateway
```

---

## See Also

- [**API Gateway**](./api-gateway.md) — JWT verification, JWKS caching
- [**System Architecture**](../architecture/overview.md) — Auth flow in context
