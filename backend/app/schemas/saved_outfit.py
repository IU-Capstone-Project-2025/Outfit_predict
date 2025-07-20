from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MatchedItem(BaseModel):
    """Matched wardrobe item for an outfit."""

    wardrobe_image_index: Optional[int] = Field(
        None,
        description="Index of the wardrobe image if the item is from the wardrobe.",
    )
    wardrobe_image_object_name: Optional[str] = Field(
        None,
        description="Object name of the wardrobe image if the item is from the wardrobe.",
    )
    clothing_type: Optional[str] = Field(
        None, description="Type of clothing if the item is a suggestion."
    )
    external_image_url: Optional[str] = Field(
        None, description="URL of the external image if the item is a suggestion."
    )
    suggested_item_product_link: Optional[str] = Field(
        None,
        description="Product link for the suggested item (if the item comes from external source).",
    )
    outfit_item_id: str
    score: Optional[float] = Field(None, description="Match score for the item.")


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
