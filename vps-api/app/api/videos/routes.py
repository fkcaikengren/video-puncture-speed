from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request, Form
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.logging import get_logger
from app.api.videos.service import VideoService
from app.api.videos.schemas import VideoListResponse, VideoDetailResponse, UploadResponse, AnalysisResponse, CategoryResponse
from app.api.users.service import UserService
from app.core.schemas import BaseResponse
import uuid
import os
from typing import List

logger = get_logger(__name__)

router = APIRouter(prefix="/videos", tags=["videos"])
categories_router = APIRouter(tags=["categories"])

ALLOWED_EXTENSIONS = {'.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv'}
MAX_FILE_SIZE = 200 * 1024 * 1024

@router.get("", response_model=BaseResponse[VideoListResponse])
async def get_videos(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    keyword: str = None,
    category_id: int = None,
    status: int = None,
    uploader: str = None,
    session: AsyncSession = Depends(get_session)
):
  
    service = VideoService(session)
    data = await service.get_videos(
        page=page,
        page_size=page_size,
        keyword=keyword,
        category_id=category_id,
        status=status,
        uploader=uploader,
    )
    return BaseResponse(data=data)

@router.get("/candidates", response_model=BaseResponse[VideoListResponse])
async def get_candidates(
    request: Request,
    page: int = 1,
    page_size: int = 20,
    keyword: str = None,
    category_id: int = None,
    session: AsyncSession = Depends(get_session)
):
    user = request.state.user
    service = VideoService(session)
    data = await service.get_candidates(user.id, page, page_size, keyword, category_id)
    return BaseResponse(data=data)

@router.get("/detail", response_model=BaseResponse[VideoDetailResponse])
async def get_video_detail(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session)
):
    service = VideoService(session)
    data = await service.get_video_detail(id)
    return BaseResponse(data=data)

@router.post("/upload", response_model=BaseResponse[UploadResponse])
async def upload_video(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(None),
    category_id: int = Form(None),
    session: AsyncSession = Depends(get_session)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size allowed is {MAX_FILE_SIZE / (1024 * 1024)}MB"
        )

    user = request.state.user
    logger.warn(f"User {user.username} is uploading video {file.filename}")
    print(request.state)
    service = VideoService(session)
    data = await service.process_video_upload(file, user.id, username=user.username, title=title, category_id=category_id)
    return BaseResponse(data=data)

@router.post("/delete", response_model=BaseResponse[dict])
async def delete_video(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session)
):
    service = VideoService(session)
    await service.delete_video(id)
    return BaseResponse(data={"deleted": True})

@router.get("/analysis", response_model=BaseResponse[AnalysisResponse])
async def get_analysis(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session)
):
    service = VideoService(session)
    data = await service.get_analysis(id)
    return BaseResponse(data=data)


@router.post("/analysis", response_model=BaseResponse[dict])
async def analyze_video(
    id: uuid.UUID,
    session: AsyncSession = Depends(get_session)
):
    service = VideoService(session)
    await service.process_video_analysis(id)
    return BaseResponse(data={})

@router.get("/uploaders", response_model=BaseResponse[List[str]])
async def get_uploaders(session: AsyncSession = Depends(get_session)):
    data = await UserService(session).get_all_usernames()
    return BaseResponse(data=data)


@categories_router.get("/categories", response_model=BaseResponse[List[CategoryResponse]])
async def get_categories(session: AsyncSession = Depends(get_session)):
    from app.api.videos.repository import VideoRepository
    repo = VideoRepository(session)
    data = await repo.get_all_categories()
    return BaseResponse(data=data)
