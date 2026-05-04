"""
JWT utilities for RS256 signing and verification.

Implements asymmetric RS256 JWT generation and validation.
The auth-service owns the private key; other services verify using the public key.
"""

import os
import json
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt as pyjwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
import hashlib
import secrets

ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def generate_rsa_keypair() -> tuple[str, str]:
    """
    Generate a new RS256 RSA key pair.

    Returns:
        Tuple of (private_key_pem, public_key_pem) as strings
    """
    # Generate 2048-bit RSA key pair
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    public_key = private_key.public_key()

    # Serialize to PEM format
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_key_pem, public_key_pem


def get_key_id(public_key_pem: str) -> str:
    """
    Generate a key ID from public key (SHA256 hash, hex-encoded).

    This uniquely identifies a key for the JWKS endpoint.
    """
    key_hash = hashlib.sha256(public_key_pem.encode()).hexdigest()
    return key_hash[:16]  # Truncate to 16 chars for brevity


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    private_key_pem: Optional[str] = None,
    key_id: Optional[str] = None,
) -> str:
    """
    Create a JWT access token (short-lived, 15 minutes).

    Args:
        subject: User ID or identifier (goes into "sub" claim)
        expires_delta: Override default expiration
        private_key_pem: RSA private key (PEM format)
        key_id: Key ID for the JWKS endpoint

    Returns:
        Encoded JWT string
    """
    if private_key_pem is None:
        private_key_pem = os.getenv("JWT_PRIVATE_KEY", "")
    if not private_key_pem:
        raise ValueError("JWT_PRIVATE_KEY not set")

    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }

    headers = {}
    if key_id:
        headers["kid"] = key_id

    token = pyjwt.encode(
        payload,
        private_key_pem,
        algorithm=ALGORITHM,
        headers=headers if headers else None,
    )
    return token


def create_refresh_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    private_key_pem: Optional[str] = None,
    key_id: Optional[str] = None,
) -> str:
    """
    Create a JWT refresh token (long-lived, 7 days).

    Refresh tokens are used to obtain new access tokens without re-authenticating.
    They should be rotated periodically and revoked on logout.
    """
    if private_key_pem is None:
        private_key_pem = os.getenv("JWT_PRIVATE_KEY", "")
    if not private_key_pem:
        raise ValueError("JWT_PRIVATE_KEY not set")

    if expires_delta is None:
        expires_delta = timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    now = datetime.now(timezone.utc)
    expire = now + expires_delta

    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "refresh",
        "jti": secrets.token_urlsafe(16),  # JWT ID for revocation tracking
    }

    headers = {}
    if key_id:
        headers["kid"] = key_id

    token = pyjwt.encode(
        payload,
        private_key_pem,
        algorithm=ALGORITHM,
        headers=headers if headers else None,
    )
    return token


def verify_token(
    token: str,
    public_key_pem: Optional[str] = None,
    token_type: str = "access",
) -> dict:
    """
    Verify a JWT token and return its claims.

    Args:
        token: JWT token string
        public_key_pem: RSA public key (PEM format)
        token_type: Expected type ("access" or "refresh")

    Returns:
        Decoded payload dictionary

    Raises:
        jwt.InvalidTokenError: If token is invalid or expired
    """
    if public_key_pem is None:
        public_key_pem = os.getenv("JWT_PUBLIC_KEY", "")
    if not public_key_pem:
        raise ValueError("JWT_PUBLIC_KEY not set")

    try:
        payload = pyjwt.decode(
            token,
            public_key_pem,
            algorithms=[ALGORITHM],
        )

        # Verify token type
        if payload.get("type") != token_type:
            raise pyjwt.InvalidTokenError(f"Expected token type '{token_type}'")

        return payload
    except pyjwt.ExpiredSignatureError:
        raise pyjwt.InvalidTokenError("Token has expired")
    except pyjwt.InvalidTokenError as e:
        raise e


def get_jwks_from_public_key(public_key_pem: str, key_id: str) -> dict:
    """
    Convert a public key to JWKS format for the .well-known/jwks.json endpoint.

    JWKS (JSON Web Key Set) is a standard format for exposing public keys.

    Returns:
        JWKS-formatted dictionary
    """
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    public_key = load_pem_public_key(
        public_key_pem.encode(),
        backend=default_backend(),
    )

    # Extract RSA components
    public_numbers = public_key.public_numbers()

    # Convert to base64url-encoded integers (JWKS format)
    import base64

    def int_to_base64url(val: int, length: int) -> str:
        val_bytes = val.to_bytes(length, byteorder="big")
        return base64.urlsafe_b64encode(val_bytes).decode().rstrip("=")

    n_len = (public_numbers.n.bit_length() + 7) // 8
    e_len = (public_numbers.e.bit_length() + 7) // 8

    jwk = {
        "kty": "RSA",
        "use": "sig",
        "kid": key_id,
        "n": int_to_base64url(public_numbers.n, n_len),
        "e": int_to_base64url(public_numbers.e, e_len),
        "alg": ALGORITHM,
    }

    return jwk


def hash_token(token: str) -> str:
    """
    Hash a token for secure storage.

    Used for storing refresh tokens in the database (not storing plaintext).
    """
    return hashlib.sha256(token.encode()).hexdigest()
