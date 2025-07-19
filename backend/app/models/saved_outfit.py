import uuid

from app.db.database import Base
from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class SavedOutfit(Base):
    __tablename__ = "saved_outfits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    outfit_id = Column(UUID(as_uuid=True), ForeignKey("outfits.id"), nullable=False)
    completeness_score = Column(Float, nullable=False)
    matches = Column(JSON, nullable=False)  # Store the matches data as JSON
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    owner = relationship("User")
    outfit = relationship("Outfit")
