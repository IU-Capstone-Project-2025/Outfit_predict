from app.core.logging import get_logger
from app.core.url_utils import build_url
from app.deps import get_current_user, get_db
from app.models.image import Image
from app.models.user import User
from app.schemas.utilities import ObjectURL
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Initialize logger for image operations
logger = get_logger("app.api.utilities")

router = APIRouter(prefix="/utilities", tags=["utilities"])


@router.get("/{object_name}/url", response_model=ObjectURL)
async def get_object_url(
    request: Request,
    object_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves the URL for a given object name.

    This endpoint maps an object name to its corresponding image URL and thumbnail URL.

    - **request**: The request object.
    - **object_name**: The name of the object to retrieve the URL for.
    - **db**: The database session.
    - **current_user**: The authenticated user.

    Returns an object containing the URL and thumbnail URL for the specified object.
    """
    logger.info(
        f"Retrieving the image url for {current_user.email} (object_name: {object_name})"
    )

    try:
        res = await db.execute(
            select(Image).where(
                Image.object_name == object_name, Image.user_id == current_user.id
            )
        )
        image = res.scalar_one_or_none()

        if image:
            logger.debug(f"Image {image.id} found for user {current_user.id}")
        else:
            logger.debug(f"Image {object_name} not found for user {current_user.id}")
            raise HTTPException(status_code=404, detail="Image not found")

        return ObjectURL(
            url=build_url(request, "get_image_file", image_id=image.id),
            thumbnail_url=(
                build_url(request, "get_image_thumbnail", image_id=image.id)
                if image.thumbnail_object_name
                else None
            ),
        )

    except Exception as e:
        logger.error(
            f"Error getting image {object_name} for user {current_user.id}: {str(e)}"
        )
        raise
