from app.db.database import Base
from app.models.image import Image
from app.models.outfit import Outfit
from app.models.saved_outfit import SavedOutfit

# Import all models here so they are registered with SQLAlchemy
__all__ = ["Base", "Outfit", "Image", "SavedOutfit"]
