from unittest.mock import MagicMock, patch

import numpy as np
from app.ml.image_search import ImageSearchEngine
from PIL import Image


def test_image_search_engine_initialization():
    """Test that ImageSearchEngine initializes properly with FashionCLIP."""
    with patch("app.ml.image_search.FashionClipEncoder") as mock_encoder:
        mock_encoder_instance = MagicMock()
        mock_encoder.return_value = mock_encoder_instance
        mock_encoder_instance.device = "cpu"

        engine = ImageSearchEngine()

        assert engine.encoder == mock_encoder_instance
        mock_encoder.assert_called_once_with(model_name="patrickjohncyh/fashion-clip")


def test_get_image_embeddings_success():
    """Test successful embedding generation."""
    with patch("app.ml.image_search.FashionClipEncoder") as mock_encoder:
        mock_encoder_instance = MagicMock()
        mock_encoder.return_value = mock_encoder_instance

        # Mock the encoder to return test embeddings
        test_embeddings = np.array([[0.1, 0.2, 0.3]])
        mock_encoder_instance.encode_images.return_value = test_embeddings

        engine = ImageSearchEngine()

        # Create a mock PIL image
        mock_image = MagicMock(spec=Image.Image)

        result = engine.get_image_embeddings(mock_image)

        # Verify the result
        np.testing.assert_array_equal(result, test_embeddings)
        mock_encoder_instance.encode_images.assert_called_once_with(
            [mock_image], batch_size=32, normalize=True
        )


def test_get_image_embeddings_multiple_images():
    """Test embedding generation for multiple images."""
    with patch("app.ml.image_search.FashionClipEncoder") as mock_encoder:
        mock_encoder_instance = MagicMock()
        mock_encoder.return_value = mock_encoder_instance

        # Mock the encoder to return test embeddings for multiple images
        test_embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])
        mock_encoder_instance.encode_images.return_value = test_embeddings

        engine = ImageSearchEngine()

        # Create mock PIL images
        mock_images = [MagicMock(spec=Image.Image), MagicMock(spec=Image.Image)]

        result = engine.get_image_embeddings(mock_images, batch_size=16)

        # Verify the result
        np.testing.assert_array_equal(result, test_embeddings)
        mock_encoder_instance.encode_images.assert_called_once_with(
            mock_images, batch_size=16, normalize=True
        )


def test_get_image_embeddings_failure():
    """Test handling of embedding generation failure."""
    with patch("app.ml.image_search.FashionClipEncoder") as mock_encoder:
        mock_encoder_instance = MagicMock()
        mock_encoder.return_value = mock_encoder_instance

        # Mock the encoder to raise an exception
        mock_encoder_instance.encode_images.side_effect = Exception(
            "FashionCLIP encoding failed"
        )

        engine = ImageSearchEngine()
        mock_image = MagicMock(spec=Image.Image)

        try:
            engine.get_image_embeddings(mock_image)
            assert False, "Expected exception was not raised"
        except Exception as e:
            assert str(e) == "FashionCLIP encoding failed"
