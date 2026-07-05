from fastapi import Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import get_db
from app.models import User


class RedirectException(HTTPException):
    def __init__(self, url: str):
        super().__init__(status_code=303, detail="Redirect")
        self.url = url


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()


def require_login(request: Request, user: User | None = Depends(get_current_user)) -> User:
    if user is None:
        raise RedirectException("/login")
    return user


def require_admin(user: User = Depends(require_login)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def get_flash(request: Request) -> dict | None:
    flash = request.session.pop("flash", None)
    return flash


def set_flash(request: Request, message: str, flash_type: str = "success"):
    request.session["flash"] = {"type": flash_type, "message": message}
