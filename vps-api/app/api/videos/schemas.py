from pydantic import BaseModel, ConfigDict, Field, field_serializer, computed_field
from uuid import UUID
from datetime import datetime
from typing import Optional, List, Any
from app.core.storage import storage
from .enums import VideoStatus

class CategoryBase(BaseModel):
    name: str

class CategoryCreate(CategoryBase):
    pass

class CategoryResponse(CategoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime

class VideoBase(BaseModel):
    title: str
    category_id: Optional[int] = None

class VideoCreate(VideoBase):
    raw_path: str
    thumbnail_path: Optional[str] = None
    duration: Optional[int] = None
    size: Optional[int] = None
    fps: Optional[int] = None
    uploader: Optional[str] = None
    
class VideoUpdate(BaseModel):
    status: Optional[int] = None
    error_log: Optional[str] = None
    thumbnail_path: Optional[str] = None
    duration: Optional[int] = None
    size: Optional[int] = None
    fps: Optional[int] = None

class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    category_id: Optional[int] = None
    title: str
    duration: Optional[int] = None
    fps: Optional[int] = None
    status: VideoStatus
    uploader: Optional[str] = None
    created_at: datetime
    
    raw_path: str = Field(exclude=True)
    thumbnail_path: Optional[str] = Field(default=None, exclude=True)

    @computed_field
    def url(self) -> Optional[str]:
        if self.raw_path:
            return storage.get_url(self.raw_path)
        return None

    @computed_field
    def thumbnail_url(self) -> Optional[str]:
        if self.thumbnail_path:
            return storage.get_url(self.thumbnail_path)
        return None
    
    @field_serializer('created_at')
    def serialize_created_at(self, created_at: datetime, _info):
        return int(created_at.timestamp() * 1000)

class VideoDetailResponse(VideoResponse):
    error_log: Optional[str] = None

class VideoListResponse(BaseModel):
    items: List[VideoResponse]
    total: int
    page: int
    page_size: int

class UploadResponse(BaseModel):
    id: UUID
    status: int
    raw_url: str
    thumbnail_url: Optional[str] = None
    created_at: datetime

    @field_serializer('created_at')
    def serialize_created_at(self, created_at: datetime, _info):
        return int(created_at.timestamp() * 1000)

class AnalysisResultBase(BaseModel):
    marked_path: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    init_speed: Optional[float] = None
    avg_speed: Optional[float] = None
    curve_data: Optional[List[Any]] = None
    processed_at: Optional[datetime] = None

class AnalysisResultCreate(AnalysisResultBase):
    video_id: UUID

class AnalysisResultResponse(AnalysisResultBase):
    model_config = ConfigDict(from_attributes=True)
    marked_url: Optional[str] = None
    processed_at: Optional[datetime] = None

    @field_serializer('processed_at')
    def serialize_processed_at(self, processed_at: Optional[datetime], _info):
        if processed_at:
            return int(processed_at.timestamp() * 1000)
        return None

class AnalysisMetrics(BaseModel):
    start_time: float
    end_time: float
    init_speed: float
    avg_speed: float

class AnalysisCurvePoint(BaseModel):
    t: float
    v: float

class AnalysisResponse(BaseModel):
    video: VideoDetailResponse
    analysis: Optional[AnalysisResultResponse] = None
