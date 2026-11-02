"""Tests for the GitHub client, the README sections, the sync and the routes.

No live call is made: the client runs against a mocked transport, and the sync
tests stub ``fetch_repos``. The client uses an https base URL so the Secure
session cookie round-trips.
"""

import importlib

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.content.models import Technology
from app.db.connection import get_session
from app.github import client as gh
from app.github import repository, sync
from app.github.models import GithubRepo, GithubSync
from app.github.readme import sections
from app.github.schemas import SyncedRepo

ADMIN_PASSWORD = "correct horse battery staple"

README = """# Alpha

**Tagline** with [a link](https://example.com)

## Why This Exists

I wanted **bold** words, `code` and a [link](https://example.com).
A second line of the same paragraph.

![screenshot](shot.png)

## What It Does

### Model Performance

| Model | MAE |
|-------|-----|
| Forest | 0.83 |

- first item
- second *item*

```bash
## not a heading
curl example
```

---

<img src="x.png"> After the image.

## What I Learned

## Try It

Nothing of this is kept.
"""


# --- fixtures ------------------------------------------------------------


@pytest.fixture()
def app(migrated_db, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)
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


def _raw_repo(github_id, name, **fields):
    """A GitHub API repo object with the fields the client reads."""
    return {
        "id": github_id,
        "name": name,
        "description": None,
        "homepage": None,
        "archived": False,
        "topics": [],
        **fields,
    }


def _mock_client(pages, readmes=None, readme_status=None):
    """An httpx2.Client that serves fixed repo pages and READMEs by repo name.

    A repo without a README answers 404, unless ``readme_status`` sets another
    status for every README.
    """
    readmes = readmes or {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith("/readme"):
            name = request.url.path.split("/")[-2]

            if readme_status is not None:
                return httpx2.Response(readme_status)

            if name not in readmes:
                return httpx2.Response(404)

            return httpx2.Response(200, text=readmes[name])

        page = int(request.url.params.get("page", "1"))
        body = pages[page - 1] if page - 1 < len(pages) else []
        return httpx2.Response(200, json=body)

    return httpx2.Client(
        transport=httpx2.MockTransport(handler),
        base_url="https://api.github.com",
    )


def _repo(github_id, name, *, topics=(), archived=False, **texts) -> SyncedRepo:
    return SyncedRepo.model_validate(
        {
            "github_id": github_id,
            "homepage_url": None,
            "archived": archived,
            "topics": list(topics),
            "texts": {"name": name, **texts},
        }
    )


def _sync(monkeypatch, *repos: SyncedRepo) -> int:
    monkeypatch.setattr(gh, "fetch_repos", lambda **_: list(repos))
    return sync.sync_repos()


def _listed() -> dict[str, dict]:
    return {repo["texts"]["name"]: repo for repo in repository.overview()["repos"]}


def _count(model) -> int:
    with get_session() as session:
        return session.execute(select(func.count()).select_from(model)).scalar_one()


# --- README sections -----------------------------------------------------


def test_readme_sections_become_plain_text():
    assert sections(README) == {
        "problem": "I wanted bold words, code and a link. "
        "A second line of the same paragraph.",
        "solution": "Model Performance\n\n- first item\n- second item\n\nAfter the image.",
    }


def test_readme_without_sections_has_no_texts():
    assert sections("# Title\n\nJust an intro.\n\n## Usage\n\nRun it.") == {}


def test_why_it_ended_is_read():
    assert sections("## Why It Ended\n\nIt was done.") == {"ending": "It was done."}


# --- client --------------------------------------------------------------


def test_client_reads_repo_and_readme():
    raw = _raw_repo(
        7,
        "alpha",
        description="desc",
        homepage="https://alpha.example",
        archived=True,
        topics=["python", "fastapi"],
    )

    repos = gh.fetch_repos(client=_mock_client([[raw]], {"alpha": README}))

    assert repos == [
        SyncedRepo(
            github_id=7,
            homepage_url="https://alpha.example",
            archived=True,
            topics=["python", "fastapi"],
            texts={"name": "alpha", "description": "desc", **sections(README)},
        )
    ]


def test_client_drops_empty_texts_and_homepage_without_scheme():
    raw = _raw_repo(7, "alpha", description="", homepage="alpha.example")

    [repo] = gh.fetch_repos(client=_mock_client([[raw]]))

    assert repo.texts == {"name": "alpha"}
    assert repo.homepage_url is None


def test_client_paginates_until_short_page():
    full = [_raw_repo(i, f"r{i}") for i in range(100)]
    second = [_raw_repo(100, "last")]

    repos = gh.fetch_repos(client=_mock_client([full, second]))

    assert len(repos) == 101
    assert repos[-1].texts["name"] == "last"


def test_client_non_200_raises():
    def handler(request):
        return httpx2.Response(403, json={"message": "rate limited"})

    bad = httpx2.Client(
        transport=httpx2.MockTransport(handler), base_url="https://api.github.com"
    )

    with pytest.raises(gh.GithubApiError):
        gh.fetch_repos(client=bad)


def test_client_failing_readme_raises():
    client = _mock_client([[_raw_repo(7, "alpha")]], readme_status=500)

    with pytest.raises(gh.GithubApiError):
        gh.fetch_repos(client=client)


@pytest.mark.parametrize(
    "fields",
    [{"topics": ["Not A Topic"]}, {"id": None}, {"archived": None}],
    ids=["topic", "id", "archived"],
)
def test_client_rejects_a_malformed_repo(fields):
    client = _mock_client([[_raw_repo(7, "alpha", **fields)]])

    with pytest.raises(gh.GithubApiError):
        gh.fetch_repos(client=client)


# --- sync ----------------------------------------------------------------


def test_sync_writes_repos_texts_and_technologies(migrated_db, monkeypatch):
    with get_session() as session:
        session.add(Technology(topic="python", name="Python"))
        session.commit()

    count = _sync(
        monkeypatch,
        _repo(1, "beta", topics=["python", "dnd5e"], description="b", problem="p"),
        _repo(2, "Alpha"),
    )

    assert count == 2
    assert list(_listed()) == ["Alpha", "beta"]
    assert _listed()["beta"]["texts"] == {
        "name": "beta",
        "description": "b",
        "problem": "p",
    }
    # A new topic becomes a technology named like it, an existing one keeps
    # its name.
    assert _listed()["beta"]["technologies"] == ["Python", "dnd5e"]
    assert _count(Technology) == 2


def test_archived_repo(migrated_db, monkeypatch):
    _sync(monkeypatch, _repo(1, "alpha", archived=True))

    assert _listed()["alpha"]["archived"] is True


def test_second_sync_replaces_texts_and_topics(migrated_db, monkeypatch):
    _sync(monkeypatch, _repo(1, "alpha", topics=["python"], problem="old"))
    _sync(monkeypatch, _repo(1, "alpha", topics=["go"], description="new"))

    assert _listed()["alpha"]["technologies"] == ["go"]
    assert _listed()["alpha"]["texts"] == {"name": "alpha", "description": "new"}


def test_vanished_repo_is_not_listed_but_kept(migrated_db, monkeypatch):
    _sync(monkeypatch, _repo(1, "alpha"), _repo(2, "beta"))
    _sync(monkeypatch, _repo(1, "alpha"))

    assert list(_listed()) == ["alpha"]
    assert _count(GithubRepo) == 2


def test_rename_keeps_the_repo(migrated_db, monkeypatch):
    _sync(monkeypatch, _repo(1, "old-name"))
    [before] = repository.overview()["repos"]

    _sync(monkeypatch, _repo(1, "new-name"))
    [after] = repository.overview()["repos"]

    assert after["id"] == before["id"]
    assert after["texts"]["name"] == "new-name"


def test_failed_sync_keeps_the_last_successful_one(migrated_db, monkeypatch):
    _sync(monkeypatch, _repo(1, "alpha"))

    def boom(**_):
        raise gh.GithubApiError("GitHub returned status 403")

    monkeypatch.setattr(gh, "fetch_repos", boom)

    with pytest.raises(gh.GithubApiError):
        sync.sync_repos()

    overview = repository.overview()
    assert overview["last_sync"]["error"] == "GitHub returned status 403"
    assert overview["last_sync"]["finished_at"] is not None
    assert list(_listed()) == ["alpha"]


def test_old_runs_are_removed_unless_a_repo_was_last_seen_in_them(
    migrated_db, monkeypatch
):
    _sync(monkeypatch, _repo(1, "alpha"), _repo(2, "beta"))
    _sync(monkeypatch, _repo(1, "alpha"))
    _sync(monkeypatch, _repo(1, "alpha"))

    # The run that last saw beta and the newest run stay.
    assert _count(GithubSync) == 2


# --- routes --------------------------------------------------------------


def test_sync_without_csrf_is_403(session_client):
    assert session_client.post("/github/sync").status_code == 403


def test_overview_starts_empty(migrated_db):
    assert repository.overview() == {"last_sync": None, "repos": []}


def test_sync_endpoint_runs_and_the_overview_shows_it(admin_client, monkeypatch):
    monkeypatch.setattr(
        gh, "fetch_repos", lambda **_: [_repo(1, "alpha", topics=["python"])]
    )

    response = admin_client.post("/github/sync")
    overview = repository.overview()

    assert response.json() == {"ok": True, "synced": 1}
    assert overview["last_sync"]["error"] is None
    assert list(_listed()) == ["alpha"]
    assert overview["repos"][0]["technologies"] == ["python"]


def test_sync_endpoint_maps_api_error_to_502(admin_client, monkeypatch):
    def boom():
        raise gh.GithubApiError("rate limited")

    monkeypatch.setattr(sync, "sync_repos", boom)
    assert admin_client.post("/github/sync").status_code == 502


def test_lifespan_startup_does_not_block(app):
    # Entering the lifespan (scheduler disabled via GITHUB_SYNC_INTERVAL_SECONDS=0)
    # must start and shut down cleanly without blocking on a sync.
    with TestClient(app, base_url="https://testserver") as client:
        assert client.get("/health").status_code == 200
