from pydantic import BaseModel


class ObjectURL(BaseModel):
    url: str
    thumbnail_url: str | None
