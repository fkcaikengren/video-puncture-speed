from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import uuid

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.api.videos.routes import router as videos_router
from app.api.videos.schemas import VideoListResponse
from app.core.database import get_session


def _build_app():
    app = FastAPI()

    async def override_get_session():
        yield AsyncMock()

    @app.middleware("http")
    async def inject_user(request: Request, call_next):
        request.state.user = SimpleNamespace(
            id=uuid.uuid4(),
            username="test",
            role="user",
        )
        return await call_next(request)

    app.dependency_overrides[get_session] = override_get_session
    app.include_router(videos_router)
    return app


def test_get_videos_support_uploader_filter():
    app = _build_app()
    client = TestClient(app)

    mocked_response = VideoListResponse(items=[], total=0, page=1, page_size=20)
    mocked = AsyncMock(return_value=mocked_response)

    with patch("app.api.videos.routes.VideoService.get_videos", new=mocked):
        response = client.get("/videos", params={"uploader": "alice"})

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["items"] == []
    assert body["data"]["total"] == 0

    kwargs = mocked.call_args.kwargs
    assert kwargs["page"] == 1
    assert kwargs["page_size"] == 20
    assert kwargs["uploader"] == "alice"


def test_get_uploaders_returns_username_array():
    app = FastAPI()

    async def override_get_session():
        yield AsyncMock()

    @app.middleware("http")
    async def inject_user(request: Request, call_next):
        request.state.user = SimpleNamespace(
            id=uuid.uuid4(),
            username="test",
            role="user",
        )
        return await call_next(request)

    app.dependency_overrides[get_session] = override_get_session
    app.include_router(videos_router)

    client = TestClient(app)
    mocked = AsyncMock(return_value=["alice", "bob"])
    with patch("app.api.videos.routes.UserService.get_all_usernames", new=mocked):
        response = client.get("/videos/uploaders")
        assert response.status_code == 200

        body = response.json()
        assert body["code"] == 200
        assert body["data"] == ["alice", "bob"]
