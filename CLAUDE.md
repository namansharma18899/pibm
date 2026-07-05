# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure (copy and fill in Google OAuth credentials)
cp .env.example .env

# Run dev server (auto-reload on changes)
python run.py
# App runs at http://127.0.0.1:8000
```

Google OAuth setup: Create credentials at console.cloud.google.com, set authorized redirect URI to `http://localhost:8000/auth/google`, put client ID and secret in `.env`.

## Architecture

FastAPI app with Jinja2 server-rendered templates and SQLite via SQLAlchemy ORM.

**Key files:**
- `run.py` — uvicorn entry point
- `app/main.py` — FastAPI app factory, middleware, router registration, table creation on startup
- `app/config.py` — Pydantic BaseSettings loading from `.env`
- `app/database.py` — SQLAlchemy engine, session factory, `get_db` dependency
- `app/models.py` — User, Event, Participation, Rating (4 models, all relationships defined here)
- `app/auth.py` — Google OAuth flow via authlib (login, callback, logout)
- `app/dependencies.py` — `get_current_user`, `require_login`, `require_admin`, flash message helpers

**Routes (all in `app/routes/`):**
- `pages.py` — Home, student dashboard
- `admin.py` — Admin: student management, event CRUD, participant management, attendance
- `events.py` — Event listing, detail, rating submission
- `profile.py` — Student profile with aggregated speaking scores

**Templates:** `app/templates/` using Jinja2 inheritance from `base.html`. Tailwind CSS via CDN.

## Domain Rules

- First user to register via Google OAuth is auto-promoted to admin
- Three event types: `speed_talk` (star rating 1-5), `long_speech` and `debate` (rated on clarity, confidence, body language, presentation skills, content — each 1-5, averaged)
- Students cannot rate themselves; one rating per rater per speaker per event
- Ratings only available after admin marks event as "completed"
- Profile scores are computed on-read via aggregation, not stored denormalized
