"""initial_schema

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-05-04 14:21:38

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # Create the PostgreSQL ENUM type first (create_type=False on the column means
    # SQLAlchemy won't auto-create it — we must do it explicitly here).
    # Note: PostgreSQL does not support CREATE TYPE IF NOT EXISTS for ENUM types,
    # so we use a DO block for idempotency.
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'userroleenum') THEN
                CREATE TYPE userroleenum AS ENUM ('user', 'admin');
            END IF;
        END $$;
        """
    )

    # Auth domain tables
    op.create_table('auth_users',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', postgresql.ENUM('user', 'admin', name='userroleenum', create_type=False), nullable=False),
        sa.Column('is_active', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_auth_users_email', 'auth_users', ['email'], unique=False)
    op.create_index('idx_auth_users_created_at', 'auth_users', ['created_at'], unique=False)
    op.create_table('auth_jwt_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('private_key_pem', sa.String(length=4096), nullable=False),
        sa.Column('public_key_pem', sa.String(length=2048), nullable=False),
        sa.Column('algorithm', sa.String(length=10), nullable=False),
        sa.Column('key_id', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_auth_jwt_keys_key_id', 'auth_jwt_keys', ['key_id'], unique=False)
    op.create_table('auth_refresh_tokens',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_revoked', sa.Integer(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_auth_refresh_tokens_user', 'auth_refresh_tokens', ['user_id'], unique=False)
    op.create_index('idx_auth_refresh_tokens_hash', 'auth_refresh_tokens', ['token_hash'], unique=True)
    
    # House domain tables
    op.create_table('house_communities',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=False),
        sa.Column('street', sa.String(length=255), nullable=True),
        sa.Column('latitude', postgresql.NUMERIC(precision=10, scale=8), nullable=True),
        sa.Column('longitude', postgresql.NUMERIC(precision=11, scale=8), nullable=True),
        sa.Column('house_count', sa.Integer(), nullable=False),
        sa.Column('avg_price', postgresql.NUMERIC(precision=15, scale=2), nullable=True),
        sa.Column('min_price', sa.Integer(), nullable=True),
        sa.Column('max_price', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_house_communities_city_region', 'house_communities', ['city', 'region'], unique=False)
    op.create_index('idx_house_communities_location', 'house_communities', ['latitude', 'longitude'], unique=False)
    
    op.create_table('house_houses',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('community', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=False),
        sa.Column('street', sa.String(length=255), nullable=True),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('area', postgresql.NUMERIC(precision=10, scale=2), nullable=True),
        sa.Column('rooms', sa.Integer(), nullable=True),
        sa.Column('floor', sa.Integer(), nullable=True),
        sa.Column('decoration', sa.String(length=50), nullable=True),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('latitude', postgresql.NUMERIC(precision=10, scale=8), nullable=True),
        sa.Column('longitude', postgresql.NUMERIC(precision=11, scale=8), nullable=True),
        sa.Column('url', sa.String(length=512), nullable=True),
        sa.Column('images', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_house_houses_city_region', 'house_houses', ['city', 'region'], unique=False)
    op.create_index('idx_house_houses_price', 'house_houses', ['price'], unique=False)
    op.create_index('idx_house_houses_location', 'house_houses', ['latitude', 'longitude'], unique=False)
    op.create_index('idx_house_houses_composite', 'house_houses', ['city', 'region', 'price'], unique=False)
    op.create_index('idx_house_houses_url', 'house_houses', ['url'], unique=True)
    
    op.create_table('house_price_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('house_id', sa.Integer(), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_house_price_history_house_recorded', 'house_price_history', ['house_id', 'recorded_at'], unique=False)
    
    op.create_table('house_schools',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('latitude', postgresql.NUMERIC(precision=10, scale=8), nullable=True),
        sa.Column('longitude', postgresql.NUMERIC(precision=11, scale=8), nullable=True),
        sa.Column('level', sa.String(length=50), nullable=True),
        sa.Column('address', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_house_schools_city', 'house_schools', ['city'], unique=False)
    op.create_index('idx_house_schools_location', 'house_schools', ['latitude', 'longitude'], unique=False)
    
    op.create_table('house_hospitals',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('latitude', postgresql.NUMERIC(precision=10, scale=8), nullable=True),
        sa.Column('longitude', postgresql.NUMERIC(precision=11, scale=8), nullable=True),
        sa.Column('hospital_type', sa.String(length=50), nullable=True),
        sa.Column('address', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_house_hospitals_city', 'house_hospitals', ['city'], unique=False)
    op.create_index('idx_house_hospitals_location', 'house_hospitals', ['latitude', 'longitude'], unique=False)
    
    op.create_table('house_bus_stops',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('latitude', postgresql.NUMERIC(precision=10, scale=8), nullable=True),
        sa.Column('longitude', postgresql.NUMERIC(precision=11, scale=8), nullable=True),
        sa.Column('routes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_house_bus_stops_city', 'house_bus_stops', ['city'], unique=False)
    op.create_index('idx_house_bus_stops_location', 'house_bus_stops', ['latitude', 'longitude'], unique=False)
    
    # Junction tables — names match ORM __tablename__ definitions
    op.create_table('house_school_links',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('house_id', sa.Integer(), nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=False),
        sa.Column('distance_m', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_house_school_links_house', 'house_school_links', ['house_id'], unique=False)
    op.create_index('idx_house_school_links_school', 'house_school_links', ['school_id'], unique=False)
    op.create_index('idx_house_school_links_composite', 'house_school_links', ['house_id', 'school_id'], unique=False)

    op.create_table('house_hospital_links',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('house_id', sa.Integer(), nullable=False),
        sa.Column('hospital_id', sa.Integer(), nullable=False),
        sa.Column('distance_m', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_house_hospital_links_house', 'house_hospital_links', ['house_id'], unique=False)
    op.create_index('idx_house_hospital_links_hospital', 'house_hospital_links', ['hospital_id'], unique=False)

    op.create_table('house_bus_links',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('house_id', sa.Integer(), nullable=False),
        sa.Column('bus_stop_id', sa.Integer(), nullable=False),
        sa.Column('distance_m', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_house_bus_links_house', 'house_bus_links', ['house_id'], unique=False)
    op.create_index('idx_house_bus_links_stop', 'house_bus_links', ['bus_stop_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_house_bus_links_stop', table_name='house_bus_links')
    op.drop_index('idx_house_bus_links_house', table_name='house_bus_links')
    op.drop_table('house_bus_links')
    op.drop_index('idx_house_hospital_links_hospital', table_name='house_hospital_links')
    op.drop_index('idx_house_hospital_links_house', table_name='house_hospital_links')
    op.drop_table('house_hospital_links')
    op.drop_index('idx_house_school_links_composite', table_name='house_school_links')
    op.drop_index('idx_house_school_links_school', table_name='house_school_links')
    op.drop_index('idx_house_school_links_house', table_name='house_school_links')
    op.drop_table('house_school_links')
    op.drop_index('idx_house_bus_stops_location', table_name='house_bus_stops')
    op.drop_index('idx_house_bus_stops_city', table_name='house_bus_stops')
    op.drop_table('house_bus_stops')
    op.drop_index('idx_house_hospitals_location', table_name='house_hospitals')
    op.drop_index('idx_house_hospitals_city', table_name='house_hospitals')
    op.drop_table('house_hospitals')
    op.drop_index('idx_house_schools_location', table_name='house_schools')
    op.drop_index('idx_house_schools_city', table_name='house_schools')
    op.drop_table('house_schools')
    op.drop_index('idx_house_price_history_house_recorded', table_name='house_price_history')
    op.drop_table('house_price_history')
    op.drop_index('idx_house_houses_url', table_name='house_houses')
    op.drop_index('idx_house_houses_composite', table_name='house_houses')
    op.drop_index('idx_house_houses_location', table_name='house_houses')
    op.drop_index('idx_house_houses_price', table_name='house_houses')
    op.drop_index('idx_house_houses_city_region', table_name='house_houses')
    op.drop_table('house_houses')
    op.drop_index('idx_house_communities_location', table_name='house_communities')
    op.drop_index('idx_house_communities_city_region', table_name='house_communities')
    op.drop_table('house_communities')
    op.drop_index('idx_auth_refresh_tokens_hash', table_name='auth_refresh_tokens')
    op.drop_index('idx_auth_refresh_tokens_user', table_name='auth_refresh_tokens')
    op.drop_table('auth_refresh_tokens')
    op.drop_index('idx_auth_jwt_keys_key_id', table_name='auth_jwt_keys')
    op.drop_table('auth_jwt_keys')
    op.drop_index('idx_auth_users_created_at', table_name='auth_users')
    op.drop_index('idx_auth_users_email', table_name='auth_users')
    op.drop_table('auth_users')
    op.execute("DROP TYPE IF EXISTS userroleenum")