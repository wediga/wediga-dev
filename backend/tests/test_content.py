"""Tests for the content CRUD layer.

Cover the profile with its two views, create, read, update and delete for
projects and skills, the public reads that need no session, the 401 when a
write has no session and the 403 when a write has a session but no valid CSRF
token. The client uses an
https base URL so the Secure session cookie round-trips.
"""

import importlib
import uuid

import pytest
from fastapi.testclient import TestClient

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


# --- profile -------------------------------------------------------------

PROFILE = {
    "name": "Alexander Wedig",
    "email": "a@example.com",
    "about_md": "# Hi\n\nText",
    "links": {
        "github": "https://github.com/example",
        "linkedin": "https://linkedin.com/in/example",
    },
    "address": {"street": "Street 1", "postal_code": "12345", "city": "City"},
}


def test_profile_round_trip(admin_client) -> None:
    assert admin_client.put("/content/profile", json=PROFILE).status_code == 200
    assert admin_client.get("/content/profile").json() == PROFILE


def test_profile_update_replaces_links_and_address(admin_client) -> None:
    admin_client.put("/content/profile", json=PROFILE)
    changed = {
        **PROFILE,
        "name": "Changed",
        "links": {"github": "https://github.com/other"},
        "address": None,
    }

    assert admin_client.put("/content/profile", json=changed).status_code == 200
    assert admin_client.get("/content/profile").json() == changed


def test_views_are_empty_without_profile(admin_client) -> None:
    assert admin_client.get("/content/profile").json() is None
    assert admin_client.get("/content/contact").json() is None
    assert admin_client.get("/content/impressum").json() is None


def test_contact_shows_name_email_and_links_only(admin_client) -> None:
    admin_client.put("/content/profile", json=PROFILE)

    assert admin_client.get("/content/contact").json() == {
        "name": PROFILE["name"],
        "email": PROFILE["email"],
        "links": PROFILE["links"],
    }


def test_public_impressum_shows_name_and_email_only(admin_client, client) -> None:
    admin_client.put("/content/profile", json=PROFILE)

    assert client.get("/content/impressum").json() == {
        "name": PROFILE["name"],
        "email": PROFILE["email"],
    }


@pytest.mark.parametrize(
    "links",
    [
        {"mastodon": "https://example.social/@a"},
        {"github": "javascript:alert(1)"},
        {"github": ""},
    ],
)
def test_profile_rejects_bad_links(admin_client, links) -> None:
    body = {**PROFILE, "links": links}

    assert admin_client.put("/content/profile", json=body).status_code == 422


# --- projects ------------------------------------------------------------


def test_project_crud_and_visibility(admin_client) -> None:
    create = admin_client.post(
        "/content/projects",
        json={"name": "Demo", "tagline": "t", "tech_stack": ["Python"]},
    )
    assert create.status_code == 201
    project = create.json()
    assert uuid.UUID(project["id"])
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

    assert (
        admin_client.put(
            f"/content/skills/{skill_id}", json={"name": "Python 3"}
        ).status_code
        == 200
    )
    assert (
        admin_client.put(
            f"/content/skills/categories/{category_id}", json={"name": "Langs"}
        ).status_code
        == 200
    )

    assert admin_client.delete(f"/content/skills/{skill_id}").status_code == 200
    assert (
        admin_client.delete(f"/content/skills/categories/{category_id}").status_code
        == 200
    )
    assert admin_client.get("/content/skills").json() == []


def test_create_skill_in_missing_category_is_404(admin_client) -> None:
    assert (
        admin_client.post(
            f"/content/skills/categories/{uuid.uuid4()}/skills", json={"name": "X"}
        ).status_code
        == 404
    )


def test_duplicate_project_name_is_409(admin_client) -> None:
    assert (
        admin_client.post("/content/projects", json={"name": "Dup"}).status_code == 201
    )
    assert (
        admin_client.post("/content/projects", json={"name": "Dup"}).status_code == 409
    )


# --- public reads --------------------------------------------------------


def test_public_reads_need_no_session(client) -> None:
    # The impressum and skills feed the public pages, so they stay open.
    assert client.get("/content/impressum").status_code == 200
    assert client.get("/content/skills").status_code == 200


def test_recruiter_reads_need_a_session(client) -> None:
    # The full portfolio and the contact details sit behind the recruiter gate.
    assert client.get("/content/projects").status_code == 401
    assert client.get("/content/contact").status_code == 401


# --- write protection ----------------------------------------------------


def test_writes_without_session_are_401(client) -> None:
    assert client.put("/content/profile", json=PROFILE).status_code == 401
    assert client.post("/content/projects", json={"name": "X"}).status_code == 401
    assert client.delete("/content/projects/1").status_code == 401


def test_writes_without_csrf_are_403(session_client) -> None:
    assert session_client.put("/content/profile", json=PROFILE).status_code == 403
    assert (
        session_client.post("/content/projects", json={"name": "X"}).status_code == 403
    )


def test_writes_with_wrong_csrf_are_403(session_client) -> None:
    session_client.headers.update({"X-CSRF-Token": "not-the-real-token"})
    assert session_client.put("/content/profile", json=PROFILE).status_code == 403


def test_admin_projects_read_needs_session(client) -> None:
    assert client.get("/content/admin/projects").status_code == 401


def test_profile_read_needs_session(client) -> None:
    assert client.get("/content/profile").status_code == 401


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
