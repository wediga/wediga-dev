"""The sync step that ties the client to the repository layer.

The order keeps the cache safe: repos are fetched in full before the
transactional upsert, so if the fetch raises the database is never touched and
the existing cache stays whole.
"""

from app.db.connection import now
from app.github import client, repository


def sync_repos() -> int:
    """Fetch the public repos and upsert their mirrored fields.

    Returns the number of repos written. Raises ``GithubApiError`` from the
    client on any API problem, in which case nothing was written.
    """
    repos = client.fetch_repos()
    return repository.upsert_repos(repos, now())
