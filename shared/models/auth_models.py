"""
SQLAlchemy ORM models for auth domain.

Tables are prefixed with 'auth_' to maintain domain separation in the shared PostgreSQL instance.
"""

from sqlalchemy import Column, Integer, String, DateTime, Enum, Index
from sqlalchemy.sql import func
import enum

from shared.database.postgres import Base


class UserRoleEnum(str, enum.Enum):
    """User roles in the system."""

    USER = "user"
    ADMIN = "admin"


class User(Base):
    """
    User account and identity.

    Domain: auth
    Prefix: auth_
    """

    __tablename__ = "auth_users"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Identity
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)

    # Metadata
    role = Column(
        Enum(UserRoleEnum, values_callable=lambda obj: [e.value for e in obj]),
        default=UserRoleEnum.USER,
        nullable=False,
    )
    # SQLite compatibility
    is_active = Column(Integer, default=1, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("idx_auth_users_email", "email"),
        Index("idx_auth_users_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class JWTKeyPair(Base):
    """
    RS256 public/private key pair for JWT signing.

    The auth-service generates this on first startup and stores the private key here.
    The public key is exposed at GET /api/v1/auth/.well-known/jwks.json for other services.

    Domain: auth
    Prefix: auth_
    """

    __tablename__ = "auth_jwt_keys"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Key data (PEM format)
    private_key_pem = Column(String(4096), nullable=False)
    public_key_pem = Column(String(2048), nullable=False)

    # Metadata
    algorithm = Column(String(10), default="RS256", nullable=False)
    key_id = Column(String(64), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at = Column(DateTime(timezone=True),
                        nullable=True)  # For key rotation
    is_active = Column(Integer, default=1, nullable=False)

    def __repr__(self):
        return f"<JWTKeyPair(id={self.id}, algorithm={self.algorithm}, key_id={self.key_id})>"


class RefreshToken(Base):
    """
    Issued refresh tokens (for token revocation tracking).

    In a simple implementation, we just store them to support explicit logout.
    In a more sophisticated system, we could track token family, device info, etc.

    Domain: auth
    Prefix: auth_
    """

    __tablename__ = "auth_refresh_tokens"

    # Primary key
    id = Column(Integer, primary_key=True)

    # Foreign key
    user_id = Column(Integer, nullable=False, index=True)

    # Token metadata
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    is_revoked = Column(Integer, default=0, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id})>"
