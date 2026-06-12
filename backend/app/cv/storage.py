"""Storage for the single uploaded CV PDF.

The CV is one uploaded PDF, kept under a fixed name in the data volume. There
is no database row, the file's presence is the whole state. The fixed name
means a client filename never reaches the path, so an upload can neither
traverse out of the directory nor collide with another file. The write goes
through a temporary file in the same directory and an atomic ``replace``, so a
swap is all-or-nothing and an interrupted upload never leaves a half-written
PDF at the served path.
"""

from pathlib import Path

from app.paths import cv_dir

# The fixed on-disk name. The client filename is never used.
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
    # Atomic on the same filesystem, so the served file is never half-written.
    tmp.replace(cv_path())
