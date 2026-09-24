"""open_data

Revision ID: 005_open_data
Revises: 004_portfolio_saved_houses
Create Date: 2026-09-24 00:00:00

Tables for public open data (see services/ingestion-worker/ingestion/opendata):

- od_areas            neighbourhood polygons (PostGIS) per city
- od_area_stats       long-format metrics per area (census, crime, permits…)
- od_census_points    census dissemination areas: representative point + values
- od_properties       municipal assessment roll records (real properties)
- od_permits          issued building permits (future supply)
- od_indicators       time series (Bank of Canada rates, StatCan tables)
- od_load_log         provenance: what was loaded, when, under which licence

house_houses.area_id and od_properties.area_id link rows to their polygon;
house_bus_stops.weekday_departures carries GTFS service frequency.
"""

from typing import Union

from alembic import op

revision: str = "005_open_data"
down_revision: Union[str, None] = "004_portfolio_saved_houses"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    op.execute("""
        CREATE TABLE od_areas (
            id          SERIAL PRIMARY KEY,
            city        VARCHAR(100) NOT NULL,
            name        VARCHAR(255) NOT NULL,
            code        VARCHAR(64),
            source      VARCHAR(64)  NOT NULL,
            geom        geometry(MultiPolygon, 4326) NOT NULL,
            latitude    DOUBLE PRECISION,
            longitude   DOUBLE PRECISION,
            area_km2    DOUBLE PRECISION,
            loaded_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_od_areas_city_name UNIQUE (city, name)
        )
    """)
    op.execute("CREATE INDEX idx_od_areas_geom ON od_areas USING GIST (geom)")
    op.execute("CREATE INDEX idx_od_areas_city ON od_areas (LOWER(city))")

    op.execute("""
        CREATE TABLE od_area_stats (
            area_id  INTEGER NOT NULL REFERENCES od_areas(id) ON DELETE CASCADE,
            metric   VARCHAR(64) NOT NULL,
            period   VARCHAR(16) NOT NULL DEFAULT '',
            value    DOUBLE PRECISION,
            source   VARCHAR(64) NOT NULL,
            PRIMARY KEY (area_id, metric, period)
        )
    """)

    op.execute("""
        CREATE TABLE od_census_points (
            geo_code   VARCHAR(32) PRIMARY KEY,   -- DAUID
            latitude   DOUBLE PRECISION NOT NULL,
            longitude  DOUBLE PRECISION NOT NULL,
            population INTEGER,
            values     JSONB NOT NULL DEFAULT '{}'::jsonb
        )
    """)
    op.execute(
        "CREATE INDEX idx_od_census_points_geom ON od_census_points "
        "USING GIST (ST_SetSRID(ST_MakePoint(longitude, latitude), 4326))"
    )

    op.execute("""
        CREATE TABLE od_properties (
            id                 SERIAL PRIMARY KEY,
            city               VARCHAR(100) NOT NULL,
            source             VARCHAR(64)  NOT NULL,
            source_id          VARCHAR(64)  NOT NULL,
            address            VARCHAR(255),
            postal_code        VARCHAR(7),
            latitude           DOUBLE PRECISION,
            longitude          DOUBLE PRECISION,
            area_id            INTEGER REFERENCES od_areas(id) ON DELETE SET NULL,
            neighbourhood      VARCHAR(255),
            property_class     VARCHAR(64),
            zoning             VARCHAR(64),
            year_built         INTEGER,
            units              INTEGER,
            floor_area_sqft    INTEGER,
            lot_size_sqft      INTEGER,
            land_value         BIGINT,
            improvement_value  BIGINT,
            assessed_value     BIGINT,
            previous_value     BIGINT,
            tax_levy           INTEGER,
            assessment_year    INTEGER,
            loaded_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_od_properties_source UNIQUE (source, source_id)
        )
    """)
    op.execute("CREATE INDEX idx_od_properties_city ON od_properties (LOWER(city))")
    op.execute("CREATE INDEX idx_od_properties_area ON od_properties (area_id)")
    op.execute("CREATE INDEX idx_od_properties_address ON od_properties (LOWER(address) text_pattern_ops)")
    op.execute(
        "CREATE INDEX idx_od_properties_geom ON od_properties "
        "USING GIST (ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)) WHERE latitude IS NOT NULL"
    )

    op.execute("""
        CREATE TABLE od_permits (
            id          SERIAL PRIMARY KEY,
            city        VARCHAR(100) NOT NULL,
            source      VARCHAR(64)  NOT NULL,
            source_id   VARCHAR(64)  NOT NULL,
            issued_date DATE,
            kind        VARCHAR(128),
            units       INTEGER,
            value       BIGINT,
            latitude    DOUBLE PRECISION,
            longitude   DOUBLE PRECISION,
            area_id     INTEGER REFERENCES od_areas(id) ON DELETE SET NULL,
            CONSTRAINT uq_od_permits_source UNIQUE (source, source_id)
        )
    """)

    op.execute("""
        CREATE TABLE od_indicators (
            series   VARCHAR(64) NOT NULL,
            date     DATE        NOT NULL,
            value    DOUBLE PRECISION NOT NULL,
            label    VARCHAR(255),
            unit     VARCHAR(32),
            source   VARCHAR(64) NOT NULL,
            PRIMARY KEY (series, date)
        )
    """)

    op.execute("""
        CREATE TABLE od_load_log (
            id         SERIAL PRIMARY KEY,
            source     VARCHAR(64) NOT NULL,
            loaded_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            row_count  INTEGER,
            licence     VARCHAR(255),
            attribution VARCHAR(512),
            status     VARCHAR(16) NOT NULL,
            message    TEXT
        )
    """)

    op.execute(
        "ALTER TABLE house_houses ADD COLUMN area_id INTEGER REFERENCES od_areas(id) ON DELETE SET NULL"
    )
    op.execute("CREATE INDEX idx_house_houses_area ON house_houses (area_id)")
    op.execute("ALTER TABLE house_bus_stops ADD COLUMN weekday_departures INTEGER")
    # External ids now include GTFS keys ("gtfs:<feed>:<stop_id>"), not only OSM ids
    op.execute("ALTER TABLE house_bus_stops ALTER COLUMN osm_id TYPE VARCHAR(64)")


def downgrade() -> None:
    op.execute("ALTER TABLE house_bus_stops DROP COLUMN weekday_departures")
    op.execute("DROP INDEX IF EXISTS idx_house_houses_area")
    op.execute("ALTER TABLE house_houses DROP COLUMN area_id")
    for table in (
        "od_load_log",
        "od_indicators",
        "od_permits",
        "od_properties",
        "od_census_points",
        "od_area_stats",
        "od_areas",
    ):
        op.execute(f"DROP TABLE IF EXISTS {table}")
