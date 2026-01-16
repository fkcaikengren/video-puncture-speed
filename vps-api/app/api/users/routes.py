from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_session
from app.core.logging import get_logger
from app.core.security import UseGuards
from app.api.users.schemas import (
    LoginData,
    UpdatePasswordRequest,
    UserCreate,
    UserListResponse,
    LoginResponse,
    UserResponse,
    SetRoleRequest,
)
from app.api.users.service import UserService
from app.core.schemas import BaseResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
user_router = APIRouter(prefix="/user", tags=["user"])
admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(UseGuards(["admin"]))],
)

@user_router.post("/password", response_model=BaseResponse[UserResponse])
async def update_password(
    request: Request,
    body: UpdatePasswordRequest,
    session: AsyncSession = Depends(get_session),
) -> BaseResponse[UserResponse]:
    """更新密码"""
    user = request.state.user
    result = await UserService(session).update_password(
        user.id, body.old_password, body.new_password
    )
    return BaseResponse(data=result)


@user_router.get("/profile", response_model=BaseResponse[UserResponse])
async def get_profile(
    request: Request,
    session: AsyncSession = Depends(get_session)
) -> BaseResponse[UserResponse]:
    """获取用户信息"""
    user = request.state.user
    result = await UserService(session).get_user(user.id)
    return BaseResponse(data=UserResponse.model_validate(result))


@router.post("/login", response_model=BaseResponse[LoginResponse])
async def login(
    data: LoginData,
    session: AsyncSession = Depends(get_session),
) -> BaseResponse[LoginResponse]:
    """Authenticate user and return token."""
    logger.debug(f"Login attempt: {data.username}")
    result = await UserService(session).authenticate(data)
    return BaseResponse(data=result)


@router.get("/me", response_model=BaseResponse[UserResponse])
async def get_me(request: Request) -> BaseResponse[UserResponse]:
    """Get current authenticated user."""
    return BaseResponse(data=request.state.user)

# Admin Routes
@admin_router.get("/users", response_model=BaseResponse[UserListResponse])
async def get_users(
    page: int = 1,
    page_size: int = 20,
    keyword: str = None,
    role: str = None,
    session: AsyncSession = Depends(get_session)
):
    result = await UserService(session).get_users(page, page_size, keyword, role)
    return BaseResponse(data=result)

@admin_router.post("/users/create", response_model=BaseResponse[dict])
async def create_user_admin(
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    new_user = await UserService(session).create_user(user_data)
    return BaseResponse(data={"id": new_user.id})

@admin_router.post("/users/delete", response_model=BaseResponse[dict])
async def delete_user_admin(
    user_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_session)
):
    await UserService(session).delete_user(user_id)
    return BaseResponse(data={"success": True})



@admin_router.post("/users/set-role", response_model=BaseResponse[dict])
async def set_role(
    body: SetRoleRequest,
    user_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_session)
):
    await UserService(session).update_role(user_id, body.role)
    return BaseResponse(data={"success": True})
