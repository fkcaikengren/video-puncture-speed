import uuid

from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from jose import ExpiredSignatureError, JWTError, jwt
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings
from app.core.exceptions import NotFoundException
from app.core.logging import get_logger
from app.core.schemas import ApiErrorResponse


logger = get_logger(__name__)

WHITE_LIST = ["/", "/docs", "/redoc", "/openapi.json", "/api", "/api/health", "/api/auth/login"]


def setup_cors_middleware(app: FastAPI) -> None:
    allow_origins = settings.CORS_ORIGINS
    allow_credentials = "*" not in allow_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class JWTMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.user = None

        if request.method == "OPTIONS":
            return await call_next(request)

        if request.url.path in WHITE_LIST:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")

        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content=ApiErrorResponse(
                    code=401,
                    err_msg="Not authenticated",
                    data=None,
                ).model_dump(),
            )

        token = auth_header.split(" ", 1)[1].strip()

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
        except ExpiredSignatureError:
            return JSONResponse(
                status_code=401,
                content=ApiErrorResponse(
                    code=401,
                    err_msg="Token expired",
                    data=None,
                ).model_dump(),
            )
        except JWTError:
            return JSONResponse(
                status_code=401,
                content=ApiErrorResponse(
                    code=401,
                    err_msg="Invalid token",
                    data=None,
                ).model_dump(),
            )

        user_id: str | None = payload.get("sub")
        if user_id is None:
            return JSONResponse(
                status_code=401,
                content=ApiErrorResponse(
                    code=401,
                    err_msg="Invalid authentication credentials",
                    data=None,
                ).model_dump(),
            )

        try:
            uuid_user_id = uuid.UUID(user_id)
        except ValueError:
            return JSONResponse(
                status_code=401,
                content=ApiErrorResponse(
                    code=401,
                    err_msg="Invalid authentication credentials",
                    data=None,
                ).model_dump(),
            )

        from app.core.database import get_session
        from app.api.users.service import UserService

        async for session in get_session():
            try:
                user = await UserService(session).get_user(uuid_user_id)
            except NotFoundException:
                return JSONResponse(
                    status_code=401,
                    content=ApiErrorResponse(
                        code=401,
                        err_msg="Invalid authentication credentials",
                        data=None,
                    ).model_dump(),
                )

            request.state.user = user

        response = await call_next(request)
        return response
