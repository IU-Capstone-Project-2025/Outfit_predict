import uuid

from app.db.database import Base
from sqlalchemy import Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship


class Outfit(Base):
    __tablename__ = "outfits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    object_name = Column(String(length=512), nullable=False, unique=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    owner = relationship("User", back_populates="outfits")
