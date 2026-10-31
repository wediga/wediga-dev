"""One-off transfer of the old SQLite data and the CV file into PostgreSQL.

It runs once on the server after the switch to PostgreSQL, in a throwaway
container from the backend image with the old data volume mounted read-only:

    python -m app.db.sqlite_transfer /data

By then the bootstrap and the GitHub sync have already written rows, so every
table is emptied first. Each old integer id gets a new UUID, and the references
from ``skill`` and ``link_view`` follow the new ids. Everything happens in one
transaction that only commits once the row counts of both databases agree, so a
failed run leaves PostgreSQL as it was.
"""

import argparse
import json
import sqlite3
import sys
import uuid
from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.auth.models import Admin
from app.content.models import Project, SiteSetting, Skill, SkillCategory
from app.content.repository import ABOUT_KEY
from app.cv.models import CvDocument
from app.db.base import Base
from app.db.connection import get_session
from app.github.models import GithubRepo
from app.recruiter.models import LinkView, RecruiterLink
from app.recruiter.repository import _hash_token

DATABASE_FILE = "wediga.db"
CV_FILE = Path("cv") / "cv.pdf"

# The old tables and the models they move into, in the order they are filled
# and compared.
TABLES: dict[str, type[Base]] = {
    "admin": Admin,
    "recruiter_link": RecruiterLink,
    "link_view": LinkView,
    "project": Project,
    "skill_category": SkillCategory,
    "skill": Skill,
    "github_repo": GithubRepo,
    "site_setting": SiteSetting,
}


# The models with an old integer id, whose new UUID is read back after insert.
type _WithId = (
    Admin | RecruiterLink | LinkView | Project | SkillCategory | Skill | GithubRepo
)


class TransferError(Exception):
    """The transfer cannot go on, and nothing was written."""


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _optional_time(value: str | None) -> datetime | None:
    return _time(value) if value is not None else None


def _rows(source: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    return source.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()


def _add(
    session: Session,
    rows: Iterable[sqlite3.Row],
    build: Callable[[sqlite3.Row], _WithId],
) -> dict[int, uuid.UUID]:
    """Insert one new row per old row and return the new id for each old id."""
    added = {row["id"]: build(row) for row in rows}
    session.add_all(added.values())
    session.flush()

    return {old_id: row.id for old_id, row in added.items()}


def _check_origins(source: sqlite3.Connection) -> None:
    """Refuse views without an origin, which PostgreSQL no longer accepts."""
    missing = [
        row["id"]
        for row in source.execute("SELECT id FROM link_view WHERE origin IS NULL")
    ]

    if missing:
        raise TransferError(f"link_view rows without origin: {missing}")


def _empty_tables(session: Session) -> None:
    tables = ", ".join(table.fullname for table in Base.metadata.sorted_tables)
    session.execute(text(f"TRUNCATE {tables}"))


def _transfer_access(session: Session, source: sqlite3.Connection) -> None:
    _add(
        session,
        _rows(source, "admin"),
        lambda row: Admin(
            password_hash=row["password_hash"],
            totp_secret=row["totp_secret"],
            totp_enabled=bool(row["totp_enabled"]),
            created_at=_time(row["created_at"]),
            updated_at=_time(row["updated_at"]),
        ),
    )
    link_ids = _add(
        session,
        _rows(source, "recruiter_link"),
        lambda row: RecruiterLink(
            token_hash=_hash_token(row["token"]),
            label=row["label"],
            created_at=_time(row["created_at"]),
            expires_at=_optional_time(row["expires_at"]),
            revoked_at=_optional_time(row["revoked_at"]),
        ),
    )
    _add(
        session,
        _rows(source, "link_view"),
        lambda row: LinkView(
            recruiter_link_id=link_ids[row["link_id"]],
            viewed_at=_time(row["viewed_at"]),
            origin=row["origin"],
        ),
    )


def _transfer_content(session: Session, source: sqlite3.Connection) -> None:
    _add(
        session,
        _rows(source, "project"),
        lambda row: Project(
            name=row["name"],
            tagline=row["tagline"],
            problem=row["problem"],
            solution=row["solution"],
            learning=row["learning"],
            tech_stack=json.loads(row["tech_stack"]) if row["tech_stack"] else None,
            demo_link=row["demo_link"],
            github_link=row["github_link"],
            status=row["status"],
            sort_order=row["sort_order"],
            visible=bool(row["visible"]),
        ),
    )
    category_ids = _add(
        session,
        _rows(source, "skill_category"),
        lambda row: SkillCategory(name=row["name"], sort_order=row["sort_order"]),
    )
    _add(
        session,
        _rows(source, "skill"),
        lambda row: Skill(
            category_id=category_ids[row["category_id"]],
            name=row["name"],
            sort_order=row["sort_order"],
        ),
    )
    # The about text was stored as plain text, contact and impressum as JSON.
    session.add_all(
        SiteSetting(
            key=row["key"],
            value=row["value"] if row["key"] == ABOUT_KEY else json.loads(row["value"]),
            updated_at=_time(row["updated_at"]),
        )
        for row in source.execute("SELECT * FROM site_setting ORDER BY key")
    )


def _transfer_github(session: Session, source: sqlite3.Connection) -> None:
    _add(
        session,
        _rows(source, "github_repo"),
        lambda row: GithubRepo(
            name=row["name"],
            description=row["description"],
            language=row["language"],
            stars=row["stars"],
            url=row["url"],
            last_push=_optional_time(row["last_push"]),
            last_sync=_optional_time(row["last_sync"]),
            visible=bool(row["visible"]),
            pinned=bool(row["pinned"]),
            description_override=row["description_override"],
            sort_order=row["sort_order"],
        ),
    )


def _transfer_cv(session: Session, cv_file: Path) -> int:
    """Store the CV file if there is one and return how many rows that made."""
    if not cv_file.is_file():
        return 0

    uploaded_at = datetime.fromtimestamp(cv_file.stat().st_mtime, UTC)
    session.add(CvDocument(content=cv_file.read_bytes(), uploaded_at=uploaded_at))

    return 1


def _compare(
    session: Session, source: sqlite3.Connection, cv_rows: int
) -> list[tuple[str, int, int]]:
    """Count the rows on both sides and refuse any table where they differ."""
    session.flush()
    counts = [
        (
            table,
            source.execute(f"SELECT count(*) FROM {table}").fetchone()[0],
            session.execute(select(func.count()).select_from(model)).scalar_one(),
        )
        for table, model in TABLES.items()
    ]
    cv_count = session.execute(select(func.count(CvDocument.id))).scalar_one()
    counts.append(("cv_document", cv_rows, cv_count))
    mismatched = [table for table, old, new in counts if old != new]

    if mismatched:
        raise TransferError(f"row counts differ for: {', '.join(mismatched)}")

    return counts


def transfer(database_file: Path, cv_file: Path) -> list[tuple[str, int, int]]:
    """Replace the PostgreSQL data with the old data and return the row counts."""
    source = sqlite3.connect(f"file:{database_file}?mode=ro", uri=True)
    source.row_factory = sqlite3.Row

    try:
        _check_origins(source)

        with get_session() as session:
            _empty_tables(session)
            _transfer_access(session, source)
            _transfer_content(session, source)
            _transfer_github(session, source)
            counts = _compare(session, source, _transfer_cv(session, cv_file))
            session.commit()
    finally:
        source.close()

    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Move the old SQLite data and the CV into PostgreSQL."
    )
    parser.add_argument("data_dir", type=Path, help="the old data volume")
    data_dir = parser.parse_args(argv).data_dir
    database_file = data_dir / DATABASE_FILE

    if not database_file.is_file():
        print(f"{database_file} does not exist", file=sys.stderr)

        return 1

    try:
        counts = transfer(database_file, data_dir / CV_FILE)
    except TransferError as error:
        print(f"Nothing was written: {error}", file=sys.stderr)

        return 1

    print(f"{'table':<16}{'sqlite':>8}{'postgres':>10}")

    for table, old, new in counts:
        print(f"{table:<16}{old:>8}{new:>10}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
