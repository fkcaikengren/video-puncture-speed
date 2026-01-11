import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.api.users.service import UserService
from app.api.users.schemas import LoginData, UserCreate
from app.core.exceptions import UnauthorizedException
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
