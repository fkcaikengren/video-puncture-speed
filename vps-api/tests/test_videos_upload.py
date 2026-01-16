from datetime import datetime
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.api.videos.routes import router as videos_router
from app.api.videos.schemas import UploadResponse
from app.core.database import get_session
from app.core.exceptions import UnprocessableEntityException


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

def test_upload_video_success():
    app = _build_app()
    client = TestClient(app)

    mocked_response = UploadResponse(
        id=uuid.uuid4(),
        status=0,
        raw_url="http://example.com/videos/test.mp4",
        thumbnail_url=None,
        created_at=datetime.utcnow(),
    )

    with patch(
        "app.api.videos.routes.VideoService.process_video_upload",
        new=AsyncMock(return_value=mocked_response),
    ):
        response = client.post(
            "/videos/upload",
            files={"file": ("test_video.mov", b"fake video content", "video/quicktime")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 200
    assert body["data"]["raw_url"] == "http://example.com/videos/test.mp4"
    assert isinstance(body["data"]["created_at"], int)

def test_upload_video_transcode_fail():
    app = _build_app()
    client = TestClient(app)

    with patch(
        "app.api.videos.routes.VideoService.process_video_upload",
        new=AsyncMock(
            side_effect=UnprocessableEntityException(
                detail="Transcoding failed: Transcode error"
            )
        ),
    ):
        response = client.post(
            "/videos/upload",
            files={"file": ("fail.mov", b"content", "video/quicktime")},
        )

    assert response.status_code == 422
    assert "Transcoding failed" in response.json()["detail"]
