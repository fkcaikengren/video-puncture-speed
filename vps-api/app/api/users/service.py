from datetime import timedelta
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import UnauthorizedException, UnprocessableEntityException
from app.core.logging import get_logger
from app.core.security import create_access_token, get_password_hash, verify_password
from app.api.users.models import User
from app.api.users.repository import UserRepository
from app.api.users.schemas import LoginData, Token, UserCreate, LoginResponse, UserResponse, UserListResponse
from app.api.videos.repository import VideoRepository
from app.api.comparisons.repository import ComparisonRepository
from app.core.storage import storage

logger = get_logger(__name__)


class UserService:
    """Service for handling user business logic."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = UserRepository(session)
        self.video_repo = VideoRepository(session)
        self.comparison_repo = ComparisonRepository(session)

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

    async def get_all_usernames(self) -> list[str]:
        return await self.repository.get_all_usernames()

    async def update_role(self, user_id: uuid.UUID, role: str) -> UserResponse:
        user = await self.repository.update_role(user_id, role)
        return UserResponse.model_validate(user)

    async def update_password(
        self, user_id: uuid.UUID, old_password: str, new_password: str
    ) -> UserResponse:
        user = await self.repository.get_by_id(user_id)

        if not verify_password(old_password, str(user.password_hash)):
            raise UnprocessableEntityException(detail="当前密码不正确")

        updated_user = await self.repository.update_password_hash(
            user, get_password_hash(new_password)
        )
        return UserResponse.model_validate(updated_user)

    async def delete_user(self, user_id: uuid.UUID) -> bool:
        user = await self.repository.get_by_id(user_id)

        videos = await self.video_repo.get_videos_by_user_with_analysis(user_id)
        video_ids = [v.id for v in videos]

        for video in videos:
            if video.analysis_result and video.analysis_result.marked_path:
                try:
                    storage.delete_file(video.analysis_result.marked_path)
                except Exception as e:
                    logger.warning(
                        f"Failed to delete analysis marked file {video.analysis_result.marked_path}: {e}"
                    )

            if video.raw_path:
                try:
                    storage.delete_file(video.raw_path)
                except Exception as e:
                    logger.warning(f"Failed to delete raw file {video.raw_path}: {e}")

            if video.thumbnail_path:
                try:
                    storage.delete_file(video.thumbnail_path)
                except Exception as e:
                    logger.warning(f"Failed to delete thumbnail {video.thumbnail_path}: {e}")

        if video_ids:
            await self.comparison_repo.delete_by_video_ids(video_ids)

        await self.comparison_repo.delete_by_user_id(user_id)
        await self.video_repo.delete_analysis_results_by_video_ids(video_ids)
        await self.video_repo.delete_videos_by_user_id(user_id)
        await self.repository.delete(user)
        return True
