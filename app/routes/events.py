from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_flash, require_login, set_flash
from app.models import Event, Participation, Rating, User
from app.templating import templates

router = APIRouter()


@router.get("/events", response_class=HTMLResponse)
async def list_events(
    request: Request,
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    upcoming = db.query(Event).filter(Event.is_deleted == False, Event.status.in_(["upcoming", "in_progress"])).order_by(Event.scheduled_date).all()
    completed = db.query(Event).filter(Event.is_deleted == False, Event.status == "completed").order_by(Event.scheduled_date.desc()).all()

    pending_event_ids = set()
    rated_event_ids = set()
    if user:
        for event in completed:
            is_speaker = any(p.student_id == user.id for p in event.participations)
            if is_speaker:
                continue
            has_pending = False
            has_rateable = False
            for p in event.participations:
                has_rateable = True
                existing = (
                    db.query(Rating)
                    .filter(Rating.participation_id == p.id, Rating.rater_id == user.id)
                    .first()
                )
                if not existing:
                    has_pending = True
                    break
            if has_pending:
                pending_event_ids.add(event.id)
            elif has_rateable:
                rated_event_ids.add(event.id)

    return templates.TemplateResponse(
        "events/list.html",
        {
            "request": request,
            "user": user,
            "flash": flash,
            "upcoming": upcoming,
            "completed": completed,
            "pending_event_ids": pending_event_ids,
            "rated_event_ids": rated_event_ids,
        },
    )


@router.get("/events/{event_id}", response_class=HTMLResponse)
async def event_detail(
    request: Request,
    event_id: int,
    user: User | None = Depends(get_current_user),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    event = db.query(Event).filter(Event.id == event_id, Event.is_deleted == False).first()
    if not event:
        set_flash(request, "Event not found", "error")
        return RedirectResponse(url="/events", status_code=303)

    my_ratings = {}
    user_is_speaker = False
    if user:
        for p in event.participations:
            if p.student_id == user.id:
                user_is_speaker = True
            rating = (
                db.query(Rating)
                .filter(Rating.participation_id == p.id, Rating.rater_id == user.id)
                .first()
            )
            if rating:
                my_ratings[p.id] = rating

    return templates.TemplateResponse(
        "events/detail.html",
        {
            "request": request,
            "user": user,
            "flash": flash,
            "event": event,
            "my_ratings": my_ratings,
            "user_is_speaker": user_is_speaker,
        },
    )


@router.get("/events/{event_id}/rate/{participation_id}", response_class=HTMLResponse)
async def rate_form(
    request: Request,
    event_id: int,
    participation_id: int,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    participation = (
        db.query(Participation)
        .filter(Participation.id == participation_id, Participation.event_id == event_id)
        .first()
    )
    if not participation:
        set_flash(request, "Participation not found", "error")
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    if participation.student_id == user.id:
        set_flash(request, "You cannot rate yourself", "error")
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    event = participation.event

    is_speaker = db.query(Participation).filter(
        Participation.event_id == event_id, Participation.student_id == user.id
    ).first() is not None
    if is_speaker:
        set_flash(request, "Speakers cannot rate other speakers in the same event", "error")
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    if event.status != "completed":
        set_flash(request, "Ratings are only available for completed events", "error")
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    existing = (
        db.query(Rating)
        .filter(Rating.participation_id == participation_id, Rating.rater_id == user.id)
        .first()
    )

    return templates.TemplateResponse(
        "events/rate.html",
        {
            "request": request,
            "user": user,
            "flash": flash,
            "event": event,
            "participation": participation,
            "existing": existing,
        },
    )


@router.post("/events/{event_id}/rate/{participation_id}")
async def submit_rating(
    request: Request,
    event_id: int,
    participation_id: int,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
):
    participation = (
        db.query(Participation)
        .filter(Participation.id == participation_id, Participation.event_id == event_id)
        .first()
    )
    if not participation:
        set_flash(request, "Participation not found", "error")
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    if participation.student_id == user.id:
        set_flash(request, "You cannot rate yourself", "error")
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    event = participation.event

    is_speaker = db.query(Participation).filter(
        Participation.event_id == event_id, Participation.student_id == user.id
    ).first() is not None
    if is_speaker:
        set_flash(request, "Speakers cannot rate other speakers in the same event", "error")
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    if event.status != "completed":
        set_flash(request, "Ratings are only available for completed events", "error")
        return RedirectResponse(url=f"/events/{event_id}", status_code=303)

    form = await request.form()

    rating = (
        db.query(Rating)
        .filter(Rating.participation_id == participation_id, Rating.rater_id == user.id)
        .first()
    )
    if not rating:
        rating = Rating(participation_id=participation_id, rater_id=user.id)
        db.add(rating)

    if event.event_type == "speed_talk":
        rating.star_rating = int(form.get("star_rating", 0))
        if not 1 <= rating.star_rating <= 5:
            set_flash(request, "Please select a rating between 1 and 5", "error")
            return RedirectResponse(
                url=f"/events/{event_id}/rate/{participation_id}", status_code=303
            )
    else:
        try:
            rating.clarity = int(form.get("clarity", 0))
            rating.confidence = int(form.get("confidence", 0))
            rating.body_language = int(form.get("body_language", 0))
            rating.presentation_skills = int(form.get("presentation_skills", 0))
            rating.content = int(form.get("content", 0))
        except (ValueError, TypeError):
            set_flash(request, "Invalid rating values", "error")
            return RedirectResponse(
                url=f"/events/{event_id}/rate/{participation_id}", status_code=303
            )
        for val in [rating.clarity, rating.confidence, rating.body_language, rating.presentation_skills, rating.content]:
            if not 1 <= val <= 5:
                set_flash(request, "All scores must be between 1 and 5", "error")
                return RedirectResponse(
                    url=f"/events/{event_id}/rate/{participation_id}", status_code=303
                )

    db.commit()
    set_flash(request, f"Rating submitted for {participation.student.name}")
    return RedirectResponse(url=f"/events/{event_id}", status_code=303)
