import sys
from unittest.mock import patch, MagicMock, AsyncMock
sys.modules["clip"] = MagicMock()
import numpy as np
import pytest
from PIL import Image as PILImage
from app.ml.image_search import ImageSearchEngine
import torch
from app.schemas.outfit import RecommendedOutfit, MatchedItem



@patch.object(ImageSearchEngine, '__init__', lambda self, model_name=None: None)
def test_get_image_embeddings_batches():
    engine = ImageSearchEngine()
    # Mock preprocess to return a tensor of ones
    engine.preprocess = MagicMock(
        side_effect=lambda img: torch.ones((3, 224, 224)))
    # Mock model

    class DummyModel:
        def to(self, device):
            return self

        def eval(self):
            return self

        def encode_image(self, batch_tensor):
            # Return a tensor with shape (batch_size, 512)
            batch_size = batch_tensor.shape[0]
            return MagicMock(cpu=lambda: MagicMock(numpy=lambda: np.ones((batch_size, 512))))
    engine.model = DummyModel()
    engine.device = 'cpu'
    # Create 5 fake images
    images = [MagicMock(spec=PILImage.Image) for _ in range(5)]
    # Run
    embeddings = engine.get_image_embeddings(images, batch_size=2)
    # Assert
    assert embeddings.shape == (5, 512)
    assert np.all(embeddings == 1)


@patch.object(ImageSearchEngine, '__init__', lambda self, model_name=None: None)
@patch.object(ImageSearchEngine, 'get_image_embeddings', return_value=np.ones((1, 512)))
def test_find_similar_images(mock_get_emb):
    engine = ImageSearchEngine()
    engine.device = 'cpu'
    # Mock QdrantService
    mock_qdrant = MagicMock()
    mock_qdrant.search_vectors.return_value = [
        MagicMock(id='img1', score=0.9), MagicMock(id='img2', score=0.8)]
    # Run
    import types

    async def run():
        result = await engine.find_similar_images(MagicMock(), mock_qdrant, limit=2, score_threshold=0.5)
        assert result == [('img1', 0.9), ('img2', 0.8)]
        mock_get_emb.assert_called_once()
        mock_qdrant.search_vectors.assert_called_once()
    import asyncio
    asyncio.run(run())


@patch.object(ImageSearchEngine, '__init__', lambda self, model_name=None: None)
@patch.object(ImageSearchEngine, 'get_image_embeddings', return_value=np.ones((1, 512)))
def test_add_image_to_index(mock_get_emb):
    engine = ImageSearchEngine()
    engine.device = 'cpu'
    # Mock QdrantService
    mock_qdrant = MagicMock()
    # Run
    import types

    async def run():
        await engine.add_image_to_index(MagicMock(), 'imgid', 'outfitid', mock_qdrant)
        mock_get_emb.assert_called_once()
        mock_qdrant.upsert_vectors.assert_called_once()
    import asyncio
    asyncio.run(run())


@patch.object(ImageSearchEngine, '__init__', lambda self, model_name=None: None)
@patch.object(ImageSearchEngine, 'get_image_embeddings', return_value=np.ones((2, 512)))
def test_find_similar_outfit(mock_get_emb):
    engine = ImageSearchEngine()
    engine.device = 'cpu'
    # Mock QdrantService
    mock_qdrant = MagicMock()
    # Mock search_vectors to return points with outfit_id payloads
    mock_point1 = MagicMock()
    mock_point1.payload = {"outfit_id": "outfit1"}
    mock_point2 = MagicMock()
    mock_point2.payload = {"outfit_id": "outfit2"}
    mock_qdrant.search_vectors.side_effect = [
        [mock_point1, mock_point2], [mock_point1]]
    # Mock get_outfit_vectors to return fake vectors
    mock_record = MagicMock()
    mock_record.vector = np.ones(512)
    mock_record.id = 'item1'
    mock_qdrant.get_outfit_vectors.return_value = [mock_record, mock_record]
    # Run
    images = [MagicMock(), MagicMock()]
    wardrobe_object_names = ["shirt", "pants"]
    import types

    async def run():
        result = await engine.find_similar_outfit(images, wardrobe_object_names, mock_qdrant, score_threshold=0.5, limit_outfits=2)
        assert isinstance(result, list)
    import asyncio
    asyncio.run(run())
