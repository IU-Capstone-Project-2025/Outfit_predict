import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.crud.image import create_image, get_image, list_images
from app.models.image import Image


@pytest.mark.asyncio
async def test_create_image():
    # Arrange
    db = AsyncMock()
    description = "A test image"
    object_name = "test_image.png"
    # Mock the add, commit, and refresh methods
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    # Act
    result = await create_image(db, description, object_name)
    # Assert
    db.add.assert_called_once()
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(result)
    assert isinstance(result, Image)
    assert result.description == description
    assert result.object_name == object_name


@pytest.mark.asyncio
async def test_get_image_found():
    db = AsyncMock()
    image_id = uuid.uuid4()
    expected_image = Image(description="desc", object_name="obj.png")
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = expected_image
    db.execute.return_value = mock_result
    result = await get_image(db, image_id)
    db.execute.assert_awaited_once()
    assert result == expected_image


@pytest.mark.asyncio
async def test_get_image_not_found():
    db = AsyncMock()
    image_id = uuid.uuid4()
    mock_result = AsyncMock()
    mock_result.scalar_one_or_none.return_value = None
    db.execute.return_value = mock_result
    result = await get_image(db, image_id)
    db.execute.assert_awaited_once()
    assert result is None


@pytest.mark.asyncio
async def test_list_images():
    db = AsyncMock()
    images = [
        Image(description=f"desc{i}", object_name=f"obj{i}.png") for i in range(3)
    ]
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = images
    mock_result.scalars.return_value = mock_scalars
    db.execute = AsyncMock(return_value=mock_result)
    result = await list_images(db)
    db.execute.assert_awaited_once()
    assert result == images
