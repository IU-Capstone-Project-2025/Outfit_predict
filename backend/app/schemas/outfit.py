from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

class OutfitBase(BaseModel):
    object_name: str

class OutfitCreate(OutfitBase):
    pass

class OutfitRead(OutfitBase):
    id: UUID
    created_at: datetime
    url: str

    class Config:
        from_attributes = True 