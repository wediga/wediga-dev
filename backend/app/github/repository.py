"""Read and write functions for the tables of the GitHub sync.

Only the sync writes them. A run is saved as soon as it starts, so a failed or
broken run stays visible, and a successful run writes every repo with its
texts and topics in one transaction. A missing text field is added on the
way, and a topic without a technology gets one named like the topic, an
existing technology is never changed. Every query
goes through SQLAlchemy with bound parameters, no SQL is built from input.
"""

import uuid
from collections import defaultdict
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.content.models import Technology
from app.db.connection import get_session
from app.github.models import (
    GithubRepo,
    GithubRepoTechnology,
    GithubRepoText,
    GithubSync,
    TextField,
)
from app.github.schemas import TEXT_FIELDS, SyncedRepo

# The columns of a repo that a later run overwrites.
_SYNCED_COLUMNS = ("homepage_url", "archived", "last_seen_sync_id")


def start_run(started_at: datetime) -> uuid.UUID:
    with get_session() as session:
        run = GithubSync(started_at=started_at)
        session.add(run)
        session.commit()

        return run.id


def fail_run(run_id: uuid.UUID, error: str, finished_at: datetime) -> None:
    with get_session() as session:
        session.execute(
            update(GithubSync)
            .where(GithubSync.id == run_id)
            .values(finished_at=finished_at, error=error)
        )
        session.commit()


def _field_ids(session: Session) -> dict[str, uuid.UUID]:
    session.execute(
        insert(TextField)
        .values([{"key": key} for key in TEXT_FIELDS])
        .on_conflict_do_nothing(index_elements=[TextField.key])
    )

    return dict(session.execute(select(TextField.key, TextField.id)).all())


def _technology_ids(session: Session, repos: list[SyncedRepo]) -> dict[str, uuid.UUID]:
    topics = {topic for repo in repos for topic in repo.topics}

    if not topics:
        return {}

    session.execute(
        insert(Technology)
        .values([{"topic": topic, "name": topic} for topic in topics])
        .on_conflict_do_nothing(index_elements=[Technology.topic])
    )

    return dict(
        session.execute(
            select(Technology.topic, Technology.id).where(Technology.topic.in_(topics))
        ).all()
    )


def _save_repo(
    session: Session,
    repo: SyncedRepo,
    run_id: uuid.UUID,
    field_ids: dict[str, uuid.UUID],
    technology_ids: dict[str, uuid.UUID],
) -> None:
    """Write one repo by its GitHub id and replace its texts and topics."""
    statement = insert(GithubRepo).values(
        github_id=repo.github_id,
        homepage_url=repo.homepage_url,
        archived=repo.archived,
        last_seen_sync_id=run_id,
    )
    repo_id = session.execute(
        statement.on_conflict_do_update(
            index_elements=[GithubRepo.github_id],
            set_={column: statement.excluded[column] for column in _SYNCED_COLUMNS},
        ).returning(GithubRepo.id)
    ).scalar_one()
    session.execute(
        delete(GithubRepoText).where(GithubRepoText.github_repo_id == repo_id)
    )
    session.execute(
        delete(GithubRepoTechnology).where(
            GithubRepoTechnology.github_repo_id == repo_id
        )
    )
    session.add_all(
        GithubRepoText(
            github_repo_id=repo_id, text_field_id=field_ids[key], value=value
        )
        for key, value in repo.texts.items()
    )
    session.add_all(
        GithubRepoTechnology(
            github_repo_id=repo_id, technology_id=technology_ids[topic]
        )
        for topic in repo.topics
    )


def finish_run(
    run_id: uuid.UUID, repos: list[SyncedRepo], finished_at: datetime
) -> None:
    """Write the repos of a successful run and mark it finished.

    Afterwards only the finished runs that some repo was last seen in are
    kept, besides this one, because nothing else reads them.
    """
    with get_session() as session:
        field_ids = _field_ids(session)
        technology_ids = _technology_ids(session, repos)

        for repo in repos:
            _save_repo(session, repo, run_id, field_ids, technology_ids)

        session.execute(
            update(GithubSync)
            .where(GithubSync.id == run_id)
            .values(finished_at=finished_at)
        )
        session.execute(
            delete(GithubSync).where(
                GithubSync.id != run_id,
                GithubSync.finished_at.is_not(None),
                GithubSync.id.not_in(select(GithubRepo.last_seen_sync_id)),
            )
        )
        session.commit()


def _repos_seen_in(session: Session, run_id: uuid.UUID) -> list[dict]:
    """Return the repos of one run with their texts and topics."""
    seen = GithubRepo.last_seen_sync_id == run_id
    repos = session.scalars(select(GithubRepo).where(seen)).all()
    texts: dict[uuid.UUID, dict[str, str]] = defaultdict(dict)
    technologies: dict[uuid.UUID, list[str]] = defaultdict(list)

    for repo_id, key, value in session.execute(
        select(GithubRepoText.github_repo_id, TextField.key, GithubRepoText.value)
        .join(TextField)
        .join(GithubRepo)
        .where(seen)
    ):
        texts[repo_id][key] = value

    for repo_id, name in session.execute(
        select(GithubRepoTechnology.github_repo_id, Technology.name)
        .join(Technology)
        .join(GithubRepo)
        .where(seen)
        .order_by(Technology.name)
    ):
        technologies[repo_id].append(name)

    listed = [
        {
            **repo.as_dict(),
            "texts": texts[repo.id],
            "technologies": technologies[repo.id],
        }
        for repo in repos
    ]

    return sorted(listed, key=lambda repo: repo["texts"]["name"].lower())


def overview() -> dict:
    """Return the latest run, and the repos of the latest successful one."""
    newest_first = GithubSync.started_at.desc()

    with get_session() as session:
        last = session.scalar(select(GithubSync).order_by(newest_first).limit(1))
        succeeded = session.scalar(
            select(GithubSync.id)
            .where(GithubSync.finished_at.is_not(None), GithubSync.error.is_(None))
            .order_by(newest_first)
            .limit(1)
        )

        return {
            "last_sync": last.as_dict() if last else None,
            "repos": _repos_seen_in(session, succeeded) if succeeded else [],
        }
