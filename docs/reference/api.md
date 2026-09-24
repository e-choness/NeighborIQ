---
title: HTTP API
description: Every NeighborIQ API endpoint, generated from the OpenAPI snapshot.
outline: false
---

# HTTP API

Every endpoint of the `api` service. This page is generated from
[`services/api/openapi.json`](../../services/api/openapi.json), which CI checks against the code on every push,
so it cannot drift. A running instance serves interactive docs at `/docs` (Swagger UI) and the raw schema at
`/openapi.json`.

- **Base path:** `/api/v1`.
- **Auth:** send the `access_token` cookie set by `POST /api/v1/auth/login`, or `Authorization: Bearer <token>`.
  "Signed in" routes need any account; "Admin" routes need an address listed in `ADMIN_EMAILS`.
- **Errors:** a validation failure returns `422` with FastAPI's `detail` array. Other errors return
  `{"detail": "message"}`.
- **Money** is whole Canadian dollars. Inputs named `*_pct` are percentages (`4.5` means 4.5%).

<ApiReference />
