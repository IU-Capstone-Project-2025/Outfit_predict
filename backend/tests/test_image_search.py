from unittest.mock import MagicMock, patch

from app.ml.image_search import search_similar_images


def test_search_similar_images_success():
    with patch("app.ml.image_search.CLIP") as mock_clip:
        mock_model = MagicMock()
        mock_clip.load.return_value = mock_model
        mock_model.encode_image.return_value = [0.1, 0.2]
        mock_model.encode_text.return_value = [0.1, 0.2]
        result = search_similar_images("fake_path", ["desc1", "desc2"])
        assert isinstance(result, list)


def test_search_similar_images_failure():
    with patch("app.ml.image_search.CLIP", side_effect=Exception("fail")):
        result = search_similar_images("fake_path", ["desc1"])
        assert result == []
