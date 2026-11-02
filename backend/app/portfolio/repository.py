"""Read and write functions of the portfolio.

The portfolio builds on the repos of the latest successful sync, so a repo
that vanished from GitHub drops out of the admin list and the tiles while its
entry stays. Every query goes through SQLAlchemy with bound parameters, no SQL
is built from input.
"""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db.connection import get_session, now
from app.github import client
from app.github import repository as github
from app.github.models import GithubRepo, TextField
from app.portfolio.models import PortfolioEntry, PortfolioTextOverride, ProjectStatus
from app.portfolio.schemas import EntryWrite

GITHUB_WEB = "https://github.com"


def _statuses(session: Session) -> list[dict]:
    statuses = session.scalars(select(ProjectStatus).order_by(ProjectStatus.sort_order))

    return [
        {"id": status.id, "key": status.key, "label": status.label}
        for status in statuses
    ]


def _entries(session: Session) -> dict[uuid.UUID, dict]:
    """Return every entry with its own texts, keyed by the id of its repo."""
    rows = session.scalars(select(PortfolioEntry)).all()
    entries = {
        entry.id: {
            "project_status_id": entry.project_status_id,
            "sort_order": entry.sort_order,
            "published": entry.published_at is not None,
            "texts": {},
        }
        for entry in rows
    }

    for entry_id, key, value in session.execute(
        select(
            PortfolioTextOverride.portfolio_entry_id,
            TextField.key,
            PortfolioTextOverride.value,
        ).join(TextField)
    ):
        entries[entry_id]["texts"][key] = value

    return {entry.github_repo_id: entries[entry.id] for entry in rows}


def _partly_translated(entry: dict, github_texts: dict[str, str]) -> bool:
    own = entry["texts"]

    return entry["published"] and bool(own) and not own.keys() >= github_texts.keys()


def admin_overview() -> dict:
    """Return the latest run, the statuses and every repo with its entry."""
    overview = github.overview()

    with get_session() as session:
        statuses = _statuses(session)
        entries = _entries(session)

    repos = []

    for repo in overview["repos"]:
        entry = entries.get(repo["id"])

        if entry is not None:
            entry["partly_translated"] = _partly_translated(entry, repo["texts"])

        repos.append({**repo, "entry": entry})

    # Published first in their order, the rest stays sorted by name.
    def position(repo: dict) -> tuple[bool, int]:
        published = bool(repo["entry"] and repo["entry"]["published"])

        return not published, repo["entry"]["sort_order"] if published else 0

    repos.sort(key=position)

    return {**overview, "statuses": statuses, "repos": repos}


def tiles() -> list[dict]:
    """Return the published repos as tiles, in the order of their entries."""
    repos = github.overview()["repos"]

    with get_session() as session:
        statuses = {status["id"]: status for status in _statuses(session)}
        entries = _entries(session)

    published = [
        (entries[repo["id"]], repo)
        for repo in repos
        if repo["id"] in entries and entries[repo["id"]]["published"]
    ]
    published.sort(key=lambda pair: pair[0]["sort_order"])

    return [
        {
            "id": repo["id"],
            "texts": {**repo["texts"], **entry["texts"]},
            "status": statuses[entry["project_status_id"]],
            "archived": repo["archived"],
            "technologies": repo["technologies"],
            "demo_url": repo["homepage_url"],
            "github_url": f"{GITHUB_WEB}/{client.username()}/{repo['texts']['name']}",
        }
        for entry, repo in published
    ]


def save_entry(repo_id: uuid.UUID, data: EntryWrite) -> bool:
    """Write the entry of a repo and replace its own texts.

    A published entry keeps its first release time, and taking the release
    back keeps the texts. Returns False when there is no such repo.
    """
    with get_session() as session:
        if session.get(GithubRepo, repo_id) is None:
            return False

        entry = session.scalar(
            select(PortfolioEntry).where(PortfolioEntry.github_repo_id == repo_id)
        )

        if entry is None:
            entry = PortfolioEntry(
                github_repo_id=repo_id, project_status_id=data.project_status_id
            )
            session.add(entry)

        entry.project_status_id = data.project_status_id
        entry.sort_order = data.sort_order
        entry.published_at = (entry.published_at or now()) if data.published else None

        session.flush()
        session.execute(
            delete(PortfolioTextOverride).where(
                PortfolioTextOverride.portfolio_entry_id == entry.id
            )
        )
        # Every field has a row once a sync wrote a repo, and the repo exists.
        field_ids = dict(session.execute(select(TextField.key, TextField.id)).all())
        session.add_all(
            PortfolioTextOverride(
                portfolio_entry_id=entry.id, text_field_id=field_ids[key], value=value
            )
            for key, value in data.texts.items()
            if value.strip()
        )
        session.commit()

    return True
