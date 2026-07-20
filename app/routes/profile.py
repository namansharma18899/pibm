from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_flash, require_login
from app.models import Event, Participation, Rating, User, VideoAnalysis
from app.templating import templates

router = APIRouter()


def compute_profile_stats(db: Session, target_user: User) -> dict:
    participations = (
        db.query(Participation)
        .filter(Participation.student_id == target_user.id)
        .all()
    )

    total_events = len(participations)
    attended_events = sum(1 for p in participations if p.attended)

    speed_talk_avg = None
    category_avgs = {}
    event_history = []

    speed_talk_ratings = []
    detailed_ratings = {"clarity": [], "confidence": [], "body_language": [], "presentation_skills": [], "content": []}

    for p in participations:
        event = p.event
        score = p.average_score
        event_history.append({
            "event": event,
            "participation": p,
            "score": score,
            "rating_count": len(p.ratings),
        })

        for r in p.ratings:
            if event.event_type == "speed_talk" and r.star_rating is not None:
                speed_talk_ratings.append(r.star_rating)
            else:
                for field in detailed_ratings:
                    val = getattr(r, field)
                    if val is not None:
                        detailed_ratings[field].append(val)

    if speed_talk_ratings:
        speed_talk_avg = sum(speed_talk_ratings) / len(speed_talk_ratings)

    for field, values in detailed_ratings.items():
        if values:
            category_avgs[field] = sum(values) / len(values)

    overall_avg = None
    all_scores = []
    if speed_talk_avg is not None:
        all_scores.append(speed_talk_avg)
    all_scores.extend(category_avgs.values())
    if all_scores:
        overall_avg = sum(all_scores) / len(all_scores)

    event_history.sort(key=lambda x: x["event"].scheduled_date, reverse=True)

    video_analyses = (
        db.query(VideoAnalysis)
        .filter(VideoAnalysis.user_id == target_user.id, VideoAnalysis.status == "completed")
        .order_by(VideoAnalysis.created_at.desc())
        .limit(5)
        .all()
    )

    return {
        "total_events": total_events,
        "attended_events": attended_events,
        "speed_talk_avg": speed_talk_avg,
        "category_avgs": category_avgs,
        "overall_avg": overall_avg,
        "event_history": event_history,
        "video_analyses": video_analyses,
    }


@router.get("/profile/me", response_class=HTMLResponse)
async def my_profile(
    request: Request,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    stats = compute_profile_stats(db, user)
    return templates.TemplateResponse(
        "profile/view.html",
        {"request": request, "user": user, "flash": flash, "target": user, "stats": stats, "is_own": True, "can_view_stats": True},
    )


@router.get("/profile/{user_id}", response_class=HTMLResponse)
async def view_profile(
    request: Request,
    user_id: int,
    user: User = Depends(require_login),
    db: Session = Depends(get_db),
    flash: dict | None = Depends(get_flash),
):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        return RedirectResponse(url="/events", status_code=303)
    is_own = user.id == target.id
    can_view_stats = is_own or user.role == "admin"
    stats = compute_profile_stats(db, target) if can_view_stats else None
    return templates.TemplateResponse(
        "profile/view.html",
        {"request": request, "user": user, "flash": flash, "target": target, "stats": stats, "is_own": is_own, "can_view_stats": can_view_stats},
    )
