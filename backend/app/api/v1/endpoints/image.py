from typing import Annotated, List
from uuid import UUID

from app.core.logging import get_logger
from app.core.url_utils import build_url
from app.crud import image as crud_image
from app.deps import get_current_user, get_db, get_minio
from app.models.user import User
from app.schemas.image import ImageRead
from app.storage.minio_client import MinioService
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

# Initialize logger for image operations
logger = get_logger("app.api.images")

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/", response_model=List[ImageRead])
async def list_images(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(
        f"Listing images for user {current_user.email} (skip={skip}, limit={limit})"
    )

    try:
        images = await crud_image.list_images(db, current_user.id, skip, limit)
        logger.info(f"Retrieved {len(images)} images for user {current_user.email}")

        return [
            ImageRead(
                **img.__dict__,
                url=build_url(request, "get_image_file", image_id=img.id),
            )
            for img in images
        ]
    except Exception as e:
        logger.error(f"Error listing images for user {current_user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving images",
        )


@router.post("/", response_model=ImageRead, status_code=status.HTTP_201_CREATED)
async def upload_image(
    request: Request,
    description: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile, File(...)] = None,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"Image upload started for user {current_user.email}")
    logger.debug(
        f"Upload details - filename: {file.filename}, content_type: {file.content_type}, size: {file.size}"
    )

    try:
        # Validate file type
        if not file.content_type or not file.content_type.startswith("image/"):
            logger.warning(
                f"Invalid file type uploaded by user {current_user.email}: {file.content_type}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="File must be an image"
            )

        # Read file content
        file_content = await file.read()
        logger.debug(f"Read {len(file_content)} bytes from uploaded file")

        # Save to MinIO
        object_name = minio.save_file(file_content, content_type=file.content_type)
        logger.info(f"Image saved to MinIO with object_name: {object_name}")

        # Save metadata to database
        image = await crud_image.create_image(
            db, current_user.id, description, object_name
        )
        logger.info(f"Image metadata saved to database with ID: {image.id}")

        result = ImageRead(
            **image.__dict__,
            url=build_url(request, "get_image_file", image_id=image.id),
        )

        logger.info(
            f"Image upload completed successfully for user {current_user.email} - Image ID: {image.id}"
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading image for user {current_user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading image",
        )


@router.get("/{image_id}", response_model=ImageRead)
async def get_image(
    image_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"Getting image {image_id} for user {current_user.email}")

    try:
        image = await crud_image.get_image(db, image_id, current_user.id)
        if not image:
            logger.warning(f"Image {image_id} not found for user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
            )

        logger.debug(f"Image {image_id} retrieved successfully")
        return ImageRead(
            **image.__dict__,
            url=build_url(request, "get_image_file", image_id=image.id),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting image {image_id} for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving image",
        )


@router.get("/{image_id}/file")
async def get_image_file(
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"Downloading image file {image_id} for user {current_user.email}")

    try:
        # Get image metadata
        image = await crud_image.get_image(db, image_id, current_user.id)
        if not image:
            logger.warning(
                f"Image file {image_id} not found for user {current_user.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
            )

        # Get file from MinIO
        logger.debug(f"Retrieving file from MinIO: {image.object_name}")
        stream = minio.get_stream(image.object_name)

        logger.info(
            f"Image file {image_id} download started for user {current_user.email}"
        )

        return StreamingResponse(
            stream,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={image.object_name}"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error downloading image file {image_id} for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error downloading image file",
        )


@router.delete("/{image_id}")
async def delete_image(
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    logger.info(f"Deleting image {image_id} for user {current_user.email}")

    try:
        # Get image metadata
        image = await crud_image.get_image(db, image_id, current_user.id)
        if not image:
            logger.warning(
                f"Image {image_id} not found for deletion by user {current_user.email}"
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
            )

        # Delete from MinIO
        logger.debug(f"Deleting file from MinIO: {image.object_name}")
        minio_deleted = minio.delete_file(image.object_name)
        if not minio_deleted:
            logger.warning(f"Failed to delete file from MinIO: {image.object_name}")

        # Delete from database
        await crud_image.delete_image(db, image_id, current_user.id)
        logger.info(
            f"Image {image_id} deleted successfully for user {current_user.email}"
        )

        return {"message": "Image deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error deleting image {image_id} for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting image",
        )
