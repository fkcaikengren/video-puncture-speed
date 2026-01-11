from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from app.api.videos.models import Video
from app.api.dashboard.schemas import StatsData, PendingVideoGroup
from app.api.videos.schemas import VideoResponse
import uuid
from itertools import groupby

class DashboardService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_stats(self, user_id: uuid.UUID, is_admin: bool, scope: str = "me") -> StatsData:
        query = select(Video.status, func.count(Video.id)).group_by(Video.status)
        
        if scope == "me" or not is_admin:
            query = query.where(Video.user_id == user_id)
            
        result = await self.session.execute(query)
        rows = result.all()
        
        stats = {
            0: 0, # pending
            1: 0, # processing
            2: 0, # completed
            3: 0  # failed
        }
        
        for status, count in rows:
            if status in stats:
                stats[status] = count
                
        total = sum(stats.values())
        
        return StatsData(
            total=total,
            completed=stats[2],
            pending=stats[0],
            failed=stats[3],
            processing=stats[1]
        )

    async def get_pending_videos(self, user_id: uuid.UUID, is_admin: bool) -> list[PendingVideoGroup]:
        # Requirement: only status=0 (pending)
        query = select(Video).where(Video.status == 0).order_by(desc(Video.created_at))
        
        query = query.where(Video.user_id == user_id)
            
        result = await self.session.execute(query)
        videos = result.scalars().all()
        
        # Group by date
        grouped_data = []
        
        def get_date_str(v):
            return v.created_at.strftime("%Y-%m-%d")
            
        for date, group in groupby(videos, key=get_date_str):
            video_list = []
            for v in group:
                video_list.append(VideoResponse.model_validate(v))
            grouped_data.append(PendingVideoGroup(date=date, list=video_list))
            
        return grouped_data
