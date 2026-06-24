"""Read and write functions for the ``github_repo`` table.

The invariant: the sync upsert writes only the mirrored fields, never the
curation. The ``ON CONFLICT`` clause lists only description, language, stars,
url, last push and last sync, so an existing row's visible, pinned,
description override and sort order survive every sync. A new row takes the
schema's curation defaults. Every query is parameterised, no SQL is built from
input.
"""

from app.db.connection import get_connection
from app.github.schemas import RepoCurationWrite

# Mirrored columns only; the curation columns (visible, pinned,
# description_override, sort_order) are deliberately absent.
_UPSERT = (
    "INSERT INTO github_repo "
    "(name, description, language, stars, url, last_push, last_sync) "
    "VALUES (:name, :description, :language, :stars, :url, :last_push, :last_sync) "
    "ON CONFLICT(name) DO UPDATE SET "
    "description = excluded.description, "
    "language = excluded.language, "
    "stars = excluded.stars, "
    "url = excluded.url, "
    "last_push = excluded.last_push, "
    "last_sync = excluded.last_sync"
)


def upsert_repos(repos: list[dict], synced_at: str) -> int:
    """Upsert the mirrored fields of each repo in one transaction.

    The batch commits once, so either all rows land or none do. Curation is
    never part of the write.
    """
    with get_connection() as conn:
        for repo in repos:
            conn.execute(_UPSERT, {**repo, "last_sync": synced_at})
        conn.commit()
    return len(repos)


def _row_to_read(row) -> dict:
    data = dict(row)
    data["visible"] = bool(data["visible"])
    data["pinned"] = bool(data["pinned"])
    return data


# Pinned first, then manual sort order, then name as a stable tie-breaker. One
# ordering serves both the admin and the curated recruiter list.
_ORDER = " ORDER BY pinned DESC, sort_order, name"


def list_all() -> list[dict]:
    """Return every repo with all fields, for the admin view."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, description, language, stars, url, last_push, "
            "last_sync, visible, pinned, description_override, sort_order "
            "FROM github_repo" + _ORDER
        ).fetchall()
    return [_row_to_read(row) for row in rows]


def list_curated() -> list[dict]:
    """Return the visible repos for the recruiter view, pinned first.

    ``description`` resolves to the admin override when set, else the mirrored
    GitHub description, so the view stays simple.
    """
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT name, "
            "COALESCE(NULLIF(description_override, ''), description) AS description, "
            "language, stars, url, last_push, pinned "
            "FROM github_repo WHERE visible = 1" + _ORDER
        ).fetchall()
    result = []
    for row in rows:
        data = dict(row)
        data["pinned"] = bool(data["pinned"])
        result.append(data)
    return result


def _get(conn, repo_id: int) -> dict | None:
    row = conn.execute(
        "SELECT id, name, description, language, stars, url, last_push, "
        "last_sync, visible, pinned, description_override, sort_order "
        "FROM github_repo WHERE id = ?",
        (repo_id,),
    ).fetchone()
    return _row_to_read(row) if row is not None else None


def update_curation(repo_id: int, data: RepoCurationWrite) -> dict | None:
    """Set the four curation fields of one repo; return it or ``None``.

    Only the curation columns are written, leaving the mirrored fields as the
    last sync set them.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE github_repo SET "
            "visible = ?, pinned = ?, description_override = ?, sort_order = ? "
            "WHERE id = ?",
            (
                1 if data.visible else 0,
                1 if data.pinned else 0,
                data.description_override,
                data.sort_order,
                repo_id,
            ),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
        return _get(conn, repo_id)
