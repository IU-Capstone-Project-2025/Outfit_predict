from app.db.database import Base
from app.models.outfit import Outfit
from app.models.image import Image

# Import all models here so they are registered with SQLAlchemy
__all__ = ["Base", "Outfit", "Image"] 