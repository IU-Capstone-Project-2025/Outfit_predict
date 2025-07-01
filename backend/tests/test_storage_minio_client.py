import sys
from unittest.mock import patch, MagicMock
sys.modules["minio"] = MagicMock()
sys.modules["minio.error"] = MagicMock()
import pytest
from app.storage.minio_client import MinioService


@patch('app.storage.minio_client.Minio')
@patch('app.storage.minio_client.get_settings')
def test_save_file(mock_get_settings, mock_minio):
    # Mock settings
    mock_settings = MagicMock()
    mock_settings.minio_endpoint = 'endpoint'
    mock_settings.minio_access_key = 'access'
    mock_settings.minio_secret_key = 'secret'
    mock_settings.minio_secure = False
    mock_settings.minio_bucket = 'bucket'
    mock_get_settings.return_value = mock_settings
    # Mock client
    mock_client = MagicMock()
    mock_minio.return_value = mock_client
    mock_client.bucket_exists.return_value = True
    service = MinioService()
    data = b'data'
    object_name = service.save_file(data, content_type='text/plain')
    mock_client.put_object.assert_called_once()
    assert isinstance(object_name, str)


@patch('app.storage.minio_client.Minio')
@patch('app.storage.minio_client.get_settings')
def test_get_stream(mock_get_settings, mock_minio):
    mock_settings = MagicMock()
    mock_settings.minio_endpoint = 'endpoint'
    mock_settings.minio_access_key = 'access'
    mock_settings.minio_secret_key = 'secret'
    mock_settings.minio_secure = False
    mock_settings.minio_bucket = 'bucket'
    mock_get_settings.return_value = mock_settings
    mock_client = MagicMock()
    mock_minio.return_value = mock_client
    mock_client.bucket_exists.return_value = True
    service = MinioService()
    service.client.get_object.return_value = 'stream'
    result = service.get_stream('obj')
    mock_client.get_object.assert_called_once_with(service.bucket, 'obj')
    assert result == 'stream'


@patch('app.storage.minio_client.Minio')
@patch('app.storage.minio_client.get_settings')
def test_presigned_url_success(mock_get_settings, mock_minio):
    mock_settings = MagicMock()
    mock_settings.minio_endpoint = 'endpoint'
    mock_settings.minio_access_key = 'access'
    mock_settings.minio_secret_key = 'secret'
    mock_settings.minio_secure = False
    mock_settings.minio_bucket = 'bucket'
    mock_get_settings.return_value = mock_settings
    mock_client = MagicMock()
    mock_minio.return_value = mock_client
    mock_client.bucket_exists.return_value = True
    service = MinioService()
    mock_client.presigned_get_object.return_value = 'url'
    url = service.presigned_url('obj', expiry=60)
    mock_client.presigned_get_object.assert_called_once()
    assert url == 'url'


@patch('app.storage.minio_client.Minio')
@patch('app.storage.minio_client.get_settings')
@patch('app.storage.minio_client.S3Error', new=Exception)
def test_presigned_url_error(mock_get_settings, mock_minio):
    mock_settings = MagicMock()
    mock_settings.minio_endpoint = 'endpoint'
    mock_settings.minio_access_key = 'access'
    mock_settings.minio_secret_key = 'secret'
    mock_settings.minio_secure = False
    mock_settings.minio_bucket = 'bucket'
    mock_get_settings.return_value = mock_settings
    mock_client = MagicMock()
    mock_minio.return_value = mock_client
    mock_client.bucket_exists.return_value = True
    service = MinioService()
    mock_client.presigned_get_object.side_effect = Exception('fail')
    with pytest.raises(RuntimeError):
        service.presigned_url('obj', expiry=60)
