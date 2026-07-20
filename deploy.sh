#!/usr/bin/env bash
set -euo pipefail

ENV="${1:-}"

usage() {
    echo "Usage: ./deploy.sh <local|prod>"
    echo ""
    echo "  local  - Run locally with mock AI (no Gemini API key needed)"
    echo "  prod   - Run in production with real Gemini AI analysis"
    exit 1
}

if [ -z "$ENV" ]; then
    usage
fi

# Ensure we're in the project root
cd "$(dirname "$0")"

setup_venv() {
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv .venv
    fi
    source .venv/bin/activate
    pip install -q -r requirements.txt
}

run_migrations() {
    echo "Running database migrations..."
    alembic upgrade head
}

case "$ENV" in
    local)
        echo "=== Starting in LOCAL mode (mock AI) ==="
        setup_venv
        run_migrations

        export MOCK_AI=true
        # Use defaults for OAuth if not set — login will fail but the rest of the app works
        export GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-placeholder}"
        export GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-placeholder}"
        export SECRET_KEY="${SECRET_KEY:-local-dev-secret}"

        echo ""
        echo "Mock AI is ON — video uploads return fake scores"
        echo "App running at http://127.0.0.1:8000"
        echo ""
        python run.py
        ;;

    prod)
        echo "=== Starting in PRODUCTION mode ==="

        # Validate required env vars
        missing=""
        for var in GOOGLE_CLIENT_ID GOOGLE_CLIENT_SECRET SECRET_KEY GEMINI_API_KEY; do
            if [ -z "${!var:-}" ]; then
                missing="$missing $var"
            fi
        done
        if [ -n "$missing" ]; then
            echo "ERROR: Missing required environment variables:$missing"
            echo "Set them in .env or export them before running."
            exit 1
        fi

        setup_venv
        run_migrations

        export MOCK_AI=false

        echo ""
        echo "Gemini AI is LIVE — real video analysis enabled"
        echo "App running at http://0.0.0.0:8000"
        echo ""
        uvicorn app.main:app --host 0.0.0.0 --port 8000
        ;;

    *)
        usage
        ;;
esac
