from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import AlreadyExistsException, NotFoundException
from app.core.logging import get_logger
from app.core.security import get_password_hash
from app.api.users.models import User
from app.api.users.schemas import UserCreate
import uuid

logger = get_logger(__name__)

class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user_data: UserCreate) -> User:
        existing_user = await self.get_by_username(user_data.username)
        if existing_user:
            raise AlreadyExistsException("Username already registered")

        user = User(
            username=user_data.username,
            password_hash=get_password_hash(user_data.password),
            role=user_data.role
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        
        logger.info(f"Created user: {user.username}")
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User:
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            raise NotFoundException("User not found")
        return user

    async def get_by_username(self, username: str) -> User | None:
        query = select(User).where(User.username == username)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_users(self, page: int, page_size: int, keyword: str = None, role: str = None) -> tuple[list[User], int]:
        query = select(User)
        if keyword:
            query = query.where(User.username.ilike(f"%{keyword}%"))
        if role:
            query = query.where(User.role == role)
            
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0
        
        query = query.offset((page - 1) * page_size).limit(page_size).order_by(desc(User.created_at))
        result = await self.session.execute(query)
        items = result.scalars().all()
        return items, total

    async def update_role(self, user_id: uuid.UUID, role: str) -> User:
        user = await self.get_by_id(user_id)
        user.role = role
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_password_hash(self, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.commit()
