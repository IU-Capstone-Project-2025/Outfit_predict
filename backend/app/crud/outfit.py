from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.outfit import Outfit
from app.schemas.outfit import OutfitCreate
from uuid import UUID

async def create_outfit(db: AsyncSession, object_name: str) -> Outfit:
    outfit = Outfit(object_name=object_name)
    db.add(outfit)
    await db.commit()
    await db.refresh(outfit)
    return outfit

async def get_outfit(db: AsyncSession, outfit_id: UUID) -> Outfit | None:
    res = await db.execute(select(Outfit).where(Outfit.id == outfit_id))
    return res.scalar_one_or_none()

async def list_outfits(db: AsyncSession, skip: int = 0, limit: int = 100) -> list[Outfit]:
    """Return outfits ordered by newest first."""
    stmt = select(Outfit).order_by(Outfit.created_at.desc()).offset(skip).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())
