"""Fixtures for the tests of the login through authentik."""

import importlib

import pytest
from fastapi.testclient import TestClient

from tests.oidc.login import ADMIN_PASSWORD
from tests.oidc.oidc_fake import SETTINGS, FakeAuthentik


@pytest.fixture()
def app(migrated_db, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)

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
