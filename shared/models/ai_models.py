"""
SQLAlchemy ORM models for AI insights domain.

Tables store ML model outputs (price predictions, rental yields)
and LLM-generated market narratives.

Domain prefix: house_ (shares the house domain namespace)
"""

from sqlalchemy import Column, Integer, String, DateTime, Numeric, Text, ForeignKey, Index
from sqlalchemy.sql import func

from shared.database.postgres import Base


class HousePricePrediction(Base):
    """
    XGBoost/LightGBM price prediction output for a house.

    One row per prediction run (a house may have multiple predictions over time).
    """

    __tablename__ = "house_price_predictions"

    id = Column(Integer, primary_key=True, index=True)
    house_id = Column(
        Integer,
        ForeignKey("house_houses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    predicted_price = Column(Integer, nullable=False)   # Point estimate (yuan)
    price_low = Column(Integer, nullable=False)          # 80% CI lower bound
    price_high = Column(Integer, nullable=False)         # 80% CI upper bound
    confidence = Column(Numeric(5, 4), nullable=False)   # 0.0000 – 1.0000
    model_version = Column(String(50), nullable=False)
    predicted_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_house_price_predictions_house", "house_id"),
        Index("idx_house_price_predictions_at", "predicted_at"),
    )

    def __repr__(self):
        return (
            f"<HousePricePrediction(house_id={self.house_id}, "
            f"predicted_price={self.predicted_price}, model={self.model_version})>"
        )


class HouseRentalYield(Base):
    """
    Formula-based rental yield estimate for a house.

    Computed as: annual_rent = area × regional_rate × 12
    One row per house (upserted on each compute run).
    """

    __tablename__ = "house_rental_yields"

    id = Column(Integer, primary_key=True, index=True)
    house_id = Column(
        Integer,
        ForeignKey("house_houses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    annual_rent = Column(Integer, nullable=False)          # Estimated annual rent (yuan)
    gross_yield = Column(Numeric(6, 4), nullable=False)    # e.g. 0.0523 = 5.23%
    net_yield = Column(Numeric(6, 4), nullable=False)      # After management costs
    computed_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("idx_rental_yields_house", "house_id"),)

    def __repr__(self):
        return (
            f"<HouseRentalYield(house_id={self.house_id}, "
            f"gross_yield={self.gross_yield}, net_yield={self.net_yield})>"
        )


class MarketInsight(Base):
    """
    LLM-generated market narrative for a city/region (once per day per city).

    The LLM receives pre-computed stats and produces a plain-language summary.
    Expires after 7 days so Celery Beat regenerates it.
    """

    __tablename__ = "house_market_insights"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=True)
    summary_text = Column(Text, nullable=False)   # LLM-generated narrative
    model_version = Column(String(50), nullable=False)
    computed_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)  # 7-day TTL

    __table_args__ = (
        Index("idx_market_insights_city", "city"),
        Index("idx_market_insights_computed_at", "computed_at"),
    )

    def __repr__(self):
        return (
            f"<MarketInsight(city={self.city}, region={self.region}, "
            f"computed_at={self.computed_at})>"
        )
