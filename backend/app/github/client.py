"""GitHub REST client for the public repos of one account.

Fetches ``GET /users/{username}/repos`` page by page and maps each repo onto
the mirrored ``github_repo`` fields. The account is ``GITHUB_USERNAME``
(default ``wediga``) and an optional ``GITHUB_TOKEN`` only lifts the hourly
rate limit, never logged or written anywhere. Any non-200 or transport failure
raises ``GithubApiError`` so the caller fails without touching the cache.
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


def _parse_batch(payload) -> list[dict]:
    """Validate one page payload and map its repos to the mirrored fields.

    Raises ``GithubApiError`` on a malformed page so it never reaches the cache.
    """
    if not isinstance(payload, list):
        raise GithubApiError("unexpected GitHub response shape")
    for item in payload:
        if not isinstance(item, dict) or not item.get("name"):
            raise GithubApiError("unexpected GitHub response shape")
    return [_map_repo(item) for item in payload]


def fetch_repos(*, client: httpx.Client | None = None) -> list[dict]:
    """Return the account's public repos mapped to the mirrored fields.

    All pages are fetched before anything returns, so the caller can write them
    in one transaction and a failure raises ``GithubApiError`` instead of
    returning a partial list. A ``client`` may be injected for tests.
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
                # Surface only the error class, not the request internals, so
                # nothing sensitive leaks into a log or response.
                raise GithubApiError(
                    f"request to GitHub failed: {exc.__class__.__name__}"
                ) from exc
            if response.status_code != 200:
                raise GithubApiError(
                    f"GitHub returned status {response.status_code}"
                )
            batch = response.json()
            repos.extend(_parse_batch(batch))
            if len(batch) < PER_PAGE:
                break
        return repos
    finally:
        if owns_client:
            client.close()
