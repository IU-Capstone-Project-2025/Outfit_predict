from app.core.logging import get_logger
from app.ml.encoding_models import FashionClipEncoder
from app.ml.image_search import ImageSearchEngine
from app.ml.outfit_processing import FashionSegmentationModel
from app.storage.qdrant_client import QdrantService

# Initialize logger for ML models
logger = get_logger("app.ml.models")

logger.info("Initializing ML models...")

try:
    # Инициализация моделей один раз при старте приложения
    logger.info("Loading FashionSegmentationModel...")
    fashion_segmentation_model = FashionSegmentationModel(
        yolo_model_path="app/ml/best.pt", sam_model_path="app/ml/sam_b.pt"
    )
    logger.info("FashionSegmentationModel loaded successfully")
except Exception as e:
    logger.error(f"Failed to load FashionSegmentationModel: {str(e)}")
    raise

try:
    logger.info("Loading ImageSearchEngine...")
    image_search_engine = ImageSearchEngine()
    logger.info("ImageSearchEngine loaded successfully")
except Exception as e:
    logger.error(f"Failed to load ImageSearchEngine: {str(e)}")
    raise

try:
    logger.info("Initializing QdrantService...")
    qdrant_service = QdrantService()
    logger.info("QdrantService initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize QdrantService: {str(e)}")
    raise

try:
    logger.info("Loading FashionClipEncoder...")
    fashion_clip_encoder = FashionClipEncoder()
    logger.info("FashionClipEncoder loaded successfully")
except Exception as e:
    logger.error(f"Failed to load FashionClipEncoder: {str(e)}")
    raise

logger.info("All ML models and services initialized successfully")
