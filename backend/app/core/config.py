from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # PostgreSQL
    database_url: str = Field(..., alias="DATABASE_URL")

    # MinIO
    minio_endpoint: str = Field(..., env="MINIO_ENDPOINT")  # host:port
    minio_access_key: str = Field(..., env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(..., env="MINIO_SECRET_KEY")
    minio_bucket: str = Field("images", env="MINIO_BUCKET")
    minio_secure: bool = Field(False, env="MINIO_SECURE")

    api_prefix: str = "/api/v1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:  # pragma: no cover
    return Settings()  # type: ignore[arg-type]
