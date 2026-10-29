"""Protocol side of the login through authentik (OpenID Connect).

Builds the authorization URL, trades the code for tokens and validates the ID
token. The browser always talks to the public issuer. The backend's own calls
(discovery, token, keys) may go to ``OIDC_INTERNAL_URL`` instead, with the
public host in the ``Host`` header, so authentik still names itself after the
public issuer and the token checks below stay exact.

Every endpoint taken from the discovery document must live on the issuer's
origin, so a tampered document can neither send the browser elsewhere nor make
the backend post the client secret to a foreign host.
"""

from urllib.parse import urlsplit

import httpx2

# Typed through backend/typings, the module docstring there says why.
from authlib.integrations.httpx_client import OAuth2Client, OAuthError
from authlib.oauth2.client import DEFAULT_HEADERS
from authlib.oidc.core import CodeIDToken
from joserfc import jwt
from joserfc.errors import JoseError
from joserfc.jwk import KeySet, KeySetSerialization

from app.auth.oidc_settings import OidcSettings

SCOPE = "openid profile"
# authentik signs with the RSA key of its certificate. joserfc already refuses
# "none" and keys of the wrong type, the pin keeps it that way should its
# defaults ever widen.
ID_TOKEN_ALGORITHMS = ["RS256"]
# Allowed clock difference between authentik and the backend.
CLOCK_LEEWAY_SECONDS = 60
TIMEOUT = httpx2.Timeout(5.0)
DISCOVERY_PATH = ".well-known/openid-configuration"


class OidcProviderError(RuntimeError):
    """authentik could not be reached or answered something unusable."""


class OidcTokenError(RuntimeError):
    """The ID token failed validation."""


def _origin(url: str) -> tuple[str, str]:
    parts = urlsplit(url)

    return parts.scheme, parts.netloc


def _require_issuer_origin(settings: OidcSettings, url: object) -> str:
    if not isinstance(url, str) or _origin(url) != _origin(settings.issuer):
        raise OidcProviderError("endpoint is not on the issuer's origin")

    return url


def _server_side(settings: OidcSettings, url: str) -> tuple[str, dict[str, str]]:
    """Return the URL and headers the backend itself uses for ``url``."""

    if settings.internal_url is None:
        return url, {}

    scheme, netloc = _origin(settings.issuer)
    internal = urlsplit(settings.internal_url)
    parts = urlsplit(url)._replace(scheme=internal.scheme, netloc=internal.netloc)
    headers = {"Host": netloc, "X-Forwarded-Proto": scheme}

    return parts.geturl(), headers


def _get_json(settings: OidcSettings, url: str) -> dict:
    target, headers = _server_side(settings, url)

    try:
        response = httpx2.get(target, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except (httpx2.HTTPError, ValueError) as exc:
        raise OidcProviderError(f"request to authentik failed: {exc}") from exc

    if not isinstance(data, dict):
        raise OidcProviderError("authentik returned no JSON object")

    return data


def load_metadata(settings: OidcSettings) -> dict:
    """Fetch the discovery document and check it belongs to our issuer."""
    metadata = _get_json(settings, settings.issuer + DISCOVERY_PATH)

    if metadata.get("issuer") != settings.issuer:
        raise OidcProviderError("discovery document names a different issuer")

    for key in ("authorization_endpoint", "token_endpoint", "jwks_uri"):
        _require_issuer_origin(settings, metadata.get(key))

    return metadata


def _client(settings: OidcSettings) -> OAuth2Client:
    return OAuth2Client(
        client_id=settings.client_id,
        client_secret=settings.client_secret,
        scope=SCOPE,
        redirect_uri=settings.redirect_uri,
        code_challenge_method="S256",
        timeout=TIMEOUT,
    )


def authorization_url(
    settings: OidcSettings, metadata: dict, state: str, nonce: str, verifier: str
) -> str:
    """Return the authentik URL the browser is sent to, with PKCE (S256)."""

    with _client(settings) as client:
        url, _ = client.create_authorization_url(
            metadata["authorization_endpoint"],
            state=state,
            nonce=nonce,
            code_verifier=verifier,
        )

    return url


def end_session_url(settings: OidcSettings, metadata: dict) -> str:
    """Return the authentik URL that ends the session there as well."""

    return _require_issuer_origin(settings, metadata.get("end_session_endpoint"))


def exchange_code(
    settings: OidcSettings, metadata: dict, code: str, verifier: str
) -> dict:
    """Trade the authorization code for tokens at authentik's token endpoint."""
    target, headers = _server_side(settings, metadata["token_endpoint"])

    try:
        with _client(settings) as client:
            token = client.fetch_token(
                target,
                grant_type="authorization_code",
                code=code,
                code_verifier=verifier,
                headers={**DEFAULT_HEADERS, **headers},
            )
    except (httpx2.HTTPError, OAuthError, ValueError) as exc:
        raise OidcProviderError(f"token exchange failed: {exc}") from exc

    if not isinstance(token.get("id_token"), str):
        raise OidcProviderError("token response carries no ID token")

    return token


def validate_id_token(
    settings: OidcSettings, metadata: dict, token: dict, nonce: str
) -> dict:
    """Check signature, issuer, audience, lifetime and nonce of the ID token
    and return its claims."""
    jwks = _get_json(settings, metadata["jwks_uri"])

    try:
        decoded = jwt.decode(
            token["id_token"],
            KeySet.import_key_set(KeySetSerialization(keys=jwks["keys"])),
            algorithms=ID_TOKEN_ALGORITHMS,
        )
        # Without the audience listed here, Authlib would accept a token for
        # another client as long as its "azp" names ours.
        claims = CodeIDToken(
            decoded.claims,
            decoded.header,
            {
                "iss": {"essential": True, "value": settings.issuer},
                "aud": {"essential": True, "value": settings.client_id},
            },
            {
                "nonce": nonce,
                "client_id": settings.client_id,
                "access_token": token.get("access_token"),
            },
        )
        claims.validate(leeway=CLOCK_LEEWAY_SECONDS)
    except (JoseError, ValueError, KeyError, TypeError) as exc:
        raise OidcTokenError(f"ID token rejected: {exc}") from exc

    return dict(claims)
