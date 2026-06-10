"""API layer: central place that wires the service routers.

This module binds the feature routers (auth so far) and the healthcheck into
one ``api_router``, which ``app.main`` includes. Later phases add their
routers here, so ``main`` stays a thin entry point.
"""

from fastapi import APIRouter

from app.auth.router import router as auth_router

api_router = APIRouter()
api_router.include_router(auth_router)


@api_router.get("/health")
def health() -> dict[str, str]:
    """Return service liveness status."""
    return {"status": "ok"}
