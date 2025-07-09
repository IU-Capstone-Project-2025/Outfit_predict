from app.ml.outfit_processing import FashionSegmentationModel
from app.ml.image_search import ImageSearchEngine
from app.storage.qdrant_client import QdrantService

# Инициализация моделей один раз при старте приложения
fashion_segmentation_model = FashionSegmentationModel(
    yolo_model_path="app/ml/best.pt",
    sam_model_path="app/ml/sam_b.pt"
)

image_search_engine = ImageSearchEngine()
qdrant_service = QdrantService()
