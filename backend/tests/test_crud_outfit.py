import pytest
import uuid
from unittest.mock import AsyncMock, MagicMock
from app.crud.outfit import create_outfit, get_outfit, list_outfits
from app.models.outfit import Outfit
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID


@pytest.mark.asyncio
async def test_create_outfit():
    db = AsyncMock()
    object_name = "test_outfit.png"
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    result = await create_outfit(db, object_name)
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(result)
    assert isinstance(result, Outfit)
    assert result.object_name == object_name


@pytest.mark.asyncio
async def test_get_outfit_found():
    db = AsyncMock()
    outfit_id = uuid.uuid4()
    expected_outfit = Outfit(object_name="obj.png")
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = expected_outfit
    db.execute.return_value = mock_result
    result = await get_outfit(db, outfit_id)
    db.execute.assert_awaited_once()
    assert result == expected_outfit


@pytest.mark.asyncio
async def test_get_outfit_not_found():
    db = AsyncMock()
    outfit_id = uuid.uuid4()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    result = await get_outfit(db, outfit_id)
    db.execute.assert_awaited_once()
    assert result is None


@pytest.mark.asyncio
async def test_list_outfits():
    db = AsyncMock()
    outfits = [Outfit(object_name=f"obj{i}.png") for i in range(3)]
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = outfits
    mock_result.scalars.return_value = mock_scalars
    db.execute = AsyncMock(return_value=mock_result)
    result = await list_outfits(db)
    db.execute.assert_awaited_once()
    assert result == outfits
