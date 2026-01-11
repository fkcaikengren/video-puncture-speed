import uuid
from datetime import datetime
from sqlalchemy import TIMESTAMP, func, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
# Use string forward reference for Video to avoid circular imports if any, 
# or just import it if needed for type checking.
# Since we use string "Video" in relationship, we rely on the registry.
class ComparisonReport(Base):
    __tablename__ = "comparison_reports"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    video_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False)
    video_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    ai_analysis: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

    video_a: Mapped["Video"] = relationship("Video", foreign_keys=[video_a_id])
    video_b: Mapped["Video"] = relationship("Video", foreign_keys=[video_b_id])
