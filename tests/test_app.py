import os
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

EXAMPLE_CONTENT = Path(__file__).parent.parent / "content.example"

os.environ.setdefault("SESSION_SECRET", "test-secret")
os.environ.setdefault("RECRUITER_USERNAME", "testrecruiter")
os.environ.setdefault("RECRUITER_PASSWORD", "testpass1")
os.environ.setdefault("FRIENDS_USERNAME", "testfriend")
os.environ.setdefault("FRIENDS_PASSWORD", "testpass2")


@pytest.fixture()
def client():
    with patch("content_loader.CONTENT_DIR", EXAMPLE_CONTENT):
        import importlib
        import main
        importlib.reload(main)
        yield TestClient(main.app)


# --- Öffentliche Seiten ---

def test_landing_page(client):
    r = client.get("/")
    assert r.status_code == 200


def test_login_page(client):
    r = client.get("/login")
    assert r.status_code == 200


def test_impressum_page(client):
    r = client.get("/impressum")
    assert r.status_code == 200


# --- Geschützte Seiten ohne Login ---

def test_portfolio_redirects_without_login(client):
    r = client.get("/portfolio", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"


def test_friends_redirects_without_login(client):
    r = client.get("/friends", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"


# --- Login ---

def test_login_with_valid_credentials(client):
    r = client.post("/login", data={"username": "testrecruiter", "password": "testpass1"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/portfolio"


def test_login_with_invalid_credentials(client):
    r = client.post("/login", data={"username": "wrong", "password": "wrong"})
    assert r.status_code == 200
    assert "Invalid credentials" in r.text


# --- Logout ---

def test_logout_redirects(client):
    r = client.get("/logout", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"] == "/"
