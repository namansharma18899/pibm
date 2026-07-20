import logging
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import UploadFile
from sqlalchemy.orm import Session

from app.config import settings

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".mp4", ".webm", ".mov"}
UPLOAD_DIR = Path("uploads")


def ensure_upload_dir() -> None:
    UPLOAD_DIR.mkdir(exist_ok=True)


def validate_video_file(filename: str, size: int) -> str | None:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"Invalid file type '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    max_bytes = settings.max_video_size_mb * 1024 * 1024
    if size > max_bytes:
        return f"File too large ({size // (1024*1024)}MB). Maximum: {settings.max_video_size_mb}MB"
    return None


async def save_upload(file: UploadFile) -> tuple[str, int]:
    ext = Path(file.filename).suffix.lower()
    stored_name = f"{uuid.uuid4()}{ext}"
    dest = UPLOAD_DIR / stored_name
    total = 0
    with open(dest, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)
            total += len(chunk)
    return stored_name, total


def get_upload_path(filename: str) -> Path:
    return UPLOAD_DIR / filename


def delete_upload(filename: str) -> None:
    path = UPLOAD_DIR / filename
    if path.exists():
        path.unlink()


def cleanup_expired_videos(db: Session) -> int:
    from app.models import VideoAnalysis

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.video_retention_days)
    expired = (
        db.query(VideoAnalysis)
        .filter(VideoAnalysis.filename.is_not(None), VideoAnalysis.created_at < cutoff)
        .all()
    )
    count = 0
    for analysis in expired:
        delete_upload(analysis.filename)
        analysis.filename = None
        count += 1
    if count:
        db.commit()
        logger.info("Cleaned up %d expired video(s)", count)
    return count
