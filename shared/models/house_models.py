"""
SQLAlchemy ORM models for house domain.

Tables are prefixed with 'house_' to maintain domain separation in the shared PostgreSQL instance.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Numeric,
    Text,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from shared.database.postgres import Base


class House(Base):
    """
    House/Property listing.

    Domain: house
    Prefix: house_
    """

    __tablename__ = "house_houses"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    title = Column(String(255), nullable=False, index=True)
    community = Column(String(255), nullable=True, index=True)  # Neighbourhood
    city = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=False, index=True)  # District / borough
    street = Column(String(255), nullable=True, index=True)
    postal_code = Column(String(7), nullable=True, index=True)  # e.g. "M5V 2T6"

    # Property details
    property_type = Column(String(30), nullable=True, index=True)  # condo|townhouse|semi|detached
    price = Column(Integer, nullable=False, index=True)  # Asking price, CAD
    sqft = Column(Integer, nullable=True)  # Interior living area, ft²
    area = Column(Numeric(10, 2), nullable=True)  # Same area in m² (derived from sqft)
    rooms = Column(Integer, nullable=True)  # Bedrooms (0 = bachelor/studio)
    bathrooms = Column(Numeric(3, 1), nullable=True)
    parking = Column(Integer, nullable=True)
    floor = Column(Integer, nullable=True)
    decoration = Column(String(50), nullable=True)  # original|standard|renovated|luxury
    age = Column(Integer, nullable=True)  # Years since construction

    # Carrying costs — required for an honest cash-flow estimate
    condo_fee = Column(Integer, nullable=True)  # Monthly maintenance fee, CAD
    property_tax = Column(Integer, nullable=True)  # Annual, CAD

    # Listing lifecycle
    status = Column(String(20), nullable=False, default="active", server_default="active")
    listed_at = Column(DateTime(timezone=True), nullable=True)

    # Location (WGS-84 coordinates for OpenStreetMap)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)

    # Source
    url = Column(String(512), nullable=True, unique=True, index=True)  # Stable listing key
    images = Column(Text, nullable=True)  # JSON list stored as text
    source = Column(String(30), nullable=False, default="seed", server_default="seed")
    # 1 = generated demo data. The UI must label these listings as synthetic.
    is_synthetic = Column(Integer, nullable=False, default=0, server_default="0")

    # Metadata
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

    # Relationships
    price_history = relationship(
        "HousePriceHistory", back_populates="house", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_house_houses_city_region", "city", "region"),
        Index("idx_house_houses_price", "price"),
        Index("idx_house_houses_location", "latitude", "longitude"),
        Index("idx_house_houses_composite", "city", "region", "price"),
        Index("idx_house_houses_comps", "city", "property_type", "rooms"),
    )

    def __repr__(self):
        return f"<House(id={self.id}, title={self.title}, city={self.city}, price={self.price})>"


class HousePriceHistory(Base):
    """
    Historical price snapshots for a house.
    Used for AI/ML training and price trend analysis.

    Domain: house
    Prefix: house_
    """

    __tablename__ = "house_price_history"

    id = Column(Integer, primary_key=True, index=True)
    house_id = Column(
        Integer,
        ForeignKey("house_houses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    price = Column(Integer, nullable=False)  # CAD
    recorded_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationship
    house = relationship("House", back_populates="price_history")

    __table_args__ = (
        Index("idx_house_price_history_house_recorded", "house_id", "recorded_at"),
    )

    def __repr__(self):
        return f"<HousePriceHistory(house_id={self.house_id}, price={self.price}, recorded_at={self.recorded_at})>"


class Community(Base):
    """
    Neighborhood/community aggregate data.
    This is a normalized table; houses reference communities by name (or could be linked by ID).

    Domain: house
    Prefix: house_
    """

    __tablename__ = "house_communities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=False, index=True)
    street = Column(String(255), nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)

    # Aggregated stats
    house_count = Column(Integer, default=0, nullable=False)
    avg_price = Column(Numeric(15, 2), nullable=True)
    min_price = Column(Integer, nullable=True)
    max_price = Column(Integer, nullable=True)

    # Metadata
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_house_communities_city_region", "city", "region"),
        Index("idx_house_communities_location", "latitude", "longitude"),
    )

    def __repr__(self):
        return f"<Community(id={self.id}, name={self.name}, city={self.city}, avg_price={self.avg_price})>"


class School(Base):
    """
    School POI (Point of Interest).

    Domain: house
    Prefix: house_
    """

    __tablename__ = "house_schools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    level = Column(String(50), nullable=True)  # elementary|secondary|college|university
    osm_id = Column(String(32), nullable=True, unique=True)  # "node/123" — idempotent reloads
    address = Column(String(512), nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_house_schools_city", "city"),
        Index("idx_house_schools_location", "latitude", "longitude"),
    )


class Hospital(Base):
    """
    Hospital POI.

    Domain: house
    Prefix: house_
    """

    __tablename__ = "house_hospitals"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    hospital_type = Column(String(50), nullable=True)
    osm_id = Column(String(32), nullable=True, unique=True)
    address = Column(String(512), nullable=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_house_hospitals_city", "city"),
        Index("idx_house_hospitals_location", "latitude", "longitude"),
    )


class BusStop(Base):
    """
    Bus stop POI.

    Domain: house
    Prefix: house_
    """

    __tablename__ = "house_bus_stops"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    city = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=True)
    latitude = Column(Numeric(10, 8), nullable=True)
    longitude = Column(Numeric(11, 8), nullable=True)
    routes = Column(Text, nullable=True)  # JSON list of route numbers
    # bus|streetcar|subway|rail — the table holds all transit stops, not only buses
    mode = Column(String(20), nullable=True)
    osm_id = Column(String(32), nullable=True, unique=True)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_house_bus_stops_city", "city"),
        Index("idx_house_bus_stops_location", "latitude", "longitude"),
    )


class HouseSchoolLink(Base):
    """
    Junction table: House <-> School relationship (distance matrix).

    Domain: house
    Prefix: house_
    """

    __tablename__ = "house_school_links"

    id = Column(Integer, primary_key=True, index=True)
    house_id = Column(
        Integer,
        ForeignKey("house_houses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    school_id = Column(
        Integer,
        ForeignKey("house_schools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    distance_m = Column(Integer, nullable=False)  # Distance in meters

    __table_args__ = (
        Index("idx_house_school_links_house", "house_id"),
        Index("idx_house_school_links_school", "school_id"),
        Index("idx_house_school_links_composite", "house_id", "school_id"),
    )


class HouseHospitalLink(Base):
    """
    Junction table: House <-> Hospital relationship.

    Domain: house
    Prefix: house_
    """

    __tablename__ = "house_hospital_links"

    id = Column(Integer, primary_key=True, index=True)
    house_id = Column(
        Integer,
        ForeignKey("house_houses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hospital_id = Column(
        Integer,
        ForeignKey("house_hospitals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    distance_m = Column(Integer, nullable=False)

    __table_args__ = (
        Index("idx_house_hospital_links_house", "house_id"),
        Index("idx_house_hospital_links_hospital", "hospital_id"),
    )


class HouseBusLink(Base):
    """
    Junction table: House <-> BusStop relationship.

    Domain: house
    Prefix: house_
    """

    __tablename__ = "house_bus_links"

    id = Column(Integer, primary_key=True, index=True)
    house_id = Column(
        Integer,
        ForeignKey("house_houses.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bus_stop_id = Column(
        Integer,
        ForeignKey("house_bus_stops.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    distance_m = Column(Integer, nullable=False)

    __table_args__ = (
        Index("idx_house_bus_links_house", "house_id"),
        Index("idx_house_bus_links_bus", "bus_stop_id"),
    )


class RentBenchmark(Base):
    """
    Reference average monthly rent by city and bedroom count.

    Loaded from data/reference/rent_benchmarks.csv (CMHC Rental Market Survey
    format). Used as the default rent in valuation and cash-flow estimates; the
    user can always override it.

    Domain: house
    Prefix: house_
    """

    __tablename__ = "house_rent_benchmarks"

    id = Column(Integer, primary_key=True)
    city = Column(String(100), nullable=False)
    bedrooms = Column(Integer, nullable=False)  # 0 = bachelor; 3 = 3+
    avg_rent = Column(Integer, nullable=False)  # Monthly, CAD
    source = Column(String(255), nullable=False)
    survey_date = Column(String(20), nullable=True)  # e.g. "2024-10"

    __table_args__ = (UniqueConstraint("city", "bedrooms", name="uq_rent_benchmark_city_beds"),)
