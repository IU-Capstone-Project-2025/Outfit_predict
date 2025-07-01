import os
import pytest
from app.core.config import Settings


def test_settings_parsing(monkeypatch):
    monkeypatch.setenv("POSTGRES_USER", "user")
    monkeypatch.setenv("POSTGRES_PASSWORD", "pass")
    monkeypatch.setenv("POSTGRES_DB", "db")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("Qdrant_URL", "http://qdrant")
    monkeypatch.setenv("Qdrant_API_KEY", "qkey")
    monkeypatch.setenv("MINIO_ENDPOINT", "localhost:9000")
    monkeypatch.setenv("MINIO_ACCESS_KEY", "minio-access")
    monkeypatch.setenv("MINIO_SECRET_KEY", "minio-secret")
    monkeypatch.setenv("MINIO_BUCKET", "mybucket")
    monkeypatch.setenv("MINIO_SECURE", "1")
    s = Settings()
    assert s.database_user == "user"
    assert s.database_password == "pass"
    assert s.database_db == "db"
    assert s.database_port == "5432"
    assert s.database_host == "localhost"
    assert s.qdrant_url == "http://qdrant"
    assert s.qdrant_api_key == "qkey"
    assert s.minio_endpoint == "localhost:9000"
    assert s.minio_access_key == "minio-access"
    assert s.minio_secret_key == "minio-secret"
    assert s.minio_bucket == "mybucket"
    assert s.minio_secure is True
    # Test default
    assert s.STORAGE_DIR.endswith("storage")
    assert s.api_prefix == "/api/v1"
    # Test property
    assert s.database_url_async.startswith(
        "postgresql+asyncpg://user:pass@localhost:5432/db")

