from uuid import uuid4

from app.core.config import get_settings
from minio import Minio
from minio.error import S3Error

settings = get_settings()


class MinioService:
    def __init__(self) -> None:
        self.client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    # --- write --------------------------------------------------------------
    def save_file(self, data: bytes, content_type: str | None = None) -> str:
        """Save raw bytes into MinIO and return generated object name."""
        import io

        object_name = f"{uuid4().hex}"
        self.client.put_object(
            self.bucket,
            object_name,
            data=io.BytesIO(data),  # wrap bytes so MinIO gets a file-like stream
            length=len(data),  # exact length is required when sending BytesIO
            content_type=content_type,
        )
        return object_name

    # --- read ---------------------------------------------------------------
    def get_stream(self, object_name: str):
        """Return an HTTPResponse-like stream object from MinIO."""
        return self.client.get_object(self.bucket, object_name)

    # --- helpers ------------------------------------------------------------
    def presigned_url(self, object_name: str, expiry: int = 60 * 60) -> str:
        """Return a presigned GET URL valid for `expiry` seconds."""
        from datetime import timedelta

        try:
            return self.client.presigned_get_object(
                self.bucket, object_name, expires=timedelta(seconds=expiry)
            )
        except S3Error as exc:  # pragma: no cover
            raise RuntimeError("Cannot generate URL") from exc
