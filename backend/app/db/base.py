from app.db.database import Base
from app.models.image import Image
from app.models.outfit import Outfit

# Import all models here so they are registered with SQLAlchemy
__all__ = ["Base", "Outfit", "Image"]
