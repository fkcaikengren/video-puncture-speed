from sqlalchemy import select, update, func, desc, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.exceptions import NotFoundException
from app.api.videos.models import Video, Category, AnalysisResult
from app.api.videos.schemas import VideoCreate, CategoryCreate, AnalysisResultCreate
import uuid

class VideoRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_category(self, category_data: CategoryCreate) -> Category:
        category = Category(name=category_data.name)
        self.session.add(category)
        await self.session.commit()
        await self.session.refresh(category)
        return category
        
    async def get_category_by_name(self, name: str) -> Category | None:
        query = select(Category).where(Category.name == name)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
        
    async def get_all_categories(self) -> list[Category]:
        query = select(Category)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create_video(self, video_data: VideoCreate, user_id: uuid.UUID) -> Video:
        video = Video(
            title=video_data.title,
            raw_path=video_data.raw_path,
            category_id=video_data.category_id,
            user_id=user_id,
            thumbnail_path=video_data.thumbnail_path,
            duration=video_data.duration,
            size=video_data.size,
            fps=video_data.fps,
            uploader=video_data.uploader,
            status=0
        )
        self.session.add(video)
        await self.session.commit()
        await self.session.refresh(video)
        return video

    async def get_video(self, video_id: uuid.UUID) -> Video:
        result = await self.session.get(Video, video_id)
        if not result:
            raise NotFoundException("Video not found")
        return result
    
    async def get_video_with_relations(self, video_id: uuid.UUID) -> Video:
        query = (
            select(Video)
            .where(Video.id == video_id)
            .options(
                selectinload(Video.analysis_result),
                selectinload(Video.comparisons_as_a),
                selectinload(Video.comparisons_as_b)
            )
        )
        result = await self.session.execute(query)
        video = result.scalar_one_or_none()
        if not video:
            raise NotFoundException("Video not found")
        return video

    async def get_videos(self, user_id: uuid.UUID, page: int, page_size: int, 
                         keyword: str = None, category_id: int = None, status: int = None, 
                         require_analysis: bool = False) -> tuple[list[Video], int]:
        query = select(Video).where(Video.user_id == user_id)
        
        if require_analysis:
            query = query.join(AnalysisResult, Video.id == AnalysisResult.video_id)
        
        if keyword:
            query = query.where(Video.title.ilike(f"%{keyword}%"))
        if category_id is not None:
            query = query.where(Video.category_id == category_id)
        if status is not None:
            query = query.where(Video.status == status)
            
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(desc(Video.created_at))
        result = await self.session.execute(query)
        items = result.scalars().all()
        
        return items, total

    async def get_candidates(self, user_id: uuid.UUID, page: int, page_size: int, 
                             keyword: str = None, category_id: int = None) -> tuple[list[Video], int]:
        return await self.get_videos(
            user_id, page, page_size, keyword, category_id, status=2, require_analysis=True
        )

    async def delete_video_record(self, video: Video):
        """Physical delete of video record"""
        await self.session.delete(video)
        await self.session.commit()

    async def create_analysis_result(self, result_data: AnalysisResultCreate) -> AnalysisResult:
        result = AnalysisResult(
            video_id=result_data.video_id,
            marked_path=result_data.marked_path,
            start_time=result_data.start_time,
            end_time=result_data.end_time,
            init_speed=result_data.init_speed,
            avg_speed=result_data.avg_speed,
            curve_data=result_data.curve_data,
            processed_at=result_data.processed_at
        )
        self.session.add(result)
        await self.session.commit()
        await self.session.refresh(result)
        return result
        
    async def get_analysis_result(self, video_id: uuid.UUID) -> AnalysisResult | None:
        query = select(AnalysisResult).where(AnalysisResult.video_id == video_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def delete_analysis_result_by_video_id(self, video_id: uuid.UUID):
        query = delete(AnalysisResult).where(AnalysisResult.video_id == video_id)
        await self.session.execute(query)
        await self.session.commit()
