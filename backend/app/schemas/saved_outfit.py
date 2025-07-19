from datetime import datetime
from typing import Any, Dict, List
from uuid import UUID

from pydantic import BaseModel


class MatchedItem(BaseModel):
    """Matched wardrobe item for an outfit."""

    wardrobe_image_index: int
    wardrobe_image_object_name: str
    outfit_item_id: str
    score: float


class SavedOutfitCreate(BaseModel):
    """Request model to save an outfit."""

    outfit_id: UUID
    completeness_score: float
    matches: List[MatchedItem]


class SavedOutfitRead(BaseModel):
    """Response model for saved outfit."""

    id: UUID
    user_id: UUID
    outfit_id: UUID
    completeness_score: float
    matches: List[MatchedItem]
    created_at: datetime

    class Config:
        from_attributes = True


class SavedOutfitWithDetails(BaseModel):
    """Response model for saved outfit with outfit details."""

    id: UUID
    user_id: UUID
    outfit_id: UUID
    completeness_score: float
    matches: List[MatchedItem]
    created_at: datetime
    outfit: Dict[str, Any]  # Will contain outfit details (id, url, object_name, etc.)

    class Config:
        from_attributes = True
