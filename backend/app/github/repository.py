"""Read and write functions for the ``github_repo`` table.

The invariant: the sync upsert writes only the mirrored fields, never the
curation. The ``ON CONFLICT`` update lists only description, language, stars,
url, last push and last sync, so an existing row's visible, pinned,
description override and sort order survive every sync. A new row takes the
schema's curation defaults. Every query goes through SQLAlchemy with bound
parameters, no SQL is built from input.
"""

from sqlalchemy import func, select
from sqlalchemy.dialects.sqlite import insert

from app.db.connection import get_session
from app.github.models import GithubRepo
from app.github.schemas import RepoCurationWrite

# Mirrored columns only; the curation columns (visible, pinned,
# description_override, sort_order) are deliberately absent.
_MIRRORED = ("description", "language", "stars", "url", "last_push", "last_sync")


def upsert_repos(repos: list[dict], synced_at: str) -> int:
    """Upsert the mirrored fields of each repo in one transaction.

    The batch commits once, so either all rows land or none do. Curation is
    never part of the write.
    """
    with get_session() as session:
        for repo in repos:
            statement = insert(GithubRepo).values(**repo, last_sync=synced_at)
            session.execute(
                statement.on_conflict_do_update(
                    index_elements=[GithubRepo.name],
                    set_={column: statement.excluded[column] for column in _MIRRORED},
                )
            )
        session.commit()

    return len(repos)


# Pinned first, then manual sort order, then name as a stable tie-breaker. One
# ordering serves both the admin and the curated recruiter list.
_ORDER = (GithubRepo.pinned.desc(), GithubRepo.sort_order, GithubRepo.name)


def list_all() -> list[dict]:
    """Return every repo with all fields, for the admin view."""
    with get_session() as session:
        repos = session.scalars(select(GithubRepo).order_by(*_ORDER))

        return [repo.as_dict() for repo in repos]


def list_curated() -> list[dict]:
    """Return the visible repos for the recruiter view, pinned first.

    ``description`` resolves to the admin override when set, else the mirrored
    GitHub description, so the view stays simple.
    """
    query = (
        select(
            GithubRepo.name,
            func.coalesce(
                func.nullif(GithubRepo.description_override, ""),
                GithubRepo.description,
            ).label("description"),
            GithubRepo.language,
            GithubRepo.stars,
            GithubRepo.url,
            GithubRepo.last_push,
            GithubRepo.pinned,
        )
        .where(GithubRepo.visible)
        .order_by(*_ORDER)
    )

    with get_session() as session:
        return [dict(row) for row in session.execute(query).mappings()]


def update_curation(repo_id: int, data: RepoCurationWrite) -> dict | None:
    """Set the four curation fields of one repo; return it or ``None``.

    Only the curation columns are written, leaving the mirrored fields as the
    last sync set them.
    """
    with get_session() as session:
        repo = session.get(GithubRepo, repo_id)

        if repo is None:
            return None

        repo.visible = data.visible
        repo.pinned = data.pinned
        repo.description_override = data.description_override
        repo.sort_order = data.sort_order
        session.commit()

        return repo.as_dict()
