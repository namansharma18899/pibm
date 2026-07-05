from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.database import Base, engine
from app.dependencies import RedirectException


def create_app() -> FastAPI:
    app = FastAPI(title="PIBM - Public Speaking Tracker")

    app.add_middleware(SessionMiddleware, secret_key=settings.secret_key)
    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    @app.exception_handler(RedirectException)
    async def redirect_exception_handler(request: Request, exc: RedirectException):
        return RedirectResponse(url=exc.url, status_code=303)

    from app.auth import router as auth_router
    from app.routes.admin import router as admin_router
    from app.routes.events import router as events_router
    from app.routes.pages import router as pages_router
    from app.routes.profile import router as profile_router

    app.include_router(auth_router)
    app.include_router(pages_router)
    app.include_router(admin_router)
    app.include_router(events_router)
    app.include_router(profile_router)

    @app.on_event("startup")
    def on_startup():
        Base.metadata.create_all(bind=engine)

    return app


app = create_app()
