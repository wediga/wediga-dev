"""Tests for recruiter links, redemption, the recruiter gate and the login limit.

The client uses an https base URL so the Secure session cookie round-trips.
"""

import importlib
import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.auth.sessions import RECRUITER_ACCESS_LIFETIME
from app.recruiter.models import RecruiterAccess
from app.recruiter.schemas import DEFAULT_LINK_LIFETIME
from tests.oidc.login import age, read_session

ADMIN_PASSWORD = "correct horse battery staple"


@pytest.fixture()
def app(migrated_db, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)

    from app.auth.bootstrap import ensure_admin

    ensure_admin()
    main = importlib.import_module("app.main")
    return main.app


@pytest.fixture()
def client(app):
    """An anonymous client with no session."""
    return TestClient(app, base_url="https://testserver")


def _login(app) -> TestClient:
    c = TestClient(app, base_url="https://testserver")
    assert c.post("/auth/login", json={"password": ADMIN_PASSWORD}).status_code == 200
    return c


@pytest.fixture()
def session_client(app):
    """A logged-in admin client that does not send the CSRF header."""
    return _login(app)


@pytest.fixture()
def admin_client(app):
    """A logged-in admin client that sends a valid CSRF token on every request."""
    c = _login(app)
    token = c.get("/auth/csrf").json()["csrf_token"]
    c.headers.update({"X-CSRF-Token": token})
    return c


def _create_link(admin_client, **body) -> dict:
    response = admin_client.post("/recruiter/links", json=body)
    assert response.status_code == 201
    return response.json()


# --- link management -----------------------------------------------------


def test_create_returns_token_once_and_lists_link(admin_client) -> None:
    created = _create_link(admin_client, label="Acme Corp")
    assert created["token"]
    assert created["label"] == "Acme Corp"
    assert created["view_count"] == 0
    assert created["active"] is True

    listed = admin_client.get("/recruiter/links").json()
    assert len(listed) == 1
    assert listed[0]["label"] == "Acme Corp"
    # The plaintext token is never returned again, only its absence in the list.
    assert "token" not in listed[0]


def test_create_and_revoke_require_admin_and_csrf(client, session_client) -> None:
    assert client.post("/recruiter/links", json={}).status_code == 401
    assert client.get("/recruiter/links").status_code == 401
    assert client.post("/recruiter/links/1/revoke").status_code == 401
    # Logged in but no CSRF token is a 403 on the writes.
    assert session_client.post("/recruiter/links", json={}).status_code == 403
    assert session_client.post("/recruiter/links/1/revoke").status_code == 403


def test_revoke_missing_link_is_404(admin_client) -> None:
    assert (
        admin_client.post(f"/recruiter/links/{uuid.uuid4()}/revoke").status_code == 404
    )


# --- expiry --------------------------------------------------------------


def _today() -> date:
    return datetime.now(UTC).date()


def _set_expiry(admin_client, link_id: str, expires_on: date | None):
    return admin_client.put(
        f"/recruiter/links/{link_id}/expiry",
        json={"expires_on": expires_on.isoformat() if expires_on else None},
    )


def test_create_without_expiry_gets_the_default_lifetime(admin_client) -> None:
    created = _create_link(admin_client, label="Default")
    expected = (_today() + DEFAULT_LINK_LIFETIME).isoformat()

    assert created["expires_at"] == f"{expected}T23:59:59Z"


def test_create_with_null_expiry_never_expires(admin_client) -> None:
    created = _create_link(admin_client, label="Forever", expires_on=None)

    assert created["expires_at"] is None
    assert created["active"] is True


def test_set_expiry_moves_the_date(admin_client) -> None:
    created = _create_link(admin_client, label="Extend")
    later = _today() + DEFAULT_LINK_LIFETIME * 2

    response = _set_expiry(admin_client, created["id"], later)

    assert response.status_code == 200
    assert response.json()["expires_at"] == f"{later.isoformat()}T23:59:59Z"
    assert admin_client.get("/recruiter/links").json()[0]["expires_at"] == (
        f"{later.isoformat()}T23:59:59Z"
    )


def test_set_expiry_to_null_removes_it(admin_client) -> None:
    created = _create_link(admin_client, label="Unlimited")

    response = _set_expiry(admin_client, created["id"], None)

    assert response.status_code == 200
    assert response.json()["expires_at"] is None


def test_set_expiry_in_the_past_ends_the_link(app, admin_client) -> None:
    created = _create_link(admin_client, label="Shorten")

    response = _set_expiry(admin_client, created["id"], _today() - timedelta(days=1))

    assert response.json()["active"] is False
    visitor = TestClient(app, base_url="https://testserver")
    assert (
        visitor.post("/recruiter/redeem", json={"token": created["token"]}).status_code
        == 410
    )


def test_extending_an_expired_link_makes_it_usable_again(app, admin_client) -> None:
    yesterday = _today() - timedelta(days=1)
    created = _create_link(
        admin_client, label="Renew", expires_on=yesterday.isoformat()
    )

    response = _set_expiry(admin_client, created["id"], _today())

    assert response.json()["active"] is True
    visitor = TestClient(app, base_url="https://testserver")
    assert (
        visitor.post("/recruiter/redeem", json={"token": created["token"]}).status_code
        == 200
    )


def test_extending_a_revoked_link_keeps_it_revoked(app, admin_client) -> None:
    created = _create_link(admin_client, label="Gone")
    admin_client.post(f"/recruiter/links/{created['id']}/revoke")

    response = _set_expiry(admin_client, created["id"], None)

    assert response.json()["active"] is False
    visitor = TestClient(app, base_url="https://testserver")
    assert (
        visitor.post("/recruiter/redeem", json={"token": created["token"]}).status_code
        == 410
    )


def test_set_expiry_requires_the_field(admin_client) -> None:
    created = _create_link(admin_client, label="Body")

    response = admin_client.put(f"/recruiter/links/{created['id']}/expiry", json={})

    assert response.status_code == 422


def test_set_expiry_on_missing_link_is_404(admin_client) -> None:
    assert _set_expiry(admin_client, str(uuid.uuid4()), None).status_code == 404


def test_set_expiry_requires_admin_and_csrf(client, session_client) -> None:
    path = f"/recruiter/links/{uuid.uuid4()}/expiry"

    assert client.put(path, json={"expires_on": None}).status_code == 401
    assert session_client.put(path, json={"expires_on": None}).status_code == 403


# --- redemption ----------------------------------------------------------


def test_redeem_starts_session_and_records_view(app, admin_client) -> None:
    created = _create_link(admin_client, label="Open me")
    token = created["token"]

    visitor = TestClient(app, base_url="https://testserver")
    redeem = visitor.post("/recruiter/redeem", json={"token": token})
    assert redeem.status_code == 200
    assert visitor.cookies.get("wediga_session") is not None

    # The recruiter session now unlocks the gated views.
    assert visitor.get("/recruiter/session").status_code == 200
    assert visitor.get("/content/projects").status_code == 200
    assert visitor.get("/content/contact").status_code == 200

    # The view is tracked and visible to the admin with a count and a time.
    listed = admin_client.get("/recruiter/links").json()
    assert listed[0]["view_count"] == 1
    assert listed[0]["last_viewed_at"] is not None


def test_redeem_invalid_token_is_404(client) -> None:
    assert (
        client.post("/recruiter/redeem", json={"token": "not-a-real-token"}).status_code
        == 404
    )


def test_redeem_takes_no_token_in_the_path(app, admin_client) -> None:
    # The access log records every path, so a token there would end up in the
    # server's logs in plain text.
    created = admin_client.post("/recruiter/links", json={}).json()
    visitor = TestClient(app)

    assert visitor.post(f"/recruiter/redeem/{created['token']}").status_code == 404


def test_redeem_is_rate_limited(client) -> None:
    # The redeem limiter allows thirty attempts per window per IP; the next one
    # is 429, checked before the token is validated.
    for _ in range(30):
        client.post("/recruiter/redeem", json={"token": "whatever"})
    assert (
        client.post("/recruiter/redeem", json={"token": "whatever"}).status_code == 429
    )


def test_redeem_revoked_link_is_410(app, admin_client) -> None:
    created = _create_link(admin_client, label="To revoke")
    revoke = admin_client.post(f"/recruiter/links/{created['id']}/revoke")
    assert revoke.status_code == 200
    assert revoke.json()["active"] is False

    visitor = TestClient(app, base_url="https://testserver")
    assert (
        visitor.post("/recruiter/redeem", json={"token": created["token"]}).status_code
        == 410
    )


def test_redeem_expired_link_is_410(app, admin_client) -> None:
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    created = _create_link(admin_client, label="Stale", expires_on=yesterday)
    assert created["active"] is False

    visitor = TestClient(app, base_url="https://testserver")
    assert (
        visitor.post("/recruiter/redeem", json={"token": created["token"]}).status_code
        == 410
    )


# --- session separation and the gate -------------------------------------


def test_recruiter_session_grants_no_admin_rights(app, admin_client) -> None:
    created = _create_link(admin_client, label="Recruiter only")

    visitor = TestClient(app, base_url="https://testserver")
    assert (
        visitor.post("/recruiter/redeem", json={"token": created["token"]}).status_code
        == 200
    )

    # A recruiter session must not reach any admin surface.
    assert visitor.get("/auth/me").status_code == 401
    assert visitor.post("/recruiter/links", json={}).status_code == 401
    assert visitor.get("/recruiter/links").status_code == 401
    assert visitor.get("/content/admin/projects").status_code == 401


def test_recruiter_gate_blocks_anonymous_but_admin_passes(client, admin_client) -> None:
    assert client.get("/content/projects").status_code == 401
    # An admin session satisfies the recruiter-or-admin gate.
    assert admin_client.get("/content/projects").status_code == 200
    assert admin_client.get("/recruiter/session").status_code == 200


def test_revocation_cuts_an_active_recruiter_session(app, admin_client) -> None:
    created = _create_link(admin_client, label="Cut me")
    visitor = TestClient(app, base_url="https://testserver")
    assert (
        visitor.post("/recruiter/redeem", json={"token": created["token"]}).status_code
        == 200
    )
    assert visitor.get("/content/projects").status_code == 200

    # The admin revokes the link the visitor is currently using.
    assert (
        admin_client.post(f"/recruiter/links/{created['id']}/revoke").status_code == 200
    )

    # The open session loses access on the next read; revocation closes the
    # door and not only the entrance.
    assert visitor.get("/recruiter/session").status_code == 401
    assert visitor.get("/content/projects").status_code == 401
    assert visitor.get("/content/contact").status_code == 401


def test_redeem_keeps_the_link_in_the_session(app, admin_client) -> None:
    created = _create_link(admin_client, label="Session")
    visitor = TestClient(app, base_url="https://testserver")
    visitor.post("/recruiter/redeem", json={"token": created["token"]})

    access = read_session(visitor)[RecruiterAccess.__tablename__]
    assert access["recruiter_link_id"] == uuid.UUID(created["id"])


def test_recruiter_access_ends_after_its_lifetime(app, admin_client) -> None:
    created = _create_link(admin_client, label="Week")
    visitor = TestClient(app, base_url="https://testserver")
    visitor.post("/recruiter/redeem", json={"token": created["token"]})
    age(RecruiterAccess.redeemed_at, RECRUITER_ACCESS_LIFETIME - timedelta(minutes=1))

    assert visitor.get("/recruiter/session").status_code == 200

    age(RecruiterAccess.redeemed_at, timedelta(minutes=1))

    assert visitor.get("/recruiter/session").status_code == 401


def test_redeeming_again_replaces_the_link(app, admin_client) -> None:
    first = _create_link(admin_client, label="First")
    second = _create_link(admin_client, label="Second")
    visitor = TestClient(app, base_url="https://testserver")
    visitor.post("/recruiter/redeem", json={"token": first["token"]})

    assert visitor.post("/recruiter/redeem", json={"token": second["token"]}).is_success

    access = read_session(visitor)[RecruiterAccess.__tablename__]
    assert access["recruiter_link_id"] == uuid.UUID(second["id"])


# --- login rate limit ----------------------------------------------------


def test_login_rate_limit_blocks_after_too_many_attempts(client) -> None:
    # The limiter allows ten attempts per window; the eleventh is rejected with
    # 429 before the password is even checked.
    for _ in range(10):
        assert client.post("/auth/login", json={"password": "wrong"}).status_code == 401
    assert client.post("/auth/login", json={"password": "wrong"}).status_code == 429
    # A correct password is also blocked once the limit is hit.
    assert (
        client.post("/auth/login", json={"password": ADMIN_PASSWORD}).status_code == 429
    )
