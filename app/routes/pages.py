from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_flash, require_login
from app.models import Event, Participation, Rating, User
from app.templating import templates

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(
    request: Request,
    user: User | None = Depends(get_current_user),
    flash: dict | None = Depends(get_flash),
):
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("home.html", {"request": request, "user": None, "flash": flash})


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    upcoming_events = (
        db.query(Event)
        .filter(Event.is_deleted == False, Event.status.in_(["upcoming", "in_progress"]))
        .order_by(Event.scheduled_date)
        .limit(5)
        .all()
    )

    my_participations = (
        db.query(Participation)
        .filter(Participation.student_id == user.id)
        .join(Event)
        .filter(Event.is_deleted == False)
        .order_by(Event.scheduled_date.desc())
        .limit(5)
        .all()
    )

    completed_events = (
        db.query(Event)
        .filter(Event.is_deleted == False, Event.status == "completed")
        .order_by(Event.scheduled_date.desc())
        .limit(5)
        .all()
    )

    pending_ratings = []
    for event in completed_events:
        is_speaker = any(p.student_id == user.id for p in event.participations)
        if is_speaker:
            continue
        for p in event.participations:
            existing = (
                db.query(Rating)
                .filter(Rating.participation_id == p.id, Rating.rater_id == user.id)
                .first()
            )
            if not existing:
                pending_ratings.append({"event": event, "participation": p})

    hour = datetime.now(timezone.utc).hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"

    total_participations = db.query(Participation).filter(Participation.student_id == user.id).count()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "flash": flash,
            "greeting": greeting,
            "total_participations": total_participations,
            "upcoming_events": upcoming_events,
            "my_participations": my_participations,
            "pending_ratings": pending_ratings[:10],
        },
    )
