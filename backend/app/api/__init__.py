"""API layer: binds the feature routers and the healthcheck into one
``api_router`` that ``app.main`` includes, keeping ``main`` thin.
"""

from fastapi import APIRouter

from app.auth.router import router as auth_router
from app.content.router import router as content_router
from app.cv.router import router as cv_router
from app.github.router import router as github_router
from app.recruiter.router import router as recruiter_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(content_router)
api_router.include_router(cv_router)
api_router.include_router(github_router)
api_router.include_router(recruiter_router)


@api_router.get("/health")
def health() -> dict[str, str]:
    """Return service liveness status."""
    return {"status": "ok"}
