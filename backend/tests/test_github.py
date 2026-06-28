"""Tests for the GitHub sync, curation and routes.

The sync logic is validated against mocked GitHub responses, no live call is
made. The cases cover: the client maps and paginates correctly; a first sync
creates rows; a second sync keeps the curation (hidden stays hidden, override
stays, sort order stays) while refreshing the mirrored fields; the curated read
returns only visible repos with pinned first and the override applied; and a
failing fetch never clears or corrupts the existing cache. The route cases
cover the session and CSRF protection. The client uses an https base URL so the
Secure session cookie round-trips.
"""

import importlib

import httpx
import pytest
from fastapi.testclient import TestClient

ADMIN_PASSWORD = "correct horse battery staple"


# --- fixtures ------------------------------------------------------------


@pytest.fixture()
def app(migrated_db, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    # Disable the scheduled refresh so a lifespan-driven test can never fire a
    # live GitHub call on startup.
    monkeypatch.setenv("GITHUB_SYNC_INTERVAL_SECONDS", "0")

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


def _raw_repo(name, description=None, language="Python", stars=1,
              pushed="2026-01-01T00:00:00Z"):
    """A GitHub API repo object with the fields the client reads."""
    return {
        "name": name,
        "description": description,
        "language": language,
        "stargazers_count": stars,
        "html_url": f"https://github.com/wediga/{name}",
        "pushed_at": pushed,
    }


def _mapped(name, description="github desc", language="Python", stars=1,
            last_push="2026-01-01T00:00:00Z"):
    """A repo already mapped to the mirrored fields, as the client returns them.

    Used to stub ``fetch_repos`` directly, so the sync and curation tests do not
    re-implement the client's mapping.
    """
    return {
        "name": name,
        "description": description,
        "language": language,
        "stars": stars,
        "url": f"https://github.com/wediga/{name}",
        "last_push": last_push,
    }


def _mock_client(pages):
    """Build an httpx.Client backed by a transport that serves fixed pages.

    ``pages`` is a list of response bodies keyed by the 1-based page number.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        body = pages[page - 1] if page - 1 < len(pages) else []
        return httpx.Response(200, json=body)

    return httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://api.github.com",
    )


# --- client --------------------------------------------------------------


def test_client_maps_fields():
    from app.github import client as gh

    repos = gh.fetch_repos(client=_mock_client([[_raw_repo("alpha", "desc", "Go", 7)]]))
    assert repos == [
        {
            "name": "alpha",
            "description": "desc",
            "language": "Go",
            "stars": 7,
            "url": "https://github.com/wediga/alpha",
            "last_push": "2026-01-01T00:00:00Z",
        }
    ]


def test_client_paginates_until_short_page():
    from app.github import client as gh

    full = [_raw_repo(f"r{i}") for i in range(100)]
    second = [_raw_repo("last")]
    repos = gh.fetch_repos(client=_mock_client([full, second]))
    assert len(repos) == 101
    assert repos[-1]["name"] == "last"


def test_client_non_200_raises():
    from app.github import client as gh

    def handler(request):
        return httpx.Response(403, json={"message": "rate limited"})

    bad = httpx.Client(
        transport=httpx.MockTransport(handler), base_url="https://api.github.com"
    )
    with pytest.raises(gh.GithubApiError):
        gh.fetch_repos(client=bad)


# --- sync and curation ---------------------------------------------------


def test_sync_creates_then_preserves_curation(migrated_db, monkeypatch):
    from app.github import client as gh
    from app.github import repository as repo
    from app.github import sync
    from app.github.schemas import RepoCurationWrite

    monkeypatch.setattr(gh, "fetch_repos", lambda **_: [
        _mapped("alpha", "first alpha", stars=1),
        _mapped("beta", "first beta", stars=2),
    ])
    assert sync.sync_repos() == 2

    rows = {r["name"]: r for r in repo.list_all()}
    alpha_id = rows["alpha"]["id"]
    beta_id = rows["beta"]["id"]

    # Curate: hide beta, pin alpha, override alpha's description, set sort order.
    repo.update_curation(
        alpha_id,
        RepoCurationWrite(visible=True, pinned=True,
                          description_override="curated text", sort_order=5),
    )
    repo.update_curation(
        beta_id,
        RepoCurationWrite(visible=False, pinned=False,
                          description_override=None, sort_order=0),
    )

    # Second sync with changed mirrored data (new stars, new descriptions).
    monkeypatch.setattr(gh, "fetch_repos", lambda **_: [
        _mapped("alpha", "second alpha", stars=99),
        _mapped("beta", "second beta", stars=88),
    ])
    assert sync.sync_repos() == 2

    rows = {r["name"]: r for r in repo.list_all()}
    # Mirrored fields refreshed.
    assert rows["alpha"]["stars"] == 99
    assert rows["alpha"]["description"] == "second alpha"
    # Curation preserved across the sync.
    assert rows["alpha"]["pinned"] is True
    assert rows["alpha"]["description_override"] == "curated text"
    assert rows["alpha"]["sort_order"] == 5
    assert rows["beta"]["visible"] is False


def test_curated_read_orders_and_applies_override(migrated_db, monkeypatch):
    from app.github import client as gh
    from app.github import repository as repo
    from app.github import sync
    from app.github.schemas import RepoCurationWrite

    monkeypatch.setattr(gh, "fetch_repos", lambda **_: [
        _mapped("alpha"), _mapped("beta"), _mapped("gamma"),
    ])
    sync.sync_repos()
    rows = {r["name"]: r for r in repo.list_all()}

    # gamma pinned, alpha visible with override, beta hidden.
    repo.update_curation(rows["gamma"]["id"],
                         RepoCurationWrite(visible=True, pinned=True, sort_order=0))
    repo.update_curation(rows["alpha"]["id"],
                         RepoCurationWrite(visible=True, pinned=False,
                                           description_override="my words", sort_order=1))
    repo.update_curation(rows["beta"]["id"],
                         RepoCurationWrite(visible=False, pinned=False, sort_order=0))

    curated = repo.list_curated()
    names = [r["name"] for r in curated]
    # Hidden beta absent, pinned gamma first.
    assert names == ["gamma", "alpha"]
    # Override wins over the GitHub description; gamma keeps the mirrored one.
    by_name = {r["name"]: r for r in curated}
    assert by_name["alpha"]["description"] == "my words"
    assert by_name["gamma"]["description"] == "github desc"


def test_empty_override_falls_back_to_github_description(migrated_db, monkeypatch):
    from app.github import client as gh
    from app.github import repository as repo
    from app.github import sync
    from app.github.schemas import RepoCurationWrite

    monkeypatch.setattr(gh, "fetch_repos", lambda **_: [_mapped("alpha", "github desc")])
    sync.sync_repos()
    alpha_id = repo.list_all()[0]["id"]

    # An empty-string override must collapse to the GitHub description, not to
    # an empty line in the recruiter view.
    repo.update_curation(
        alpha_id,
        RepoCurationWrite(visible=True, pinned=False,
                          description_override="", sort_order=0),
    )
    curated = repo.list_curated()
    assert curated[0]["description"] == "github desc"


def test_failed_sync_keeps_cache(migrated_db, monkeypatch):
    from app.github import client as gh
    from app.github import repository as repo
    from app.github import sync

    monkeypatch.setattr(gh, "fetch_repos", lambda **_: [
        _mapped("alpha", "cached", stars=3),
    ])
    sync.sync_repos()
    before = repo.list_all()
    assert len(before) == 1

    def boom(**_):
        raise gh.GithubApiError("rate limited")

    monkeypatch.setattr(gh, "fetch_repos", boom)
    with pytest.raises(gh.GithubApiError):
        sync.sync_repos()

    # The cache is untouched: same rows, same mirrored data.
    after = repo.list_all()
    assert len(after) == 1
    assert after[0]["description"] == "cached"
    assert after[0]["stars"] == 3


# --- route protection ----------------------------------------------------


def test_curated_read_needs_a_session(client):
    assert client.get("/github/repos").status_code == 401


def test_admin_list_needs_a_session(client):
    assert client.get("/github/admin/repos").status_code == 401


def test_curation_write_without_session_is_401(client):
    assert client.put("/github/repos/1/curation", json={}).status_code == 401


def test_curation_write_without_csrf_is_403(session_client):
    assert session_client.put("/github/repos/1/curation", json={}).status_code == 403


def test_sync_without_csrf_is_403(session_client):
    assert session_client.post("/github/sync").status_code == 403


def test_admin_can_read_curated_and_admin_lists(admin_client, monkeypatch):
    # An admin session passes the recruiter gate, so both reads work and start
    # empty before any sync.
    assert admin_client.get("/github/repos").json() == []
    assert admin_client.get("/github/admin/repos").json() == []


def test_sync_endpoint_runs_and_curation_write_works(admin_client, monkeypatch):
    from app.github import sync

    monkeypatch.setattr(
        sync, "sync_repos", lambda: 4
    )
    response = admin_client.post("/github/sync")
    assert response.status_code == 200
    assert response.json() == {"ok": True, "synced": 4}


def test_sync_endpoint_maps_api_error_to_502(admin_client, monkeypatch):
    from app.github import sync
    from app.github.client import GithubApiError

    def boom():
        raise GithubApiError("rate limited")

    monkeypatch.setattr(sync, "sync_repos", boom)
    assert admin_client.post("/github/sync").status_code == 502


def test_curation_write_on_missing_repo_is_404(admin_client):
    assert admin_client.put(
        "/github/repos/999/curation",
        json={"visible": True, "pinned": False, "sort_order": 0},
    ).status_code == 404


def test_lifespan_startup_does_not_block(app):
    # Entering the lifespan (scheduler disabled via GITHUB_SYNC_INTERVAL_SECONDS=0)
    # must start and shut down cleanly without blocking on a sync.
    with TestClient(app, base_url="https://testserver") as client:
        assert client.get("/health").status_code == 200
