import pytest
import uuid
from app.models.image import Image


def test_image_instantiation():
    obj_name = "test.png"
    img = Image(object_name=obj_name, description="desc")
    assert img.object_name == obj_name
    assert img.description == "desc"
    # id is set by default or by DB
    assert isinstance(img.id, uuid.UUID) or img.id is None

