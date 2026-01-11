from sqlalchemy import select, delete, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.api.comparisons.models import ComparisonReport
from app.api.comparisons.schemas import ComparisonReportCreate
import uuid

class ComparisonRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, report_data: ComparisonReportCreate, user_id: uuid.UUID) -> ComparisonReport:
        report = ComparisonReport(
            video_a_id=report_data.video_a_id,
            video_b_id=report_data.video_b_id,
            user_id=user_id,
            ai_analysis="# AI Analysis Report\n\nThis is a placeholder for AI analysis result."
        )
        self.session.add(report)
        await self.session.commit()
        await self.session.refresh(report)
        return report

    async def get_by_id(self, report_id: uuid.UUID) -> ComparisonReport | None:
        query = (
            select(ComparisonReport)
            .where(ComparisonReport.id == report_id)
            .options(
                selectinload(ComparisonReport.video_a),
                selectinload(ComparisonReport.video_b)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
        
    async def get_by_videos(self, user_id: uuid.UUID, video_a_id: uuid.UUID, video_b_id: uuid.UUID) -> ComparisonReport | None:
        # Check (a, b) or (b, a) for current user
        query = select(ComparisonReport).where(
            ComparisonReport.user_id == user_id,
            or_(
                and_(ComparisonReport.video_a_id == video_a_id, ComparisonReport.video_b_id == video_b_id),
                and_(ComparisonReport.video_a_id == video_b_id, ComparisonReport.video_b_id == video_a_id)
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
        
    async def delete_by_video_id(self, video_id: uuid.UUID):
        query = delete(ComparisonReport).where(
            or_(ComparisonReport.video_a_id == video_id, ComparisonReport.video_b_id == video_id)
        )
        await self.session.execute(query)
        await self.session.commit()
