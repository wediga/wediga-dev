"""Tests for the routes of the login through authentik.

authentik is replaced by the fake from ``oidc_fake``, which signs real ID
tokens. The client uses an https base URL so the Secure session cookie
round-trips, and the session content is read straight from the signed cookie.
"""

import base64
import importlib
import json
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from starlette.middleware.sessions import SessionMiddleware

from app.auth import oidc_router
from app.auth.csrf import CSRF_HEADER_NAME, CSRF_SESSION_KEY
from app.auth.sessions import (
    ADMIN_SESSION_KEY,
    OIDC_FLOW_SESSION_KEY,
    OIDC_SESSION_KEY,
    RECRUITER_SESSION_KEY,
    SESSION_COOKIE_NAME,
)
from tests.oidc_fake import METADATA, SETTINGS, FakeAuthentik, make_id_token

ADMIN_PASSWORD = "correct horse battery staple"
BLUEPRINT = (
    Path(__file__).resolve().parents[2] / "deploy/authentik/blueprints/wediga.yaml"
)


@pytest.fixture()
def app(migrated_db, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")

    from app.auth.bootstrap import ensure_admin

    ensure_admin()
    main = importlib.import_module("app.main")
    monkeypatch.setattr(main.app.state, "oidc", SETTINGS, raising=False)

    return main.app


@pytest.fixture()
def client(app) -> TestClient:
    return TestClient(app, base_url="https://testserver")


@pytest.fixture()
def fake(monkeypatch) -> FakeAuthentik:
    return FakeAuthentik(monkeypatch)


def _session(client: TestClient) -> dict:
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


def _start(client: TestClient, target: str | None = None) -> dict[str, str]:
    """Start a login and return the query authentik would receive."""
    params = {} if target is None else {"next": target}
    response = client.get("/auth/oidc/login", params=params, follow_redirects=False)
    assert response.status_code == 303
    query = parse_qs(urlsplit(response.headers["location"]).query)

    return {name: values[0] for name, values in query.items()}


def _callback(client: TestClient, state: str, code: str = "the-code"):
    return client.get(
        "/auth/oidc/callback",
        params={"code": code, "state": state},
        follow_redirects=False,
    )


def _login(client, fake, groups, target=None, **claims):
    """Run a whole login with the given groups and return the callback."""
    query = _start(client, target)
    fake.id_token = make_id_token(
        **{"nonce": query["nonce"], "groups": groups, **claims}
    )

    return _callback(client, query["state"])


# --- switched off ------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/auth/oidc/login"),
        ("GET", "/auth/oidc/callback"),
        ("POST", "/auth/oidc/logout"),
    ],
)
def test_routes_do_not_answer_while_switched_off(
    app, client, monkeypatch, method, path
) -> None:
    monkeypatch.setattr(app.state, "oidc", None)

    assert client.request(method, path).status_code == 404


# --- start -------------------------------------------------------------------


@pytest.mark.usefixtures("fake")
def test_start_sends_the_browser_to_authentik_with_pkce(client) -> None:
    response = client.get("/auth/oidc/login", follow_redirects=False)

    location = response.headers["location"]
    assert location.startswith(METADATA["authorization_endpoint"])
    query = parse_qs(urlsplit(location).query)
    flow = _session(client)[OIDC_FLOW_SESSION_KEY]
    assert query["state"] == [flow["state"]]
    assert query["nonce"] == [flow["nonce"]]
    assert query["code_challenge"] == [create_s256_code_challenge(flow["verifier"])]
    assert flow["verifier"] not in location


@pytest.mark.usefixtures("fake")
def test_every_start_gets_new_random_values(client) -> None:
    first = _start(client)
    second = _start(client)

    assert first["state"] != second["state"]
    assert first["nonce"] != second["nonce"]
    assert first["code_challenge"] != second["code_challenge"]


def test_start_answers_502_when_authentik_is_down(client, fake) -> None:
    fake.unreachable = True

    assert client.get("/auth/oidc/login").status_code == 502


# --- callback ----------------------------------------------------------------


def test_admin_lands_in_admin_with_both_roles(client, fake) -> None:
    response = _login(client, fake, ["wediga-admins"])

    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    session = _session(client)
    assert session[OIDC_SESSION_KEY]["roles"] == ["admin", "hub"]
    assert abs(session[OIDC_SESSION_KEY]["login_at"] - time.time()) < 5
    assert OIDC_FLOW_SESSION_KEY not in session
    assert session[CSRF_SESSION_KEY]


def test_friend_lands_in_hub_without_admin_role(client, fake) -> None:
    response = _login(client, fake, ["friends"])

    assert response.headers["location"] == "/hub"
    assert _session(client)[OIDC_SESSION_KEY]["roles"] == ["hub"]


@pytest.mark.parametrize("groups", [[], ["valheim"], "wediga-admins", None, [1]])
def test_account_without_matching_group_gets_no_session(client, fake, groups) -> None:
    response = _login(client, fake, groups)

    assert response.headers["location"] == "/no-access"
    assert OIDC_SESSION_KEY not in _session(client)


def test_session_holds_no_token_from_authentik(client, fake) -> None:
    _login(client, fake, ["friends"])

    cookie = json.dumps(_session(client))
    assert fake.id_token not in cookie
    assert "access" not in _session(client)[OIDC_SESSION_KEY]


def test_safe_target_is_kept(client, fake) -> None:
    response = _login(client, fake, ["friends"], target="/hub/games?sort=name")

    assert response.headers["location"] == "/hub/games?sort=name"


@pytest.mark.parametrize(
    "target",
    [
        "//evil.example",
        "https://evil.example/",
        "/\\evil.example",
        "/\\/evil.example",
        "/ //evil.example",
        "/\t/evil.example",
        "javascript:alert(1)",
        "/admin#x",
        "admin",
        "",
        "/" + "a" * oidc_router.MAX_TARGET_LENGTH,
    ],
)
def test_target_outside_the_site_falls_back_to_home(client, fake, target) -> None:
    response = _login(client, fake, ["wediga-admins"], target=target)

    assert response.headers["location"] == "/admin"


def test_wrong_state_is_refused_and_ends_the_flow(client, fake) -> None:
    query = _start(client)
    fake.id_token = make_id_token(nonce=query["nonce"], groups=["friends"])

    assert _callback(client, "wrong-state").status_code == 400
    assert _callback(client, query["state"]).status_code == 400
    assert OIDC_SESSION_KEY not in _session(client)


def test_state_works_only_once(client, fake) -> None:
    query = _start(client)
    fake.id_token = make_id_token(nonce=query["nonce"], groups=["friends"])

    assert _callback(client, query["state"]).status_code == 303
    assert _callback(client, query["state"]).status_code == 400


@pytest.mark.usefixtures("fake")
def test_callback_without_started_login_is_refused(client) -> None:
    assert _callback(client, "any-state").status_code == 400


@pytest.mark.usefixtures("fake")
def test_callback_without_code_is_refused(client) -> None:
    query = _start(client)

    assert _callback(client, query["state"], code="").status_code == 400


def test_flow_older_than_the_limit_is_refused(client, fake, monkeypatch) -> None:
    query = _start(client)
    later = time.time() + oidc_router.FLOW_MAX_AGE_SECONDS + 1
    # The token itself is still valid then, so only the age of the flow counts.
    fake.id_token = make_id_token(
        nonce=query["nonce"], groups=["friends"], exp=int(later) + 300
    )
    monkeypatch.setattr(oidc_router.time, "time", lambda: later)

    assert _callback(client, query["state"]).status_code == 400


@pytest.mark.parametrize(
    "claims",
    [
        {"nonce": "other-nonce"},
        {"iss": "https://evil.example/"},
        {"aud": "other-client"},
        {"exp": 1},
    ],
)
def test_invalid_id_token_is_refused(client, fake, claims) -> None:
    response = _login(client, fake, ["wediga-admins"], **claims)

    assert response.status_code == 400
    assert OIDC_SESSION_KEY not in _session(client)


def test_nonce_of_another_login_is_refused(client, fake) -> None:
    """A token captured from one login cannot finish another one."""
    first = _start(client)
    second = _start(client)
    fake.id_token = make_id_token(nonce=first["nonce"], groups=["wediga-admins"])

    assert _callback(client, second["state"]).status_code == 400


def test_failed_token_exchange_answers_502(client, fake) -> None:
    query = _start(client)
    fake.token_error = oidc_router.oidc.OidcProviderError("down")

    assert _callback(client, query["state"]).status_code == 502
    assert OIDC_SESSION_KEY not in _session(client)


def test_login_drops_the_old_admin_marker_and_csrf_token(client, fake) -> None:
    assert client.post("/auth/login", json={"password": ADMIN_PASSWORD}).is_success
    old_csrf = client.get("/auth/csrf").json()["csrf_token"]

    _login(client, fake, ["friends"])

    session = _session(client)
    assert ADMIN_SESSION_KEY not in session
    assert session[CSRF_SESSION_KEY] != old_csrf
    assert client.get("/auth/me").status_code == 401


def test_failed_login_also_ends_an_earlier_one(client, fake) -> None:
    _login(client, fake, ["wediga-admins"])

    _login(client, fake, [])

    assert OIDC_SESSION_KEY not in _session(client)


# --- logout ------------------------------------------------------------------


def _redeem_recruiter_link(app, client: TestClient) -> None:
    admin = TestClient(app, base_url="https://testserver")
    assert admin.post("/auth/login", json={"password": ADMIN_PASSWORD}).is_success
    admin.headers[CSRF_HEADER_NAME] = admin.get("/auth/csrf").json()["csrf_token"]
    token = admin.post("/recruiter/links", json={"label": "r"}).json()["token"]

    assert client.post(f"/recruiter/redeem/{token}").is_success


def _logout(client: TestClient):
    csrf = _session(client).get(CSRF_SESSION_KEY, "")

    return client.post("/auth/oidc/logout", headers={CSRF_HEADER_NAME: csrf})


def test_logout_needs_the_csrf_token(client, fake) -> None:
    _login(client, fake, ["friends"])

    assert client.post("/auth/oidc/logout").status_code == 403
    assert OIDC_SESSION_KEY in _session(client)


def test_logout_ends_the_login_and_points_to_authentik(client, fake) -> None:
    _login(client, fake, ["wediga-admins"])

    response = _logout(client)

    assert response.json() == {"redirect": METADATA["end_session_endpoint"]}
    session = _session(client)
    assert OIDC_SESSION_KEY not in session
    assert CSRF_SESSION_KEY not in session


def test_logout_keeps_the_recruiter_session(app, client, fake) -> None:
    _redeem_recruiter_link(app, client)
    _login(client, fake, ["friends"])

    assert _logout(client).is_success

    assert RECRUITER_SESSION_KEY in _session(client)
    assert client.get("/recruiter/session").status_code == 200


def test_login_keeps_the_recruiter_session(app, client, fake) -> None:
    _redeem_recruiter_link(app, client)

    _login(client, fake, ["friends"])

    assert client.get("/recruiter/session").status_code == 200


def test_logout_still_works_when_authentik_is_down(client, fake) -> None:
    _login(client, fake, ["friends"])
    fake.unreachable = True

    response = _logout(client)

    assert response.json() == {"redirect": "/"}
    assert OIDC_SESSION_KEY not in _session(client)


# --- groups ------------------------------------------------------------------


@pytest.mark.parametrize("group", oidc_router.GROUP_ROLES)
def test_mapped_groups_exist_in_the_blueprint(group) -> None:
    """The group names live in the blueprint and here, so they must match."""
    assert f"name: {group}\n" in BLUEPRINT.read_text(encoding="utf-8")
