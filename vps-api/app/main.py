from fastapi import FastAPI, APIRouter, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.middlewares import JWTMiddleware, setup_cors_middleware
from app.core.schemas import BaseResponse
from app.api.users.routes import router as auth_router, admin_router
from app.api.videos.routes import router as video_router, categories_router
from app.api.dashboard.routes import router as dashboard_router
from app.api.comparisons.routes import router as comparison_router
from app.core.tempfile_manager import TempfileManager


# from api.utils.migrations import run_migrations

setup_logging()

# run_migrations()

logger = get_logger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
)
app.add_middleware(JWTMiddleware)
setup_cors_middleware(app)
v1_router = APIRouter()
v1_router.include_router(auth_router)
v1_router.include_router(video_router)
v1_router.include_router(categories_router)
v1_router.include_router(dashboard_router)
v1_router.include_router(comparison_router)

app.include_router(v1_router, prefix="/api")

# 兜底异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=BaseResponse(
            code=exc.status_code,
            err_msg=str(exc.detail),
            data=None,
        ).model_dump(),
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=BaseResponse(
            code=422,
            err_msg="Request validation error",
            data=None,
        ).model_dump(),
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content=BaseResponse(
            code=500,
            err_msg="Internal server error",
            data=None,
        ).model_dump(),
    )


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.get("/api/")
async def root():
    logger.debug("Root endpoint called")
    return {"message": "Welcome to Hero API!"}


# 作用：在应用启动时清理过期的临时文件
@app.on_event("startup")
async def startup_cleanup_tmp():
    logger.info("Starting cleanup of stale temporary files...")
    count = TempfileManager.cleanup_stale_files()
    logger.info(f"Cleanup finished. Removed {count} stale files.")
