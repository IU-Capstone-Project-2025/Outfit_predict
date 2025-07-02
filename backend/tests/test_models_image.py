import uuid

from app.models.image import Image


def test_image_instantiation():
    obj_name = "test.png"
    img = Image(object_name=obj_name, description="desc")
    assert img.object_name == obj_name
    assert img.description == "desc"
    # id is set by default or by DB
    assert isinstance(img.id, uuid.UUID) or img.id is None


def test_image_model_fields():
    image = Image(id=1, url="test", description="desc")
    assert image.id == 1
    assert image.url == "test"
    assert image.description == "desc"
