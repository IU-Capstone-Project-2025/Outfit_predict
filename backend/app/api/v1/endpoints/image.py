from typing import Annotated, List
from uuid import UUID

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

router = APIRouter(prefix="/images", tags=["images"])


@router.get("/", response_model=List[ImageRead])
async def list_images(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    images = await crud_image.list_images(db, current_user.id, skip, limit)
    return [
        ImageRead(
            **img.__dict__, url=str(request.url_for("get_image_file", image_id=img.id))
        )
        for img in images
    ]


@router.post("/", response_model=ImageRead, status_code=status.HTTP_201_CREATED)
async def upload_image(
    request: Request,
    description: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile, File(...)] = None,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    object_name = minio.save_file(await file.read(), content_type=file.content_type)
    image = await crud_image.create_image(db, current_user.id, description, object_name)
    return ImageRead(
        **image.__dict__,
        url=str(request.url_for("get_image_file", image_id=image.id)),
    )


@router.get("/{image_id}/file", name="get_image_file")
async def get_image_file(
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    image = await crud_image.get_image(db, image_id, current_user.id)
    if image is None:
        raise HTTPException(status_code=404, detail="image not found")
    return StreamingResponse(
        minio.get_stream(image.object_name),
        media_type="application/octet-stream",
    )


@router.delete("/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_image(
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    """Delete an image and its associated file from all storage systems."""
    # Get the image to ensure it exists and user owns it
    image = await crud_image.get_image(db, image_id, current_user.id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Delete from MinIO
    minio_success = minio.delete_file(image.object_name)
    if not minio_success:
        # Log warning but continue with database deletion
        print(f"Warning: Failed to delete file {image.object_name} from MinIO")

    # Delete from PostgreSQL
    deleted_image = await crud_image.delete_image(db, image_id, current_user.id)
    if not deleted_image:
        raise HTTPException(status_code=404, detail="Failed to delete image from database")

    # Note: Images are not typically stored in Qdrant, only outfit vectors are
    # If you have image vectors in Qdrant, add deletion logic here

    return None  # 204 No Content
