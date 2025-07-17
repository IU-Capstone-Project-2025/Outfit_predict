from pydantic import BaseModel


class ObjectURL(BaseModel):
    url: str
