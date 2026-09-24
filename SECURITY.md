# Security policy

## Reporting a vulnerability

Please **do not open a public issue** for security problems. Report them privately through GitHub:
**Security → Report a vulnerability** on this repository
([private vulnerability reporting](https://github.com/e-choness/NeighborIQ/security/advisories/new)).

Include what an attacker can do, the steps to reproduce, and the affected version or commit. You will get an
acknowledgement within a week. Fixes are released as soon as they are ready, and the advisory credits you
unless you ask otherwise.

## Supported versions

Only the latest commit on `main` receives fixes.

## Scope

In scope: the API (`services/api`), the workers, the frontend, the Compose and Caddy configuration shipped here.

Out of scope: vulnerabilities in third-party dependencies with no demonstrated impact on NeighborIQ (report
those upstream), and deployments that ignore [the production checklist](docs/DEPLOYMENT.md#checklist) (for
example, running without `JWT_PRIVATE_KEY` or with the development ports exposed).

## Design notes for reviewers

- Authentication: RS256 JWTs in `HttpOnly`, `SameSite=Strict` cookies; refresh tokens rotated on use and
  stored as SHA-256 hashes. Every protected route verifies the token in-process (`services/api/app/security.py`).
- Authorisation: admin routes require `role=admin` from the token. The role is granted only to
  `ADMIN_EMAILS` at sign-up.
- Outbound requests: partner feed URLs are restricted to `https` hosts in `FEED_ALLOWED_HOSTS`. Open-data URLs
  come from the source registry, not from users.
- Rate limits on authentication endpoints (`AUTH_RATE_LIMIT`).
