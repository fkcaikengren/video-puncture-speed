import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.api.videos.service import VideoService
from datetime import datetime
import uuid

@pytest.mark.asyncio
async def test_get_videos():
    mock_session = AsyncMock()
    service = VideoService(mock_session)
    
    # Mock repository
    service.repository = MagicMock()
    service.repository.get_videos = AsyncMock()
    
    mock_video = MagicMock()
    mock_video.id = uuid.uuid4()
    mock_video.user_id = uuid.uuid4()
    mock_video.title = "test"
    mock_video.status = 0
    mock_video.created_at = datetime.now()
    mock_video.raw_path = "path"
    mock_video.thumbnail_path = "thumb"
    mock_video.__dict__ = {
        "id": mock_video.id,
        "user_id": mock_video.user_id,
        "title": "test",
        "status": 0,
        "created_at": mock_video.created_at,
        "raw_path": "path",
        "thumbnail_path": "thumb",
        "category_id": None,
        "duration": None,
        "error_log": None
    }
    
    service.repository.get_videos.return_value = ([mock_video], 1)
    
    with patch("app.api.videos.service.storage") as mock_storage:
        mock_storage.get_url.return_value = "http://url"
        
        result = await service.get_videos(uuid.uuid4(), 1, 10)
        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].thumbnail_url == "http://url"

@pytest.mark.asyncio
async def test_delete_video():
    mock_session = AsyncMock()
    service = VideoService(mock_session)
    service.repository = MagicMock()
    service.comparison_repo = MagicMock()
    
    service.comparison_repo.delete_by_video_id = AsyncMock()
    service.repository.delete_analysis_result_by_video_id = AsyncMock()
    service.repository.get_video = AsyncMock()
    service.repository.delete_video_record = AsyncMock()
    
    mock_video = MagicMock()
    mock_video.raw_path = "raw"
    mock_video.thumbnail_path = "thumb"
    service.repository.get_video.return_value = mock_video
    
    with patch("app.api.videos.service.storage") as mock_storage:
        await service.delete_video(uuid.uuid4())
        
        mock_storage.delete_file.assert_any_call("raw")
        mock_storage.delete_file.assert_any_call("thumb")
        service.comparison_repo.delete_by_video_id.assert_called_once()
        service.repository.delete_video_record.assert_called_once()
