import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # PostgreSQL
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: str
    POSTGRES_HOST: str

    # Qdrant
    QDRANT_URL: str
    QDRANT_API_KEY: str

    # MinIO
    MINIO_ENDPOINT: str  # host:port
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "images"
    MINIO_SECURE: bool = False

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Storage
    STORAGE_DIR: str = Field(default=os.path.join(os.getcwd(), "storage"))
    api_prefix: str = "/api/v1"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url_async(self):
        db_url = (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:"
            f"{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )
        print(db_url)
        return db_url


@lru_cache
def get_settings() -> Settings:  # pragma: no cover
    return Settings()  # type: ignore[arg-type]
