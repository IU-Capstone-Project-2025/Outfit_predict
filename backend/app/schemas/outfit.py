from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel


class OutfitBase(BaseModel):
    pass


class OutfitCreate(OutfitBase):
    object_name: str


class OutfitRead(OutfitBase):
    id: UUID
    created_at: datetime
    url: str
    clothing_items: Optional[List[Dict[str, str]]] = None

    class Config:
        from_attributes = True


class MatchedItem(BaseModel):
    outfit_item_id: str
    score: float
    wardrobe_image_index: Optional[int] = None
    wardrobe_image_object_name: Optional[str] = None
    suggested_item_product_link: Optional[str] = None
    suggested_item_image_link: Optional[str] = None


class RecommendedOutfit(BaseModel):
    outfit_id: str
    completeness_score: float
    matches: List[MatchedItem]
