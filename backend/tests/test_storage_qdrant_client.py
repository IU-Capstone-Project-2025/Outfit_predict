import sys
from unittest.mock import patch, MagicMock
import pytest
from app.storage.qdrant_client import QdrantService


@patch('app.storage.qdrant_client.QdrantClient')
@patch('app.storage.qdrant_client.get_settings')
@patch('app.storage.qdrant_client.models')
def test_upsert_vectors(mock_models, mock_get_settings, mock_qdrant):
    mock_settings = MagicMock()
    mock_settings.qdrant_url = 'url'
    mock_settings.qdrant_api_key = 'key'
    mock_get_settings.return_value = mock_settings
    mock_client = MagicMock()
    mock_qdrant.return_value = mock_client
    mock_client.get_collections.return_value.collections = []
    service = QdrantService()
    points = [MagicMock()]
    service.upsert_vectors(points)
    mock_client.upsert.assert_called_once_with(
        collection_name=service.collection_name, points=points)


@patch('app.storage.qdrant_client.QdrantClient')
@patch('app.storage.qdrant_client.get_settings')
@patch('app.storage.qdrant_client.models')
def test_search_vectors(mock_models, mock_get_settings, mock_qdrant):
    mock_settings = MagicMock()
    mock_settings.qdrant_url = 'url'
    mock_settings.qdrant_api_key = 'key'
    mock_get_settings.return_value = mock_settings
    mock_client = MagicMock()
    mock_qdrant.return_value = mock_client
    mock_client.get_collections.return_value.collections = []
    service = QdrantService()
    mock_client.search.return_value = ['result']
    result = service.search_vectors([1.0]*512, limit=5, score_threshold=0.5)
    mock_client.search.assert_called_once()
    assert result == ['result']


@patch('app.storage.qdrant_client.QdrantClient')
@patch('app.storage.qdrant_client.get_settings')
@patch('app.storage.qdrant_client.models')
def test_get_point_success(mock_models, mock_get_settings, mock_qdrant):
    mock_settings = MagicMock()
    mock_settings.qdrant_url = 'url'
    mock_settings.qdrant_api_key = 'key'
    mock_get_settings.return_value = mock_settings
    mock_client = MagicMock()
    mock_qdrant.return_value = mock_client
    mock_client.get_collections.return_value.collections = []
    service = QdrantService()
    mock_client.retrieve.return_value = ['point']
    result = service.get_point('pid')
    mock_client.retrieve.assert_called_once()
    assert result == 'point'


@patch('app.storage.qdrant_client.QdrantClient')
@patch('app.storage.qdrant_client.get_settings')
@patch('app.storage.qdrant_client.models')
def test_get_point_not_found(mock_models, mock_get_settings, mock_qdrant):
    mock_settings = MagicMock()
    mock_settings.qdrant_url = 'url'
    mock_settings.qdrant_api_key = 'key'
    mock_get_settings.return_value = mock_settings
    mock_client = MagicMock()
    mock_qdrant.return_value = mock_client
    mock_client.get_collections.return_value.collections = []
    service = QdrantService()
    mock_client.retrieve.return_value = []
    with pytest.raises(ValueError):
        service.get_point('pid')


@patch('app.storage.qdrant_client.QdrantClient')
@patch('app.storage.qdrant_client.get_settings')
@patch('app.storage.qdrant_client.models')
def test_get_outfit_vectors(mock_models, mock_get_settings, mock_qdrant):
    mock_settings = MagicMock()
    mock_settings.qdrant_url = 'url'
    mock_settings.qdrant_api_key = 'key'
    mock_get_settings.return_value = mock_settings
    mock_client = MagicMock()
    mock_qdrant.return_value = mock_client
    mock_client.get_collections.return_value.collections = []
    service = QdrantService()
    mock_client.scroll.return_value = (['rec1', 'rec2'], None)
    result = service.get_outfit_vectors('oid')
    mock_client.scroll.assert_called_once()
    assert result == ['rec1', 'rec2']
