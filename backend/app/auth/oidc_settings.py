"""Settings for the login through authentik, read from the environment.

The login is off unless ``OIDC_ENABLED`` is ``true``. When it is on, every
required value must be set and the addresses the browser sees must use https,
so the backend refuses to start with a half configured or downgraded login
instead of failing on the first visitor. Error messages name the variable and
never echo its value, so neither the client secret nor the API token can end
up in a log.
"""

import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit

ENABLED_VAR = "OIDC_ENABLED"
ISSUER_VAR = "OIDC_ISSUER"
CLIENT_ID_VAR = "OIDC_CLIENT_ID"
CLIENT_SECRET_VAR = "OIDC_CLIENT_SECRET"
REDIRECT_URI_VAR = "OIDC_REDIRECT_URI"
# The token of the service account the hub asks authentik with.
API_TOKEN_VAR = "AUTHENTIK_API_TOKEN"
# Optional. In production the backend reaches authentik over the internal
# container network instead of going out and back in through Caddy.
INTERNAL_URL_VAR = "OIDC_INTERNAL_URL"

REQUIRED_VARS = (
    ISSUER_VAR,
    CLIENT_ID_VAR,
    CLIENT_SECRET_VAR,
    REDIRECT_URI_VAR,
    API_TOKEN_VAR,
)

# Plain http is only accepted for a public address on the developer's own
# machine, where the test authentik and the frontend run without TLS.
LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1"})


class OidcConfigError(RuntimeError):
    """Raised when the login is switched on but its settings are incomplete or
    unsafe."""


@dataclass(frozen=True)
class OidcSettings:
    issuer: str
    client_id: str
    # Kept out of the repr, so printing the settings never shows the secrets.
    client_secret: str = field(repr=False)
    redirect_uri: str
    internal_url: str | None
    api_token: str = field(repr=False)


def _env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _check_public_url(name: str, value: str) -> None:
    """Accept https, and http only for a local development host."""
    parts = urlsplit(value)
    if parts.scheme == "https" and parts.hostname:
        return

    if parts.scheme == "http" and parts.hostname in LOCAL_HOSTS:
        return

    raise OidcConfigError(f"{name} must be an https URL (http only for localhost)")


def _check_internal_url(value: str) -> None:
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise OidcConfigError(f"{INTERNAL_URL_VAR} must be an http or https URL")


def load_oidc_settings() -> OidcSettings | None:
    """Return the login settings, ``None`` when the login is off.

    Raises :class:`OidcConfigError` when the login is on and a value is
    missing or not allowed.
    """
    if _env(ENABLED_VAR).lower() != "true":
        return None

    missing = [name for name in REQUIRED_VARS if not _env(name)]
    if missing:
        raise OidcConfigError(
            f"{ENABLED_VAR} is true but these are not set: {', '.join(missing)}"
        )

    _check_public_url(ISSUER_VAR, _env(ISSUER_VAR))
    _check_public_url(REDIRECT_URI_VAR, _env(REDIRECT_URI_VAR))
    internal_url = _env(INTERNAL_URL_VAR) or None

    if internal_url is not None:
        _check_internal_url(internal_url)

    return OidcSettings(
        issuer=_env(ISSUER_VAR),
        client_id=_env(CLIENT_ID_VAR),
        client_secret=_env(CLIENT_SECRET_VAR),
        redirect_uri=_env(REDIRECT_URI_VAR),
        internal_url=internal_url,
        api_token=_env(API_TOKEN_VAR),
    )
