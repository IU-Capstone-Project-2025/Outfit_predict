import os
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # PostgreSQL
    POSTGRES_USER: str = Field(..., env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(..., env="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(..., env="POSTGRES_DB")
    POSTGRES_PORT: str = Field(..., env="POSTGRES_PORT")
    POSTGRES_HOST: str = Field(..., env="POSTGRES_HOST")

    # Qdrant
    QDRANT_URL: str = Field(..., env="QDRANT_URL")
    QDRANT_API_KEY: str = Field(..., env="QDRANT_API_KEY")

    # MinIO
    MINIO_ENDPOINT: str = Field(..., env="MINIO_ENDPOINT")  # host:port
    MINIO_ACCESS_KEY: str = Field(..., env="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field(..., env="MINIO_SECRET_KEY")
    MINIO_BUCKET: str = Field("images", env="MINIO_BUCKET")
    MINIO_SECURE: bool = Field(False, env="MINIO_SECURE")

    SECRET_KEY: str = Field(..., env="SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Storage
    STORAGE_DIR: str = Field(default=os.path.join(os.getcwd(), "storage"))
    api_prefix: str = "/api/v1"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def database_url_async(self):
        return f"""postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"""  # noqa


@lru_cache
def get_settings() -> Settings:  # pragma: no cover
    return Settings()  # type: ignore[arg-type]
