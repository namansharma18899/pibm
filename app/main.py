import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.dependencies import RedirectException
from app.services.news import maybe_refresh_cache
from app.services.storage import cleanup_expired_videos, ensure_upload_dir

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

log_format = logging.Formatter("%(asctime)s %(levelname)-5s [%(name)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

file_handler = RotatingFileHandler(LOG_DIR / "app.log", maxBytes=5 * 1024 * 1024, backupCount=3)
file_handler.setFormatter(log_format)
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_format)
console_handler.setLevel(logging.INFO)

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="Student Prep - Public Speaking Tracker")

    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)

    @app.middleware("http")
    async def forward_proto(request: Request, call_next):
        if request.headers.get("x-forwarded-proto") == "https":
            request.scope["scheme"] = "https"
        return await call_next(request)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")
    ensure_upload_dir()
    app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

    @app.exception_handler(RedirectException)
    async def redirect_exception_handler(request: Request, exc: RedirectException):
        return RedirectResponse(url=exc.url, status_code=303)

    from app.auth import router as auth_router
    from app.routes.admin import router as admin_router
    from app.routes.events import router as events_router
    from app.routes.pages import router as pages_router
    from app.routes.profile import router as profile_router
    from app.routes.video import router as video_router

    app.include_router(auth_router)
    app.include_router(pages_router)
    app.include_router(admin_router)
    app.include_router(events_router)
    app.include_router(profile_router)
    app.include_router(video_router)

    @app.on_event("startup")
    def on_startup():
        logger.info("Starting app — mock_ai=%s, retention=%dd, db=%s",
                     settings.mock_ai, settings.video_retention_days, settings.database_url)

        from app.database import SessionLocal

        db = SessionLocal()
        try:
            cleanup_expired_videos(db)
        finally:
            db.close()

        maybe_refresh_cache()

    return app


app = create_app()
