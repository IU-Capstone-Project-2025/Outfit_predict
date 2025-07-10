import io
import os
import tempfile
import uuid
from typing import List
from uuid import UUID

import cv2
from app.crud import image as crud_image
from app.crud import outfit as outfit_crud
from app.deps import get_current_user, get_db, get_minio
from app.ml.image_search import ImageSearchEngine
from app.ml.ml_models import (
    fashion_segmentation_model,
    image_search_engine,
    qdrant_service,
)
from app.ml.outfit_processing import FashionSegmentationModel, get_clothes_from_img
from app.models.outfit import Outfit
from app.models.user import User
from app.schemas.outfit import OutfitRead
from app.storage.minio_client import MinioService
from app.storage.qdrant_client import QdrantService
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def get_fashion_segmentation_model():
    return fashion_segmentation_model


def get_image_search_engine():
    return image_search_engine


def get_qdrant_service():
    return qdrant_service


router = APIRouter(prefix="/outfits", tags=["outfits"])


@router.post("/upload/", response_model=OutfitRead)
async def upload_outfit(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    """Upload a new outfit image."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Upload to MinIO
    object_name = minio.save_file(await file.read(), content_type=file.content_type)

    # Create outfit record
    outfit = await outfit_crud.create_outfit(db, current_user.id, object_name)

    # Build proxy URL
    proxy_url = request.url_for("get_outfit_file", object_name=outfit.object_name)

    # Convert to schema
    return OutfitRead(
        id=outfit.id,
        object_name=outfit.object_name,
        created_at=outfit.created_at,
        url=str(proxy_url),
    )


@router.get("/", response_model=List[OutfitRead])
async def get_outfits(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a list of outfits."""
    outfits = await outfit_crud.list_outfits(
        db, current_user.id, skip=skip, limit=limit
    )
    return [
        OutfitRead(
            id=outfit.id,
            object_name=outfit.object_name,
            created_at=outfit.created_at,
            url=str(request.url_for("get_outfit_file", object_name=outfit.object_name)),
        )
        for outfit in outfits
    ]


@router.get("/{outfit_id}", response_model=OutfitRead)
async def get_outfit(
    request: Request,
    outfit_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific outfit by ID."""
    outfit = await outfit_crud.get_outfit(db, outfit_id, current_user.id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return OutfitRead(
        id=outfit.id,
        object_name=outfit.object_name,
        created_at=outfit.created_at,
        url=str(request.url_for("get_outfit_file", object_name=outfit.object_name)),
    )


@router.get("/file/{object_name}", name="get_outfit_file")
async def get_outfit_file(
    object_name: str,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    """Stream an outfit image from MinIO."""
    # Verify user owns this outfit
    outfit = await outfit_crud.get_outfit_by_object_name(
        db, object_name, current_user.id
    )
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    try:
        obj = minio.get_stream(object_name)

        # Build generator to cleanly close the connection afterwards
        def iter_data():
            for chunk in obj.stream(32 * 1024):
                yield chunk
            obj.close()

        headers = {
            "Content-Disposition": f'inline; filename="{object_name}"',
            "Content-Length": obj.headers.get("Content-Length", "0"),
        }
        media_type = obj.headers.get("Content-Type", "application/octet-stream")
        return StreamingResponse(iter_data(), media_type=media_type, headers=headers)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File not found. Exception:{e}")


@router.post("/search-similar/", response_model=List[dict])
async def search_similar_outfits(
    request: Request,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
    image_search: ImageSearchEngine = Depends(get_image_search_engine),
    qdrant: QdrantService = Depends(get_qdrant_service),
):
    """
    Search for similar outfits based on the user's wardrobe (all images in the DB).
    This endpoint uses a two-stage search process to find outfits that can be
    best completed with items from the user's wardrobe.

    Returns a list of recommended outfits, including a completeness score and
    details on which wardrobe items match the outfit's components.
    """
    # 1. Get all wardrobe images from the database
    wardrobe_images = await crud_image.list_images(
        db, current_user.id, skip=0, limit=1000
    )  # Assume 1000 is enough
    if not wardrobe_images:
        raise HTTPException(status_code=404, detail="No wardrobe images found.")

    # 2. Load images from MinIO and convert to PIL format
    pil_images = []
    valid_wardrobe_items = []
    for db_image in wardrobe_images:
        try:
            obj = minio.get_stream(db_image.object_name)
            img_bytes = obj.read()
            obj.close()
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
            pil_images.append(pil_img)
            valid_wardrobe_items.append(db_image)
        except Exception:
            # Skip images that fail to load
            continue

    if not pil_images:
        raise HTTPException(
            status_code=400, detail="Could not load any wardrobe images."
        )

    # 3. Find similar outfits using the new two-stage algorithm
    wardrobe_object_names = [item.object_name for item in valid_wardrobe_items]
    recommended_outfits = await image_search.find_similar_outfit(
        images=pil_images, wardrobe_object_names=wardrobe_object_names, qdrant=qdrant
    )

    # 4. Augment the results with full outfit details
    results = []
    for reco in recommended_outfits:
        # Get full outfit details - NOTE: This searches across all users' outfits
        # This might need to be reconsidered for privacy
        res = await db.execute(select(Outfit).where(Outfit.id == UUID(reco.outfit_id)))
        outfit = res.scalar_one_or_none()
        if not outfit:
            continue

        proxy_url = request.url_for("get_outfit_file", object_name=outfit.object_name)
        outfit_details = OutfitRead(
            id=outfit.id,
            object_name=outfit.object_name,
            created_at=outfit.created_at,
            url=str(proxy_url),
        )

        results.append({"outfit": outfit_details, "recommendation": reco})

    return results


@router.post("/upload-and-process/", response_model=OutfitRead)
async def upload_and_process_outfit(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
    image_search: ImageSearchEngine = Depends(get_image_search_engine),
    qdrant: QdrantService = Depends(get_qdrant_service),
):
    """
    Upload an outfit image, store it, detect clothing, and add detected items to Qdrant.
    Returns the created outfit metadata and detected clothing info.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Save uploaded file to a temp file for OpenCV
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=os.path.splitext(file.filename)[-1]
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 1. Upload to MinIO
        object_name = minio.save_file(content, content_type=file.content_type)

        # 2. Create outfit record in DB
        outfit = await outfit_crud.create_outfit(db, current_user.id, object_name)
        outfit_id = str(outfit.id)

        # 3. Detect clothing items
        detected_clothes = get_clothes_from_img(tmp_path)
        if not detected_clothes:
            raise HTTPException(
                status_code=422, detail="No clothing items detected in the image."
            )

        # 4. Add each detected clothing item to Qdrant
        clothing_info = []
        for name, cropped_img in detected_clothes:
            # Convert cropped_img (numpy array) to PIL Image

            if cropped_img.size == 0:
                continue  # skip empty crops
            pil_img = Image.fromarray(cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB))
            image_id = str(uuid.uuid4())
            await image_search.add_image_to_index(
                image=pil_img, image_id=image_id, outfit_id=outfit_id, qdrant=qdrant
            )
            clothing_info.append({"name": name, "image_id": image_id})

        # 5. Build proxy URL
        proxy_url = request.url_for("get_outfit_file", object_name=outfit.object_name)

        # 6. Return outfit metadata and clothing info
        return {
            "id": outfit.id,
            "object_name": outfit.object_name,
            "created_at": outfit.created_at,
            "url": str(proxy_url),
            "clothing_items": clothing_info,
        }
    finally:
        os.remove(tmp_path)


@router.delete("/{outfit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_outfit(
    outfit_id: UUID,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    """Delete an outfit and its associated data from all storage systems."""
    # Get the outfit to ensure it exists and user owns it
    outfit = await outfit_crud.get_outfit(db, outfit_id, current_user.id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    # Delete from Qdrant (vectors for this outfit)
    qdrant = QdrantService()
    qdrant_success = qdrant.delete_outfit_vectors(str(outfit_id))
    if not qdrant_success:
        print(f"Warning: Failed to delete vectors for outfit {outfit_id} from Qdrant")

    # Delete from MinIO
    minio_success = minio.delete_file(outfit.object_name)
    if not minio_success:
        print(f"Warning: Failed to delete file {outfit.object_name} from MinIO")

    # Delete from PostgreSQL
    deleted_outfit = await outfit_crud.delete_outfit(db, outfit_id, current_user.id)
    if not deleted_outfit:
        raise HTTPException(
            status_code=404, detail="Failed to delete outfit from database"
        )

    return None  # 204 No Content


@router.post("/split-outfit-to-clothes/", response_model=OutfitRead)
async def split_outfit_to_clothes(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    segmentation_model: FashionSegmentationModel = Depends(
        get_fashion_segmentation_model
    ),
    image_search: ImageSearchEngine = Depends(get_image_search_engine),
    qdrant: QdrantService = Depends(get_qdrant_service),
    current_user: User = Depends(get_current_user),
):
    """
    Upload an outfit image, segment it into clothes using FashionSegmentationModel, and return
    the same response as upload_and_process_outfit.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Save uploaded file to a temp file for OpenCV
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=os.path.splitext(file.filename)[-1]
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 1. Upload to MinIO
        object_name = minio.save_file(content, content_type=file.content_type)

        # 2. Create outfit record in DB
        outfit = await outfit_crud.create_outfit(db, current_user.id, object_name)
        outfit_id = str(outfit.id)

        # 3. Segment clothing items using FashionSegmentationModel
        result = segmentation_model.get_segment_images(tmp_path)
        if not result or len(result) == 0:
            raise HTTPException(
                status_code=422, detail="No clothing items detected in the image."
            )
        segmented_clothes, cloth_names = result
        if len(segmented_clothes) == 0:
            raise HTTPException(
                status_code=422, detail="No clothing items detected in the image."
            )

        # 4. Add each detected clothing item to Qdrant
        clothing_info = []
        for name, cropped_img in zip(cloth_names, segmented_clothes):
            if cropped_img.size == 0:
                continue  # skip empty crops
            pil_img = Image.fromarray(cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB))
            image_id = str(uuid.uuid4())
            await image_search.add_image_to_index(
                image=pil_img, image_id=image_id, outfit_id=outfit_id, qdrant=qdrant
            )
            clothing_info.append({"name": name, "image_id": image_id})

        # 5. Build proxy URL
        proxy_url = request.url_for("get_outfit_file", object_name=outfit.object_name)

        # 6. Return outfit metadata and clothing info
        return {
            "id": outfit.id,
            "object_name": outfit.object_name,
            "created_at": outfit.created_at,
            "url": str(proxy_url),
            "clothing_items": clothing_info,
        }
    finally:
        os.remove(tmp_path)
