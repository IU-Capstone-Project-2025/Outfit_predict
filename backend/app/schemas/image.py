from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ImageBase(BaseModel):
    description: str | None


class ImageCreate(ImageBase):
    object_name: str


class ImageRead(ImageBase):
    id: UUID
    object_name: str
    created_at: datetime
    user_id: UUID
    url: str
    thumbnail_url: str | None

    class Config:
        from_attributes = True
