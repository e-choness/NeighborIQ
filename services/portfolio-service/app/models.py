"""
SQLAlchemy ORM models for portfolio/domain.

Tables are prefixed with 'portfolio_' to maintain domain separation in the shared PostgreSQL instance.
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from shared.database.postgres import Base


class SavedHouse(Base):
    """
    User-saved houses in their portfolio.

    Domain: portfolio
    Prefix: portfolio_
    """

    __tablename__ = "portfolio_saved_houses"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign keys
    user_id = Column(
        Integer,
        ForeignKey("auth_users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    house_id = Column(
        Integer,
        ForeignKey("house_houses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Metadata
    notes = Column(String(512), nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    house = relationship("House", lazy="joined")

    __table_args__ = (
        Index("idx_portfolio_saved_houses_user", "user_id"),
        Index("idx_portfolio_saved_houses_house", "house_id"),
        Index("idx_portfolio_saved_houses_user_house", "user_id", "house_id"),
    )

    def __repr__(self):
        return f"<SavedHouse(id={self.id}, user_id={self.user_id}, house_id={self.house_id})>"
