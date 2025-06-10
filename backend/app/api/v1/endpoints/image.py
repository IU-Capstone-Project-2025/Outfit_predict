from typing import Annotated, List
from uuid import UUID

from app.crud import image as crud_image
from app.deps import get_db, get_minio
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

# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------


@router.get("/", response_model=List[ImageRead])
async def list_images(
    request: Request,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, le=1000),
    db: AsyncSession = Depends(get_db),
):
    images = await crud_image.list_images(db, skip, limit)
    base_url_for = lambda img_id: request.url_for("get_image_file", image_id=img_id)
    return [ImageRead(**img.__dict__, url=str(base_url_for(img.id))) for img in images]


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


@router.post("/", response_model=ImageRead, status_code=status.HTTP_201_CREATED)
async def upload_image(
    request: Request,
    description: Annotated[str | None, Form()] = None,
    file: Annotated[UploadFile, File(...)] = None,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
):
    # 1) Store object in MinIO
    object_name = minio.save_file(await file.read(), content_type=file.content_type)

    # 2) Store metadata in DB
    image = await crud_image.create_image(db, description, object_name)

    # 3) Build absolute proxy URL
    proxy_url = request.url_for("get_image_file", image_id=image.id)

    return ImageRead(**image.__dict__, url=str(proxy_url))


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------


@router.get("/{image_id}", response_model=ImageRead)
async def get_image(
    request: Request, image_id: UUID, db: AsyncSession = Depends(get_db)
):
    image = await crud_image.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    proxy_url = request.url_for("get_image_file", image_id=image_id)
    return ImageRead(**image.__dict__, url=str(proxy_url))


# ---------------------------------------------------------------------------
# File proxy
# ---------------------------------------------------------------------------


@router.get("/{image_id}/file", name="get_image_file")
async def get_image_file(
    image_id: UUID,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
):
    """Stream the raw object from MinIO through the backend so the client never sees S3 URLs."""
    image = await crud_image.get_image(db, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    obj = minio.get_stream(image.object_name)  # HTTPResponse-like object

    # Build generator to cleanly close the connection afterwards
    def iter_data():
        for chunk in obj.stream(32 * 1024):
            yield chunk
        obj.close()

    headers = {
        "Content-Disposition": f'inline; filename="{image.object_name}"',
        "Content-Length": obj.headers.get("Content-Length", "0"),
    }
    media_type = obj.headers.get("Content-Type", "application/octet-stream")
    return StreamingResponse(iter_data(), media_type=media_type, headers=headers)
