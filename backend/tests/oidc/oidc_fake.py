"""A stand-in for authentik in the login and hub tests.

Signs real RS256 ID tokens with a key generated for the test run and answers
the backend's discovery, key and token requests, and the hub's question for
applications. Requests must arrive on the
internal URL with the public host in the ``Host`` header, so every test also
checks that the backend never talks to the public address itself.
"""

import time

import httpx2
from joserfc import jwt
from joserfc.jwk import Key, RSAKey

from app.auth import oidc
from app.auth.oidc_settings import OidcSettings

ISSUER = "https://auth.example/application/o/wediga-dev/"
PUBLIC_HOST = "auth.example"
INTERNAL_URL = "http://authentik-server:9000"
CLIENT_ID = "wediga-dev"
# authentik sends the account's numeric ID as "sub".
ACCOUNT_ID = "21"
KEY_ID = "test-key"
API_TOKEN = "test-api-token"
APPLICATIONS_URL = "https://auth.example/api/v3/core/applications/"
TOKEN_LIFETIME_SECONDS = 300

SETTINGS = OidcSettings(
    issuer=ISSUER,
    client_id=CLIENT_ID,
    client_secret="test-client-secret",
    redirect_uri="https://www.example/auth/callback",
    internal_url=INTERNAL_URL,
    api_token=API_TOKEN,
)

METADATA = {
    "issuer": ISSUER,
    "authorization_endpoint": "https://auth.example/application/o/authorize/",
    "token_endpoint": "https://auth.example/application/o/token/",
    "jwks_uri": ISSUER + "jwks/",
    "end_session_endpoint": ISSUER + "end-session/",
}

SIGNING_KEY = RSAKey.generate_key(2048, parameters={"kid": KEY_ID})


def internal(url: str) -> str:
    return url.replace("https://auth.example", INTERNAL_URL)


def make_id_token(key: Key = SIGNING_KEY, alg: str = "RS256", **claims) -> str:
    """Return a signed ID token. ``claims`` (always with the ``nonce``) override
    or, with ``None``, remove the defaults."""
    now = int(time.time())
    payload = {
        "iss": ISSUER,
        "sub": ACCOUNT_ID,
        "aud": CLIENT_ID,
        "exp": now + TOKEN_LIFETIME_SECONDS,
        "iat": now,
        "groups": [],
    }
    payload.update(claims)
    payload = {name: value for name, value in payload.items() if value is not None}

    return jwt.encode({"alg": alg, "kid": KEY_ID}, payload, key)


class FakeAuthentik:
    """Answers the backend's requests and records them."""

    def __init__(self, monkeypatch, settings: OidcSettings = SETTINGS) -> None:
        self.settings = settings
        self.metadata = dict(METADATA)
        self.id_token: str | None = None
        self.token_error: Exception | None = None
        self.unreachable = False
        # The body and status of the hub's question for applications.
        self.applications: object = {"results": []}
        self.applications_status = 200
        self.application_calls: list[dict] = []
        self.get_calls: list[tuple[str, dict]] = []
        self.token_calls: list[tuple[str, dict]] = []
        monkeypatch.setattr(oidc.httpx2, "get", self._get)
        monkeypatch.setattr(oidc.OAuth2Client, "fetch_token", self._fetch_token)

    def _expected_url(self, url: str) -> str:
        return internal(url) if self.settings.internal_url else url

    def _check_headers(self, headers: dict) -> None:
        if self.settings.internal_url:
            assert headers["Host"] == PUBLIC_HOST
            assert headers["X-Forwarded-Proto"] == "https"
        else:
            assert "Host" not in headers

    def _get(
        self, url: str, headers: dict, timeout, params: dict | None = None
    ) -> httpx2.Response:
        self.get_calls.append((url, headers))
        self._check_headers(headers)
        request = httpx2.Request("GET", url)

        if self.unreachable:
            raise httpx2.ConnectError("unreachable", request=request)

        if url == self._expected_url(APPLICATIONS_URL):
            assert headers["Authorization"] == f"Bearer {API_TOKEN}"
            self.application_calls.append(params or {})

            return httpx2.Response(
                self.applications_status, json=self.applications, request=request
            )

        if url == self._expected_url(ISSUER + oidc.DISCOVERY_PATH):
            return httpx2.Response(200, json=self.metadata, request=request)

        if url == self._expected_url(METADATA["jwks_uri"]):
            keys = {"keys": [SIGNING_KEY.as_dict(private=False)]}

            return httpx2.Response(200, json=keys, request=request)

        return httpx2.Response(404, request=request)

    def _fetch_token(self, url: str, **kwargs) -> dict:
        self.token_calls.append((url, kwargs))
        assert url == self._expected_url(METADATA["token_endpoint"])
        self._check_headers(kwargs["headers"])

        if self.token_error is not None:
            raise self.token_error

        return {"access_token": "access", "id_token": self.id_token}
