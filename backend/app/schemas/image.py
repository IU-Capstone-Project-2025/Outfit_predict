from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ImageBase(BaseModel):
    description: Optional[str] = None


class ImageCreate(ImageBase):
    pass  # description + file provided via form data


class ImageRead(ImageBase):
    id: UUID
    object_name: str
    url: str

    class Config:
        from_attributes = True  # SQLA → Pydantic
