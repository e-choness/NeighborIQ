"""
Request authentication — FastAPI dependencies that replace the old gateway.

Tokens arrive in the HttpOnly `access_token` cookie (browser) or an
`Authorization: Bearer` header (API clients) and are verified in-process
against the RS256 public key; no identity is ever read from request headers.
"""

from dataclasses import dataclass
from typing import Optional

import jwt as pyjwt
from fastapi import Depends, HTTPException, Request

from app.keys import keys
from app.tokens import verify_token


@dataclass(frozen=True)
class CurrentUser:
    id: int
    role: str

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def _token(request: Request) -> Optional[str]:
    token = request.cookies.get("access_token")
    if token:
        return token
    header = request.headers.get("Authorization", "")
    return header[7:] if header.startswith("Bearer ") else None


def optional_user(request: Request) -> Optional[CurrentUser]:
    """The caller if they sent a valid token, else None (never raises)."""
    token = _token(request)
    if not token:
        return None
    try:
        payload = verify_token(token, public_key_pem=keys.public_pem, token_type="access")
        return CurrentUser(id=int(payload["sub"]), role=payload.get("role", "user"))
    except (pyjwt.InvalidTokenError, ValueError, KeyError):
        return None


def current_user(request: Request) -> CurrentUser:
    token = _token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Missing access token")
    try:
        payload = verify_token(token, public_key_pem=keys.public_pem, token_type="access")
    except pyjwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}") from e
    return CurrentUser(id=int(payload["sub"]), role=payload.get("role", "user"))


def admin_user(user: CurrentUser = Depends(current_user)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user
