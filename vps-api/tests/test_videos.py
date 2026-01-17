import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.api.videos.service import VideoService
from datetime import datetime
import uuid
from types import SimpleNamespace

@pytest.mark.asyncio
async def test_get_videos():
    mock_session = AsyncMock()
    service = VideoService(mock_session)
    
    # Mock repository
    service.repository = MagicMock()
    service.repository.get_videos = AsyncMock()
    
    mock_video = SimpleNamespace(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        category_id=None,
        title="test",
        duration=None,
        fps=None,
        status=0,
        uploader=None,
        created_at=datetime.now(),
        raw_path="path",
        thumbnail_path="thumb",
    )
    
    service.repository.get_videos.return_value = ([mock_video], 1)
    
    with patch("app.api.videos.schemas.storage") as mock_storage:
        mock_storage.get_url.return_value = "http://url"
        
        result = await service.get_videos(1, 10, user_id=uuid.uuid4())
        assert result.total == 1
        assert len(result.items) == 1
        assert result.items[0].thumbnail_url == "http://url"

@pytest.mark.asyncio
async def test_get_videos_pass_uploader_filter():
    mock_session = AsyncMock()
    service = VideoService(mock_session)
    
    service.repository = MagicMock()
    service.repository.get_videos = AsyncMock(return_value=([], 0))
    
    await service.get_videos(1, 10, uploader="alice")
    kwargs = service.repository.get_videos.await_args.kwargs
    assert kwargs["uploader"] == "alice"
    assert kwargs["user_id"] is None

@pytest.mark.asyncio
async def test_delete_video():
    mock_session = AsyncMock()
    service = VideoService(mock_session)
    service.repository = MagicMock()
    service.comparison_repo = MagicMock()

    service.repository.get_video_with_analysis_result = AsyncMock()
    service.repository.delete_video_record = AsyncMock()

    mock_video = MagicMock()
    mock_video.raw_path = "raw"
    mock_video.thumbnail_path = "thumb"
    mock_video.analysis_result = None
    mock_video.comparison_reports = []
    service.repository.get_video_with_analysis_result.return_value = mock_video
    
    with patch("app.api.videos.service.storage") as mock_storage:
        await service.delete_video(uuid.uuid4())
        
        mock_storage.delete_file.assert_any_call("raw")
        mock_storage.delete_file.assert_any_call("thumb")
        service.repository.delete_video_record.assert_called_once()
