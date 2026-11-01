"""Tests for the sessions kept on the server: what the cookie holds, when a
session ends and what the clean-up deletes."""

import importlib
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.auth import sessions
from app.auth.models import BrowserSession, LegacyAdminLogin
from app.db.connection import get_session
from tests.oidc.login import ADMIN_PASSWORD, age, read_session

ONE_MINUTE = timedelta(minutes=1)


@pytest.fixture()
def app(migrated_db, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)

    from app.auth.bootstrap import ensure_admin

    ensure_admin()

    return importlib.import_module("app.main").app


@pytest.fixture()
def client(app) -> TestClient:
    return TestClient(app, base_url="https://testserver")


def _log_in(client: TestClient) -> None:
    assert client.post("/auth/login", json={"password": ADMIN_PASSWORD}).is_success


def _session_count() -> int:
    with get_session() as db:
        return db.scalar(select(func.count()).select_from(BrowserSession)) or 0


def test_cookie_holds_only_the_random_token(client) -> None:
    response = client.post("/auth/login", json={"password": ADMIN_PASSWORD})

    cookie = response.headers["set-cookie"]
    token = client.cookies.get(sessions.SESSION_COOKIE_NAME)
    assert token is not None
    assert cookie.startswith(f"{sessions.SESSION_COOKIE_NAME}={token};")
    stored = read_session(client)
    assert stored["token_hash"] == sessions.hash_token(token)
    assert stored["csrf_token"] not in cookie


def test_cookie_settings(client) -> None:
    response = client.post("/auth/login", json={"password": ADMIN_PASSWORD})

    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "secure" in cookie
    assert "samesite=lax" in cookie
    assert f"max-age={sessions.COOKIE_MAX_AGE_SECONDS}" in cookie


def test_visitor_without_a_login_gets_no_session(client) -> None:
    response = client.get("/content/projects")

    assert "set-cookie" not in response.headers
    assert _session_count() == 0


def test_deleted_session_stops_working_at_once(client) -> None:
    _log_in(client)
    assert client.get("/auth/me").status_code == 200

    with get_session() as db:
        db.execute(delete(BrowserSession))
        db.commit()

    response = client.get("/auth/me")
    assert response.status_code == 401
    assert client.cookies.get(sessions.SESSION_COOKIE_NAME) is None


def test_unknown_cookie_is_removed(client) -> None:
    # Such as the signed cookie from before the sessions moved to the server.
    client.cookies.set(sessions.SESSION_COOKIE_NAME, "eyJhZG1pbiI6IHRydWV9.old")

    response = client.get("/auth/me")

    assert response.status_code == 401
    cookie = response.headers["set-cookie"]
    assert cookie.startswith(f'{sessions.SESSION_COOKIE_NAME}="";')
    assert "max-age=0" in cookie.lower()


def test_session_lasts_while_it_is_used(client) -> None:
    _log_in(client)
    age(BrowserSession.last_seen_at, sessions.IDLE_TIMEOUT - ONE_MINUTE)

    assert client.get("/auth/me").status_code == 200
    age(BrowserSession.last_seen_at, sessions.IDLE_TIMEOUT - ONE_MINUTE)
    assert client.get("/auth/me").status_code == 200


def test_session_ends_after_the_idle_timeout(client) -> None:
    _log_in(client)
    age(BrowserSession.last_seen_at, sessions.IDLE_TIMEOUT)

    assert client.get("/auth/me").status_code == 401


def test_login_replaces_a_known_token(app, client) -> None:
    _log_in(client)
    before = client.cookies.get(sessions.SESSION_COOKIE_NAME)

    _log_in(client)

    attacker = TestClient(app, base_url="https://testserver")
    attacker.cookies.set(sessions.SESSION_COOKIE_NAME, before)
    assert client.get("/auth/me").status_code == 200
    assert attacker.get("/auth/me").status_code == 401


def test_logout_deletes_the_session(client) -> None:
    _log_in(client)

    assert client.post("/auth/logout").is_success
    assert _session_count() == 0
    assert client.cookies.get(sessions.SESSION_COOKIE_NAME) is None


def test_user_agent_is_kept_and_cut(client) -> None:
    long_agent = "a" * (sessions.MAX_USER_AGENT_LENGTH + 1)
    client.headers["user-agent"] = long_agent

    _log_in(client)

    assert read_session(client)["user_agent"] == long_agent[:-1]


def test_clean_up_deletes_only_what_has_expired(app) -> None:
    idle = TestClient(app, base_url="https://testserver")
    _log_in(idle)
    age(BrowserSession.last_seen_at, sessions.IDLE_TIMEOUT)
    fresh = TestClient(app, base_url="https://testserver")
    _log_in(fresh)

    sessions.delete_expired()

    assert _session_count() == 1
    assert LegacyAdminLogin.__tablename__ in read_session(fresh)
    assert fresh.get("/auth/me").status_code == 200
