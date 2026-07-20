import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.dependencies import get_flash, require_admin, set_flash
from app.models import Event, Participation, User
from app.services.credits import admin_set_credits, get_daily_upload_count, get_user_credit
from app.templating import templates

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin")


@router.get("", response_class=HTMLResponse)
async def admin_dashboard(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    student_count = db.query(User).filter(User.role == "student").count()
    event_count = db.query(Event).filter(Event.is_deleted == False).count()
    upcoming_events = (
        db.query(Event)
        .filter(Event.is_deleted == False, Event.status == "upcoming")
        .order_by(Event.scheduled_date)
        .limit(5)
        .all()
    )
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "user": user,
            "flash": flash,
            "student_count": student_count,
            "event_count": event_count,
            "upcoming_events": upcoming_events,
        },
    )


@router.get("/students", response_class=HTMLResponse)
async def list_students(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    students = db.query(User).order_by(User.name).all()
    return templates.TemplateResponse(
        "admin/students.html",
        {"request": request, "user": user, "flash": flash, "students": students},
    )


@router.post("/students/{user_id}/role")
async def change_role(
    request: Request,
    user_id: int,
    role: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if role not in ("student", "admin"):
        set_flash(request, "Invalid role", "error")
        return RedirectResponse(url="/admin/students", status_code=303)
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        set_flash(request, "User not found", "error")
        return RedirectResponse(url="/admin/students", status_code=303)
    if target.id == user.id:
        set_flash(request, "Cannot change your own role", "error")
        return RedirectResponse(url="/admin/students", status_code=303)
    logger.info("Role changed — admin_id=%d target_id=%d old_role=%s new_role=%s", user.id, target.id, target.role, role)
    target.role = role
    db.commit()
    set_flash(request, f"{target.name} is now {role}")
    return RedirectResponse(url="/admin/students", status_code=303)


@router.get("/events", response_class=HTMLResponse)
async def list_events_admin(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    events = db.query(Event).filter(Event.is_deleted == False).order_by(Event.scheduled_date.desc()).all()
    return templates.TemplateResponse(
        "admin/events.html",
        {"request": request, "user": user, "flash": flash, "events": events},
    )


@router.get("/events/new", response_class=HTMLResponse)
async def create_event_form(
    request: Request,
    user: User = Depends(require_admin),
    flash: dict | None = Depends(get_flash),
):
    return templates.TemplateResponse(
        "admin/event_form.html",
        {"request": request, "user": user, "flash": flash, "event": None},
    )


@router.post("/events/new")
async def create_event(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    event_type: str = Form(...),
    scheduled_date: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if event_type not in ("speed_talk", "long_speech", "debate"):
        set_flash(request, "Invalid event type", "error")
        return RedirectResponse(url="/admin/events/new", status_code=303)
    try:
        dt = datetime.fromisoformat(scheduled_date)
    except ValueError:
        set_flash(request, "Invalid date format", "error")
        return RedirectResponse(url="/admin/events/new", status_code=303)

    event = Event(
        title=title,
        description=description,
        event_type=event_type,
        scheduled_date=dt,
        created_by_id=user.id,
    )
    db.add(event)
    db.commit()
    logger.info("Event created — id=%d title=%s type=%s by_admin=%d", event.id, title, event_type, user.id)
    set_flash(request, f"Event '{title}' created")
    return RedirectResponse(url=f"/admin/events/{event.id}/participants", status_code=303)


@router.get("/events/{event_id}/edit", response_class=HTMLResponse)
async def edit_event_form(
    request: Request,
    event_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    event = db.query(Event).filter(Event.id == event_id, Event.is_deleted == False).first()
    if not event:
        set_flash(request, "Event not found", "error")
        return RedirectResponse(url="/admin/events", status_code=303)
    return templates.TemplateResponse(
        "admin/event_form.html",
        {"request": request, "user": user, "flash": flash, "event": event},
    )


@router.post("/events/{event_id}/edit")
async def edit_event(
    request: Request,
    event_id: int,
    title: str = Form(...),
    description: str = Form(""),
    event_type: str = Form(...),
    scheduled_date: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    event = db.query(Event).filter(Event.id == event_id, Event.is_deleted == False).first()
    if not event:
        set_flash(request, "Event not found", "error")
        return RedirectResponse(url="/admin/events", status_code=303)
    try:
        dt = datetime.fromisoformat(scheduled_date)
    except ValueError:
        set_flash(request, "Invalid date format", "error")
        return RedirectResponse(url=f"/admin/events/{event_id}/edit", status_code=303)

    event.title = title
    event.description = description
    event.event_type = event_type
    event.scheduled_date = dt
    db.commit()
    logger.info("Event updated — id=%d title=%s by_admin=%d", event.id, title, user.id)
    set_flash(request, f"Event '{title}' updated")
    return RedirectResponse(url="/admin/events", status_code=303)


@router.post("/events/{event_id}/delete")
async def delete_event(
    request: Request,
    event_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    event = db.query(Event).filter(Event.id == event_id, Event.is_deleted == False).first()
    if not event:
        set_flash(request, "Event not found", "error")
        return RedirectResponse(url="/admin/events", status_code=303)
    logger.info("Event deleted — id=%d title=%s by_admin=%d", event.id, event.title, user.id)
    event.is_deleted = True
    db.commit()
    set_flash(request, f"Event '{event.title}' deleted")
    return RedirectResponse(url="/admin/events", status_code=303)


@router.post("/events/{event_id}/status")
async def change_event_status(
    request: Request,
    event_id: int,
    status: str = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if status not in ("upcoming", "in_progress", "completed"):
        set_flash(request, "Invalid status", "error")
        return RedirectResponse(url="/admin/events", status_code=303)
    event = db.query(Event).filter(Event.id == event_id, Event.is_deleted == False).first()
    if not event:
        set_flash(request, "Event not found", "error")
        return RedirectResponse(url="/admin/events", status_code=303)
    logger.info("Event status changed — id=%d status=%s by_admin=%d", event.id, status, user.id)
    event.status = status
    db.commit()
    set_flash(request, f"Event status changed to {status}")
    return RedirectResponse(url="/admin/events", status_code=303)


@router.get("/events/{event_id}/participants", response_class=HTMLResponse)
async def manage_participants(
    request: Request,
    event_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    event = db.query(Event).filter(Event.id == event_id, Event.is_deleted == False).first()
    if not event:
        set_flash(request, "Event not found", "error")
        return RedirectResponse(url="/admin/events", status_code=303)
    participant_ids = [p.student_id for p in event.participations]
    available_students = (
        db.query(User)
        .filter(User.id.notin_(participant_ids) if participant_ids else True)
        .order_by(User.name)
        .all()
    )
    return templates.TemplateResponse(
        "admin/participants.html",
        {
            "request": request,
            "user": user,
            "flash": flash,
            "event": event,
            "available_students": available_students,
        },
    )


@router.post("/events/{event_id}/participants/add")
async def add_participant(
    request: Request,
    event_id: int,
    student_id: int = Form(...),
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    event = db.query(Event).filter(Event.id == event_id, Event.is_deleted == False).first()
    if not event:
        set_flash(request, "Event not found", "error")
        return RedirectResponse(url="/admin/events", status_code=303)
    existing = (
        db.query(Participation)
        .filter(Participation.event_id == event_id, Participation.student_id == student_id)
        .first()
    )
    if existing:
        set_flash(request, "Student already added", "error")
        return RedirectResponse(url=f"/admin/events/{event_id}/participants", status_code=303)
    p = Participation(event_id=event_id, student_id=student_id)
    db.add(p)
    db.commit()
    set_flash(request, "Student added to event")
    return RedirectResponse(url=f"/admin/events/{event_id}/participants", status_code=303)


@router.post("/events/{event_id}/participants/{participation_id}/remove")
async def remove_participant(
    request: Request,
    event_id: int,
    participation_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    p = db.query(Participation).filter(Participation.id == participation_id).first()
    if p:
        db.delete(p)
        db.commit()
        set_flash(request, "Student removed from event")
    return RedirectResponse(url=f"/admin/events/{event_id}/participants", status_code=303)


@router.get("/events/{event_id}/attendance", response_class=HTMLResponse)
async def attendance_page(
    request: Request,
    event_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    event = db.query(Event).filter(Event.id == event_id, Event.is_deleted == False).first()
    if not event:
        set_flash(request, "Event not found", "error")
        return RedirectResponse(url="/admin/events", status_code=303)
    return templates.TemplateResponse(
        "admin/attendance.html",
        {"request": request, "user": user, "flash": flash, "event": event},
    )


@router.post("/events/{event_id}/attendance")
async def update_attendance(
    request: Request,
    event_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    event = db.query(Event).filter(Event.id == event_id, Event.is_deleted == False).first()
    if not event:
        set_flash(request, "Event not found", "error")
        return RedirectResponse(url="/admin/events", status_code=303)

    form = await request.form()
    attended_ids = set(form.getlist("attended"))
    for p in event.participations:
        p.attended = str(p.id) in attended_ids
    db.commit()
    logger.info("Attendance updated — event_id=%d marked=%d/%d by_admin=%d",
                event_id, len(attended_ids), len(event.participations), user.id)
    set_flash(request, "Attendance updated")
    return RedirectResponse(url=f"/admin/events/{event_id}/attendance", status_code=303)


@router.get("/credits", response_class=HTMLResponse)
async def manage_credits(
    request: Request,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    students = db.query(User).filter(User.role == "student").order_by(User.name).all()
    student_credits = []
    for student in students:
        credit = get_user_credit(db, student.id)
        daily_count = get_daily_upload_count(db, student.id)
        student_credits.append({
            "student": student,
            "credit": credit,
            "daily_count": daily_count,
        })
    db.commit()
    return templates.TemplateResponse(
        "admin/credits.html",
        {
            "request": request,
            "user": user,
            "flash": flash,
            "student_credits": student_credits,
            "monthly_credits": settings.monthly_credits,
            "daily_limit": settings.daily_video_limit,
        },
    )


@router.post("/credits/{user_id}")
async def adjust_credits(
    request: Request,
    user_id: int,
    user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    form = await request.form()
    try:
        new_balance = int(form.get("new_balance", 0))
    except (ValueError, TypeError):
        set_flash(request, "Invalid credit value", "error")
        return RedirectResponse(url="/admin/credits", status_code=303)

    if new_balance < 0:
        set_flash(request, "Credit balance cannot be negative", "error")
        return RedirectResponse(url="/admin/credits", status_code=303)

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        set_flash(request, "User not found", "error")
        return RedirectResponse(url="/admin/credits", status_code=303)

    old_credit = get_user_credit(db, user_id)
    old_balance = old_credit.balance
    admin_set_credits(db, user_id, new_balance)
    db.commit()
    logger.info("Credits adjusted — admin_id=%d target_id=%d old=%d new=%d", user.id, user_id, old_balance, new_balance)
    set_flash(request, f"Credits for {target.name} updated to {new_balance}")
    return RedirectResponse(url="/admin/credits", status_code=303)
