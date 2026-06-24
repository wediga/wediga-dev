"""Shared 404 factory so the routers stay consistent on the detail shape."""

from fastapi import HTTPException, status


def not_found(detail: str = "Not found") -> HTTPException:
    """Build a 404 with a case-specific detail, defaulting to ``Not found``."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
