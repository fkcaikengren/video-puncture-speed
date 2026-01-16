from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.api.dashboard.service import DashboardService
from app.api.dashboard.schemas import BaseResponse, StatsData, PendingVideoGroup
from app.api.videos.enums import VideoStatus
from typing import List

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=BaseResponse[StatsData])
async def get_stats(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    user = request.state.user
    service = DashboardService(session)
    data = await service.get_stats(user.id)
    return BaseResponse(data=data)

@router.get("/videos", response_model=BaseResponse[List[PendingVideoGroup]])
async def get_videos(
    request: Request,
    status: VideoStatus | None = None,
    session: AsyncSession = Depends(get_session)
):
    user = request.state.user
    service = DashboardService(session)
    data = await service.get_videos(user.id, status=status)
    return BaseResponse(data=data)
