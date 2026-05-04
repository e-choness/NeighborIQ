from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    service_name: str = "neighbor-iq-service"
    database_url: str = "postgresql+asyncpg://root:root@postgres:5432/house_discovery"
    redis_url: str = "redis://redis:6379/0"
    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> ServiceSettings:
    return ServiceSettings()
