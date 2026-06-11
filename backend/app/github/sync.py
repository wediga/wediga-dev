"""The sync step that ties the client to the repository layer.

The order is what keeps the cache safe: the repos are fetched in full first,
and only a complete fetch reaches the transactional upsert. If the fetch raises
(a non-200, a rate limit, a transport error), the database is never touched and
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
