# PIBM — Student Communication Performance Tracker

A web app for tracking and rating student speaking performance across events like speed talks, long speeches, and debates. Built for institutions that want peer-driven feedback on communication skills.

**Live:** [studentprep.duckdns.org](https://studentprep.duckdns.org)

## Features

- **Google OAuth login** — no passwords to manage
- **Three event types** — Speed Talk (quick star rating), Long Speech, and Debate (multi-criteria: clarity, confidence, body language, presentation skills, content)
- **Peer ratings** — students rate each other after events; one rating per speaker per event
- **Admin dashboard** — manage students, create events, mark attendance, control when ratings open
- **Student profiles** — aggregated speaking scores computed from all past ratings
- **Auto-admin** — first user to sign in becomes the admin

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy ORM + SQLite
- **Frontend:** Jinja2 server-rendered templates + Tailwind CSS
- **Auth:** Google OAuth via Authlib
- **Deployment:** Ubuntu EC2 + Nginx + Let's Encrypt SSL

## Quick Start

```bash
# Clone
git clone https://github.com/namansharma18899/pibm.git
cd pibm

# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your Google OAuth credentials

# Run
python run.py
```

App runs at http://127.0.0.1:8000

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_CLIENT_ID` | OAuth client ID from Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | OAuth client secret |
| `SECRET_KEY` | Random string for session encryption |
| `DATABASE_URL` | SQLAlchemy DB URL (default: `sqlite:///./pibm.db`) |

## Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials
2. Create an OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URI: `http://localhost:8000/auth/google` (dev) or `https://studentprep.duckdns.org/auth/google` (prod)
4. Copy client ID and secret into `.env`

## Project Structure

```
app/
├── main.py            # App factory, middleware, router registration
├── config.py          # Pydantic settings from .env
├── database.py        # SQLAlchemy engine and session
├── models.py          # User, Event, Participation, Rating
├── auth.py            # Google OAuth flow
├── dependencies.py    # Auth guards, flash messages
├── routes/
│   ├── pages.py       # Home, student dashboard
│   ├── admin.py       # Admin: students, events, attendance
│   ├── events.py      # Event listing, detail, rating
│   └── profile.py     # Student profile with scores
├── templates/         # Jinja2 templates (Tailwind CSS)
└── static/            # CSS and JS assets
```

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for a full guide to deploying on AWS EC2 with Nginx and HTTPS.

## License

MIT

## Special Thanks to Komal Suthar[https://github.com/19-komal] for the help & debugging support 🍁.
