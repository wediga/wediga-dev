"""Tests for the content CRUD layer.

Cover the profile with its two views, create, read, update and delete for
technologies and skills, the public reads that need no session, the 401 when a
write has no session and the 403 when a write has a session but no valid CSRF
token. The client uses an
https base URL so the Secure session cookie round-trips.
"""

import importlib
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.content.models import Skill, Technology
from app.content.schemas import TOPIC_MAX
from app.db.connection import get_session

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
    "phone": "+49 151 2345-678",
    "about_md": "# Hi\n\nText",
    "links": {
        "github": "https://github.com/example",
        "linkedin": "https://linkedin.com/in/example",
        "website": "https://example.com",
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


def test_profile_without_phone_reads_as_empty(admin_client) -> None:
    body = {key: value for key, value in PROFILE.items() if key != "phone"}

    assert admin_client.put("/content/profile", json=body).status_code == 200
    assert admin_client.get("/content/profile").json()["phone"] == ""


@pytest.mark.parametrize(
    "phone",
    ["javascript:alert(1)", "0151 abc", "+", "++49 151", " 0151", "1" * 201],
)
def test_profile_rejects_bad_phone(admin_client, phone) -> None:
    body = {**PROFILE, "phone": phone}

    assert admin_client.put("/content/profile", json=body).status_code == 422


# --- skills and technologies ---------------------------------------------


def _category(admin_client, name: str) -> str:
    response = admin_client.post("/content/skills/categories", json={"name": name})
    assert response.status_code == 201

    return response.json()["id"]


def _technology(admin_client, **body) -> dict:
    response = admin_client.post("/content/technologies", json=body)
    assert response.status_code == 201

    return response.json()


def _skill_names(client) -> dict[str, list[str]]:
    return {
        category["name"]: [skill["name"] for skill in category["skills"]]
        for category in client.get("/content/skills").json()
    }


def test_skills_show_the_name_of_their_technology(admin_client) -> None:
    category_id = _category(admin_client, "Languages")
    python = _technology(
        admin_client, topic="python", name="Python", skill_category_id=category_id
    )
    assert _skill_names(admin_client) == {"Languages": ["Python"]}

    renamed = admin_client.put(
        f"/content/technologies/{python['id']}",
        json={"topic": "python", "name": "Python 3", "skill_category_id": category_id},
    )
    assert renamed.status_code == 200
    assert _skill_names(admin_client) == {"Languages": ["Python 3"]}


def test_technology_without_category_is_no_skill(admin_client) -> None:
    _category(admin_client, "Languages")
    _technology(admin_client, topic="fastapi", name="FastAPI")

    assert _skill_names(admin_client) == {"Languages": []}
    assert admin_client.get("/content/technologies").json()[0]["sort_order"] is None


def test_technology_moves_to_the_end_of_another_category(admin_client) -> None:
    languages = _category(admin_client, "Languages")
    tools = _category(admin_client, "Tools")
    _technology(admin_client, topic="git", name="Git", skill_category_id=tools)
    python = _technology(
        admin_client, topic="python", name="Python", skill_category_id=languages
    )

    moved = admin_client.put(
        f"/content/technologies/{python['id']}",
        json={"topic": "python", "name": "Python", "skill_category_id": tools},
    )

    assert moved.json()["sort_order"] == 1
    assert _skill_names(admin_client) == {"Languages": [], "Tools": ["Git", "Python"]}


def test_technology_stands_in_at_most_one_category(admin_client) -> None:
    languages = _category(admin_client, "Languages")
    tools = _category(admin_client, "Tools")
    python = _technology(
        admin_client, topic="python", name="Python", skill_category_id=languages
    )

    with get_session() as session, pytest.raises(IntegrityError):
        session.add(
            Skill(
                skill_category_id=uuid.UUID(tools),
                technology_id=uuid.UUID(python["id"]),
            )
        )
        session.commit()


def test_deleting_a_category_keeps_its_technologies(admin_client) -> None:
    category_id = _category(admin_client, "Languages")
    _technology(
        admin_client, topic="python", name="Python", skill_category_id=category_id
    )

    assert (
        admin_client.delete(f"/content/skills/categories/{category_id}").status_code
        == 200
    )
    assert admin_client.get("/content/skills").json() == []
    assert [
        (technology["name"], technology["skill_category_id"])
        for technology in admin_client.get("/content/technologies").json()
    ] == [("Python", None)]


def test_deleting_a_technology_removes_its_skill(admin_client) -> None:
    category_id = _category(admin_client, "Languages")
    python = _technology(
        admin_client, topic="python", name="Python", skill_category_id=category_id
    )

    assert (
        admin_client.delete(f"/content/technologies/{python['id']}").status_code == 200
    )
    assert _skill_names(admin_client) == {"Languages": []}
    assert (
        admin_client.delete(f"/content/technologies/{python['id']}").status_code == 404
    )


def test_duplicate_topic_is_409(admin_client) -> None:
    _technology(admin_client, topic="python", name="Python")

    response = admin_client.post(
        "/content/technologies", json={"topic": "python", "name": "Python 3"}
    )
    assert response.status_code == 409


def test_technology_in_missing_category_is_409(admin_client) -> None:
    response = admin_client.post(
        "/content/technologies",
        json={
            "topic": "python",
            "name": "Python",
            "skill_category_id": str(uuid.uuid4()),
        },
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "topic", ["", "Python", "tailwind css", "-python", "a" * (TOPIC_MAX + 1)]
)
def test_topic_follows_the_github_rules(admin_client, topic) -> None:
    response = admin_client.post(
        "/content/technologies", json={"topic": topic, "name": "X"}
    )
    assert response.status_code == 422


# --- public reads --------------------------------------------------------


def test_public_reads_need_no_session(client) -> None:
    # The impressum and skills feed the public pages, so they stay open.
    assert client.get("/content/impressum").status_code == 200
    assert client.get("/content/skills").status_code == 200


def test_recruiter_reads_need_a_session(client) -> None:
    # The contact details sit behind the recruiter gate.
    assert client.get("/content/contact").status_code == 401


# --- write protection ----------------------------------------------------


def test_writes_without_session_are_401(client) -> None:
    assert client.put("/content/profile", json=PROFILE).status_code == 401
    assert (
        client.post("/content/skills/categories", json={"name": "X"}).status_code == 401
    )


def test_writes_without_csrf_are_403(session_client) -> None:
    assert session_client.put("/content/profile", json=PROFILE).status_code == 403
    assert (
        session_client.post(
            "/content/skills/categories", json={"name": "X"}
        ).status_code
        == 403
    )


def test_writes_with_wrong_csrf_are_403(session_client) -> None:
    session_client.headers.update({"X-CSRF-Token": "not-the-real-token"})
    assert session_client.put("/content/profile", json=PROFILE).status_code == 403


def test_technology_with_a_derived_long_topic_still_loads(admin_client) -> None:
    # The migration derives topics from names without the limits of a write.
    topic = "a" * (TOPIC_MAX + 1)

    with get_session() as session:
        session.add(Technology(topic=topic, name="Long"))
        session.commit()

    response = admin_client.get("/content/technologies")

    assert response.status_code == 200
    assert response.json()[0]["topic"] == topic


def test_technologies_read_needs_session(client) -> None:
    assert client.get("/content/technologies").status_code == 401


def test_profile_read_needs_session(client) -> None:
    assert client.get("/content/profile").status_code == 401


def test_invalid_body_is_422(admin_client) -> None:
    # An empty category name violates the min_length constraint.
    response = admin_client.post("/content/skills/categories", json={"name": ""})

    assert response.status_code == 422
