import uuid

from app.models.image import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def create_image(
    db: AsyncSession, description: str | None, object_name: str
) -> Image:
    image = Image(description=description, object_name=object_name)
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


async def get_image(db: AsyncSession, image_id: uuid.UUID) -> Image | None:
    res = await db.execute(select(Image).where(Image.id == image_id))
    return await res.scalar_one_or_none()


async def list_images(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Image]:
    """Return images ordered by newest first."""
    stmt = select(Image).order_by(
        Image.created_at.desc()).offset(skip).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())
