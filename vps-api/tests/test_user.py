import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.api.users.service import UserService
from app.api.users.schemas import LoginData, UserCreate
from app.core.exceptions import UnauthorizedException, UnprocessableEntityException
import uuid
from datetime import datetime

@pytest.mark.asyncio
async def test_authenticate_success():
    mock_session = AsyncMock()
    service = UserService(mock_session)
    service.repository = MagicMock()
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.username = "test"
    mock_user.role = "user"
    mock_user.created_at = datetime.now()
    mock_user.updated_at = datetime.now()
    
    service.repository.get_by_username = AsyncMock(return_value=mock_user)
    
    with patch("app.api.users.service.verify_password", return_value=True):
        data = LoginData(username="test", password="password")
        result = await service.authenticate(data)
        
        assert result.token is not None
        assert result.user.username == "test"

@pytest.mark.asyncio
async def test_authenticate_fail():
    mock_session = AsyncMock()
    service = UserService(mock_session)
    service.repository = MagicMock()
    
    service.repository.get_by_username = AsyncMock(return_value=None)
    
    data = LoginData(username="test", password="password")
    with pytest.raises(UnauthorizedException):
        await service.authenticate(data)

@pytest.mark.asyncio
async def test_get_users():
    mock_session = AsyncMock()
    service = UserService(mock_session)
    service.repository = MagicMock()
    
    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.username = "test"
    mock_user.role = "user"
    mock_user.created_at = datetime.now()
    mock_user.updated_at = datetime.now()
    
    service.repository.get_users = AsyncMock(return_value=([mock_user], 1))
    
    result = await service.get_users(1, 10)
    assert result.total == 1
    assert result.items[0].username == "test"


@pytest.mark.asyncio
async def test_update_password_success():
    mock_session = AsyncMock()
    service = UserService(mock_session)
    service.repository = MagicMock()

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.username = "test"
    mock_user.role = "user"
    mock_user.password_hash = "old_hash"
    mock_user.created_at = datetime.now()
    mock_user.updated_at = datetime.now()

    service.repository.get_by_id = AsyncMock(return_value=mock_user)
    service.repository.update_password_hash = AsyncMock(return_value=mock_user)

    with patch("app.api.users.service.verify_password", return_value=True):
        with patch("app.api.users.service.get_password_hash", return_value="new_hash"):
            result = await service.update_password(mock_user.id, "old", "newpass")

    assert result.id == mock_user.id
    service.repository.update_password_hash.assert_called_once()


@pytest.mark.asyncio
async def test_update_password_fail_wrong_old_password():
    mock_session = AsyncMock()
    service = UserService(mock_session)
    service.repository = MagicMock()

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    mock_user.username = "test"
    mock_user.role = "user"
    mock_user.password_hash = "old_hash"
    mock_user.created_at = datetime.now()
    mock_user.updated_at = datetime.now()

    service.repository.get_by_id = AsyncMock(return_value=mock_user)
    service.repository.update_password_hash = AsyncMock(return_value=mock_user)

    with patch("app.api.users.service.verify_password", return_value=False):
        with pytest.raises(UnprocessableEntityException):
            await service.update_password(mock_user.id, "old", "newpass")

    service.repository.update_password_hash.assert_not_called()


@pytest.mark.asyncio
async def test_delete_user():
    mock_session = AsyncMock()
    service = UserService(mock_session)
    service.repository = MagicMock()
    service.video_repo = MagicMock()
    service.comparison_repo = MagicMock()

    mock_user = MagicMock()
    mock_user.id = uuid.uuid4()
    service.repository.get_by_id = AsyncMock(return_value=mock_user)
    service.repository.delete = AsyncMock()

    video_id = uuid.uuid4()
    mock_video = MagicMock()
    mock_video.id = video_id
    mock_video.raw_path = "raw"
    mock_video.thumbnail_path = "thumb"
    mock_video.analysis_result = MagicMock()
    mock_video.analysis_result.marked_path = "marked"
    service.video_repo.get_videos_by_user_with_analysis = AsyncMock(return_value=[mock_video])
    service.video_repo.delete_analysis_results_by_video_ids = AsyncMock()
    service.video_repo.delete_videos_by_user_id = AsyncMock()

    service.comparison_repo.delete_by_video_ids = AsyncMock()
    service.comparison_repo.delete_by_user_id = AsyncMock()

    with patch("app.api.users.service.storage") as mock_storage:
        await service.delete_user(mock_user.id)

        mock_storage.delete_file.assert_any_call("marked")
        mock_storage.delete_file.assert_any_call("raw")
        mock_storage.delete_file.assert_any_call("thumb")

    service.comparison_repo.delete_by_video_ids.assert_called_once()
    service.comparison_repo.delete_by_user_id.assert_called_once_with(mock_user.id)
    service.video_repo.delete_analysis_results_by_video_ids.assert_called_once()
    service.video_repo.delete_videos_by_user_id.assert_called_once_with(mock_user.id)
    service.repository.delete.assert_called_once_with(mock_user)
