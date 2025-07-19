from typing import List, Optional
from uuid import UUID

from app.models.saved_outfit import SavedOutfit
from app.schemas.saved_outfit import SavedOutfitCreate
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession


async def save_outfit(
    db: AsyncSession, user_id: UUID, outfit_data: SavedOutfitCreate
) -> SavedOutfit:
    """Save an outfit to user's saved collection."""

    # Check if outfit is already saved by this user
    existing = await db.execute(
        select(SavedOutfit).where(
            SavedOutfit.user_id == user_id,
            SavedOutfit.outfit_id == outfit_data.outfit_id,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError("Outfit already saved")

    # Convert matches to dict format for JSON storage
    matches_dict = [match.model_dump() for match in outfit_data.matches]

    saved_outfit = SavedOutfit(
        user_id=user_id,
        outfit_id=outfit_data.outfit_id,
        completeness_score=outfit_data.completeness_score,
        matches=matches_dict,
    )

    db.add(saved_outfit)
    await db.commit()
    await db.refresh(saved_outfit)
    return saved_outfit


async def list_saved_outfits(
    db: AsyncSession, user_id: UUID, skip: int = 0, limit: int = 100
) -> List[SavedOutfit]:
    """Get all saved outfits for a user, ordered by newest first."""
    stmt = (
        select(SavedOutfit)
        .where(SavedOutfit.user_id == user_id)
        .order_by(SavedOutfit.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_saved_outfit(
    db: AsyncSession, saved_outfit_id: UUID, user_id: UUID
) -> Optional[SavedOutfit]:
    """Get a specific saved outfit by ID for a user."""
    stmt = select(SavedOutfit).where(
        SavedOutfit.id == saved_outfit_id, SavedOutfit.user_id == user_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def delete_saved_outfit(
    db: AsyncSession, saved_outfit_id: UUID, user_id: UUID
) -> bool:
    """Delete a saved outfit. Returns True if deleted, False if not found."""
    stmt = delete(SavedOutfit).where(
        SavedOutfit.id == saved_outfit_id, SavedOutfit.user_id == user_id
    )
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def is_outfit_saved(db: AsyncSession, user_id: UUID, outfit_id: UUID) -> bool:
    """Check if an outfit is already saved by the user."""
    stmt = select(SavedOutfit).where(
        SavedOutfit.user_id == user_id, SavedOutfit.outfit_id == outfit_id
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None
