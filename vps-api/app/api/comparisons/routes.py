from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.api.comparisons.service import ComparisonService
from app.api.comparisons.schemas import AIAnalyzeRequest, ComparisonReportResponse
from app.core.schemas import BaseResponse
import uuid

router = APIRouter(prefix="/comparisons", tags=["comparisons"])

@router.post("/ai-analyze", response_model=BaseResponse[ComparisonReportResponse])
async def ai_analyze(
    request: Request,
    data: AIAnalyzeRequest,
    session: AsyncSession = Depends(get_session)
):
    user = request.state.user
    service = ComparisonService(session)
    result = await service.ai_analyze(data, user.id)
    return BaseResponse(data=result)

@router.get("/report", response_model=BaseResponse[ComparisonReportResponse])
async def get_report(
    request: Request,
    video_a_id: uuid.UUID,
    video_b_id: uuid.UUID,
    session: AsyncSession = Depends(get_session)
):
    user = request.state.user
    service = ComparisonService(session)
    result = await service.get_report(video_a_id, video_b_id, user.id)
    return BaseResponse(data=result)
