import io
from typing import Annotated, List
from uuid import UUID

from app.core.logging import get_logger
from app.core.url_utils import build_url
from app.crud import image as crud_image
from app.deps import get_current_user, get_db, get_minio
from app.models.image import Image
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
from PIL import Image as PILImage
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

# Initialize logger for image operations
logger = get_logger("app.api.images")

router = APIRouter(prefix="/images", tags=["images"])


def get_fashion_clip_encoder():
    """Dependency function to get the FashionClipEncoder instance."""
    from app.ml.ml_models import fashion_clip_encoder

    return fashion_clip_encoder


@router.get("/", response_model=List[ImageRead])
async def list_images(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Lists all images uploaded by the current user.

    - **request**: The request object.
    - **skip**: The number of images to skip.
    - **limit**: The maximum number of images to return.
    - **db**: The database session.
    - **current_user**: The authenticated user.

    Returns a list of image details.
    """
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
                thumbnail_url=(
                    build_url(request, "get_image_thumbnail", image_id=img.id)
                    if img.thumbnail_object_name
                    else None
                ),
            )
            for img in images
        ]
    except Exception as e:
        logger.error(f"Error listing images for user {current_user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving images",
        )


@router.post("/generate-missing-thumbnails/")
async def generate_missing_thumbnails(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    """
    Generates thumbnails for existing images that do not have one.

    This endpoint processes images in batches to avoid overwhelming the system.

    - **request**: The request object.
    - **limit**: The maximum number of thumbnails to generate in one batch.
    - **db**: The database session.
    - **minio**: The Minio service client.
    - **current_user**: The authenticated user.

    Returns a report on the number of thumbnails processed and failed.
    """
    logger.info(
        f"Generating missing thumbnails for user {current_user.email} (limit: {limit})"
    )

    try:
        # Find images without thumbnails
        stmt = (
            select(Image)
            .where(
                and_(
                    Image.user_id == current_user.id,
                    Image.thumbnail_object_name.is_(None),
                )
            )
            .limit(limit)
        )
        result = await db.execute(stmt)
        images_without_thumbnails = list(result.scalars().all())

        if not images_without_thumbnails:
            logger.info(
                f"No images without thumbnails found for user {current_user.email}"
            )
            return {
                "message": "No images without thumbnails found",
                "processed": 0,
                "failed": 0,
                "total_found": 0,
            }

        logger.info(
            f"Found {len(images_without_thumbnails)} images without thumbnails for user {current_user.email}"
        )

        processed_count = 0
        failed_count = 0
        failed_images = []

        for image in images_without_thumbnails:
            try:
                logger.debug(
                    f"Processing image {image.id} (object_name: {image.object_name})"
                )

                # Download original image from MinIO
                original_stream = minio.get_stream(image.object_name)
                original_data = original_stream.read()
                original_stream.close()

                # Generate thumbnail
                try:
                    # Open image and create thumbnail
                    pil_image = PILImage.open(io.BytesIO(original_data))
                    pil_image = pil_image.convert("RGB")  # Ensure RGB format

                    # Create thumbnail (200x200 with aspect ratio preserved)
                    thumbnail_size = (200, 200)
                    pil_image.thumbnail(thumbnail_size, PILImage.Resampling.LANCZOS)

                    # Save thumbnail to bytes
                    thumbnail_buffer = io.BytesIO()
                    pil_image.save(
                        thumbnail_buffer, format="JPEG", quality=85, optimize=True
                    )
                    thumbnail_data = thumbnail_buffer.getvalue()

                    # Save thumbnail to MinIO
                    thumbnail_object_name = f"{image.object_name}_thumb"
                    minio.client.put_object(
                        minio.bucket,
                        thumbnail_object_name,
                        data=io.BytesIO(thumbnail_data),
                        length=len(thumbnail_data),
                        content_type="image/jpeg",
                    )

                    # Update database record
                    image.thumbnail_object_name = thumbnail_object_name
                    await db.commit()

                    processed_count += 1
                    logger.debug(
                        f"Successfully generated thumbnail for image {image.id}"
                    )

                except Exception as thumbnail_error:
                    logger.error(
                        f"Error generating thumbnail for image {image.id}: {str(thumbnail_error)}"
                    )
                    failed_count += 1
                    failed_images.append(
                        {
                            "image_id": str(image.id),
                            "object_name": image.object_name,
                            "error": str(thumbnail_error),
                        }
                    )
                    continue

            except Exception as image_error:
                logger.error(f"Error processing image {image.id}: {str(image_error)}")
                failed_count += 1
                failed_images.append(
                    {
                        "image_id": str(image.id),
                        "object_name": image.object_name,
                        "error": str(image_error),
                    }
                )
                continue

        logger.info(
            f"Thumbnail generation completed for user {current_user.email}: "
            f"{processed_count} processed, {failed_count} failed"
        )

        response = {
            "message": f"Processed {processed_count} images, {failed_count} failed",
            "processed": processed_count,
            "failed": failed_count,
            "total_found": len(images_without_thumbnails),
        }

        if failed_images:
            response["failed_images"] = failed_images

        return response

    except Exception as e:
        logger.error(
            f"Error in thumbnail generation for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating thumbnails",
        )


@router.get("/thumbnail-status/")
async def get_thumbnail_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves statistics about thumbnail coverage for the current user's images.

    - **db**: The database session.
    - **current_user**: The authenticated user.

    Returns a summary of total images, images with thumbnails, and coverage percentage.
    """
    logger.info(f"Getting thumbnail status for user {current_user.email}")

    try:
        # Count total images
        total_stmt = select(Image).where(Image.user_id == current_user.id)
        total_result = await db.execute(total_stmt)
        total_images = len(list(total_result.scalars().all()))

        # Count images with thumbnails
        with_thumbnails_stmt = select(Image).where(
            and_(
                Image.user_id == current_user.id,
                Image.thumbnail_object_name.isnot(None),
            )
        )
        with_thumbnails_result = await db.execute(with_thumbnails_stmt)
        images_with_thumbnails = len(list(with_thumbnails_result.scalars().all()))

        images_without_thumbnails = total_images - images_with_thumbnails
        coverage_percentage = (
            (images_with_thumbnails / total_images * 100) if total_images > 0 else 100
        )

        return {
            "total_images": total_images,
            "images_with_thumbnails": images_with_thumbnails,
            "images_without_thumbnails": images_without_thumbnails,
            "coverage_percentage": round(coverage_percentage, 2),
        }

    except Exception as e:
        logger.error(
            f"Error getting thumbnail status for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving thumbnail status",
        )


@router.post("/", response_model=ImageRead, status_code=status.HTTP_201_CREATED)
async def upload_image(
    request: Request,
    description: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile, File(...)] = None,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
    fashion_encoder=Depends(get_fashion_clip_encoder),
):
    """
    Uploads a new image, generates a thumbnail, and classifies the clothing type.

    - **request**: The request object.
    - **description**: An optional description for the image.
    - **file**: The image file to upload.
    - **db**: The database session.
    - **minio**: The Minio service client.
    - **current_user**: The authenticated user.
    - **fashion_encoder**: The FashionCLIP encoder for clothing classification.

    Returns the details of the uploaded image.
    """
    from app.ml.ml_models import image_search_engine, qdrant_service

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

        # Convert image to PIL format for clothing classification
        pil_image = PILImage.open(io.BytesIO(file_content)).convert("RGB")

        # Classify clothing type automatically
        from app.ml.clothes_type_classification import identify_clothes_type

        clothing_types = identify_clothes_type(fashion_encoder, [pil_image])
        clothing_type = clothing_types[0] if clothing_types else None

        logger.info(f"Automatically classified clothing type: {clothing_type}")

        # Save to MinIO with thumbnail generation
        object_name, thumbnail_object_name = minio.save_file_with_thumbnail(
            file_content, content_type=file.content_type
        )
        logger.info(
            f"Image saved to MinIO with object_name: {object_name}, thumbnail: {thumbnail_object_name}"
        )

        # Save metadata to database including clothing_type
        image = await crud_image.create_image(
            db,
            current_user.id,
            description,
            object_name,
            thumbnail_object_name,
            clothing_type,
        )
        logger.info(f"Image metadata saved to database with ID: {image.id}")

        # Add wardrobe image embeddings to Qdrant
        if clothing_type:  # Only add to index if we could classify the clothing type
            try:
                await image_search_engine.add_wardrobe_image_to_index(
                    image=pil_image,
                    image_id=str(image.id),
                    user_id=str(current_user.id),
                    object_name=object_name,
                    qdrant=qdrant_service,
                    clothing_type=clothing_type,
                )
                logger.info(
                    f"Added wardrobe image embeddings to Qdrant for image {image.id}"
                )
            except Exception as e:
                logger.error(f"Failed to add wardrobe embeddings to Qdrant: {str(e)}")
                # Don't fail the upload if Qdrant indexing fails
        else:
            logger.warning(
                f"Skipping Qdrant indexing for image {image.id} - no clothing type detected"
            )

        result = ImageRead(
            **image.__dict__,
            url=build_url(request, "get_image_file", image_id=image.id),
            thumbnail_url=(
                build_url(request, "get_image_thumbnail", image_id=image.id)
                if image.thumbnail_object_name
                else None
            ),
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
    """
    Retrieves the details of a specific image.

    - **image_id**: The ID of the image to retrieve.
    - **request**: The request object.
    - **db**: The database session.
    - **current_user**: The authenticated user.

    Returns the details of the specified image.
    """
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
            thumbnail_url=(
                build_url(request, "get_image_thumbnail", image_id=image.id)
                if image.thumbnail_object_name
                else None
            ),
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
    """
    Downloads the original file for a specific image.

    - **image_id**: The ID of the image to download.
    - **db**: The database session.
    - **minio**: The Minio service client.
    - **current_user**: The authenticated user.

    Returns the image file as a streaming response.
    """
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


@router.get("/{image_id}/thumbnail")
async def get_image_thumbnail(
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    """
    Downloads the thumbnail for a specific image.

    - **image_id**: The ID of the image to get the thumbnail for.
    - **db**: The database session.
    - **minio**: The Minio service client.
    - **current_user**: The authenticated user.

    Returns the image thumbnail as a streaming response. If a thumbnail does not exist,
    it falls back to the original image.
    """
    logger.info(
        f"Downloading thumbnail for image {image_id} for user {current_user.email}"
    )

    try:
        # Get image metadata
        image = await crud_image.get_image(db, image_id, current_user.id)
        if not image:
            logger.warning(f"Image {image_id} not found for user {current_user.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Image not found"
            )

        # Use thumbnail if available, otherwise fall back to original
        object_name = image.thumbnail_object_name or image.object_name

        # Get file from MinIO
        logger.debug(f"Retrieving thumbnail from MinIO: {object_name}")
        stream = minio.get_stream(object_name)

        logger.info(
            f"Thumbnail for image {image_id} download started for user {current_user.email}"
        )

        return StreamingResponse(
            stream,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f"inline; filename=thumb_{image.object_name}"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error downloading thumbnail for image {image_id} for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error downloading thumbnail",
        )


@router.delete("/{image_id}")
async def delete_image(
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    """
    Deletes a specific image and its associated files.

    This will remove the image from the database, MinIO storage (both original and thumbnail),
    and the Qdrant vector index.

    - **image_id**: The ID of the image to delete.
    - **db**: The database session.
    - **minio**: The Minio service client.
    - **current_user**: The authenticated user.

    Returns a confirmation message upon successful deletion.
    """
    from app.ml.ml_models import image_search_engine, qdrant_service

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

        # Delete from Qdrant wardrobe collection
        try:
            await image_search_engine.remove_wardrobe_image_from_index(
                user_id=str(current_user.id),
                object_name=image.object_name,
                qdrant=qdrant_service,
            )
            logger.info(f"Removed wardrobe embeddings from Qdrant for image {image_id}")
        except Exception as e:
            logger.error(f"Failed to remove wardrobe embeddings from Qdrant: {str(e)}")
            # Don't fail the deletion if Qdrant removal fails

        # Delete from MinIO (both original and thumbnail)
        logger.debug(f"Deleting file from MinIO: {image.object_name}")
        minio_deleted = minio.delete_file(image.object_name)
        if not minio_deleted:
            logger.warning(f"Failed to delete file from MinIO: {image.object_name}")

        # Delete thumbnail if it exists and is different from original
        if (
            image.thumbnail_object_name
            and image.thumbnail_object_name != image.object_name
        ):
            logger.debug(
                f"Deleting thumbnail from MinIO: {image.thumbnail_object_name}"
            )
            thumbnail_deleted = minio.delete_file(image.thumbnail_object_name)
            if not thumbnail_deleted:
                logger.warning(
                    f"Failed to delete thumbnail from MinIO: {image.thumbnail_object_name}"
                )

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
