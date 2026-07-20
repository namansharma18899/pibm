import asyncio
import json
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_flash, require_login, set_flash
from app.models import Participation, User, VideoAnalysis
from app.services.credits import (
    check_upload_allowed,
    deduct_credits,
    get_daily_upload_count,
    get_user_credit,
    refund_credits,
)
from app.services.gemini import analyze_video, compute_overall_score
from app.services.storage import UPLOAD_DIR, get_upload_path, validate_video_file
from app.templating import templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/video")


@router.get("/upload", response_class=HTMLResponse)
async def upload_form(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    credit = get_user_credit(db, user.id)
    daily_count = get_daily_upload_count(db, user.id)
    db.commit()
    return templates.TemplateResponse(
        "video/upload.html",
        {
            "request": request,
            "user": user,
            "flash": flash,
            "participation": None,
            "event": None,
            "credit_balance": credit.balance,
            "daily_remaining": max(0, settings.daily_video_limit - daily_count),
        },
    )


@router.get("/upload/{participation_id}", response_class=HTMLResponse)
async def upload_form_event(
    request: Request,
    participation_id: int,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    participation = (
        db.query(Participation)
        .filter(Participation.id == participation_id, Participation.student_id == user.id)
        .first()
    )
    if not participation:
        set_flash(request, "Participation not found or not yours", "error")
        return RedirectResponse(url="/events", status_code=303)
    credit = get_user_credit(db, user.id)
    daily_count = get_daily_upload_count(db, user.id)
    db.commit()
    return templates.TemplateResponse(
        "video/upload.html",
        {
            "request": request,
            "user": user,
            "flash": flash,
            "participation": participation,
            "event": participation.event,
            "credit_balance": credit.balance,
            "daily_remaining": max(0, settings.daily_video_limit - daily_count),
        },
    )


@router.post("/upload")
async def handle_upload(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    form = await request.form()
    file = form.get("video_file")

    if not file or not file.filename:
        logger.warning("Upload attempt with no file — user_id=%d", user.id)
        set_flash(request, "Please select a video file", "error")
        return RedirectResponse(url="/video/upload", status_code=303)

    participation_id = form.get("participation_id")
    participation_id = int(participation_id) if participation_id else None

    if participation_id:
        participation = (
            db.query(Participation)
            .filter(Participation.id == participation_id, Participation.student_id == user.id)
            .first()
        )
        if not participation:
            set_flash(request, "Participation not found or not yours", "error")
            return RedirectResponse(url="/events", status_code=303)

    file_bytes = await file.read()
    file_size = len(file_bytes)
    logger.info("Upload received — user_id=%d file=%s size=%.1fMB",
                user.id, file.filename, file_size / (1024 * 1024))

    error = validate_video_file(file.filename, file_size)
    if error:
        logger.warning("Validation failed — user_id=%d reason=%s", user.id, error)
        set_flash(request, error, "error")
        redirect_url = f"/video/upload/{participation_id}" if participation_id else "/video/upload"
        return RedirectResponse(url=redirect_url, status_code=303)

    block_reason = check_upload_allowed(db, user.id, file_size)
    if block_reason:
        logger.warning("Upload blocked — user_id=%d reason=%s", user.id, block_reason)
        set_flash(request, block_reason, "error")
        redirect_url = f"/video/upload/{participation_id}" if participation_id else "/video/upload"
        return RedirectResponse(url=redirect_url, status_code=303)

    cost = deduct_credits(db, user.id, file_size)
    logger.info("Credits deducted — user_id=%d cost=%d", user.id, cost)

    ext = Path(file.filename).suffix.lower()
    stored_name = f"{uuid.uuid4()}{ext}"
    dest = UPLOAD_DIR / stored_name
    with open(dest, "wb") as f:
        f.write(file_bytes)

    analysis = VideoAnalysis(
        user_id=user.id,
        participation_id=participation_id,
        filename=stored_name,
        original_filename=file.filename,
        file_size=file_size,
        credits_used=cost,
        status="processing",
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    logger.info("Analysis started — analysis_id=%d user_id=%d file=%s", analysis.id, user.id, stored_name)
    try:
        result = await asyncio.to_thread(analyze_video, get_upload_path(stored_name))
        analysis.analysis_data = json.dumps(result)
        analysis.overall_score = compute_overall_score(result)
        analysis.summary = result.get("overall_summary", "")
        analysis.status = "completed"
        logger.info("Analysis completed — analysis_id=%d score=%.1f", analysis.id, analysis.overall_score)
    except Exception as e:
        analysis.status = "failed"
        analysis.error_message = str(e)
        refund_credits(db, user.id, cost)
        logger.error("Analysis failed — analysis_id=%d error=%s", analysis.id, e)

    db.commit()
    set_flash(
        request,
        "Video analyzed successfully!" if analysis.status == "completed" else f"Analysis failed: {analysis.error_message}",
        "success" if analysis.status == "completed" else "error",
    )
    return RedirectResponse(url=f"/video/analysis/{analysis.id}", status_code=303)


@router.get("/analysis/{analysis_id}", response_class=HTMLResponse)
async def view_analysis(
    request: Request,
    analysis_id: int,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    analysis = db.query(VideoAnalysis).filter(VideoAnalysis.id == analysis_id).first()
    if not analysis:
        set_flash(request, "Analysis not found", "error")
        return RedirectResponse(url="/video/my-analyses", status_code=303)
    if analysis.user_id != user.id and user.role != "admin":
        set_flash(request, "Access denied", "error")
        return RedirectResponse(url="/video/my-analyses", status_code=303)
    return templates.TemplateResponse(
        "video/analysis.html",
        {"request": request, "user": user, "flash": flash, "analysis": analysis},
    )


@router.get("/my-analyses", response_class=HTMLResponse)
async def my_analyses(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    analyses = (
        db.query(VideoAnalysis)
        .filter(VideoAnalysis.user_id == user.id)
        .order_by(VideoAnalysis.created_at.desc())
        .all()
    )
    return templates.TemplateResponse(
        "video/list.html",
        {"request": request, "user": user, "flash": flash, "analyses": analyses},
    )
