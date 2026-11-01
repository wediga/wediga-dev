"""Tests for the rights that a login through authentik grants.

Until the password login is removed, both ways must open the admin routes,
the friends role must open none of them, and a login through authentik must
end eight hours after it happened.
"""

from datetime import timedelta

import pytest

from app.auth import sessions
from app.auth.csrf import CSRF_HEADER_NAME
from app.auth.models import AuthentikLogin
from tests.oidc.login import age, log_in, read_session, redeem_recruiter_link

LIFETIME = sessions.AUTHENTIK_LOGIN_LIFETIME
LOGIN = AuthentikLogin.__tablename__


def _csrf(client) -> str:
    response = client.get("/auth/csrf")
    assert response.status_code == 200

    return response.json()["csrf_token"]


def test_admin_from_authentik_reaches_the_admin_routes(client, fake) -> None:
    log_in(client, fake, ["wediga-admins"])

    assert client.get("/auth/me").status_code == 200
    assert client.get("/recruiter/links").status_code == 200
    created = client.post(
        "/recruiter/links",
        json={"label": "via authentik"},
        headers={CSRF_HEADER_NAME: _csrf(client)},
    )
    assert created.status_code == 201


def test_admin_from_authentik_previews_the_recruiter_pages(client, fake) -> None:
    log_in(client, fake, ["wediga-admins"])

    assert client.get("/recruiter/session").status_code == 200


def test_friend_reaches_no_admin_or_recruiter_route(client, fake) -> None:
    log_in(client, fake, ["friends"])

    # 403 rather than 401, so the admin area does not send a logged in friend
    # back to authentik, which would return them at once.
    assert client.get("/auth/me").status_code == 403
    assert client.get("/recruiter/links").status_code == 403
    assert client.get("/recruiter/session").status_code == 401
    refused = client.post(
        "/recruiter/links",
        json={"label": "x"},
        headers={CSRF_HEADER_NAME: _csrf(client)},
    )
    assert refused.status_code == 403


def test_friend_gets_the_csrf_token_and_can_log_out(client, fake) -> None:
    log_in(client, fake, ["friends"])

    response = client.post(
        "/auth/oidc/logout", headers={CSRF_HEADER_NAME: _csrf(client)}
    )

    assert response.status_code == 200
    assert LOGIN not in read_session(client)


@pytest.mark.usefixtures("fake")
def test_csrf_token_needs_a_login(client) -> None:
    assert client.get("/auth/csrf").status_code == 401


@pytest.mark.usefixtures("fake")
def test_recruiter_gets_no_csrf_token(app, client) -> None:
    redeem_recruiter_link(app, client)

    assert client.get("/auth/csrf").status_code == 401


@pytest.mark.parametrize("groups", [["wediga-admins"], ["friends"]])
def test_login_still_counts_shortly_before_its_end(client, fake, groups) -> None:
    log_in(client, fake, groups)
    age(AuthentikLogin.logged_in_at, LIFETIME - timedelta(minutes=1))

    assert client.get("/auth/csrf").status_code == 200


def test_admin_login_ends_after_its_lifetime(client, fake) -> None:
    log_in(client, fake, ["wediga-admins"])
    age(AuthentikLogin.logged_in_at, LIFETIME)

    assert client.get("/auth/me").status_code == 401
    assert client.get("/recruiter/session").status_code == 401


def test_friend_login_ends_after_its_lifetime(client, fake) -> None:
    log_in(client, fake, ["friends"])
    age(AuthentikLogin.logged_in_at, LIFETIME)

    assert client.get("/auth/csrf").status_code == 401


def test_recruiter_link_outlives_an_expired_login(app, client, fake) -> None:
    redeem_recruiter_link(app, client)
    log_in(client, fake, ["friends"])
    age(AuthentikLogin.logged_in_at, LIFETIME)

    assert client.get("/recruiter/session").status_code == 200
