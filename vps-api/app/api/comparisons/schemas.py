from pydantic import BaseModel, ConfigDict, field_serializer
from uuid import UUID
from datetime import datetime
from typing import Optional

class AIAnalyzeRequest(BaseModel):
    video_a_id: UUID
    video_b_id: UUID

class ComparisonReportBase(BaseModel):
    video_a_id: UUID
    video_b_id: UUID

class ComparisonReportCreate(ComparisonReportBase):
    pass

class ComparisonReportResponse(ComparisonReportBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    ai_analysis: Optional[str] = None
    created_at: datetime
    
    @field_serializer('created_at')
    def serialize_created_at(self, created_at: datetime, _info):
        return int(created_at.timestamp() * 1000)
