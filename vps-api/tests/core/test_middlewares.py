from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from app.core.middlewares import setup_cors_middleware, JWTMiddleware

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
