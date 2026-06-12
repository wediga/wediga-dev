#!/usr/bin/env bash
# Start the backend for the end-to-end tests against a throwaway database and a
# synthetic content directory. The real data/ and content/ are never touched;
# both are overridden by WEDIGA_DB_PATH and WEDIGA_CONTENT_DIR, which the
# Playwright config points at a temporary path. Migrate and seed run first, so
# the backend only starts answering once the data is in place.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKEND_DIR="$REPO_ROOT/backend"

: "${WEDIGA_DB_PATH:?WEDIGA_DB_PATH must be set}"
: "${WEDIGA_CONTENT_DIR:?WEDIGA_CONTENT_DIR must be set}"
: "${BACKEND_PORT:?BACKEND_PORT must be set}"

# Rebuild the fixture content and database from scratch on every run, so the
# data state is identical each time and nothing leaks between runs. The CV is an
# uploaded PDF kept under data/, so no CV content fixture is needed; the test
# uploads its own PDF.
rm -rf "$WEDIGA_CONTENT_DIR" "$(dirname "$WEDIGA_DB_PATH")"
mkdir -p "$WEDIGA_CONTENT_DIR" "$(dirname "$WEDIGA_DB_PATH")"

# Base content from the committed synthetic example, never from the private
# content/ directory.
cp "$REPO_ROOT"/content.example/*.md "$WEDIGA_CONTENT_DIR"/
cp "$REPO_ROOT"/content.example/*.json "$WEDIGA_CONTENT_DIR"/

cd "$BACKEND_DIR"
uv run python -m app.db.migrate
uv run python -m app.db.seed
exec uv run uvicorn app.main:app --host 127.0.0.1 --port "$BACKEND_PORT"
