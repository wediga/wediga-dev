"""Shared HTTP error construction.

A single factory builds every 404 so the routers stay consistent, while each
caller keeps its own case-specific detail text.
"""

from fastapi import HTTPException, status


def not_found(detail: str = "Not found") -> HTTPException:
    """Build a 404 with a case-specific detail, defaulting to ``Not found``."""
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
