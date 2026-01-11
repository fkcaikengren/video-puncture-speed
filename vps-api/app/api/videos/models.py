import uuid
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy import String, TIMESTAMP, func, ForeignKey, Integer, DECIMAL, SmallInteger, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base

if TYPE_CHECKING:
    from app.api.comparisons.models import ComparisonReport

class Category(Base):
    __tablename__ = "categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())

class Video(Base):
    __tablename__ = "videos"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    raw_path: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_path: Mapped[str] = mapped_column(Text, nullable=True)
    duration: Mapped[int] = mapped_column(Integer, nullable=True)
    size: Mapped[int] = mapped_column(Integer, nullable=True)
    fps: Mapped[int] = mapped_column(Integer, nullable=True)
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, index=True) # 0:pending, 1:processing, 2:completed, 3:failed
    uploader: Mapped[str] = mapped_column(String(50), nullable=True)
    error_log: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())
    
    analysis_result: Mapped["AnalysisResult"] = relationship(back_populates="video", uselist=False)

    # Relationships for ComparisonReport (as video_a and video_b)
    # Using strings for class name and foreign keys to avoid circular imports
    comparisons_as_a: Mapped[list["ComparisonReport"]] = relationship(
        "ComparisonReport", 
        foreign_keys="[ComparisonReport.video_a_id]",
        viewonly=True
    )
    comparisons_as_b: Mapped[list["ComparisonReport"]] = relationship(
        "ComparisonReport", 
        foreign_keys="[ComparisonReport.video_b_id]",
        viewonly=True
    )

    @property
    def comparison_reports(self) -> list["ComparisonReport"]:
        return self.comparisons_as_a + self.comparisons_as_b

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    video_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("videos.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    marked_path: Mapped[str] = mapped_column(Text, nullable=True)
    start_time: Mapped[float] = mapped_column(DECIMAL(10, 3), nullable=True)
    end_time: Mapped[float] = mapped_column(DECIMAL(10, 3), nullable=True)
    init_speed: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=True)
    avg_speed: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=True)
    curve_data: Mapped[list] = mapped_column(JSONB, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=True)

    video: Mapped["Video"] = relationship(back_populates="analysis_result")
