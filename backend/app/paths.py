"""Filesystem paths used across the backend.

The database file and content directory can be overridden by environment
variable, which keeps tests and alternative deployments off the defaults.
"""

import os
from pathlib import Path

# backend/app/paths.py -> parents[0]=app, [1]=backend, [2]=repo root
REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = REPO_ROOT / "data"


def db_path() -> Path:
    """Return the SQLite database file path.

    ``WEDIGA_DB_PATH`` overrides the full path, else ``data/wediga.db``. The
    parent directory is created on demand.
    """
    override = os.environ.get("WEDIGA_DB_PATH")
    path = Path(override) if override else DATA_DIR / "wediga.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def content_dir() -> Path:
    """Return the content directory.

    ``WEDIGA_CONTENT_DIR`` overrides the location, else ``content/`` at the
    repository root.
    """
    override = os.environ.get("WEDIGA_CONTENT_DIR")
    return Path(override) if override else REPO_ROOT / "content"


def cv_dir() -> Path:
    """Return the directory holding the uploaded CV PDF.

    Derived from ``db_path().parent`` so it lands in the same writable data
    volume and the ``WEDIGA_DB_PATH`` override (set in the hardened container
    with a read-only repository root) carries over without a second variable.
    """
    return db_path().parent / "cv"
