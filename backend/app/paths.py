"""Filesystem paths and locations used across the backend.

The repository root contains ``backend/``, ``content/`` and ``data/``.
Both ``data/`` and ``content/`` are gitignored. Environment variables allow
overriding the database file and content directory, which keeps tests and
alternative deployments isolated from the defaults.
"""

import os
from pathlib import Path

# backend/app/paths.py -> parents[0]=app, [1]=backend, [2]=repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = REPO_ROOT / "data"


def db_path() -> Path:
    """Return the SQLite database file path.

    ``WEDIGA_DB_PATH`` overrides the full path when set, otherwise the file
    lives at ``data/wediga.db``. The parent directory is created on demand.
    """
    override = os.environ.get("WEDIGA_DB_PATH")
    path = Path(override) if override else DATA_DIR / "wediga.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def content_dir() -> Path:
    """Return the content directory.

    ``WEDIGA_CONTENT_DIR`` overrides the location, otherwise ``content/`` at
    the repository root is used.
    """
    override = os.environ.get("WEDIGA_CONTENT_DIR")
    return Path(override) if override else REPO_ROOT / "content"


def cv_dir() -> Path:
    """Return the directory holding the uploaded CV PDF.

    It sits next to the database file, so it lands in the same writable data
    volume. Deriving it from ``db_path().parent`` means the ``WEDIGA_DB_PATH``
    override (set in the hardened container, where the repository root is
    read-only) carries over without a second environment variable.
    """
    return db_path().parent / "cv"
