"""Tests for the authentication flow."""

import importlib

import pytest
from fastapi.testclient import TestClient

ADMIN_PASSWORD = "correct horse battery staple"


@pytest.fixture()
def client(migrated_db, monkeypatch):
    """Build a TestClient with a bootstrapped admin over an https base URL.

    The session cookie is marked Secure (https_only), so the client must use
    an https base URL for the cookie to round-trip.
    """
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)

    from app.auth.bootstrap import ensure_admin

    ensure_admin()

    main = importlib.import_module("app.main")
    return TestClient(main.app, base_url="https://testserver")


def test_correct_password_logs_in(client) -> None:
    response = client.post("/auth/login", json={"password": ADMIN_PASSWORD})
    assert response.status_code == 200
    assert client.cookies.get("wediga_session") is not None


def test_wrong_password_is_rejected(client) -> None:
    response = client.post("/auth/login", json={"password": "wrong"})
    assert response.status_code == 401


def test_me_requires_session(client) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_after_login_then_logout(client) -> None:
    login = client.post("/auth/login", json={"password": ADMIN_PASSWORD})
    assert login.status_code == 200

    me = client.get("/auth/me")
    assert me.status_code == 200
    assert me.json() == {"admin": True}

    logout = client.post("/auth/logout")
    assert logout.status_code == 200

    me_again = client.get("/auth/me")
    assert me_again.status_code == 401


def test_failed_admin_bootstrap_is_logged(unmigrated_db, monkeypatch, caplog) -> None:
    # Without migrations the admin table is missing, so the bootstrap fails.
    # Startup must still go through, with a warning that says why the login
    # will not work.
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("GITHUB_SYNC_INTERVAL_SECONDS", "0")
    main = importlib.import_module("app.main")

    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200

    assert "admin bootstrap failed" in caplog.text
