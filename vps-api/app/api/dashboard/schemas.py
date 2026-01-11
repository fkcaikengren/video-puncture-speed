from pydantic import BaseModel, Field
from typing import List, Generic, TypeVar, Optional
from app.core.schemas import BaseResponse
from app.api.videos.schemas import VideoResponse

class StatsData(BaseModel):
    total: int
    completed: int
    pending: int
    failed: int
    processing: int

class PendingVideoGroup(BaseModel):
    date: str
    list: List[VideoResponse]
