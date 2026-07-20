from datetime import datetime, timedelta, timezone

from fastapi.templating import Jinja2Templates

from app.config import settings

templates = Jinja2Templates(directory="app/templates")

AVATAR_EMOJIS = [
    "🐱", "🐶", "🐼", "🦊", "🐰", "🦋", "🐬", "🦄", "🐝", "🦉",
    "🐧", "🐨", "🦁", "🐯", "🐸", "🦜", "🐿️", "🐳", "🦒", "🐙",
    "🌸", "🌺", "🌻", "🌷", "🍀", "🌵", "🎋", "🌹",
    "⭐", "💎", "🔮", "🎨", "🪐", "🌈", "🍄", "🎯",
]

AVATAR_COLORS = [
    "#fecaca", "#fed7aa", "#fef08a", "#bbf7d0", "#a5f3fc",
    "#bfdbfe", "#c4b5fd", "#f9a8d4", "#fcd34d", "#86efac",
    "#67e8f9", "#a78bfa", "#f472b6", "#fdba74", "#6ee7b7",
    "#93c5fd",
]


def get_avatar(user_id: int) -> dict:
    emoji = AVATAR_EMOJIS[user_id % len(AVATAR_EMOJIS)]
    color = AVATAR_COLORS[user_id % len(AVATAR_COLORS)]
    return {"emoji": emoji, "color": color}


def days_until_deletion(created_at: datetime) -> int:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    expires_at = created_at + timedelta(days=settings.video_retention_days)
    remaining = (expires_at - datetime.now(timezone.utc)).days
    return max(remaining, 0)


templates.env.globals["get_avatar"] = get_avatar
templates.env.globals["days_until_deletion"] = days_until_deletion
templates.env.globals["video_retention_days"] = settings.video_retention_days
