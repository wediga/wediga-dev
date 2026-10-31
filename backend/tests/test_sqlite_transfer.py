"""Tests for the one-off transfer from the old SQLite file into PostgreSQL.

Each test builds a SQLite file with the schema the old migration runner left
behind (``0001_initial.sql`` and ``0002_admin_totp.sql``), and PostgreSQL
already holds rows from the bootstrap and the GitHub sync, as it does on the
server after the deploy.
"""

import os
import sqlite3
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select

OLD_SCHEMA = """
CREATE TABLE admin (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    totp_secret TEXT,
    totp_enabled INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE project (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    tagline TEXT,
    problem TEXT,
    solution TEXT,
    learning TEXT,
    tech_stack TEXT,
    demo_link TEXT,
    github_link TEXT,
    status TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    visible INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE skill_category (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE skill (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_id INTEGER NOT NULL REFERENCES skill_category (id),
    name TEXT NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE (category_id, name)
);
CREATE TABLE github_repo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    language TEXT,
    stars INTEGER,
    url TEXT,
    last_push TEXT,
    last_sync TEXT,
    visible INTEGER NOT NULL DEFAULT 1,
    pinned INTEGER NOT NULL DEFAULT 0,
    description_override TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE recruiter_link (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL UNIQUE,
    label TEXT,
    created_at TEXT NOT NULL,
    expires_at TEXT,
    revoked_at TEXT
);
CREATE TABLE link_view (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    link_id INTEGER NOT NULL REFERENCES recruiter_link (id),
    viewed_at TEXT NOT NULL,
    origin TEXT
);
CREATE TABLE site_setting (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TEXT NOT NULL
);
"""

# The rows are inserted with ids that do not start at 1, so a test notices if a
# reference keeps the old number instead of following the new id.
OLD_ROWS = """
INSERT INTO schema_migrations VALUES ('0001_initial', '2026-06-20T10:00:00+00:00');
INSERT INTO admin VALUES
    (1, 'old-hash', '2026-06-20T10:00:00+00:00', '2026-07-01T10:00:00+00:00',
     'secret', 1);
INSERT INTO recruiter_link VALUES
    (7, 'kept-token', 'Acme', '2026-09-01T08:00:00+00:00', NULL, NULL),
    (9, 'revoked-token', 'Initech', '2026-09-02T08:00:00+00:00',
     '2026-12-31T23:59:59+00:00', '2026-09-10T08:00:00+00:00');
INSERT INTO link_view VALUES
    (3, 9, '2026-09-03T08:00:00+00:00', 'net-a'),
    (4, 7, '2026-09-04T08:00:00+00:00', 'net-b'),
    (5, 7, '2026-09-05T08:00:00+00:00', 'net-b');
INSERT INTO project (id, name, tech_stack, sort_order, visible) VALUES
    (4, 'Shown', '["Python", "FastAPI"]', 2, 1),
    (6, 'Hidden', NULL, 1, 0);
INSERT INTO skill_category VALUES (5, 'Backend', 1), (8, 'Frontend', 2);
INSERT INTO skill VALUES (2, 8, 'TypeScript', 1), (3, 5, 'Python', 1);
INSERT INTO github_repo VALUES
    (11, 'old-repo', 'From GitHub', 'Python', 3, 'https://github.com/x/old-repo',
     '2026-08-01T12:00:00Z', '2026-10-29T03:00:00+00:00', 0, 1, 'Own text', 4);
INSERT INTO site_setting VALUES
    ('about_text', 'Hello', '2026-07-01T10:00:00+00:00'),
    ('contact', '{"email": "a@b.example"}', '2026-07-01T10:00:00+00:00');
"""

PDF_BYTES = b"%PDF-1.4\n%%EOF\n"
CV_MTIME = datetime(2026, 9, 15, 12, 0, tzinfo=UTC)


@pytest.fixture()
def data_dir(tmp_path):
    """The old data volume with the SQLite file and the CV."""
    database = sqlite3.connect(tmp_path / "wediga.db")
    database.executescript(OLD_SCHEMA + OLD_ROWS)
    database.close()
    cv_file = tmp_path / "cv" / "cv.pdf"
    cv_file.parent.mkdir()
    cv_file.write_bytes(PDF_BYTES)
    os.utime(cv_file, (CV_MTIME.timestamp(), CV_MTIME.timestamp()))

    return tmp_path


@pytest.fixture()
def deployed_db(migrated_db, monkeypatch):
    """PostgreSQL right after the deploy, with a fresh admin and a synced repo."""
    monkeypatch.setenv("ADMIN_PASSWORD", "fresh password")

    from app.auth.bootstrap import ensure_admin
    from app.github.repository import upsert_repos

    ensure_admin()
    upsert_repos([{"name": "synced-repo"}], datetime.now(UTC))


def _execute(data_dir, sql: str) -> None:
    database = sqlite3.connect(data_dir / "wediga.db")
    database.executescript(sql)
    database.close()


def _all(model) -> list:
    from app.db.connection import get_session

    with get_session() as session:
        return list(session.scalars(select(model)))


def _count(model) -> int:
    from app.db.connection import get_session

    with get_session() as session:
        return session.scalar(select(func.count()).select_from(model)) or 0


def _assert_untouched() -> None:
    from app.auth.models import Admin
    from app.github.models import GithubRepo
    from app.recruiter.models import RecruiterLink

    (admin,) = _all(Admin)
    assert admin.password_hash != "old-hash"
    assert [repo.name for repo in _all(GithubRepo)] == ["synced-repo"]
    assert _count(RecruiterLink) == 0


def test_replaces_the_rows_from_the_deploy(deployed_db, data_dir):
    from app.auth.models import Admin
    from app.db.sqlite_transfer import main
    from app.github.models import GithubRepo

    assert main([str(data_dir)]) == 0

    (admin,) = _all(Admin)
    assert admin.password_hash == "old-hash"
    assert admin.totp_secret == "secret"
    assert admin.totp_enabled is True
    assert admin.created_at == datetime(2026, 6, 20, 10, tzinfo=UTC)
    (repo,) = _all(GithubRepo)
    assert repo.name == "old-repo"
    assert repo.visible is False
    assert repo.pinned is True
    assert repo.last_push == datetime(2026, 8, 1, 12, tzinfo=UTC)


def test_old_links_keep_working_and_keep_their_views(deployed_db, data_dir):
    from app.db.sqlite_transfer import main
    from app.recruiter.models import LinkView
    from app.recruiter.repository import LinkStatus, list_links, validate_token

    main([str(data_dir)])

    kept = validate_token("kept-token")
    revoked = validate_token("revoked-token")
    assert kept is not None
    assert kept[0] is LinkStatus.OK
    assert revoked is not None
    assert revoked[0] is LinkStatus.REVOKED
    origins = {view.origin: view.recruiter_link_id for view in _all(LinkView)}
    assert origins == {"net-a": revoked[1], "net-b": kept[1]}
    views = {link["label"]: link["view_count"] for link in list_links()}
    assert views == {"Acme": 2, "Initech": 1}


def test_converts_the_content(deployed_db, data_dir):
    from app.content.repository import (
        get_about,
        get_contact,
        list_projects,
        list_skill_categories,
    )
    from app.db.sqlite_transfer import main

    main([str(data_dir)])

    projects = {p["name"]: p for p in list_projects()}
    assert projects["Shown"]["tech_stack"] == ["Python", "FastAPI"]
    assert projects["Shown"]["visible"] is True
    assert projects["Hidden"]["tech_stack"] == []
    assert projects["Hidden"]["visible"] is False
    skills = {
        category["name"]: [skill["name"] for skill in category["skills"]]
        for category in list_skill_categories()
    }
    assert skills == {"Backend": ["Python"], "Frontend": ["TypeScript"]}
    assert get_about() == "Hello"
    assert get_contact() == {"email": "a@b.example"}


def test_moves_the_cv_with_its_upload_time(deployed_db, data_dir):
    from app.cv.models import CvDocument
    from app.db.sqlite_transfer import main

    main([str(data_dir)])

    (cv,) = _all(CvDocument)
    assert cv.content == PDF_BYTES
    assert cv.uploaded_at == CV_MTIME


def test_without_a_cv_file_there_is_no_cv(deployed_db, data_dir):
    from app.cv.models import CvDocument
    from app.db.sqlite_transfer import main

    (data_dir / "cv" / "cv.pdf").unlink()

    assert main([str(data_dir)]) == 0
    assert _count(CvDocument) == 0


def test_prints_the_row_counts_of_both_databases(deployed_db, data_dir, capsys):
    from app.db.sqlite_transfer import main

    main([str(data_dir)])

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split() == ["table", "sqlite", "postgres"]
    assert ["link_view", "3", "3"] in [line.split() for line in lines]
    assert ["cv_document", "1", "1"] in [line.split() for line in lines]


def test_refuses_a_missing_database_file(deployed_db, tmp_path, capsys):
    from app.db.sqlite_transfer import main

    assert main([str(tmp_path)]) == 1
    assert "wediga.db does not exist" in capsys.readouterr().err
    _assert_untouched()


def test_refuses_views_without_origin(deployed_db, data_dir, capsys):
    from app.db.sqlite_transfer import main

    _execute(data_dir, "UPDATE link_view SET origin = NULL WHERE id = 4;")

    assert main([str(data_dir)]) == 1
    assert "link_view rows without origin: [4]" in capsys.readouterr().err
    _assert_untouched()


def test_refuses_differing_row_counts(deployed_db, data_dir, monkeypatch, capsys):
    from app.db import sqlite_transfer

    monkeypatch.setattr(sqlite_transfer, "_transfer_github", lambda *_: None)

    assert sqlite_transfer.main([str(data_dir)]) == 1
    assert "row counts differ for: github_repo" in capsys.readouterr().err
    _assert_untouched()


def test_a_failure_halfway_writes_nothing(deployed_db, data_dir):
    from app.db.sqlite_transfer import main

    _execute(data_dir, "UPDATE skill SET category_id = 99 WHERE id = 2;")

    with pytest.raises(KeyError):
        main([str(data_dir)])

    _assert_untouched()
