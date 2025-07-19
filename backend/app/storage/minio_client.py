from uuid import uuid4

from app.core.config import get_settings
from app.core.logging import get_logger
from minio import Minio
from minio.error import S3Error

settings = get_settings()

# Initialize logger for MinIO operations
logger = get_logger("app.storage.minio")


class MinioService:
    def __init__(self) -> None:
        logger.info(
            f"Initializing MinIO client for endpoint: {settings.MINIO_ENDPOINT}"
        )
        try:
            self.client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
            self.bucket = settings.MINIO_BUCKET
            logger.info(
                f"MinIO client initialized successfully for bucket: {self.bucket}"
            )
            self._ensure_bucket()
        except Exception as e:
            logger.error(f"Failed to initialize MinIO client: {str(e)}")
            raise

    def _ensure_bucket(self) -> None:
        logger.debug(f"Checking if bucket '{self.bucket}' exists")
        try:
            if not self.client.bucket_exists(self.bucket):
                logger.info(f"Bucket '{self.bucket}' does not exist, creating it")
                self.client.make_bucket(self.bucket)
                logger.info(f"Successfully created bucket: {self.bucket}")
            else:
                logger.debug(f"Bucket '{self.bucket}' already exists")
        except Exception as e:
            logger.error(f"Error ensuring bucket '{self.bucket}' exists: {str(e)}")
            raise

    # --- write --------------------------------------------------------------
    def save_file(self, data: bytes, content_type: str | None = None) -> str:
        """Save raw bytes into MinIO and return generated object name."""
        import io

        object_name = f"{uuid4().hex}"
        logger.debug(
            f"Saving file to MinIO with object_name: {object_name}, size: {len(data)} bytes,"
            f"content_type: {content_type}"
        )

        try:
            self.client.put_object(
                self.bucket,
                object_name,
                data=io.BytesIO(data),  # wrap bytes so MinIO gets a file-like stream
                length=len(data),  # exact length is required when sending BytesIO
                content_type=content_type or "application/octet-stream",
            )
            logger.info(
                f"Successfully saved file to MinIO: {object_name} ({len(data)} bytes)"
            )
            return object_name
        except Exception as e:
            logger.error(
                f"Error saving file to MinIO (object_name: {object_name}): {str(e)}"
            )
            raise

    # --- read ---------------------------------------------------------------
    def get_stream(self, object_name: str):
        """Return an HTTPResponse-like stream object from MinIO."""
        logger.debug(f"Retrieving file stream from MinIO: {object_name}")
        try:
            stream = self.client.get_object(
                self.bucket, object_name, length=1024 * 1024 * 50
            )  # 50 MB
            logger.debug(f"Successfully retrieved stream for object: {object_name}")
            return stream
        except Exception as e:
            logger.error(
                f"Error retrieving file stream from MinIO (object_name: {object_name}): {str(e)}"
            )
            raise

    # --- delete -------------------------------------------------------------
    def delete_file(self, object_name: str) -> bool:
        """Delete a single file from MinIO. Returns True if successful."""
        logger.debug(f"Deleting file from MinIO: {object_name}")
        try:
            self.client.remove_object(self.bucket, object_name)
            logger.info(f"Successfully deleted file from MinIO: {object_name}")
            return True
        except S3Error as exc:
            logger.warning(f"S3Error deleting {object_name} from MinIO: {exc}")
            print(f"Error deleting {object_name}: {exc}")
            return False
        except Exception as e:
            logger.error(
                f"Unexpected error deleting {object_name} from MinIO: {str(e)}"
            )
            return False

    def delete_files(self, object_names: list[str]) -> dict[str, bool]:
        """Delete multiple files from MinIO. Returns dict of object_name -> success."""
        results = {}
        for object_name in object_names:
            results[object_name] = self.delete_file(object_name)
        return results

    def file_exists(self, object_name: str) -> bool:
        """Check if a file exists in MinIO."""
        try:
            self.client.stat_object(self.bucket, object_name)
            return True
        except S3Error:
            return False

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
