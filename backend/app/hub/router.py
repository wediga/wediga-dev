"""Route of the hub: the applications the visitor may use.

Answers 404 while the login through authentik is off, like its routes. The
answer from authentik is kept for a minute per account, so reloading the hub
does not ask authentik every time and a changed binding still shows within a
minute. A failed question is not kept.
"""

import logging
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth.dependencies import require_hub
from app.auth.oidc_router import Settings, require_oidc
from app.hub import authentik
from app.hub.authentik import HubApplication

logger = logging.getLogger("uvicorn.error")

CACHE_SECONDS = 60

# Account ID to the time of the answer and the answer.
_cache: dict[int, tuple[float, list[HubApplication]]] = {}

router = APIRouter(prefix="/hub", tags=["hub"], dependencies=[Depends(require_oidc)])


class HubApplicationRead(BaseModel):
    name: str
    url: str
    icon: str | None
    description: str
    group: str


@router.get("/applications", response_model=list[HubApplicationRead])
def list_applications(
    settings: Settings, user_id: Annotated[int, Depends(require_hub)]
) -> list[HubApplication]:
    """Return the applications authentik lets the visitor use."""
    now = time.monotonic()
    cached = _cache.get(user_id)

    if cached is not None and now - cached[0] < CACHE_SECONDS:
        return cached[1]

    try:
        applications = authentik.applications_for(settings, user_id)
    except authentik.HubUnavailableError:
        logger.warning("asking authentik for the hub failed", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Hub unavailable",
        ) from None

    _cache[user_id] = (now, applications)

    return applications
