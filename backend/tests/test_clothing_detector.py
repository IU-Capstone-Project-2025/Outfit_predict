import sys
from unittest.mock import MagicMock, patch
sys.modules["ultralytics"] = MagicMock()
from app.ml.clothing_detector import get_clothes_from_img
import numpy as np
import pytest



@pytest.mark.parametrize("img_shape, boxes, expected_names", [
    ((100, 200, 3), [
        (MagicMock(item=MagicMock(return_value=3)), [0.5, 0.5, 0.2, 0.4]),
        (MagicMock(item=MagicMock(return_value=4)), [0.7, 0.7, 0.1, 0.2])
    ], ["shirt_0", "pants_0"]),
])
@patch.dict(sys.modules, {"ultralytics": MagicMock()})
@patch("app.ml.clothing_detector.model")
@patch("app.ml.clothing_detector.cv2.imread")
def test_get_clothes_from_img(mock_imread, mock_model, img_shape, boxes, expected_names):
    # Mock image
    fake_img = np.ones(img_shape, dtype=np.uint8)
    mock_imread.return_value = fake_img
    # Mock model.predict
    mock_boxes = MagicMock()
    mock_boxes.cls = [b[0] for b in boxes]
    mock_boxes.xywhn = [b[1] for b in boxes]
    mock_result = MagicMock()
    mock_result.boxes = mock_boxes
    mock_model.predict.return_value = [mock_result]
    # Run
    parts = get_clothes_from_img("fake_path.jpg")
    # Assert
    assert len(parts) == len(expected_names)
    for (name, part), expected_name in zip(parts, expected_names):
        assert name == expected_name
        assert isinstance(part, np.ndarray)
