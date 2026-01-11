from sqlalchemy.ext.asyncio import AsyncSession
from app.api.comparisons.repository import ComparisonRepository
from app.api.comparisons.schemas import AIAnalyzeRequest, ComparisonReportResponse, ComparisonReportCreate
from app.core.exceptions import NotFoundException
import uuid

class ComparisonService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = ComparisonRepository(session)

    async def ai_analyze(self, data: AIAnalyzeRequest, user_id: uuid.UUID) -> ComparisonReportResponse:
        # Check idempotency
        existing = await self.repository.get_by_videos(user_id, data.video_a_id, data.video_b_id)
        if existing:
            return ComparisonReportResponse.model_validate(existing)
            
        # Create new
        # Here we would call AI service. For now, use placeholder.
        create_data = ComparisonReportCreate(
            video_a_id=data.video_a_id,
            video_b_id=data.video_b_id
        )
        report = await self.repository.create(create_data, user_id)
        return ComparisonReportResponse.model_validate(report)

    async def get_report(self, video_a_id: uuid.UUID, video_b_id: uuid.UUID, user_id: uuid.UUID) -> ComparisonReportResponse:
        report = await self.repository.get_by_videos(user_id, video_a_id, video_b_id)
        if not report:
            raise NotFoundException("Comparison report not found")
        return ComparisonReportResponse.model_validate(report)
