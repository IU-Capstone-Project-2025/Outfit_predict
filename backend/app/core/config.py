import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # PostgreSQL
    database_user: str = Field(..., alias="POSTGRES_USER")
    database_password: str = Field(..., alias="POSTGRES_PASSWORD")
    database_db: str = Field(..., alias="POSTGRES_DB")
    database_port: str = Field(..., alias="POSTGRES_PORT")
    database_host: str = Field(..., alias="POSTGRES_HOST")

    # Qdrant
    qdrant_url: str = Field(..., alias="Qdrant_URL")
    qdrant_api_key: str = Field(..., alias="Qdrant_API_KEY")

    # MinIO
    minio_endpoint: str = Field(..., env="MINIO_ENDPOINT")  # host:port
    minio_access_key: str = Field(..., env="MINIO_ACCESS_KEY")
    minio_secret_key: str = Field(..., env="MINIO_SECRET_KEY")
    minio_bucket: str = Field("images", env="MINIO_BUCKET")
    minio_secure: bool = Field(False, env="MINIO_SECURE")

    # Storage
    STORAGE_DIR: str = Field(default=os.path.join(os.getcwd(), "storage"))

    api_prefix: str = "/api/v1"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url_async(self):
        return f"postgresql+asyncpg://{self.database_user}:{self.database_password}@{self.database_host}:{self.database_port}/{self.database_db}"


@lru_cache
def get_settings() -> Settings:  # pragma: no cover
    return Settings()  # type: ignore[arg-type]
