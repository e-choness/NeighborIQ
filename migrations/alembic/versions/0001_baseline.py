"""baseline

Revision ID: 0001_baseline
Revises:
Create Date: 2026-09-25 00:00:00

The whole schema as of release 0.3.0, in one step. It replaces revisions
001_initial_schema … 005_open_data, which built the legacy (pre-Canada) schema
and then rewrote it; this revision produces the same tables, columns,
constraints and indexes (checked in shared/tests/test_migrations.py).

A database that was migrated to 005_open_data is adopted automatically:
migrations/alembic/env.py re-stamps it as this revision before upgrading.

Tables by domain:
  auth_*       accounts, refresh tokens, development signing keys
  house_*      listings, price history, neighbourhoods, amenities, rent benchmarks,
               derived yields/predictions/market summaries
  portfolio_*  saved listings with notes and cash-flow assumptions
  od_*         public open data: areas (PostGIS), area metrics, census points,
               assessment rolls, permits, indicators, load log
"""

from typing import Union

from alembic import op

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None

TABLES = (
    # dependants first (drop order)
    "portfolio_saved_houses",
    "house_bus_links",
    "house_hospital_links",
    "house_school_links",
    "house_price_history",
    "house_price_predictions",
    "house_rental_yields",
    "house_houses",
    "house_bus_stops",
    "house_hospitals",
    "house_schools",
    "house_communities",
    "house_market_insights",
    "house_rent_benchmarks",
    "od_area_stats",
    "od_properties",
    "od_permits",
    "od_areas",
    "od_census_points",
    "od_indicators",
    "od_load_log",
    "auth_refresh_tokens",
    "auth_jwt_keys",
    "auth_users",
)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # ── Accounts ────────────────────────────────────────────────────────────
    op.execute("CREATE TYPE userroleenum AS ENUM ('user', 'admin')")
    op.execute("""
        CREATE TABLE auth_users (
            id             SERIAL PRIMARY KEY,
            email          VARCHAR(255) NOT NULL,
            name           VARCHAR(255),
            password_hash  VARCHAR(255) NOT NULL,
            role           userroleenum NOT NULL,
            is_active      INTEGER NOT NULL,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_auth_users_email ON auth_users (email)")
    op.execute("CREATE INDEX idx_auth_users_created_at ON auth_users (created_at)")

    op.execute("""
        CREATE TABLE auth_refresh_tokens (
            id          SERIAL PRIMARY KEY,
            user_id     INTEGER NOT NULL,
            token_hash  VARCHAR(255) NOT NULL,
            expires_at  TIMESTAMPTZ NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            is_revoked  INTEGER NOT NULL,
            revoked_at  TIMESTAMPTZ
        )
    """)
    op.execute("CREATE UNIQUE INDEX idx_auth_refresh_tokens_hash ON auth_refresh_tokens (token_hash)")
    op.execute("CREATE INDEX idx_auth_refresh_tokens_user ON auth_refresh_tokens (user_id)")

    op.execute("""
        CREATE TABLE auth_jwt_keys (
            id               SERIAL PRIMARY KEY,
            private_key_pem  VARCHAR(4096) NOT NULL,
            public_key_pem   VARCHAR(2048) NOT NULL,
            algorithm        VARCHAR(10) NOT NULL,
            key_id           VARCHAR(64) NOT NULL,
            created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at       TIMESTAMPTZ,
            is_active        INTEGER NOT NULL
        )
    """)
    op.execute("CREATE INDEX idx_auth_jwt_keys_key_id ON auth_jwt_keys (key_id)")

    # ── Open data (listings reference od_areas) ─────────────────────────────
    op.execute("""
        CREATE TABLE od_areas (
            id         SERIAL PRIMARY KEY,
            city       VARCHAR(100) NOT NULL,
            name       VARCHAR(255) NOT NULL,
            code       VARCHAR(64),
            source     VARCHAR(64)  NOT NULL,
            geom       geometry(MultiPolygon, 4326) NOT NULL,
            latitude   DOUBLE PRECISION,
            longitude  DOUBLE PRECISION,
            area_km2   DOUBLE PRECISION,
            loaded_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
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
            geo_code    VARCHAR(32) PRIMARY KEY,   -- dissemination area (DAUID)
            latitude    DOUBLE PRECISION NOT NULL,
            longitude   DOUBLE PRECISION NOT NULL,
            population  INTEGER,
            values      JSONB NOT NULL DEFAULT '{}'::jsonb
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
            id           SERIAL PRIMARY KEY,
            city         VARCHAR(100) NOT NULL,
            source       VARCHAR(64)  NOT NULL,
            source_id    VARCHAR(64)  NOT NULL,
            issued_date  DATE,
            kind         VARCHAR(128),
            units        INTEGER,
            value        BIGINT,
            latitude     DOUBLE PRECISION,
            longitude    DOUBLE PRECISION,
            area_id      INTEGER REFERENCES od_areas(id) ON DELETE SET NULL,
            CONSTRAINT uq_od_permits_source UNIQUE (source, source_id)
        )
    """)

    op.execute("""
        CREATE TABLE od_indicators (
            series  VARCHAR(64) NOT NULL,
            date    DATE        NOT NULL,
            value   DOUBLE PRECISION NOT NULL,
            label   VARCHAR(255),
            unit    VARCHAR(32),
            source  VARCHAR(64) NOT NULL,
            PRIMARY KEY (series, date)
        )
    """)

    op.execute("""
        CREATE TABLE od_load_log (
            id           SERIAL PRIMARY KEY,
            source       VARCHAR(64) NOT NULL,
            loaded_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            row_count    INTEGER,
            licence      VARCHAR(255),
            attribution  VARCHAR(512),
            status       VARCHAR(16) NOT NULL,
            message      TEXT
        )
    """)

    # ── Listings ────────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE house_houses (
            id             SERIAL PRIMARY KEY,
            title          VARCHAR(255) NOT NULL,
            -- location
            city           VARCHAR(100) NOT NULL,
            region         VARCHAR(100) NOT NULL,
            community      VARCHAR(255),
            street         VARCHAR(255),
            postal_code    VARCHAR(7),
            latitude       NUMERIC(10, 8),
            longitude      NUMERIC(11, 8),
            area_id        INTEGER REFERENCES od_areas(id) ON DELETE SET NULL,
            -- property
            property_type  VARCHAR(30),
            rooms          INTEGER,
            bathrooms      NUMERIC(3, 1),
            sqft           INTEGER,
            area           NUMERIC(10, 2),
            parking        INTEGER,
            floor          INTEGER,
            age            INTEGER,
            decoration     VARCHAR(50),
            -- money (CAD)
            price          INTEGER NOT NULL,
            condo_fee      INTEGER,
            property_tax   INTEGER,
            -- lifecycle and provenance
            status         VARCHAR(20) NOT NULL DEFAULT 'active',
            listed_at      TIMESTAMPTZ,
            url            VARCHAR(512),
            images         TEXT,
            source         VARCHAR(30) NOT NULL DEFAULT 'seed',
            is_synthetic   INTEGER NOT NULL DEFAULT 0,
            is_active      INTEGER NOT NULL,
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE UNIQUE INDEX idx_house_houses_url ON house_houses (url)")
    op.execute("CREATE INDEX idx_house_houses_price ON house_houses (price)")
    op.execute("CREATE INDEX idx_house_houses_city_region ON house_houses (city, region)")
    op.execute("CREATE INDEX idx_house_houses_composite ON house_houses (city, region, price)")
    op.execute("CREATE INDEX idx_house_houses_comps ON house_houses (city, property_type, rooms)")
    op.execute("CREATE INDEX idx_house_houses_location ON house_houses (latitude, longitude)")
    op.execute("CREATE INDEX idx_house_houses_area ON house_houses (area_id)")
    op.execute("CREATE INDEX ix_house_houses_postal_code ON house_houses (postal_code)")
    op.execute("CREATE INDEX ix_house_houses_property_type ON house_houses (property_type)")

    op.execute("""
        CREATE TABLE house_price_history (
            id           SERIAL PRIMARY KEY,
            house_id     INTEGER NOT NULL,
            price        INTEGER NOT NULL,
            recorded_at  TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE INDEX idx_house_price_history_house_recorded ON house_price_history (house_id, recorded_at)"
    )

    op.execute("""
        CREATE TABLE house_communities (
            id           SERIAL PRIMARY KEY,
            name         VARCHAR(255) NOT NULL,
            city         VARCHAR(100) NOT NULL,
            region       VARCHAR(100) NOT NULL,
            street       VARCHAR(255),
            latitude     NUMERIC(10, 8),
            longitude    NUMERIC(11, 8),
            house_count  INTEGER NOT NULL,
            avg_price    NUMERIC(15, 2),
            min_price    INTEGER,
            max_price    INTEGER,
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX idx_house_communities_city_region ON house_communities (city, region)")
    op.execute("CREATE INDEX idx_house_communities_location ON house_communities (latitude, longitude)")

    # Amenities (OpenStreetMap; stops also from GTFS) and their links to listings
    op.execute("""
        CREATE TABLE house_schools (
            id          SERIAL PRIMARY KEY,
            name        VARCHAR(255) NOT NULL,
            city        VARCHAR(100) NOT NULL,
            region      VARCHAR(100),
            latitude    NUMERIC(10, 8),
            longitude   NUMERIC(11, 8),
            level       VARCHAR(50),
            address     VARCHAR(512),
            osm_id      VARCHAR(32),
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_house_schools_osm_id UNIQUE (osm_id)
        )
    """)
    op.execute("CREATE INDEX idx_house_schools_city ON house_schools (city)")
    op.execute("CREATE INDEX idx_house_schools_location ON house_schools (latitude, longitude)")

    op.execute("""
        CREATE TABLE house_hospitals (
            id             SERIAL PRIMARY KEY,
            name           VARCHAR(255) NOT NULL,
            city           VARCHAR(100) NOT NULL,
            region         VARCHAR(100),
            latitude       NUMERIC(10, 8),
            longitude      NUMERIC(11, 8),
            hospital_type  VARCHAR(50),
            address        VARCHAR(512),
            osm_id         VARCHAR(32),
            created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_house_hospitals_osm_id UNIQUE (osm_id)
        )
    """)
    op.execute("CREATE INDEX idx_house_hospitals_city ON house_hospitals (city)")
    op.execute("CREATE INDEX idx_house_hospitals_location ON house_hospitals (latitude, longitude)")

    op.execute("""
        CREATE TABLE house_bus_stops (
            id                  SERIAL PRIMARY KEY,
            name                VARCHAR(255) NOT NULL,
            city                VARCHAR(100) NOT NULL,
            region              VARCHAR(100),
            latitude            NUMERIC(10, 8),
            longitude           NUMERIC(11, 8),
            routes              TEXT,
            mode                VARCHAR(20),
            osm_id              VARCHAR(64),   -- "node/123" or "gtfs:<feed>:<stop_id>"
            weekday_departures  INTEGER,
            created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_house_bus_stops_osm_id UNIQUE (osm_id)
        )
    """)
    op.execute("CREATE INDEX idx_house_bus_stops_city ON house_bus_stops (city)")
    op.execute("CREATE INDEX idx_house_bus_stops_location ON house_bus_stops (latitude, longitude)")

    for table, other in (
        ("house_school_links", "school_id"),
        ("house_hospital_links", "hospital_id"),
        ("house_bus_links", "bus_stop_id"),
    ):
        op.execute(f"""
            CREATE TABLE {table} (
                id          SERIAL PRIMARY KEY,
                house_id    INTEGER NOT NULL,
                {other}     INTEGER NOT NULL,
                distance_m  INTEGER NOT NULL
            )
        """)
    op.execute("CREATE INDEX idx_house_school_links_house ON house_school_links (house_id)")
    op.execute("CREATE INDEX idx_house_school_links_school ON house_school_links (school_id)")
    op.execute("CREATE INDEX idx_house_school_links_composite ON house_school_links (house_id, school_id)")
    op.execute("CREATE INDEX idx_house_hospital_links_house ON house_hospital_links (house_id)")
    op.execute("CREATE INDEX idx_house_hospital_links_hospital ON house_hospital_links (hospital_id)")
    op.execute("CREATE INDEX idx_house_bus_links_house ON house_bus_links (house_id)")
    op.execute("CREATE INDEX idx_house_bus_links_stop ON house_bus_links (bus_stop_id)")

    op.execute("""
        CREATE TABLE house_rent_benchmarks (
            id           SERIAL PRIMARY KEY,
            city         VARCHAR(100) NOT NULL,
            bedrooms     INTEGER NOT NULL,           -- 0 = bachelor, 3 = 3+
            avg_rent     INTEGER NOT NULL,           -- monthly CAD
            source       VARCHAR(255) NOT NULL,
            survey_date  VARCHAR(20),
            CONSTRAINT uq_rent_benchmark_city_beds UNIQUE (city, bedrooms)
        )
    """)

    # ── Derived analytics (insights-worker) ─────────────────────────────────
    op.execute("""
        CREATE TABLE house_price_predictions (
            id               SERIAL PRIMARY KEY,
            house_id         INTEGER NOT NULL REFERENCES house_houses(id) ON DELETE CASCADE,
            predicted_price  INTEGER NOT NULL,
            price_low        INTEGER NOT NULL,
            price_high       INTEGER NOT NULL,
            confidence       NUMERIC(5, 4) NOT NULL,
            model_version    VARCHAR(50) NOT NULL,
            predicted_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_price_prediction_house_model UNIQUE (house_id, model_version)
        )
    """)
    op.execute("CREATE INDEX idx_house_price_predictions_house ON house_price_predictions (house_id)")
    op.execute("CREATE INDEX idx_house_price_predictions_at ON house_price_predictions (predicted_at)")

    op.execute("""
        CREATE TABLE house_rental_yields (
            id           SERIAL PRIMARY KEY,
            house_id     INTEGER NOT NULL REFERENCES house_houses(id) ON DELETE CASCADE,
            annual_rent  INTEGER NOT NULL,
            gross_yield  NUMERIC(6, 4) NOT NULL,
            net_yield    NUMERIC(6, 4) NOT NULL,
            computed_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_rental_yields_house UNIQUE (house_id)
        )
    """)
    op.execute("CREATE INDEX idx_rental_yields_house ON house_rental_yields (house_id)")

    op.execute("""
        CREATE TABLE house_market_insights (
            id             SERIAL PRIMARY KEY,
            city           VARCHAR(100) NOT NULL,
            region         VARCHAR(100),
            summary_text   TEXT NOT NULL,
            model_version  VARCHAR(50) NOT NULL,
            computed_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at     TIMESTAMPTZ
        )
    """)
    op.execute("CREATE INDEX idx_market_insights_city ON house_market_insights (city)")
    op.execute("CREATE INDEX idx_market_insights_computed_at ON house_market_insights (computed_at)")

    # ── Portfolio ───────────────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE portfolio_saved_houses (
            id           SERIAL PRIMARY KEY,
            user_id      INTEGER NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
            house_id     INTEGER NOT NULL REFERENCES house_houses(id) ON DELETE CASCADE,
            notes        VARCHAR(512),
            assumptions  TEXT,                        -- JSON: cash-flow inputs last used
            created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at   TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    op.execute(
        "CREATE UNIQUE INDEX uq_portfolio_saved_houses_user_house ON portfolio_saved_houses (user_id, house_id)"
    )
    op.execute("CREATE INDEX idx_portfolio_saved_houses_user ON portfolio_saved_houses (user_id)")
    op.execute("CREATE INDEX idx_portfolio_saved_houses_house ON portfolio_saved_houses (house_id)")
    op.execute("CREATE INDEX ix_portfolio_saved_houses_id ON portfolio_saved_houses (id)")
    op.execute("CREATE INDEX ix_portfolio_saved_houses_user_id ON portfolio_saved_houses (user_id)")
    op.execute("CREATE INDEX ix_portfolio_saved_houses_house_id ON portfolio_saved_houses (house_id)")


def downgrade() -> None:
    for table in TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    op.execute("DROP TYPE IF EXISTS userroleenum")
