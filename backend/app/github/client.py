"""GitHub REST client for the public repos of one account.

The client fetches ``GET /users/{username}/repos`` page by page and maps each
repo onto the mirrored ``github_repo`` fields. The account comes from
``GITHUB_USERNAME`` (default ``wediga``) and an optional ``GITHUB_TOKEN`` only
raises the hourly rate limit, nothing else; the token is read from the
environment, never logged and never written anywhere. Any non-200 or transport
failure raises ``GithubApiError`` so the caller can fail cleanly without ever
touching the cache.
"""

import os

import httpx

GITHUB_API_BASE = "https://api.github.com"
PER_PAGE = 100
TIMEOUT = httpx.Timeout(10.0)
# A hard bound on the page loop so a misbehaving API can never spin forever.
MAX_PAGES = 50

DEFAULT_USERNAME = "wediga"


class GithubApiError(RuntimeError):
    """Raised when the GitHub API cannot be read or returns a non-200."""


def _username() -> str:
    return os.environ.get("GITHUB_USERNAME", DEFAULT_USERNAME) or DEFAULT_USERNAME


def _headers() -> dict[str, str]:
    """Build request headers, adding the optional token when present.

    The token only lifts the rate limit. It is taken from the environment and
    placed in the Authorization header for the request alone, so it never
    reaches a log line or the database.
    """
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _map_repo(raw: dict) -> dict:
    """Map a GitHub repo object onto the mirrored github_repo fields."""
    return {
        "name": raw.get("name"),
        "description": raw.get("description"),
        "language": raw.get("language"),
        "stars": raw.get("stargazers_count", 0),
        "url": raw.get("html_url"),
        "last_push": raw.get("pushed_at"),
    }


def fetch_repos(*, client: httpx.Client | None = None) -> list[dict]:
    """Return the account's public repos mapped to the mirrored fields.

    The pages are fetched in full before anything is returned, so the caller
    can write them in one transaction. A ``client`` may be injected for tests;
    otherwise one is built and closed here. Any failure raises
    ``GithubApiError`` and never returns a partial list.
    """
    owns_client = client is None
    if client is None:
        client = httpx.Client(
            base_url=GITHUB_API_BASE, headers=_headers(), timeout=TIMEOUT
        )
    try:
        username = _username()
        repos: list[dict] = []
        for page in range(1, MAX_PAGES + 1):
            try:
                response = client.get(
                    f"/users/{username}/repos",
                    params={"per_page": PER_PAGE, "page": page},
                )
            except httpx.HTTPError as exc:
                # Surface only the error class, never the request internals,
                # so nothing sensitive can leak into a log or response.
                raise GithubApiError(
                    f"request to GitHub failed: {exc.__class__.__name__}"
                ) from exc
            if response.status_code != 200:
                raise GithubApiError(
                    f"GitHub returned status {response.status_code}"
                )
            batch = response.json()
            if not isinstance(batch, list):
                raise GithubApiError("unexpected GitHub response shape")
            for item in batch:
                if not isinstance(item, dict) or not item.get("name"):
                    raise GithubApiError("unexpected GitHub response shape")
                repos.append(_map_repo(item))
            if len(batch) < PER_PAGE:
                break
        return repos
    finally:
        if owns_client:
            client.close()
