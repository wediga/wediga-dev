"""FastAPI application entry point.

Wires the session middleware and API router and runs the admin bootstrap on
startup. Migrations never run in the request path, only via
``python -m app.db.migrate``.
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api import api_router
from app.auth.bootstrap import ensure_admin
from app.auth.oidc_settings import load_oidc_settings
from app.auth.sessions import add_session_middleware
from app.github.scheduler import start_scheduler

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Check the login settings, bootstrap the admin and start the GitHub
    refresh. Only broken login settings block the start."""
    # Raises on a half configured login, so the backend does not start at all
    # rather than serve with a login that fails or runs downgraded.
    app.state.oidc = load_oidc_settings()

    try:
        ensure_admin()
    except Exception:
        # A missing schema must not block startup. The login fails until the
        # bootstrap succeeds on a later start, and the log says why.
        logger.warning("admin bootstrap failed, login will not work", exc_info=True)

    sync_task = start_scheduler()
    try:
        yield
    finally:
        if sync_task is not None:
            sync_task.cancel()
            with suppress(asyncio.CancelledError):
                await sync_task


# The interactive API docs are off by default, so the schema and the auth
# endpoints are not exposed. The backend has no host port and is reached only
# through the BFF, so this is defence in depth; set ENABLE_DOCS=true locally to
# bring /docs, /redoc and /openapi.json back for development.
_docs_enabled = os.environ.get("ENABLE_DOCS", "").lower() == "true"

app = FastAPI(
    title="wediga-backend",
    lifespan=lifespan,
    docs_url="/docs" if _docs_enabled else None,
    redoc_url="/redoc" if _docs_enabled else None,
    openapi_url="/openapi.json" if _docs_enabled else None,
)

add_session_middleware(app)
app.include_router(api_router)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(
    request: Request, exc: IntegrityError
) -> JSONResponse:
    """Turn a constraint violation (e.g. a duplicate name) into a 409 instead
    of an unhandled 500. The exception detail is not echoed back."""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Resource already exists or violates a constraint"},
    )
