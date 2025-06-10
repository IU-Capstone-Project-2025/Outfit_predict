from app.core.config import Settings, get_settings
from app.db.database import get_session
from app.storage.minio_client import MinioService


def get_settings_dep() -> Settings:  # alias to override easily
    return get_settings()


def get_minio() -> MinioService:
    return MinioService()


# re-export DB dependency so routers can write `Depends(get_db)`
get_db = get_session  # type: ignore[assignment]
