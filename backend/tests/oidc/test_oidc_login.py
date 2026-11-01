"""Tests for the routes of the login through authentik.

authentik is replaced by the fake from ``oidc_fake``, which signs real ID
tokens.
"""

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from authlib.oauth2.rfc7636 import create_s256_code_challenge

from app.auth import oidc_router, sessions
from app.auth.models import AuthentikLogin, LegacyAdminLogin, LoginFlow
from app.auth.sessions import SESSION_COOKIE_NAME
from app.recruiter.models import RecruiterAccess
from tests.oidc.login import (
    ADMIN_PASSWORD,
    age,
    finish_login,
    log_in,
    log_out,
    read_session,
    redeem_recruiter_link,
    start_login,
)
from tests.oidc.oidc_fake import ACCOUNT_ID, METADATA, NAME, make_id_token

LOGIN = AuthentikLogin.__tablename__
FLOW = LoginFlow.__tablename__
LEGACY = LegacyAdminLogin.__tablename__
RECRUITER = RecruiterAccess.__tablename__

BLUEPRINT = (
    Path(__file__).resolve().parents[3] / "deploy/authentik/blueprints/wediga.yaml"
)


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


def test_status_tells_whether_the_login_is_switched_on(client) -> None:
    response = client.get("/auth/oidc/status")

    assert response.status_code == 200
    assert response.json() == {"enabled": True}


def test_status_answers_while_switched_off(app, client, monkeypatch) -> None:
    monkeypatch.setattr(app.state, "oidc", None)

    assert client.get("/auth/oidc/status").json() == {"enabled": False}


# --- start -------------------------------------------------------------------


@pytest.mark.usefixtures("fake")
def test_start_sends_the_browser_to_authentik_with_pkce(client) -> None:
    response = client.get("/auth/oidc/login", follow_redirects=False)

    location = response.headers["location"]
    assert location.startswith(METADATA["authorization_endpoint"])
    query = parse_qs(urlsplit(location).query)
    flow = read_session(client)[FLOW]
    assert query["state"] == [flow["state"]]
    assert query["nonce"] == [flow["nonce"]]
    assert query["code_challenge"] == [create_s256_code_challenge(flow["verifier"])]
    assert flow["verifier"] not in location


@pytest.mark.usefixtures("fake")
def test_every_start_gets_new_random_values(client) -> None:
    first = start_login(client)
    second = start_login(client)

    assert first["state"] != second["state"]
    assert first["nonce"] != second["nonce"]
    assert first["code_challenge"] != second["code_challenge"]


def test_start_answers_502_when_authentik_is_down(client, fake) -> None:
    fake.unreachable = True

    assert client.get("/auth/oidc/login").status_code == 502


# --- callback ----------------------------------------------------------------


def test_admin_lands_in_admin_with_both_roles(client, fake) -> None:
    response = log_in(client, fake, ["wediga-admins"])

    assert response.status_code == 303
    assert response.headers["location"] == "/admin"
    session = read_session(client)
    login = session[LOGIN]
    assert login["account"]["authentik_user_id"] == int(ACCOUNT_ID)
    assert login["account"]["name"] == NAME
    assert login["roles"] == ["admin", "hub"]
    assert abs((datetime.now(UTC) - login["logged_in_at"]).total_seconds()) < 5
    assert FLOW not in session
    assert session["csrf_token"]


def test_friend_lands_in_hub_without_admin_role(client, fake) -> None:
    response = log_in(client, fake, ["friends"])

    assert response.headers["location"] == "/hub"
    assert read_session(client)[LOGIN]["roles"] == ["hub"]


@pytest.mark.parametrize("groups", [[], ["valheim"], "wediga-admins", None, [1]])
def test_account_without_matching_group_gets_no_session(client, fake, groups) -> None:
    response = log_in(client, fake, groups)

    assert response.headers["location"] == "/no-access"
    assert LOGIN not in read_session(client)


def test_session_holds_no_token_from_authentik(client, fake) -> None:
    log_in(client, fake, ["friends"])

    assert fake.id_token not in str(read_session(client))


def test_account_keeps_the_name_of_the_last_login(client, fake) -> None:
    log_in(client, fake, ["friends"])
    first = read_session(client)[LOGIN]["account"]

    log_in(client, fake, ["friends"], name="New Name")

    account = read_session(client)[LOGIN]["account"]
    assert account["id"] == first["id"]
    assert account["name"] == "New Name"
    assert account["first_login_at"] == first["first_login_at"]
    assert account["last_login_at"] > first["last_login_at"]


@pytest.mark.parametrize("name", [None, 7])
def test_login_without_a_name_is_refused(client, fake, name) -> None:
    response = log_in(client, fake, ["friends"], name=name)

    assert response.status_code == 400
    assert LOGIN not in read_session(client)


def test_start_keeps_the_token_of_a_running_session(client, fake) -> None:
    # A link from another site to the start must not swap the token of a
    # visitor who is logged in.
    log_in(client, fake, ["friends"])
    before = client.cookies.get(SESSION_COOKIE_NAME)
    csrf = read_session(client)["csrf_token"]

    start_login(client)

    assert client.cookies.get(SESSION_COOKIE_NAME) == before
    assert read_session(client)["csrf_token"] == csrf
    assert LOGIN in read_session(client)


def test_login_gives_the_session_a_new_token(client, fake) -> None:
    start_login(client)
    before = client.cookies.get(SESSION_COOKIE_NAME)
    old_csrf = read_session(client)["csrf_token"]

    log_in(client, fake, ["friends"])

    assert client.cookies.get(SESSION_COOKIE_NAME) != before
    assert read_session(client)["csrf_token"] != old_csrf


def test_safe_target_is_kept(client, fake) -> None:
    response = log_in(client, fake, ["friends"], target="/hub/games?sort=name")

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
    response = log_in(client, fake, ["wediga-admins"], target=target)

    assert response.headers["location"] == "/admin"


def test_wrong_state_is_refused_and_ends_the_flow(client, fake) -> None:
    query = start_login(client)
    fake.id_token = make_id_token(nonce=query["nonce"], groups=["friends"])

    assert finish_login(client, "wrong-state").status_code == 400
    assert finish_login(client, query["state"]).status_code == 400
    assert LOGIN not in read_session(client)


def test_state_works_only_once(client, fake) -> None:
    query = start_login(client)
    fake.id_token = make_id_token(nonce=query["nonce"], groups=["friends"])

    assert finish_login(client, query["state"]).status_code == 303
    assert finish_login(client, query["state"]).status_code == 400


@pytest.mark.usefixtures("fake")
def test_callback_without_started_login_is_refused(client) -> None:
    assert finish_login(client, "any-state").status_code == 400


@pytest.mark.usefixtures("fake")
def test_callback_without_code_is_refused(client) -> None:
    query = start_login(client)

    assert finish_login(client, query["state"], code="").status_code == 400


def test_flow_older_than_the_limit_is_refused(client, fake) -> None:
    query = start_login(client)
    fake.id_token = make_id_token(nonce=query["nonce"], groups=["friends"])
    age(LoginFlow.started_at, sessions.LOGIN_FLOW_LIFETIME)

    assert finish_login(client, query["state"]).status_code == 400


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
    response = log_in(client, fake, ["wediga-admins"], **claims)

    assert response.status_code == 400
    assert LOGIN not in read_session(client)


# A hashed sub, as authentik sends it without sub_mode user_id, and values
# that only look like a number.
@pytest.mark.parametrize("sub", ["a1b2c3", "", " 21", "21 ", "-21", "2.1", "٢١"])
def test_login_without_numeric_account_id_is_refused(client, fake, sub) -> None:
    response = log_in(client, fake, ["wediga-admins"], sub=sub)

    assert response.status_code == 400
    assert LOGIN not in read_session(client)


def test_nonce_of_another_login_is_refused(client, fake) -> None:
    """A token captured from one login cannot finish another one."""
    first = start_login(client)
    second = start_login(client)
    fake.id_token = make_id_token(nonce=first["nonce"], groups=["wediga-admins"])

    assert finish_login(client, second["state"]).status_code == 400


def test_failed_token_exchange_answers_502(client, fake) -> None:
    query = start_login(client)
    fake.token_error = oidc_router.oidc.OidcProviderError("down")

    assert finish_login(client, query["state"]).status_code == 502
    assert LOGIN not in read_session(client)


def test_login_drops_the_old_admin_login_and_csrf_token(client, fake) -> None:
    assert client.post("/auth/login", json={"password": ADMIN_PASSWORD}).is_success
    old_csrf = client.get("/auth/csrf").json()["csrf_token"]

    log_in(client, fake, ["friends"])

    session = read_session(client)
    assert LEGACY not in session
    assert session["csrf_token"] != old_csrf
    assert client.get("/auth/me").status_code == 403


def test_failed_login_also_ends_an_earlier_one(client, fake) -> None:
    log_in(client, fake, ["wediga-admins"])

    log_in(client, fake, [])

    assert LOGIN not in read_session(client)


# --- logout ------------------------------------------------------------------


def test_logout_needs_the_csrf_token(client, fake) -> None:
    log_in(client, fake, ["friends"])

    assert client.post("/auth/oidc/logout").status_code == 403
    assert LOGIN in read_session(client)


def test_logout_ends_the_login_and_points_to_authentik(client, fake) -> None:
    log_in(client, fake, ["wediga-admins"])

    old_csrf = read_session(client)["csrf_token"]

    response = log_out(client)

    assert response.json() == {"redirect": METADATA["end_session_endpoint"]}
    session = read_session(client)
    assert LOGIN not in session
    assert session["csrf_token"] != old_csrf


def test_logout_after_the_lifetime_still_points_to_authentik(client, fake) -> None:
    log_in(client, fake, ["friends"])
    age(AuthentikLogin.logged_in_at, sessions.AUTHENTIK_LOGIN_LIFETIME)

    response = log_out(client)

    assert response.json() == {"redirect": METADATA["end_session_endpoint"]}


@pytest.mark.usefixtures("fake")
def test_logout_of_a_password_login_skips_authentik(client) -> None:
    assert client.post("/auth/login", json={"password": ADMIN_PASSWORD}).is_success
    client.get("/auth/csrf")

    response = log_out(client)

    assert response.json() == {"redirect": "/login"}
    assert LEGACY not in read_session(client)


def test_logout_keeps_the_recruiter_session(app, client, fake) -> None:
    redeem_recruiter_link(app, client)
    log_in(client, fake, ["friends"])

    assert log_out(client).is_success

    assert RECRUITER in read_session(client)
    assert client.get("/recruiter/session").status_code == 200


def test_login_keeps_the_recruiter_session(app, client, fake) -> None:
    redeem_recruiter_link(app, client)

    log_in(client, fake, ["friends"])

    assert client.get("/recruiter/session").status_code == 200


def test_logout_still_works_when_authentik_is_down(client, fake) -> None:
    log_in(client, fake, ["friends"])
    fake.unreachable = True

    response = log_out(client)

    assert response.json() == {"redirect": "/"}
    assert LOGIN not in read_session(client)


# --- groups ------------------------------------------------------------------


@pytest.mark.parametrize("group", oidc_router.GROUP_ROLES)
def test_mapped_groups_exist_in_the_blueprint(group) -> None:
    """The group names live in the blueprint and here, so they must match."""
    assert f"name: {group}\n" in BLUEPRINT.read_text(encoding="utf-8")


def test_blueprint_sends_the_numeric_account_id() -> None:
    """The callback only accepts a numeric sub, which needs this setting."""
    assert "sub_mode: user_id\n" in BLUEPRINT.read_text(encoding="utf-8")
