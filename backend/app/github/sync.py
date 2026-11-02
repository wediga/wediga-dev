"""One run of the sync, from the GitHub API into the database.

The run is saved before the fetch. Everything is fetched before anything is
written, so a failed fetch only marks the run with its error and the repos of
the last successful run stay as they are.
"""

from app.db.connection import now
from app.github import client, repository


def sync_repos() -> int:
    """Fetch the public repos and write them, returning how many there are.

    Raises ``GithubApiError`` from the client on any API problem, after the run
    is saved with the error.
    """
    run_id = repository.start_run(now())

    try:
        repos = client.fetch_repos()
    except client.GithubApiError as exc:
        repository.fail_run(run_id, str(exc), now())

        raise

    repository.finish_run(run_id, repos, now())

    return len(repos)
