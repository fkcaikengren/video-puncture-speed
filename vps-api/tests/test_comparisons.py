import pytest
from unittest.mock import MagicMock, AsyncMock
from app.api.comparisons.service import ComparisonService
from app.api.comparisons.schemas import AIAnalyzeRequest
from app.core.exceptions import NotFoundException
import uuid
from datetime import datetime

@pytest.mark.asyncio
async def test_ai_analyze_new():
    mock_session = AsyncMock()
    service = ComparisonService(mock_session)
    service.repository = MagicMock()
    
    service.repository.get_by_videos = AsyncMock(return_value=None)
    service.repository.create = AsyncMock()
    
    mock_report = MagicMock()
    mock_report.id = uuid.uuid4()
    mock_report.user_id = uuid.uuid4()
    mock_report.video_a_id = uuid.uuid4()
    mock_report.video_b_id = uuid.uuid4()
    mock_report.ai_analysis = "analysis"
    mock_report.created_at = datetime.now()
    service.repository.create.return_value = mock_report
    
    data = AIAnalyzeRequest(video_a_id=uuid.uuid4(), video_b_id=uuid.uuid4())
    result = await service.ai_analyze(data, uuid.uuid4())
    
    service.repository.create.assert_called_once()
    assert result.ai_analysis == "analysis"

@pytest.mark.asyncio
async def test_ai_analyze_existing():
    mock_session = AsyncMock()
    service = ComparisonService(mock_session)
    service.repository = MagicMock()
    
    mock_report = MagicMock()
    mock_report.id = uuid.uuid4()
    mock_report.user_id = uuid.uuid4()
    mock_report.video_a_id = uuid.uuid4()
    mock_report.video_b_id = uuid.uuid4()
    mock_report.ai_analysis = "existing"
    mock_report.created_at = datetime.now()
    service.repository.get_by_videos = AsyncMock(return_value=mock_report)
    service.repository.create = AsyncMock()
    
    data = AIAnalyzeRequest(video_a_id=uuid.uuid4(), video_b_id=uuid.uuid4())
    result = await service.ai_analyze(data, uuid.uuid4())
    
    service.repository.create.assert_not_called()
    assert result.ai_analysis == "existing"

@pytest.mark.asyncio
async def test_get_report_not_found():
    mock_session = AsyncMock()
    service = ComparisonService(mock_session)
    service.repository = MagicMock()
    service.repository.get_by_videos = AsyncMock(return_value=None)
    
    with pytest.raises(NotFoundException):
        await service.get_report(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())
