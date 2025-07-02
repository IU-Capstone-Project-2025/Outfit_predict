import uuid

from app.models.outfit import Outfit


def test_outfit_instantiation():
    obj_name = "outfit.png"
    outfit = Outfit(object_name=obj_name)
    assert outfit.object_name == obj_name
    # id is set by default or by DB
    assert isinstance(outfit.id, uuid.UUID) or outfit.id is None


def test_outfit_model_fields():
    outfit = Outfit(id=1, name="test", items=[])
    assert outfit.id == 1
    assert outfit.name == "test"
    assert outfit.items == []
