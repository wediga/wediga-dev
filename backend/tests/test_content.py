"""Tests for the content CRUD layer.

Cover create, read, update and delete for each of the five content types, the
public reads that need no session, the 401 when a write has no session and the
403 when a write has a session but no valid CSRF token. The client uses an
https base URL so the Secure session cookie round-trips.
"""

import importlib

import pytest
from fastapi.testclient import TestClient

ADMIN_PASSWORD = "correct horse battery staple"


@pytest.fixture()
def app(migrated_db, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")

    from app.auth.bootstrap import ensure_admin

    ensure_admin()
    main = importlib.import_module("app.main")
    return main.app


@pytest.fixture()
def client(app):
    """An anonymous client with no session."""
    return TestClient(app, base_url="https://testserver")


def _login(app) -> TestClient:
    client = TestClient(app, base_url="https://testserver")
    response = client.post("/auth/login", json={"password": ADMIN_PASSWORD})
    assert response.status_code == 200
    return client


@pytest.fixture()
def session_client(app):
    """A logged-in client that does not send the CSRF header."""
    return _login(app)


@pytest.fixture()
def admin_client(app):
    """A logged-in client that sends a valid CSRF token on every request."""
    client = _login(app)
    token = client.get("/auth/csrf").json()["csrf_token"]
    client.headers.update({"X-CSRF-Token": token})
    return client


# --- about ---------------------------------------------------------------


def test_about_crud(admin_client) -> None:
    put = admin_client.put("/content/about", json={"text": "# Hi\n\nText"})
    assert put.status_code == 200
    assert admin_client.get("/content/about").json() == {"text": "# Hi\n\nText"}

    admin_client.put("/content/about", json={"text": "changed"})
    assert admin_client.get("/content/about").json()["text"] == "changed"

    assert admin_client.delete("/content/about").status_code == 200
    assert admin_client.get("/content/about").json() == {"text": ""}


# --- contact -------------------------------------------------------------


def test_contact_crud(admin_client) -> None:
    payload = {"name": "Alexander", "email": "a@example.com", "github": None,
               "linkedin": None}
    assert admin_client.put("/content/contact", json=payload).status_code == 200
    got = admin_client.get("/content/contact").json()
    assert got["name"] == "Alexander"
    assert got["email"] == "a@example.com"

    assert admin_client.delete("/content/contact").status_code == 200
    assert admin_client.get("/content/contact").json() is None


# --- impressum -----------------------------------------------------------


def test_impressum_crud(admin_client) -> None:
    payload = {
        "name": "Alexander Wedig",
        "email": "a@example.com",
        "address": {"street": "Street 1", "city": "12345 City"},
    }
    assert admin_client.put("/content/impressum", json=payload).status_code == 200

    # The admin read returns the full record.
    full = admin_client.get("/content/admin/impressum").json()
    assert full["address"]["city"] == "12345 City"

    # The public read exposes only name and email, never the address.
    public = admin_client.get("/content/impressum").json()
    assert public["name"] == "Alexander Wedig"
    assert public["email"] == "a@example.com"
    assert public["address"] is None

    assert admin_client.delete("/content/impressum").status_code == 200
    assert admin_client.get("/content/impressum").json() is None


# --- projects ------------------------------------------------------------


def test_project_crud_and_visibility(admin_client) -> None:
    create = admin_client.post(
        "/content/projects",
        json={"name": "Demo", "tagline": "t", "tech_stack": ["Python"]},
    )
    assert create.status_code == 201
    project = create.json()
    assert project["id"] > 0
    assert project["tech_stack"] == ["Python"]
    project_id = project["id"]

    update = admin_client.put(
        f"/content/projects/{project_id}",
        json={"name": "Demo", "tagline": "new", "visible": False},
    )
    assert update.status_code == 200
    assert update.json()["tagline"] == "new"

    # Hidden projects stay out of the public list but show in the admin list.
    assert admin_client.get("/content/projects").json() == []
    assert len(admin_client.get("/content/admin/projects").json()) == 1

    assert admin_client.delete(f"/content/projects/{project_id}").status_code == 200
    assert admin_client.delete(f"/content/projects/{project_id}").status_code == 404


# --- skills --------------------------------------------------------------


def test_skills_crud(admin_client) -> None:
    category = admin_client.post(
        "/content/skills/categories", json={"name": "Languages"}
    )
    assert category.status_code == 201
    category_id = category.json()["id"]

    skill = admin_client.post(
        f"/content/skills/categories/{category_id}/skills", json={"name": "Python"}
    )
    assert skill.status_code == 201
    skill_id = skill.json()["id"]

    skills = admin_client.get("/content/skills").json()
    assert skills[0]["name"] == "Languages"
    assert skills[0]["skills"][0]["name"] == "Python"

    assert admin_client.put(
        f"/content/skills/{skill_id}", json={"name": "Python 3"}
    ).status_code == 200
    assert admin_client.put(
        f"/content/skills/categories/{category_id}", json={"name": "Langs"}
    ).status_code == 200

    assert admin_client.delete(f"/content/skills/{skill_id}").status_code == 200
    assert admin_client.delete(
        f"/content/skills/categories/{category_id}"
    ).status_code == 200
    assert admin_client.get("/content/skills").json() == []


def test_create_skill_in_missing_category_is_404(admin_client) -> None:
    assert admin_client.post(
        "/content/skills/categories/999/skills", json={"name": "X"}
    ).status_code == 404


def test_duplicate_project_name_is_409(admin_client) -> None:
    assert admin_client.post("/content/projects", json={"name": "Dup"}).status_code == 201
    assert admin_client.post("/content/projects", json={"name": "Dup"}).status_code == 409


def test_setting_delete_is_idempotent(admin_client) -> None:
    # Deleting absent content still succeeds, so the admin never sees a spurious
    # failure when removing content that was never saved.
    assert admin_client.delete("/content/contact").status_code == 200
    assert admin_client.delete("/content/contact").status_code == 200


# --- public reads --------------------------------------------------------


def test_public_reads_need_no_session(client) -> None:
    # About and skills feed the public landing page, so they stay open.
    assert client.get("/content/about").status_code == 200
    assert client.get("/content/skills").status_code == 200


def test_recruiter_reads_need_a_session(client) -> None:
    # The full portfolio and the contact details sit behind the recruiter gate.
    assert client.get("/content/projects").status_code == 401
    assert client.get("/content/contact").status_code == 401


# --- write protection ----------------------------------------------------


def test_writes_without_session_are_401(client) -> None:
    assert client.put("/content/about", json={"text": "x"}).status_code == 401
    assert client.post("/content/projects", json={"name": "X"}).status_code == 401
    assert client.delete("/content/projects/1").status_code == 401


def test_writes_without_csrf_are_403(session_client) -> None:
    assert session_client.put("/content/about", json={"text": "x"}).status_code == 403
    assert session_client.post(
        "/content/projects", json={"name": "X"}
    ).status_code == 403


def test_writes_with_wrong_csrf_are_403(session_client) -> None:
    session_client.headers.update({"X-CSRF-Token": "not-the-real-token"})
    assert session_client.put("/content/about", json={"text": "x"}).status_code == 403


def test_admin_projects_read_needs_session(client) -> None:
    assert client.get("/content/admin/projects").status_code == 401


def test_admin_impressum_read_needs_session(client) -> None:
    assert client.get("/content/admin/impressum").status_code == 401


def test_invalid_body_is_422(admin_client) -> None:
    # Empty project name violates the min_length constraint.
    assert admin_client.post("/content/projects", json={"name": ""}).status_code == 422


def test_link_field_rejects_non_http_scheme(admin_client) -> None:
    # A javascript: link must never be storable, even by the admin.
    response = admin_client.post(
        "/content/projects",
        json={"name": "Bad", "demo_link": "javascript:alert(1)"},
    )
    assert response.status_code == 422


def test_link_field_accepts_https(admin_client) -> None:
    response = admin_client.post(
        "/content/projects",
        json={"name": "Good", "github_link": "https://github.com/wediga/x"},
    )
    assert response.status_code == 201
