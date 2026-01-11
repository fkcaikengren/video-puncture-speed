from datetime import timedelta
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedException
from app.core.logging import get_logger
from app.core.security import create_access_token, verify_password
from app.api.users.models import User
from app.api.users.repository import UserRepository
from app.api.users.schemas import LoginData, Token, UserCreate, LoginResponse, UserResponse, UserListResponse

logger = get_logger(__name__)


class UserService:
    """Service for handling user business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserRepository(session)

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        return await self.repository.create(user_data)

    async def authenticate(self, login_data: LoginData) -> LoginResponse:
        """Authenticate user and return token."""
        # Get user
        user = await self.repository.get_by_username(login_data.username)

        # Verify credentials
        if not user or not verify_password(
            login_data.password, str(user.password_hash)
        ):
            raise UnauthorizedException(detail="Incorrect username or password")

        # Create access token
        access_token = create_access_token(
            data={"sub": str(user.id)},
            expires_delta=timedelta(minutes=settings.JWT_EXPIRATION),
        )

        logger.info(f"User authenticated: {user.username}")
        return LoginResponse(
            token=access_token,
            user=UserResponse.model_validate(user)
        )

    async def get_user(self, user_id: uuid.UUID) -> User:
        """Get user by ID."""
        return await self.repository.get_by_id(user_id)

    async def get_users(self, page: int, page_size: int, keyword: str = None, role: str = None) -> UserListResponse:
        users, total = await self.repository.get_users(page, page_size, keyword, role)
        items = [UserResponse.model_validate(u) for u in users]
        return UserListResponse(items=items, total=total, page=page, page_size=page_size)

    async def update_role(self, user_id: uuid.UUID, role: str) -> UserResponse:
        user = await self.repository.update_role(user_id, role)
        return UserResponse.model_validate(user)
