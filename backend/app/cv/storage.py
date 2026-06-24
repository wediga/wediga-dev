"""Storage for the single uploaded CV PDF.

The PDF is kept under a fixed name in the data volume, its presence is the
whole state (no database row). The fixed name keeps the client filename off the
path, so an upload can neither traverse out of the directory nor collide. The
write goes through a temporary file and an atomic ``replace``, so an
interrupted upload never leaves a half-written PDF at the served path.
"""

from pathlib import Path

from app.paths import cv_dir

# Fixed on-disk name; the client filename is never used.
CV_FILENAME = "cv.pdf"


def cv_path() -> Path:
    """Return the path of the stored CV PDF."""
    return cv_dir() / CV_FILENAME


def has_cv() -> bool:
    """Return whether a CV PDF is currently stored."""
    return cv_path().is_file()


def save_cv(data: bytes) -> None:
    """Write the PDF bytes to the fixed path, replacing any existing file."""
    directory = cv_dir()
    directory.mkdir(parents=True, exist_ok=True)
    tmp = directory / f".{CV_FILENAME}.tmp"
    tmp.write_bytes(data)
    # Atomic within the same filesystem.
    tmp.replace(cv_path())
