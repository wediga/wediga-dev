"""Filesystem paths used across the backend.

The content directory can be overridden by environment variable, which keeps
tests and alternative deployments off the default.
"""

import os
from pathlib import Path

# backend/app/paths.py -> parents[0]=app, [1]=backend, [2]=repo root
REPO_ROOT = Path(__file__).resolve().parents[2]


def content_dir() -> Path:
    """Return the content directory.

    ``WEDIGA_CONTENT_DIR`` overrides the location, else ``content/`` at the
    repository root.
    """
    override = os.environ.get("WEDIGA_CONTENT_DIR")
    return Path(override) if override else REPO_ROOT / "content"
