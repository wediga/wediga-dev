"""Asks authentik which applications an account may use.

The backend asks with the hub's service account, whose only right is this
question, and authentik answers from its own bindings. The request takes the
same way to authentik as the login. Only what the hub shows leaves this
module: wediga.dev's own application is left out, and every address must be
an https URL, so no link can run script or point anywhere but a web page.
"""

from typing import TypedDict
from urllib.parse import urljoin, urlsplit

import httpx2

from app.auth.oidc import server_side
from app.auth.oidc_settings import OidcSettings

APPLICATIONS_PATH = "/api/v3/core/applications/"
# authentik's largest page. The hub shows no more entries than this.
PAGE_SIZE = 100
TIMEOUT = httpx2.Timeout(5.0)
# The slug of wediga.dev's own application in the blueprint.
OWN_APPLICATION = "wediga-dev"


class HubApplication(TypedDict):
    name: str
    url: str
    icon: str | None
    description: str
    group: str


class HubUnavailableError(RuntimeError):
    """authentik could not be asked or answered something unusable."""


def _https_url(value: object) -> str | None:
    """Return ``value`` as an https URL with a host, otherwise ``None``."""
    if not isinstance(value, str):
        return None

    try:
        parts = urlsplit(value)
        host = parts.hostname
    except ValueError:
        # Not parseable as a URL, so not a safe link either.
        return None

    if parts.scheme != "https" or not host:
        return None

    return parts.geturl()


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def _entry(raw: object) -> HubApplication | None:
    """Map one application from authentik, ``None`` for one the hub skips."""
    if not isinstance(raw, dict) or raw.get("slug") == OWN_APPLICATION:
        return None

    name = raw.get("name")
    url = _https_url(raw.get("launch_url"))

    if not isinstance(name, str) or url is None:
        return None

    return HubApplication(
        name=name,
        url=url,
        icon=_https_url(raw.get("meta_icon")),
        description=_text(raw.get("meta_description")),
        group=_text(raw.get("group")),
    )


def applications_for(settings: OidcSettings, user_id: int) -> list[HubApplication]:
    """Return the applications authentik lets the account ``user_id`` use."""
    target, headers = server_side(settings, urljoin(settings.issuer, APPLICATIONS_PATH))

    try:
        response = httpx2.get(
            target,
            params={"for_user": user_id, "page_size": PAGE_SIZE},
            headers={**headers, "Authorization": f"Bearer {settings.api_token}"},
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        results = response.json()["results"]
    except (httpx2.HTTPError, ValueError, KeyError, TypeError) as exc:
        raise HubUnavailableError(f"asking authentik failed: {exc}") from exc

    if not isinstance(results, list):
        raise HubUnavailableError("authentik returned no list of applications")

    return [entry for entry in map(_entry, results) if entry is not None]
