import json
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


def parse_analysis_data(data_str: str | None) -> dict | None:
    if not data_str:
        return None
    return json.loads(data_str)


def format_param_name(key: str) -> str:
    import re
    name = re.sub(r"_\d+pct$", "", key)
    return name.replace("_", " ").title()


from app.services.gemini import CATEGORY_WEIGHTS

ANALYSIS_CATEGORIES = [
    {"key": "visual_presence", "label": "Visual Presence", "bar": "bg-blue-500", "badge_bg": "bg-blue-100", "badge_text": "text-blue-700"},
    {"key": "vocal_delivery", "label": "Vocal Delivery", "bar": "bg-purple-500", "badge_bg": "bg-purple-100", "badge_text": "text-purple-700"},
    {"key": "content_structure", "label": "Content & Structure", "bar": "bg-emerald-500", "badge_bg": "bg-emerald-100", "badge_text": "text-emerald-700"},
    {"key": "verbal_communication", "label": "Verbal Communication", "bar": "bg-amber-500", "badge_bg": "bg-amber-100", "badge_text": "text-amber-700"},
    {"key": "audience_engagement", "label": "Audience Engagement", "bar": "bg-rose-500", "badge_bg": "bg-rose-100", "badge_text": "text-rose-700"},
]
for cat in ANALYSIS_CATEGORIES:
    cat["weight"] = int(CATEGORY_WEIGHTS[cat["key"]] * 100)

templates.env.globals["get_avatar"] = get_avatar
templates.env.globals["days_until_deletion"] = days_until_deletion
templates.env.globals["video_retention_days"] = settings.video_retention_days
templates.env.globals["parse_analysis_data"] = parse_analysis_data
templates.env.globals["format_param_name"] = format_param_name
templates.env.globals["analysis_categories"] = ANALYSIS_CATEGORIES
