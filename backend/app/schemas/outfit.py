from uuid import UUID
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime


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
    wardrobe_image_index: int
    wardrobe_image_object_name: str
    outfit_item_id: str
    score: float


class RecommendedOutfit(BaseModel):
    outfit_id: str
    completeness_score: float
    matches: List[MatchedItem]
