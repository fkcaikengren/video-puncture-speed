import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.api.dashboard.service import DashboardService
import uuid
from datetime import datetime

@pytest.mark.asyncio
async def test_get_stats_me():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    # status 0: 5, status 2: 10
    mock_result.all.return_value = [(0, 5), (2, 10)]
    mock_session.execute.return_value = mock_result
    
    service = DashboardService(mock_session)
    user_id = uuid.uuid4()
    
    stats = await service.get_stats(user_id)
    
    assert stats.total == 15
    assert stats.pending == 5
    assert stats.completed == 10
    assert stats.failed == 0

@pytest.mark.asyncio
async def test_get_pending_videos():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    
    v1 = MagicMock()
    v1.id = uuid.uuid4()
    v1.user_id = uuid.uuid4()
    v1.title = "v1"
    v1.status = 0
    v1.created_at = datetime(2025, 1, 1, 10, 0, 0)
    v1.raw_path = "path/to/raw1"
    v1.thumbnail_path = "path/to/thumb"
    v1.uploader = None
    v1.fps = None
    v1.duration = None
    
    v2 = MagicMock()
    v2.id = uuid.uuid4()
    v2.user_id = uuid.uuid4()
    v2.title = "v2"
    v2.status = 0
    v2.created_at = datetime(2025, 1, 1, 9, 0, 0)
    v2.raw_path = "path/to/raw2"
    v2.thumbnail_path = None
    v2.uploader = None
    v2.fps = None
    v2.duration = None
    
    mock_result.scalars.return_value.all.return_value = [v1, v2]
    mock_session.execute.return_value = mock_result
    
    with patch("app.api.videos.schemas.storage") as mock_storage:
        mock_storage.get_url.return_value = "http://mock-url"
        
        service = DashboardService(mock_session)
        user_id = uuid.uuid4()
        
        data = await service.get_videos(user_id, status=0)
        
        assert len(data) == 1
        assert data[0].date == "2025-01-01"
        assert len(data[0].list) == 2
        assert data[0].list[0].title == "v1"
        assert data[0].list[0].thumbnail_url == "http://mock-url"
        assert data[0].list[1].thumbnail_url is None
