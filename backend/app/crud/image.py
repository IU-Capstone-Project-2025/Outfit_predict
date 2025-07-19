import uuid

from app.core.logging import get_logger
from app.models.image import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Initialize logger for image CRUD operations
logger = get_logger("app.db.crud.image")


async def create_image(
    db: AsyncSession,
    user_id: uuid.UUID,
    description: str | None,
    object_name: str,
    thumbnail_object_name: str | None = None,
) -> Image:
    logger.debug(
        f"Creating image for user {user_id}: object_name={object_name}, "
        f"thumbnail_object_name={thumbnail_object_name}, description={description}"
    )

    try:
        image = Image(
            user_id=user_id,
            description=description,
            object_name=object_name,
            thumbnail_object_name=thumbnail_object_name,
        )
        db.add(image)
        await db.commit()
        await db.refresh(image)

        logger.info(f"Successfully created image {image.id} for user {user_id}")
        return image

    except Exception as e:
        logger.error(f"Error creating image for user {user_id}: {str(e)}")
        await db.rollback()
        raise


async def get_image(
    db: AsyncSession, image_id: uuid.UUID, user_id: uuid.UUID
) -> Image | None:
    logger.debug(f"Getting image {image_id} for user {user_id}")

    try:
        res = await db.execute(
            select(Image).where(Image.id == image_id, Image.user_id == user_id)
        )
        image = res.scalar_one_or_none()

        if image:
            logger.debug(f"Image {image_id} found for user {user_id}")
        else:
            logger.debug(f"Image {image_id} not found for user {user_id}")

        return image

    except Exception as e:
        logger.error(f"Error getting image {image_id} for user {user_id}: {str(e)}")
        raise


async def list_images(
    db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[Image]:
    logger.debug(f"Listing images for user {user_id} (skip={skip}, limit={limit})")

    try:
        stmt = (
            select(Image)
            .where(Image.user_id == user_id)
            .order_by(Image.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(stmt)
        images = list(res.scalars().all())

        logger.info(f"Retrieved {len(images)} images for user {user_id}")
        return images

    except Exception as e:
        logger.error(f"Error listing images for user {user_id}: {str(e)}")
        raise


async def delete_image(
    db: AsyncSession, image_id: uuid.UUID, user_id: uuid.UUID
) -> None:
    logger.debug(f"Deleting image {image_id} for user {user_id}")

    try:
        stmt = select(Image).where(Image.id == image_id, Image.user_id == user_id)
        res = await db.execute(stmt)
        image = res.scalar_one_or_none()

        if not image:
            logger.warning(f"Image {image_id} not found for deletion by user {user_id}")
            return

        await db.delete(image)
        await db.commit()
        logger.info(f"Successfully deleted image {image_id} for user {user_id}")

    except Exception as e:
        logger.error(f"Error deleting image {image_id} for user {user_id}: {str(e)}")
        await db.rollback()
        raise
