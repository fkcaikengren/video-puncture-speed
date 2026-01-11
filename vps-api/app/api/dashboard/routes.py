from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.api.dashboard.service import DashboardService
from app.api.dashboard.schemas import BaseResponse, StatsData, PendingVideoGroup
from typing import List

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=BaseResponse[StatsData])
async def get_stats(
    request: Request,
    scope: str = Query("me", pattern="^(me|all)$"),
    session: AsyncSession = Depends(get_session)
):
    user = request.state.user
    is_admin = user.role == "admin"
    
    service = DashboardService(session)
    data = await service.get_stats(user.id, is_admin, scope)
    return BaseResponse(data=data)

@router.get("/pending-videos", response_model=BaseResponse[List[PendingVideoGroup]])
async def get_pending_videos(
    request: Request,
    session: AsyncSession = Depends(get_session)
):
    user = request.state.user
    is_admin = user.role == "admin"
    
    service = DashboardService(session)
    data = await service.get_pending_videos(user.id, is_admin)
    return BaseResponse(data=data)
