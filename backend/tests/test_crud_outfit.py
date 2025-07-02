from unittest.mock import AsyncMock

import pytest
from app.crud.outfit import create_outfit, get_outfit, list_outfits
from app.models.outfit import Outfit
from app.schemas.outfit import OutfitCreate


@pytest.mark.asyncio
async def test_create_outfit():
    db = AsyncMock()
    outfit_in = OutfitCreate(name="Test", items=[])
    db.add.return_value = None
    db.commit.return_value = None
    db.refresh.return_value = None
    await create_outfit(db, outfit_in)
    db.add.assert_called_once()
    db.commit.assert_called_once()
    db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_get_outfit():
    db = AsyncMock()
    db.get.return_value = Outfit(id=1, name="Test", items=[])
    result = await get_outfit(db, 1)
    assert result.name == "Test"


@pytest.mark.asyncio
async def test_list_outfits():
    db = AsyncMock()
    db.execute.return_value.scalars.return_value.all.return_value = [
        Outfit(id=1, name="Test", items=[])
    ]
    result = await list_outfits(db)
    assert len(result) == 1
