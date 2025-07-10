import io
import os
import tempfile
import uuid
from typing import List
from uuid import UUID

import cv2
from app.core.logging import get_logger
from app.core.url_utils import build_url
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
from app.models.user import User
from app.schemas.outfit import OutfitRead
from app.storage.minio_client import MinioService
from app.storage.qdrant_client import QdrantService
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

# Initialize logger for outfit operations
logger = get_logger("app.api.outfits")


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
    logger.info(f"Outfit upload started for user {current_user.email}")
    logger.debug(
        f"Upload details - filename: {file.filename}, content_type: {file.content_type}"
    )

    try:
        if not file.content_type.startswith("image/"):
            logger.warning(
                f"Invalid file type for outfit upload by user {current_user.email}: {file.content_type}"
            )
            raise HTTPException(status_code=400, detail="File must be an image")

        # Upload to MinIO
        file_content = await file.read()
        logger.debug(f"Read {len(file_content)} bytes from uploaded outfit file")

        object_name = minio.save_file(file_content, content_type=file.content_type)
        logger.info(f"Outfit saved to MinIO with object_name: {object_name}")

        # Create outfit record
        outfit = await outfit_crud.create_outfit(db, current_user.id, object_name)
        logger.info(f"Outfit metadata saved to database with ID: {outfit.id}")

        # Build proxy URL
        proxy_url = build_url(
            request, "get_outfit_file", object_name=outfit.object_name
        )

        result = OutfitRead(
            id=outfit.id,
            object_name=outfit.object_name,
            created_at=outfit.created_at,
            url=proxy_url,
        )

        logger.info(
            f"Outfit upload completed successfully for user {current_user.email} - Outfit ID: {outfit.id}"
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading outfit for user {current_user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading outfit",
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
    logger.info(
        f"Listing outfits for user {current_user.email} (skip={skip}, limit={limit})"
    )

    try:
        outfits = await outfit_crud.list_outfits(
            db, current_user.id, skip=skip, limit=limit
        )
        logger.info(f"Retrieved {len(outfits)} outfits for user {current_user.email}")

        return [
            OutfitRead(
                id=outfit.id,
                object_name=outfit.object_name,
                created_at=outfit.created_at,
                url=build_url(
                    request, "get_outfit_file", object_name=outfit.object_name
                ),
            )
            for outfit in outfits
        ]

    except Exception as e:
        logger.error(f"Error listing outfits for user {current_user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving outfits",
        )


@router.get("/{outfit_id}", response_model=OutfitRead)
async def get_outfit(
    request: Request,
    outfit_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific outfit by ID."""
    logger.info(f"Getting outfit {outfit_id} for user {current_user.email}")

    try:
        outfit = await outfit_crud.get_outfit(db, outfit_id, current_user.id)
        if not outfit:
            logger.warning(
                f"Outfit {outfit_id} not found for user {current_user.email}"
            )
            raise HTTPException(status_code=404, detail="Outfit not found")

        logger.debug(f"Outfit {outfit_id} retrieved successfully")
        return OutfitRead(
            id=outfit.id,
            object_name=outfit.object_name,
            created_at=outfit.created_at,
            url=build_url(request, "get_outfit_file", object_name=outfit.object_name),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting outfit {outfit_id} for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving outfit",
        )


@router.get("/file/{object_name}", name="get_outfit_file")
async def get_outfit_file(
    object_name: str,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    """Stream an outfit image from MinIO."""
    logger.info(f"Downloading outfit file {object_name} for user {current_user.email}")

    try:
        # Verify user owns this outfit
        outfit = await outfit_crud.get_outfit_by_object_name(
            db, object_name, current_user.id
        )
        if not outfit:
            logger.warning(
                f"Outfit file {object_name} not found for user {current_user.email}"
            )
            raise HTTPException(status_code=404, detail="Outfit not found")

        logger.debug(f"Retrieving outfit file from MinIO: {object_name}")
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

        logger.info(
            f"Outfit file {object_name} download started for user {current_user.email}"
        )
        return StreamingResponse(iter_data(), media_type=media_type, headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error downloading outfit file {object_name} for user {current_user.email}: {str(e)}"
        )
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
    logger.info(f"Starting similar outfit search for user {current_user.email}")

    try:
        # 1. Get all wardrobe images from the database
        logger.debug("Retrieving user's wardrobe images from database")
        wardrobe_images = await crud_image.list_images(
            db, current_user.id, skip=0, limit=1000
        )  # Assume 1000 is enough

        if not wardrobe_images:
            logger.warning(f"No wardrobe images found for user {current_user.email}")
            raise HTTPException(status_code=404, detail="No wardrobe images found.")

        logger.info(f"Found {len(wardrobe_images)} wardrobe images for analysis")

        # 2. Load images from MinIO and convert to PIL format
        logger.debug("Loading images from MinIO storage")
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
            except Exception as img_error:
                logger.warning(
                    f"Failed to load image {db_image.object_name}: {str(img_error)}"
                )
                continue

        if not pil_images:
            logger.error(
                f"Could not load any wardrobe images for user {current_user.email}"
            )
            raise HTTPException(
                status_code=400, detail="Could not load any wardrobe images."
            )

        logger.info(f"Successfully loaded {len(pil_images)} images for analysis")

        # 3. Find similar outfits using the new two-stage algorithm
        logger.debug("Starting ML-based outfit similarity search")
        wardrobe_object_names = [item.object_name for item in valid_wardrobe_items]

        recommended_outfits = await image_search.find_similar_outfit(
            images=pil_images,
            wardrobe_object_names=wardrobe_object_names,
            qdrant=qdrant,
        )

        logger.info(
            f"Found {len(recommended_outfits)} similar outfit recommendations for user {current_user.email}"
        )
        logger.debug(
            f"Recommendation details: {[r.get('completeness_score', 0) for r in recommended_outfits]}"
        )

        return recommended_outfits

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error in similar outfit search for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error searching for similar outfits",
        )


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
    logger.info(f"Outfit upload and processing started for user {current_user.email}")
    logger.debug(
        f"Upload details - filename: {file.filename}, content_type: {file.content_type}"
    )

    try:
        if not file.content_type.startswith("image/"):
            logger.warning(
                f"Invalid file type for outfit upload and processing by user {current_user.email}: {file.content_type}"
            )
            raise HTTPException(status_code=400, detail="File must be an image")

        # Save uploaded file to a temp file for OpenCV
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(file.filename)[-1]
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        logger.debug(f"Saved uploaded file to temporary path: {tmp_path}")

        try:
            # 1. Upload to MinIO
            object_name = minio.save_file(content, content_type=file.content_type)
            logger.info(f"Outfit saved to MinIO with object_name: {object_name}")

            # 2. Create outfit record in DB
            outfit = await outfit_crud.create_outfit(db, current_user.id, object_name)
            outfit_id = str(outfit.id)
            logger.info(f"Outfit metadata saved to database with ID: {outfit_id}")

            # 3. Detect clothing items
            detected_clothes = get_clothes_from_img(tmp_path)
            if not detected_clothes:
                logger.warning(
                    f"No clothing items detected in the image for outfit {outfit_id} by user {current_user.email}"
                )
                raise HTTPException(
                    status_code=422, detail="No clothing items detected in the image."
                )

            logger.info(
                f"Successfully detected {len(detected_clothes)} clothing items for outfit {outfit_id}"
            )

            # 4. Add each detected clothing item to Qdrant
            clothing_info = []
            for name, cropped_img in detected_clothes:
                # Convert cropped_img (numpy array) to PIL Image

                if cropped_img.size == 0:
                    logger.warning(
                        f"Skipping empty crop for item {name} in outfit {outfit_id}"
                    )
                    continue  # skip empty crops
                pil_img = Image.fromarray(cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB))
                image_id = str(uuid.uuid4())
                await image_search.add_image_to_index(
                    image=pil_img, image_id=image_id, outfit_id=outfit_id, qdrant=qdrant
                )
                clothing_info.append({"name": name, "image_id": image_id})

            logger.info(
                f"Successfully added {len(clothing_info)} clothing items to Qdrant for outfit {outfit_id}"
            )

            # 5. Build proxy URL
            proxy_url = build_url(
                request, "get_outfit_file", object_name=outfit.object_name
            )

            # 6. Return outfit metadata and clothing info
            result = {
                "id": outfit.id,
                "object_name": outfit.object_name,
                "created_at": outfit.created_at,
                "url": proxy_url,
                "clothing_items": clothing_info,
            }

            logger.info(
                f"Outfit upload and processing completed successfully"
                f"for user {current_user.email} - Outfit ID: {outfit_id}"
            )
            return result

        finally:
            os.remove(tmp_path)
            logger.debug(f"Deleted temporary file: {tmp_path}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error in outfit upload and processing for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading and processing outfit",
        )


@router.delete("/{outfit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_outfit(
    outfit_id: UUID,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    """Delete an outfit and its associated data from all storage systems."""
    logger.info(f"Deleting outfit {outfit_id} for user {current_user.email}")

    try:
        # Get the outfit to ensure it exists and user owns it
        outfit = await outfit_crud.get_outfit(db, outfit_id, current_user.id)
        if not outfit:
            logger.warning(
                f"Outfit {outfit_id} not found for user {current_user.email}"
            )
            raise HTTPException(status_code=404, detail="Outfit not found")

        logger.debug(f"Outfit {outfit_id} retrieved for deletion")

        # Delete from Qdrant (vectors for this outfit)
        qdrant = QdrantService()
        qdrant_success = qdrant.delete_outfit_vectors(str(outfit_id))
        if not qdrant_success:
            logger.warning(
                f"Failed to delete vectors for outfit {outfit_id} from Qdrant by user {current_user.email}"
            )
            print(
                f"Warning: Failed to delete vectors for outfit {outfit_id} from Qdrant"
            )

        # Delete from MinIO
        minio_success = minio.delete_file(outfit.object_name)
        if not minio_success:
            logger.warning(
                f"Failed to delete file {outfit.object_name} from MinIO by user {current_user.email}"
            )
            print(f"Warning: Failed to delete file {outfit.object_name} from MinIO")

        # Delete from PostgreSQL
        deleted_outfit = await outfit_crud.delete_outfit(db, outfit_id, current_user.id)
        if not deleted_outfit:
            logger.warning(
                f"Failed to delete outfit {outfit_id} from database by user {current_user.email}"
            )
            raise HTTPException(
                status_code=404, detail="Failed to delete outfit from database"
            )

        logger.info(
            f"Outfit {outfit_id} deleted successfully for user {current_user.email}"
        )
        return None  # 204 No Content

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error deleting outfit {outfit_id} for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error deleting outfit",
        )


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
    Split an outfit image into individual clothing items and save them to the database.
    Also adds the detected clothing items to Qdrant for similarity search.
    Returns the same response as upload_and_process_outfit.
    """
    logger.info(f"Outfit split to clothes started for user {current_user.email}")
    logger.debug(
        f"Upload details - filename: {file.filename}, content_type: {file.content_type}"
    )

    try:
        if not file.content_type.startswith("image/"):
            logger.warning(
                f"Invalid file type for outfit split to clothes by user {current_user.email}: {file.content_type}"
            )
            raise HTTPException(status_code=400, detail="File must be an image")

        # Save uploaded file to a temp file for OpenCV
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=os.path.splitext(file.filename)[-1]
        ) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name

        logger.debug(f"Saved uploaded file to temporary path: {tmp_path}")

        try:
            # 1. Upload to MinIO
            object_name = minio.save_file(content, content_type=file.content_type)
            logger.info(f"Outfit saved to MinIO with object_name: {object_name}")

            # 2. Create outfit record in DB
            outfit = await outfit_crud.create_outfit(db, current_user.id, object_name)
            outfit_id = str(outfit.id)
            logger.info(f"Outfit metadata saved to database with ID: {outfit_id}")

            # 3. Segment clothing items using FashionSegmentationModel
            result = segmentation_model.get_segment_images(tmp_path)
            if not result or len(result) == 0:
                logger.warning(
                    f"No clothing items detected in the image for outfit {outfit_id} by user {current_user.email}"
                )
                raise HTTPException(
                    status_code=422, detail="No clothing items detected in the image."
                )
            segmented_clothes, cloth_names = result
            if len(segmented_clothes) == 0:
                logger.warning(
                    f"No clothing items detected in the image for outfit {outfit_id} by user {current_user.email}"
                )
                raise HTTPException(
                    status_code=422, detail="No clothing items detected in the image."
                )

            logger.info(
                f"Successfully segmented {len(segmented_clothes)} clothing items for outfit {outfit_id}"
            )

            # 4. Add each detected clothing item to Qdrant
            clothing_info = []
            for name, cropped_img in zip(cloth_names, segmented_clothes):
                if cropped_img.size == 0:
                    logger.warning(
                        f"Skipping empty crop for item {name} in outfit {outfit_id}"
                    )
                    continue  # skip empty crops
                pil_img = Image.fromarray(cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB))
                image_id = str(uuid.uuid4())
                await image_search.add_image_to_index(
                    image=pil_img, image_id=image_id, outfit_id=outfit_id, qdrant=qdrant
                )
                clothing_info.append({"name": name, "image_id": image_id})

            logger.info(
                f"Successfully added {len(clothing_info)} clothing items to Qdrant for outfit {outfit_id}"
            )

            # 5. Build proxy URL
            proxy_url = build_url(
                request, "get_outfit_file", object_name=outfit.object_name
            )

            # 6. Return outfit metadata and clothing info
            result = {
                "id": outfit.id,
                "object_name": outfit.object_name,
                "created_at": outfit.created_at,
                "url": proxy_url,
                "clothing_items": clothing_info,
            }

            logger.info(
                f"Outfit split to clothes completed successfully for user {current_user.email} - Outfit ID: {outfit_id}"
            )
            return result

        finally:
            os.remove(tmp_path)
            logger.debug(f"Deleted temporary file: {tmp_path}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error in outfit split to clothes for user {current_user.email}: {str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error splitting outfit to clothes",
        )
