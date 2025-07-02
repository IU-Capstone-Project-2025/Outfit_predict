import uuid

from app.models.image import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def create_image(
    db: AsyncSession, user_id: uuid.UUID, description: str | None, object_name: str
) -> Image:
    image = Image(user_id=user_id, description=description, object_name=object_name)
    db.add(image)
    await db.commit()
    await db.refresh(image)
    return image


async def get_image(
    db: AsyncSession, image_id: uuid.UUID, user_id: uuid.UUID
) -> Image | None:
    res = await db.execute(
        select(Image).where(Image.id == image_id, Image.user_id == user_id)
    )
    return res.scalar_one_or_none()


async def list_images(
    db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[Image]:
    stmt = (
        select(Image)
        .where(Image.user_id == user_id)
        .order_by(Image.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())
