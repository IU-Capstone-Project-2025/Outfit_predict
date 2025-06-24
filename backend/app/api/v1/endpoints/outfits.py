from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.deps import get_db, get_minio
from app.crud import outfit as outfit_crud
from app.schemas.outfit import OutfitRead
from app.storage.minio_client import MinioService
from fastapi.responses import StreamingResponse
from uuid import UUID
from PIL import Image
import io
from app.ml.clothing_detector import get_clothes_from_img
from app.ml.image_search import ImageSearchEngine
from app.storage.qdrant_client import QdrantService
import tempfile
import os
import uuid
import cv2
from app.crud import image as crud_image

router = APIRouter(prefix="/outfits", tags=["outfits"])


@router.post("/upload/", response_model=OutfitRead)
async def upload_outfit(
        request: Request,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        minio: MinioService = Depends(get_minio)
):
    """Upload a new outfit image."""
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Upload to MinIO
    object_name = minio.save_file(await file.read(), content_type=file.content_type)

    # Create outfit record
    outfit = await outfit_crud.create_outfit(db, object_name)

    # Build proxy URL
    proxy_url = request.url_for("get_outfit_file", object_name=outfit.object_name)

    # Convert to schema
    return OutfitRead(
        id=outfit.id,
        object_name=outfit.object_name,
        created_at=outfit.created_at,
        url=str(proxy_url)
    )


@router.get("/", response_model=List[OutfitRead])
async def get_outfits(
        request: Request,
        skip: int = 0,
        limit: int = 100,
        db: AsyncSession = Depends(get_db)
):
    """Get a list of outfits."""
    outfits = await outfit_crud.list_outfits(db, skip=skip, limit=limit)
    return [
        OutfitRead(
            id=outfit.id,
            object_name=outfit.object_name,
            created_at=outfit.created_at,
            url=str(request.url_for("get_outfit_file", object_name=outfit.object_name))
        )
        for outfit in outfits
    ]


@router.get("/{outfit_id}", response_model=OutfitRead)
async def get_outfit(
        request: Request,
        outfit_id: UUID,
        db: AsyncSession = Depends(get_db)
):
    """Get a specific outfit by ID."""
    outfit = await outfit_crud.get_outfit(db, outfit_id)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")
    return OutfitRead(
        id=outfit.id,
        object_name=outfit.object_name,
        created_at=outfit.created_at,
        url=str(request.url_for("get_outfit_file", object_name=outfit.object_name))
    )


@router.get("/file/{object_name}", name="get_outfit_file")
async def get_outfit_file(
        object_name: str,
        minio: MinioService = Depends(get_minio)
):
    """Stream an outfit image from MinIO."""
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
        raise HTTPException(status_code=404, detail="File not found")


@router.post("/search-similar/", response_model=List[dict])
async def search_similar_outfits(
        request: Request,
        db: AsyncSession = Depends(get_db),
        minio: MinioService = Depends(get_minio)
):
    """
    Search for similar outfits based on the user's wardrobe (all images in the DB).
    This endpoint uses a two-stage search process to find outfits that can be
    best completed with items from the user's wardrobe.

    Returns a list of recommended outfits, including a completeness score and
    details on which wardrobe items match the outfit's components.
    """
    # 1. Get all wardrobe images from the database
    wardrobe_images = await crud_image.list_images(db, skip=0, limit=1000)  # Assume 1000 is enough
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
        raise HTTPException(status_code=400, detail="Could not load any wardrobe images.")

    # 3. Find similar outfits using the new two-stage algorithm
    qdrant = QdrantService()
    image_search = ImageSearchEngine()
    wardrobe_object_names = [item.object_name for item in valid_wardrobe_items]
    recommended_outfits = await image_search.find_similar_outfit(
        images=pil_images,
        wardrobe_object_names=wardrobe_object_names,
        qdrant=qdrant
    )

    # 4. Augment the results with full outfit details
    results = []
    for reco in recommended_outfits:
        # Get full outfit details
        outfit = await outfit_crud.get_outfit(db, UUID(reco.outfit_id))
        if not outfit:
            continue

        proxy_url = request.url_for("get_outfit_file", object_name=outfit.object_name)
        outfit_details = OutfitRead(
            id=outfit.id,
            object_name=outfit.object_name,
            created_at=outfit.created_at,
            url=str(proxy_url)
        )

        results.append({
            "outfit": outfit_details,
            "recommendation": reco
        })

    return results


@router.post("/upload-and-process/", response_model=OutfitRead)
async def upload_and_process_outfit(
        request: Request,
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_db),
        minio: MinioService = Depends(get_minio)
):
    """
    Upload an outfit image, store it, detect clothing, and add detected items to Qdrant.
    Returns the created outfit metadata and detected clothing info.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Save uploaded file to a temp file for OpenCV
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[-1]) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # 1. Upload to MinIO
        object_name = minio.save_file(content, content_type=file.content_type)

        # 2. Create outfit record in DB
        outfit = await outfit_crud.create_outfit(db, object_name)
        outfit_id = str(outfit.id)

        # 3. Detect clothing items
        detected_clothes = get_clothes_from_img(tmp_path)
        if not detected_clothes:
            raise HTTPException(status_code=422, detail="No clothing items detected in the image.")

        # 4. Add each detected clothing item to Qdrant
        qdrant = QdrantService()
        image_search = ImageSearchEngine()
        clothing_info = []
        for name, cropped_img in detected_clothes:
            # Convert cropped_img (numpy array) to PIL Image
            from PIL import Image
            if cropped_img.size == 0:
                continue  # skip empty crops
            pil_img = Image.fromarray(cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB))
            image_id = str(uuid.uuid4())
            await image_search.add_image_to_index(
                image=pil_img,
                image_id=image_id,
                outfit_id=outfit_id,
                qdrant=qdrant
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
            "clothing_items": clothing_info
        }
    finally:
        os.remove(tmp_path)