from fastapi import APIRouter, Depends, Request, status, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
import uuid

from app.core.database import get_session
from app.core.logging import get_logger
from app.api.users.schemas import LoginData, Token, UserCreate, UserResponse, LoginResponse, UserListResponse, SetRoleRequest
from app.api.users.service import UserService
from app.core.schemas import BaseResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
admin_router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/register", response_model=BaseResponse[UserResponse], status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserCreate, session: AsyncSession = Depends(get_session)
) -> BaseResponse[UserResponse]:
    """Register a new user."""
    logger.debug(f"Registering user: {user_data.username}")
    user = await UserService(session).create_user(user_data)
    return BaseResponse(data=UserResponse.model_validate(user))


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
    request: Request,
    page: int = 1,
    page_size: int = 20,
    keyword: str = None,
    role: str = None,
    session: AsyncSession = Depends(get_session)
):
    user = request.state.user
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
        
    result = await UserService(session).get_users(page, page_size, keyword, role)
    return BaseResponse(data=result)

@admin_router.post("/users/create", response_model=BaseResponse[dict])
async def create_user_admin(
    request: Request,
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)
):
    user = request.state.user
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
        
    new_user = await UserService(session).create_user(user_data)
    return BaseResponse(data={"id": new_user.id})

@admin_router.post("/users/set-role", response_model=BaseResponse[dict])
async def set_role(
    request: Request,
    body: SetRoleRequest,
    user_id: uuid.UUID = Query(...),
    session: AsyncSession = Depends(get_session)
):
    user = request.state.user
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
        
    await UserService(session).update_role(user_id, body.role)
    return BaseResponse(data={"success": True})
