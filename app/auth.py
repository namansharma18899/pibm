import logging

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_current_user, get_flash
from app.models import User
from app.templating import templates

logger = logging.getLogger(__name__)

router = APIRouter()

oauth = OAuth()
oauth.register(
    name="google",
    client_id=settings.google_client_id,
    client_secret=settings.google_client_secret,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    user: User | None = Depends(get_current_user),
    flash: dict | None = Depends(get_flash),
):
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "user": None, "flash": flash})


@router.get("/login/google")
async def login_google(request: Request):
    redirect_uri = request.url_for("auth_google")
    logger.info("Login initiated — redirecting to Google OAuth")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/auth/google")
async def auth_google(request: Request, db: Session = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo")
    if not userinfo:
        logger.warning("OAuth callback received no userinfo")
        return RedirectResponse(url="/login", status_code=303)

    google_sub = userinfo["sub"]
    user = db.query(User).filter(User.google_sub == google_sub).first()

    if user is None:
        is_first_user = db.query(User).count() == 0
        user = User(
            email=userinfo["email"],
            name=userinfo.get("name", userinfo["email"]),
            picture_url=userinfo.get("picture"),
            google_sub=google_sub,
            role="admin" if is_first_user else "student",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("New user registered: id=%d email=%s role=%s", user.id, user.email, user.role)
    else:
        user.name = userinfo.get("name", user.name)
        user.picture_url = userinfo.get("picture", user.picture_url)
        db.commit()

    request.session["user_id"] = user.id
    logger.info("User logged in: id=%d email=%s", user.id, user.email)
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    user_id = request.session.get("user_id")
    request.session.clear()
    logger.info("User logged out: id=%s", user_id)
    return RedirectResponse(url="/", status_code=303)
