"""GitHub REST client for the public repos of one account.

Fetches ``GET /users/{username}/repos`` page by page and the README of each
repo, and checks every repo where it arrives, so a malformed answer never
reaches the database. The account is ``GITHUB_USERNAME`` (default ``wediga``)
and an optional ``GITHUB_TOKEN`` only lifts the hourly rate limit, never logged
or written anywhere. Any failure raises ``GithubApiError``.
"""

import os
from http import HTTPStatus

import httpx2
from pydantic import ValidationError

from app.content.schemas import is_web_link
from app.github import readme
from app.github.schemas import SyncedRepo

GITHUB_API_BASE = "https://api.github.com"
PER_PAGE = 100
TIMEOUT = httpx2.Timeout(10.0)
# A hard bound on the page loop so a misbehaving API can never spin forever.
MAX_PAGES = 50

DEFAULT_USERNAME = "wediga"

# Asks the README endpoint for the Markdown itself instead of base64 in JSON.
README_MEDIA_TYPE = "application/vnd.github.raw+json"


class GithubApiError(RuntimeError):
    """Raised when the GitHub API cannot be read or answers unexpectedly."""


def username() -> str:
    return os.environ.get("GITHUB_USERNAME", DEFAULT_USERNAME) or DEFAULT_USERNAME


def _headers() -> dict[str, str]:
    """Build request headers, adding the optional token when present.

    The token goes into the Authorization header for the request alone, so it
    never reaches a log line or the database.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _get(client: httpx2.Client, path: str, **kwargs) -> httpx2.Response:
    try:
        return client.get(path, **kwargs)
    except httpx2.HTTPError as exc:
        # Only the error class, not the request internals, so nothing
        # sensitive leaks into a log, a response or the database.
        raise GithubApiError(
            f"request to GitHub failed: {exc.__class__.__name__}"
        ) from exc


def _readme(client: httpx2.Client, name: str) -> str:
    """Return the README of a repo as Markdown, empty when it has none."""
    response = _get(
        client,
        f"/repos/{username()}/{name}/readme",
        headers={"Accept": README_MEDIA_TYPE},
    )

    if response.status_code == HTTPStatus.NOT_FOUND:
        return ""

    if response.status_code != HTTPStatus.OK:
        raise GithubApiError(f"GitHub returned status {response.status_code}")

    return response.text


def _parse(raw: dict, markdown: str) -> SyncedRepo:
    """Turn a GitHub repo object and its README into what the sync stores."""
    homepage = raw.get("homepage")
    texts = {
        "name": raw.get("name"),
        "description": raw.get("description"),
        **readme.sections(markdown),
    }

    return SyncedRepo.model_validate(
        {
            "github_id": raw.get("id"),
            # A homepage that is no web link is never shown, so it is dropped.
            "homepage_url": homepage if homepage and is_web_link(homepage) else None,
            "archived": raw.get("archived"),
            "topics": raw.get("topics"),
            "texts": {key: text for key, text in texts.items() if text},
        }
    )


def _page(client: httpx2.Client, page: int) -> list[dict]:
    response = _get(
        client,
        f"/users/{username()}/repos",
        params={"per_page": PER_PAGE, "page": page},
    )

    if response.status_code != HTTPStatus.OK:
        raise GithubApiError(f"GitHub returned status {response.status_code}")

    batch = response.json()

    if not isinstance(batch, list) or not all(
        isinstance(item, dict) and isinstance(item.get("name"), str) and item["name"]
        for item in batch
    ):
        raise GithubApiError("unexpected GitHub response shape")

    return batch


def fetch_repos(*, client: httpx2.Client | None = None) -> list[SyncedRepo]:
    """Return the account's public repos with their READMEs.

    Everything is fetched before anything returns, so the caller can write it
    in one transaction and a failure raises ``GithubApiError`` instead of
    returning a partial list. A ``client`` may be injected for tests.
    """
    owns_client = client is None
    if client is None:
        client = httpx2.Client(
            base_url=GITHUB_API_BASE, headers=_headers(), timeout=TIMEOUT
        )
    try:
        raw_repos: list[dict] = []

        for page in range(1, MAX_PAGES + 1):
            batch = _page(client, page)
            raw_repos.extend(batch)

            if len(batch) < PER_PAGE:
                break

        try:
            return [_parse(raw, _readme(client, raw["name"])) for raw in raw_repos]
        except ValidationError:
            raise GithubApiError("unexpected GitHub response shape") from None
    finally:
        if owns_client:
            client.close()
