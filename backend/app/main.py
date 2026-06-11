"""FastAPI application entry point.

Wires up the session middleware and the API router (which carries the auth
routes and the healthcheck) and runs the admin bootstrap on startup.
Migrations are never run in the request path; they are applied via
``python -m app.db.migrate``.
"""

import asyncio
import sqlite3
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api import api_router
from app.auth.bootstrap import ensure_admin
from app.auth.sessions import add_session_middleware
from app.github.scheduler import start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Bootstrap the admin and start the GitHub refresh, neither blocking start."""
    try:
        ensure_admin()
    except Exception:
        # A missing schema or unset password must not block startup; the
        # login route fails cleanly in that case.
        pass
    # The scheduler is a fire-and-forget background task: creating it returns at
    # once, so the first sync runs concurrently and never blocks the start.
    sync_task = start_scheduler()
    try:
        yield
    finally:
        if sync_task is not None:
            sync_task.cancel()
            with suppress(asyncio.CancelledError):
                await sync_task


app = FastAPI(title="wediga-backend", lifespan=lifespan)

add_session_middleware(app)
app.include_router(api_router)


@app.exception_handler(sqlite3.IntegrityError)
async def integrity_error_handler(
    request: Request, exc: sqlite3.IntegrityError
) -> JSONResponse:
    """Turn a constraint violation (e.g. a duplicate name) into a clean 409.

    Without this a unique-constraint hit would surface as an unhandled 500.
    The exception detail is not echoed back, so no internal data leaks.
    """
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Resource already exists or violates a constraint"},
    )
