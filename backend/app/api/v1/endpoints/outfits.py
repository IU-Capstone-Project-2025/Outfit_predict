import io
import os
import tempfile
import uuid
from typing import List, Optional
from uuid import UUID

import cv2
from app.core.logging import get_logger
from app.core.url_utils import build_url
from app.crud import image as crud_image
from app.crud import outfit as outfit_crud
from app.deps import (
    get_current_user,
    get_db,
    get_fashion_clip_encoder,
    get_fashion_segmentation_model,
    get_image_search_engine,
    get_minio,
    get_qdrant,
)
from app.ml.image_search import ImageSearchEngine
from app.ml.outfit_processing import FashionSegmentationModel
from app.models.user import User
from app.schemas.outfit import OutfitRead
from app.storage.minio_client import MinioService
from app.storage.qdrant_client import QdrantService
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Initialize logger for outfit operations
logger = get_logger("app.api.outfits")


router = APIRouter(prefix="/outfits", tags=["outfits"])


async def _prepare_recommendations(
    request: Request,
    db: AsyncSession,
    minio: MinioService,
    fashion_encoder,
    recommended_outfits,
):
    outfit_pil_images = []
    outfit_db_records = []
    for outfit in recommended_outfits:
        try:
            outfit_db_record = await outfit_crud.get_outfit_by_id_any(
                db, UUID(outfit.outfit_id)
            )
            if outfit_db_record:
                # Load image from MinIO
                obj = minio.get_stream(outfit_db_record.object_name)
                img_bytes = obj.read()
                obj.close()
                pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                outfit_pil_images.append(pil_img)
                outfit_db_records.append(outfit_db_record)
        except Exception as e:
            logger.warning(f"Failed to load outfit image {outfit.outfit_id}: {str(e)}")
            continue

    # Only assign styles if we successfully loaded images
    style_labels = []
    if outfit_pil_images:
        image_search = get_image_search_engine()
        style_labels = await image_search.assign_style_labels(
            outfit_pil_images, fashion_encoder
        )

    # Convert to frontend-expected format
    result = []
    style_map = {}

    # Create a mapping from outfit_id to style_label
    for idx, outfit_db_record in enumerate(outfit_db_records):
        if idx < len(style_labels):
            style_map[str(outfit_db_record.id)] = style_labels[idx]

    for rec in recommended_outfits:
        try:
            outfit = await outfit_crud.get_outfit_by_id_any(db, UUID(rec.outfit_id))
            if not outfit:
                logger.warning(f"Outfit {rec.outfit_id} not found in database")
                continue

            outfit_url = build_url(
                request, "get_outfit_file", object_name=outfit.object_name
            )

            # Get style for this outfit, default to "other" if not found
            style_label = style_map.get(str(outfit.id), "other")

            result.append(
                {
                    "outfit": {
                        "id": str(outfit.id),
                        "url": outfit_url,
                        "object_name": outfit.object_name,
                        "created_at": outfit.created_at.isoformat(),
                        "style": style_label,  # Add style to the outfit object
                    },
                    "recommendation": {
                        "completeness_score": rec.completeness_score,
                        "matches": [
                            {
                                **match.model_dump(),
                                "suggested_item_product_link": getattr(
                                    match, "suggested_item_product_link", None
                                ),
                                "suggested_item_image_link": getattr(
                                    match, "suggested_item_image_link", None
                                ),
                            }
                            for match in rec.matches
                        ],
                    },
                }
            )
        except Exception as e:
            logger.warning(f"Error processing outfit {rec.outfit_id}: {str(e)}")
            continue
    return result


@router.post("/upload/", response_model=OutfitRead)
async def upload_outfit(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    """
    Uploads a new outfit image.

    - **request**: The request object.
    - **file**: The outfit image to upload.
    - **db**: The database session.
    - **minio**: The Minio service client.
    - **current_user**: The authenticated user.

    Returns the details of the uploaded outfit.
    """
    logger.info(f"Outfit upload started for user {current_user.email}")
    logger.debug(
        f"Upload details - filename: {file.filename}, "
        f"content_type: {file.content_type}"
    )

    try:
        if not file.content_type.startswith("image/"):
            logger.warning(
                f"Invalid file type for outfit upload by user {current_user.email}: "
                f"{file.content_type}"
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
            f"Outfit upload completed successfully for user {current_user.email} - "
            f"Outfit ID: {outfit.id}"
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
    """
    Retrieves a list of outfits for the current user.

    - **request**: The request object.
    - **skip**: The number of outfits to skip.
    - **limit**: The maximum number of outfits to return.
    - **db**: The database session.
    - **current_user**: The authenticated user.

    Returns a list of outfit details.
    """
    logger.info(
        f"Listing outfits for user {current_user.email} "
        f"(skip={skip}, limit={limit})"
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
    """
    Retrieves a specific outfit by its ID.

    - **request**: The request object.
    - **outfit_id**: The ID of the outfit to retrieve.
    - **db**: The database session.
    - **current_user**: The authenticated user.

    Returns the details of the specified outfit.
    """
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
            f"Error getting outfit {outfit_id} for user {current_user.email}: "
            f"{str(e)}"
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
    current_user: User = Depends(
        get_current_user
    ),  # keep auth but drop ownership restriction
):
    """
    Streams an outfit image from MinIO without user-ownership restrictions.

    This endpoint allows any authenticated user to access an outfit image,
    which is necessary for sharing outfits across the platform.

    - **object_name**: The name of the outfit object in MinIO.
    - **db**: The database session.
    - **minio**: The Minio service client.
    - **current_user**: The authenticated user.

    Returns the outfit image file as a streaming response.
    """
    # Fetch outfit irrespective of who uploaded it – outfits are shared globally.
    outfit = await outfit_crud.get_outfit_by_object_name_any(db, object_name)
    if not outfit:
        raise HTTPException(status_code=404, detail="Outfit not found")

    # At this point we know the outfit exists in the database. Since outfit images
    # are meant to be shared across all users (e.g. when the recommender suggests
    # an outfit created by someone else), we intentionally do NOT check
    # for ownership here. Only authentication is required, ensured by
    # the `get_current_user` dependency above.

    try:
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
            f"Outfit file {object_name} download started for user "
            f"{current_user.email}"
        )
        return StreamingResponse(iter_data(), media_type=media_type, headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error downloading outfit file {object_name} for user "
            f"{current_user.email}: {str(e)}"
        )
        raise HTTPException(status_code=404, detail=f"File not found. Exception:{e}")


@router.post("/search-similar/", response_model=List[dict])
async def search_similar_outfits(
    request: Request,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
    image_search: ImageSearchEngine = Depends(get_image_search_engine),
    qdrant: QdrantService = Depends(get_qdrant),
    fashion_encoder=Depends(get_fashion_clip_encoder),
):
    """
    Searches for similar outfits based on the user's entire wardrobe.

    This endpoint uses a two-stage search process to find outfits that can be
    best completed with items from the user's wardrobe.

    - **request**: The request object.
    - **db**: The database session.
    - **minio**: The Minio service client.
    - **current_user**: The authenticated user.
    - **image_search**: The image search engine.
    - **qdrant**: The Qdrant service client.
    - **fashion_encoder**: The FashionCLIP encoder.

    Returns a list of recommended outfits, including a completeness score and
    details on which wardrobe items match the outfit's components.
    """
    logger.info(f"Starting similar outfit search for user {current_user.email}")

    try:
        # 1. Get all wardrobe images from the database for object names
        logger.debug("Retrieving user's wardrobe images from database")
        wardrobe_images_db = await crud_image.list_images(
            db, current_user.id, skip=0, limit=1000
        )  # Assume 1000 is enough

        if not wardrobe_images_db:
            logger.warning(f"No wardrobe images found for user {current_user.email}")
            raise HTTPException(status_code=404, detail="No wardrobe images found.")

        logger.info(f"Found {len(wardrobe_images_db)} wardrobe images for analysis")

        # 2. Prepare object names for the new function (no need to load images)
        wardrobe_object_names = [
            db_image.object_name for db_image in wardrobe_images_db
        ]

        # 3. Sample 50 random outfit IDs from the database
        logger.debug("Sampling 50 random outfits from the database")
        sampled_ids = await outfit_crud.get_random_outfit_ids(db, 50)
        if not sampled_ids:
            logger.warning("No outfits found in the database to sample from.")
            return []

        logger.info(f"Sampled {len(sampled_ids)} outfits for evaluation.")

        # 4. Find similar outfits using the new V2 algorithm with pre-calculated embeddings
        logger.debug(
            "Starting ML-based outfit similarity search with V2 algorithm using Qdrant embeddings"
        )
        recommended_outfits = await image_search.find_similar_outfit_v2(
            user_id=str(current_user.id),
            wardrobe_object_names=wardrobe_object_names,
            sampled_outfit_ids=sampled_ids,
            qdrant=qdrant,
            limit_outfits=10,
        )

        result = await _prepare_recommendations(
            request, db, minio, fashion_encoder, recommended_outfits
        )

        logger.info(f"Returning {len(result)} formatted outfit recommendations")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error in similar outfit search for user {current_user.email}: "
            f"{str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error searching for similar outfits",
        )


class WardrobeSubsetRequest(BaseModel):
    """
    Request model for searching similar outfits using a subset of wardrobe images.
    Provide a list of image object_names (recommended) or image IDs.
    """

    object_names: Optional[List[str]] = None
    image_ids: Optional[List[str]] = None  # UUIDs as strings


@router.post("/search-similar-subset/", response_model=List[dict])
async def search_similar_outfits_subset(
    request: Request,
    body: WardrobeSubsetRequest = Body(...),
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
    image_search: ImageSearchEngine = Depends(get_image_search_engine),
    qdrant: QdrantService = Depends(get_qdrant),
    fashion_encoder=Depends(get_fashion_clip_encoder),
):
    """
    Searches for similar outfits based on a user-selected subset of wardrobe images.

    The user must provide a list of image object names or image IDs.

    - **request**: The request object.
    - **body**: The request body containing the list of object names or image IDs.
    - **db**: The database session.
    - **minio**: The Minio service client.
    - **current_user**: The authenticated user.
    - **image_search**: The image search engine.
    - **qdrant**: The Qdrant service client.
    - **fashion_encoder**: The FashionCLIP encoder.

    Returns a list of recommended outfits, including a completeness score and
    details on which wardrobe items match the outfit's components.
    """
    logger.info(
        f"Starting similar outfit search (subset) for user {current_user.email}"
    )

    # Validate input
    if not body.object_names and not body.image_ids:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: object_names or image_ids.",
        )

    # Prepare wardrobe object names for subset search (no need to load images)
    wardrobe_object_names = []

    image_identifiers = []
    if body.object_names:
        image_identifiers = body.object_names
        id_type = "object_name"
    else:
        image_identifiers = body.image_ids  # type:ignore
        id_type = "image_id"

    for identifier in image_identifiers:
        db_image = None
        if id_type == "object_name":
            res = await db.execute(
                select(crud_image.Image).where(
                    crud_image.Image.object_name == identifier,
                    crud_image.Image.user_id == current_user.id,
                )
            )
            db_image = res.scalar_one_or_none()
        elif id_type == "image_id":
            try:
                img_uuid = UUID(identifier)
                db_image = await crud_image.get_image(db, img_uuid, current_user.id)
            except ValueError:
                logger.warning(f"Invalid UUID format for image_id: {identifier}")
                continue

        if db_image:
            wardrobe_object_names.append(db_image.object_name)
        else:
            logger.warning(
                f"Image with {id_type} '{identifier}' not found for user {current_user.email}"
            )

    if not wardrobe_object_names:
        logger.warning(
            f"No valid wardrobe images found for subset search for user {current_user.email}"
        )
        raise HTTPException(status_code=404, detail="No valid wardrobe images found.")

    logger.info(
        f"Found {len(wardrobe_object_names)} wardrobe items for subset analysis"
    )

    # Sample 50 random outfits
    sampled_ids = await outfit_crud.get_random_outfit_ids(db, 50)
    if not sampled_ids:
        logger.warning("No outfits found in the database to sample from.")
        return []

    logger.info(f"Sampled {len(sampled_ids)} outfits for evaluation.")

    # ML search logic using V2 with pre-calculated embeddings
    recommended_outfits = await image_search.find_similar_outfit_v2(
        user_id=str(current_user.id),
        wardrobe_object_names=wardrobe_object_names,
        sampled_outfit_ids=sampled_ids,
        qdrant=qdrant,
        limit_outfits=10,  # Explicitly pass limit
    )

    result = await _prepare_recommendations(
        request, db, minio, fashion_encoder, recommended_outfits
    )

    logger.info(f"Returning {len(result)} formatted outfit recommendations (subset)")
    return result


@router.delete("/{outfit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_outfit(
    outfit_id: UUID,
    db: AsyncSession = Depends(get_db),
    minio: MinioService = Depends(get_minio),
    current_user: User = Depends(get_current_user),
):
    """
    Deletes an outfit and its associated data from all storage systems.

    This includes removing the outfit from the database, its file from MinIO,
    and its associated vectors from Qdrant.

    - **outfit_id**: The ID of the outfit to delete.
    - **db**: The database session.
    - **minio**: The Minio service client.
    - **current_user**: The authenticated user.

    Returns a 204 No Content response on successful deletion.
    """
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
                f"Failed to delete vectors for outfit {outfit_id} from Qdrant by user "
                f"{current_user.email}"
            )
            print(
                f"Warning: Failed to delete vectors for outfit {outfit_id} from Qdrant"
            )

        # Delete from MinIO
        minio_success = minio.delete_file(outfit.object_name)
        if not minio_success:
            logger.warning(
                f"Failed to delete file {outfit.object_name} from MinIO by user "
                f"{current_user.email}"
            )
            print(f"Warning: Failed to delete file {outfit.object_name} from MinIO")

        # Delete from PostgreSQL
        deleted_outfit = await outfit_crud.delete_outfit(db, outfit_id, current_user.id)
        if not deleted_outfit:
            logger.warning(
                f"Failed to delete outfit {outfit_id} from database by user "
                f"{current_user.email}"
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
            f"Error deleting outfit {outfit_id} for user {current_user.email}: "
            f"{str(e)}"
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
    qdrant: QdrantService = Depends(get_qdrant),
    current_user: User = Depends(get_current_user),
):
    """
    Splits an outfit image into individual clothing items and saves them to the database.

    This endpoint also adds the detected clothing items to the Qdrant index for similarity search.

    - **request**: The request object.
    - **file**: The outfit image to process.
    - **db**: The database session.
    - **minio**: The Minio service client.
    - **segmentation_model**: The fashion segmentation model.
    - **image_search**: The image search engine.
    - **qdrant**: The Qdrant service client.
    - **current_user**: The authenticated user.

    Returns the outfit metadata along with information about the detected clothing items.
    """
    logger.info(f"Outfit split to clothes started for user {current_user.email}")
    logger.debug(
        f"Upload details - filename: {file.filename}, "
        f"content_type: {file.content_type}"
    )

    try:
        if not file.content_type.startswith("image/"):
            logger.warning(
                f"Invalid file type for outfit split to clothes by user "
                f"{current_user.email}: {file.content_type}"
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
            # This returns both segmented images and YOLO-detected clothing class names
            result = segmentation_model.get_segment_images(tmp_path)
            if not result or len(result) == 0:
                logger.warning(
                    f"No clothing items detected in the image for outfit "
                    f"{outfit_id} by user {current_user.email}"
                )
                raise HTTPException(
                    status_code=422, detail="No clothing items detected in the image."
                )
            segmented_clothes, cloth_names = result
            if len(segmented_clothes) == 0:
                logger.warning(
                    f"No clothing items detected in the image for outfit "
                    f"{outfit_id} by user {current_user.email}"
                )
                raise HTTPException(
                    status_code=422, detail="No clothing items detected in the image."
                )

            logger.info(
                f"Successfully segmented {len(segmented_clothes)} clothing items for outfit "
                f"{outfit_id}: {cloth_names}"
            )

            # 4. Add each detected clothing item to Qdrant with YOLO-provided clothing types
            clothing_info = []
            for name, cropped_img in zip(cloth_names, segmented_clothes):
                if cropped_img.size == 0:
                    logger.warning(
                        f"Skipping empty crop for item {name} in outfit " f"{outfit_id}"
                    )
                    continue  # skip empty crops
                pil_img = Image.fromarray(cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB))
                image_id = str(uuid.uuid4())

                # Extract base clothing type from YOLO name (remove _0, _1 suffixes)
                clothing_type = name.split("_")[0] if "_" in name else name

                await image_search.add_image_to_index(
                    image=pil_img,
                    image_id=image_id,
                    outfit_id=outfit_id,
                    qdrant=qdrant,
                    clothing_type=clothing_type,
                )
                clothing_info.append(
                    {"name": name, "image_id": image_id, "clothing_type": clothing_type}
                )

            logger.info(
                f"Successfully added {len(clothing_info)} clothing items to Qdrant for outfit "
                f"{outfit_id}"
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
                f"Outfit split to clothes completed successfully for user "
                f"{current_user.email} - Outfit ID: {outfit_id}"
            )
            return result

        finally:
            os.remove(tmp_path)
            logger.debug(f"Deleted temporary file: {tmp_path}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error in outfit split to clothes for user {current_user.email}: "
            f"{str(e)}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error splitting outfit to clothes",
        )
