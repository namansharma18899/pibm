from fastapi.templating import Jinja2Templates

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


templates.env.globals["get_avatar"] = get_avatar
