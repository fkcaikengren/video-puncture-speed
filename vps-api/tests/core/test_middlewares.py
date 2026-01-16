from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
import uuid
from app.core.middlewares import setup_cors_middleware, JWTMiddleware
from app.core.database import get_session
from app.api.users.routes import admin_router
from app.api.users.schemas import UserListResponse

def test_cors_preflight_bypasses_auth():
    app = FastAPI()
    app.add_middleware(JWTMiddleware)
    setup_cors_middleware(app)

    @app.get("/me")
    def me(request: Request):
        return {"user": request.state.user}

    client = TestClient(app)

    response = client.options(
        "/me",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") in {
        "*",
        "http://localhost:3000",
    }


def test_cors_headers_exist_on_401():
    app = FastAPI()
    app.add_middleware(JWTMiddleware)
    setup_cors_middleware(app)

    @app.get("/me")
    def me(request: Request):
        return {"user": request.state.user}

    client = TestClient(app)

    response = client.get(
        "/me",
        headers={
            "Origin": "http://localhost:3000",
        },
    )
    assert response.status_code == 401
    assert response.headers.get("access-control-allow-origin") in {
        "*",
        "http://localhost:3000",
    }

def test_jwt_middleware_invalid_token():
    app = FastAPI()
    app.add_middleware(JWTMiddleware)
    
    @app.get("/me")
    def me(request: Request):
        return {"user": request.state.user}

    client = TestClient(app)

    response = client.get("/me", headers={"Authorization": "Bearer invalid_token"})
    assert response.status_code == 401

def test_jwt_middleware_no_token():
    app = FastAPI()
    app.add_middleware(JWTMiddleware)
    
    @app.get("/me")
    def me(request: Request):
        return {"user": request.state.user}

    client = TestClient(app)
    
    response = client.get("/me")
    assert response.status_code == 401

def test_admin_router_forbids_non_admin_role():
    app = FastAPI()

    async def override_get_session():
        yield AsyncMock()

    @app.middleware("http")
    async def inject_user(request: Request, call_next):
        request.state.user = SimpleNamespace(role="user", id=uuid.uuid4())
        return await call_next(request)

    app.dependency_overrides[get_session] = override_get_session
    app.include_router(admin_router)

    client = TestClient(app)

    with patch(
        "app.api.users.routes.UserService.get_users",
        new=AsyncMock(side_effect=AssertionError("should not be called")),
    ):
        response = client.get("/admin/users")

    assert response.status_code == 403

def test_admin_router_allows_admin_role():
    app = FastAPI()

    async def override_get_session():
        yield AsyncMock()

    @app.middleware("http")
    async def inject_user(request: Request, call_next):
        request.state.user = SimpleNamespace(role="admin", id=uuid.uuid4())
        return await call_next(request)

    app.dependency_overrides[get_session] = override_get_session
    app.include_router(admin_router)

    client = TestClient(app)

    with patch(
        "app.api.users.routes.UserService.get_users",
        new=AsyncMock(
            return_value=UserListResponse(items=[], total=0, page=1, page_size=20)
        ),
    ):
        response = client.get("/admin/users")

    assert response.status_code == 200
    assert response.json()["code"] == 200

def test_admin_router_guards_other_admin_endpoints():
    app = FastAPI()

    async def override_get_session():
        yield AsyncMock()

    @app.middleware("http")
    async def inject_user(request: Request, call_next):
        request.state.user = SimpleNamespace(role="user", id=uuid.uuid4())
        return await call_next(request)

    app.dependency_overrides[get_session] = override_get_session
    app.include_router(admin_router)

    client = TestClient(app)

    with patch(
        "app.api.users.routes.UserService.update_role",
        new=AsyncMock(side_effect=AssertionError("should not be called")),
    ):
        response = client.post(
            f"/admin/users/set-role?user_id={uuid.uuid4()}",
            json={"role": "user"},
        )

    assert response.status_code == 403
