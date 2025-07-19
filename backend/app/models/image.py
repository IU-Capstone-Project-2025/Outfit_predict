import uuid

from app.db.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class Image(Base):
    __tablename__ = "images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    description = Column(String(length=255), nullable=True)
    object_name = Column(String(length=512), nullable=False, unique=True)
    thumbnail_object_name = Column(String(length=512), nullable=True)
    clothing_type = Column(
        String(length=50), nullable=True
    )  # Added clothing type field
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="images")
