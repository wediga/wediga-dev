"""Helpers that drive the login through authentik in the tests.

The client uses an https base URL so the Secure session cookie round-trips,
and the session content is read straight from the signed cookie.
"""

import base64
import json
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from starlette.middleware.sessions import SessionMiddleware

from app.auth.csrf import CSRF_HEADER_NAME, CSRF_SESSION_KEY
from app.auth.sessions import SESSION_COOKIE_NAME
from tests.oidc.oidc_fake import make_id_token

ADMIN_PASSWORD = "correct horse battery staple"


def read_session(client: TestClient) -> dict:
    cookie = client.cookies.get(SESSION_COOKIE_NAME)

    if cookie is None:
        return {}

    # The app may have been imported by another test before SESSION_SECRET was
    # set, so the secret is taken from the middleware actually in use.
    middleware = next(
        m for m in client.app.user_middleware if m.cls is SessionMiddleware
    )
    signer = TimestampSigner(middleware.kwargs["secret_key"])

    return json.loads(base64.b64decode(signer.unsign(cookie)))


def start_login(client: TestClient, target: str | None = None) -> dict[str, str]:
    """Start a login and return the query authentik would receive."""
    params = {} if target is None else {"next": target}
    response = client.get("/auth/oidc/login", params=params, follow_redirects=False)
    assert response.status_code == 303
    query = parse_qs(urlsplit(response.headers["location"]).query)

    return {name: values[0] for name, values in query.items()}


def finish_login(client: TestClient, state: str, code: str = "the-code"):
    return client.get(
        "/auth/oidc/callback",
        params={"code": code, "state": state},
        follow_redirects=False,
    )


def log_in(client, fake, groups, target=None, **claims):
    """Run a whole login with the given groups and return the callback."""
    query = start_login(client, target)
    fake.id_token = make_id_token(
        **{"nonce": query["nonce"], "groups": groups, **claims}
    )

    return finish_login(client, query["state"])


def redeem_recruiter_link(app, client: TestClient) -> None:
    admin = TestClient(app, base_url="https://testserver")
    assert admin.post("/auth/login", json={"password": ADMIN_PASSWORD}).is_success
    admin.headers[CSRF_HEADER_NAME] = admin.get("/auth/csrf").json()["csrf_token"]
    token = admin.post("/recruiter/links", json={"label": "r"}).json()["token"]

    assert client.post(f"/recruiter/redeem/{token}").is_success


def log_out(client: TestClient):
    csrf = read_session(client).get(CSRF_SESSION_KEY, "")

    return client.post("/auth/oidc/logout", headers={CSRF_HEADER_NAME: csrf})
