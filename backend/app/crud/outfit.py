import uuid
from uuid import UUID

from app.models.outfit import Outfit
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def create_outfit(
    db: AsyncSession, user_id: uuid.UUID, object_name: str
) -> Outfit:
    outfit = Outfit(object_name=object_name, user_id=user_id)
    db.add(outfit)
    await db.commit()
    await db.refresh(outfit)
    return outfit


async def get_outfit(
    db: AsyncSession, outfit_id: UUID, user_id: uuid.UUID
) -> Outfit | None:
    res = await db.execute(
        select(Outfit).where(Outfit.id == outfit_id, Outfit.user_id == user_id)
    )
    return res.scalar_one_or_none()


async def list_outfits(
    db: AsyncSession, user_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[Outfit]:
    """Return outfits ordered by newest first, filtered by user."""
    stmt = (
        select(Outfit)
        .where(Outfit.user_id == user_id)
        .order_by(Outfit.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    res = await db.execute(stmt)
    return list(res.scalars().all())


async def get_outfit_by_object_name(
    db: AsyncSession, object_name: str, user_id: uuid.UUID
) -> Outfit | None:
    """Get outfit by object name, ensuring user ownership."""
    res = await db.execute(
        select(Outfit).where(
            Outfit.object_name == object_name, Outfit.user_id == user_id
        )
    )
    return res.scalar_one_or_none()


async def get_outfit_by_object_name_any(
    db: AsyncSession, object_name: str
) -> Outfit | None:
    """Get outfit by object name without filtering by user ownership."""
    res = await db.execute(select(Outfit).where(Outfit.object_name == object_name))
    return res.scalar_one_or_none()


async def delete_outfit(
    db: AsyncSession, outfit_id: UUID, user_id: uuid.UUID
) -> Outfit | None:
    """Delete an outfit, ensuring user ownership."""
    # First get the outfit to ensure it exists and user owns it
    outfit = await get_outfit(db, outfit_id, user_id)
    if not outfit:
        return None

    # Delete from database
    await db.delete(outfit)
    await db.commit()
    return outfit
