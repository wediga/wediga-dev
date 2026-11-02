"""Tests for the portfolio: own texts over the ones from GitHub, the hint on
partly translated tiles, archived repos, the release and its routes.

The repos come from a stubbed sync. The client uses an https base URL so the
Secure session cookie round-trips.
"""

import importlib
import uuid

import pytest
from fastapi.testclient import TestClient

from app.github import client as gh
from app.github import sync
from app.github.schemas import SyncedRepo
from app.portfolio import repository
from app.portfolio.schemas import EntryWrite

ADMIN_PASSWORD = "correct horse battery staple"

# A repo id that no sync wrote.
MISSING = uuid.UUID(int=0)


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


# --- helpers -------------------------------------------------------------


def _sync(monkeypatch, *repos: dict) -> None:
    synced = [
        SyncedRepo.model_validate(
            {
                "github_id": github_id,
                "homepage_url": repo.pop("homepage_url", None),
                "archived": repo.pop("archived", False),
                "topics": repo.pop("topics", []),
                "texts": repo,
            }
        )
        for github_id, repo in enumerate(repos, start=1)
    ]
    monkeypatch.setattr(gh, "fetch_repos", lambda **_: synced)
    sync.sync_repos()


def _repo_ids() -> dict[str, uuid.UUID]:
    return {
        repo["texts"]["name"]: repo["id"]
        for repo in repository.admin_overview()["repos"]
    }


def _status_id(key: str = "done") -> uuid.UUID:
    statuses = repository.admin_overview()["statuses"]

    return next(status["id"] for status in statuses if status["key"] == key)


def _save(repo: str, /, *, published: bool = True, sort_order: int = 0, **texts):
    entry = EntryWrite.model_validate(
        {
            "project_status_id": _status_id(),
            "sort_order": sort_order,
            "published": published,
            "texts": texts,
        }
    )

    assert repository.save_entry(_repo_ids()[repo], entry)


def _tiles() -> dict[str, dict]:
    return {tile["texts"]["name"]: tile for tile in repository.tiles()}


def _entry(name: str) -> dict:
    repos = repository.admin_overview()["repos"]

    return next(repo["entry"] for repo in repos if repo["texts"]["name"] == name)


# --- texts ---------------------------------------------------------------


def test_own_texts_replace_the_ones_from_github(migrated_db, monkeypatch) -> None:
    _sync(monkeypatch, {"name": "alpha", "description": "en", "problem": "en"})
    _save("alpha", description="de", problem="  ")
    [tile] = repository.tiles()

    # A blank own text counts as none, so the one from GitHub stays.
    assert tile["texts"] == {"name": "alpha", "description": "de", "problem": "en"}


def test_github_change_shows_without_an_own_text(migrated_db, monkeypatch) -> None:
    _sync(monkeypatch, {"name": "alpha", "description": "old"})
    _save("alpha")
    _sync(monkeypatch, {"name": "alpha", "description": "new"})

    assert _tiles()["alpha"]["texts"]["description"] == "new"


@pytest.mark.parametrize(
    ("published", "texts", "partly"),
    [
        (True, {"description": "de"}, True),
        (True, {"name": "Alpha", "description": "de"}, False),
        (True, {}, False),
        (False, {"description": "de"}, False),
    ],
    ids=["some-fields", "every-field", "no-own-text", "not-published"],
)
def test_hint_on_partly_translated_tiles(
    migrated_db, monkeypatch, published, texts, partly
) -> None:
    _sync(monkeypatch, {"name": "alpha", "description": "en"})
    _save("alpha", published=published, **texts)

    assert _entry("alpha")["partly_translated"] is partly


def test_ending_reaches_the_tile(migrated_db, monkeypatch) -> None:
    _sync(monkeypatch, {"name": "alpha", "ending": "Moved on"})
    _save("alpha")

    assert _tiles()["alpha"]["texts"]["ending"] == "Moved on"


# --- tiles ---------------------------------------------------------------


def test_tile_carries_status_archive_and_links(migrated_db, monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_USERNAME", "someone")
    _sync(
        monkeypatch,
        {
            "name": "alpha",
            "archived": True,
            "homepage_url": "https://alpha.example",
            "topics": ["python"],
        },
    )
    _save("alpha")
    tile = _tiles()["alpha"]

    assert tile["archived"] is True
    assert tile["status"]["label"] == "Fertig"
    assert tile["technologies"] == ["python"]
    assert tile["demo_url"] == "https://alpha.example"
    assert tile["github_url"] == "https://github.com/someone/alpha"


def test_only_published_repos_of_the_last_sync_show_in_order(
    migrated_db, monkeypatch
) -> None:
    _sync(
        monkeypatch,
        {"name": "alpha"},
        {"name": "beta"},
        {"name": "delta"},
        {"name": "gamma"},
    )
    _save("alpha", sort_order=2)
    _save("beta", sort_order=1)
    # An unpublished entry stays among the rest by name, whatever its order.
    _save("gamma", published=False, sort_order=-1)

    assert list(_tiles()) == ["beta", "alpha"]
    assert list(_repo_ids()) == ["beta", "alpha", "delta", "gamma"]

    # A repo the last sync did not see drops out.
    _sync(monkeypatch, {"name": "alpha"})

    assert list(_tiles()) == ["alpha"]


def test_taking_the_release_back_keeps_the_texts(migrated_db, monkeypatch) -> None:
    _sync(monkeypatch, {"name": "alpha"})
    _save("alpha", name="Alpha")
    _save("alpha", published=False, name="Alpha")

    assert _tiles() == {}
    assert _entry("alpha")["texts"] == {"name": "Alpha"}

    _save("alpha", name="Alpha")

    assert list(_tiles()) == ["Alpha"]


def test_saving_a_missing_repo_fails(migrated_db) -> None:
    entry = EntryWrite(project_status_id=_status_id(), published=True)

    assert not repository.save_entry(MISSING, entry)


# --- routes --------------------------------------------------------------


def test_reads_need_a_session(client) -> None:
    assert client.get("/portfolio").status_code == 401
    assert client.get("/portfolio/admin").status_code == 401


def test_write_without_csrf_is_403(session_client) -> None:
    response = session_client.put(f"/portfolio/admin/repos/{MISSING}", json={})

    assert response.status_code == 403


def test_admin_publishes_a_repo_through_the_routes(admin_client, monkeypatch) -> None:
    _sync(monkeypatch, {"name": "alpha"})
    overview = admin_client.get("/portfolio/admin").json()
    [repo] = overview["repos"]
    body = {
        "project_status_id": overview["statuses"][0]["id"],
        "published": True,
        "texts": {"description": "de"},
    }

    response = admin_client.put(f"/portfolio/admin/repos/{repo['id']}", json=body)
    [tile] = admin_client.get("/portfolio").json()

    assert response.json() == {"ok": True}
    assert tile["texts"] == {"name": "alpha", "description": "de"}


def test_write_for_a_missing_repo_is_404(admin_client) -> None:
    body = {"project_status_id": str(_status_id()), "published": True}
    response = admin_client.put(f"/portfolio/admin/repos/{MISSING}", json=body)

    assert response.status_code == 404


def test_write_with_an_unknown_text_field_is_422(admin_client) -> None:
    body = {
        "project_status_id": str(_status_id()),
        "published": True,
        "texts": {"x": "y"},
    }
    response = admin_client.put(f"/portfolio/admin/repos/{MISSING}", json=body)

    assert response.status_code == 422
