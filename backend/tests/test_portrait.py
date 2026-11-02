"""Tests for the portrait: upload, crop, public reads and gating.

The upload and the crop write need an admin session and a valid CSRF token.
The image and its crop are public, because the landing page and the contact
card show them to every visitor.
"""

import importlib
import re

import pytest
from fastapi.testclient import TestClient

from app.portrait.router import ACCEPTED_TYPES
from app.portrait.schemas import FOCUS_MAX, ZOOM_MAX, ZOOM_MIN
from tests.conftest import REPO_ROOT

ADMIN_PASSWORD = "correct horse battery staple"

# The first bytes are what the upload check looks for, the rest is filler.
JPEG_BYTES = b"\xff\xd8\xff\xe0" + b"jpeg"
PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"png"
WEBP_BYTES = b"RIFF\x00\x00\x00\x00WEBPVP8 " + b"webp"
UNCROPPED = {"x": 50, "y": 50, "zoom": 100}


@pytest.fixture()
def app(migrated_db, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)

    from app.auth.bootstrap import ensure_admin

    ensure_admin()
    main = importlib.import_module("app.main")

    return main.app


@pytest.fixture()
def client(app):
    """Anonymous client with no session."""
    return TestClient(app, base_url="https://testserver")


def _login(app) -> TestClient:
    client = TestClient(app, base_url="https://testserver")

    assert (
        client.post("/auth/login", json={"password": ADMIN_PASSWORD}).status_code == 200
    )

    return client


@pytest.fixture()
def session_client(app):
    """Logged-in client that does not send the CSRF header."""
    return _login(app)


@pytest.fixture()
def admin_client(app):
    """Logged-in client that sends a valid CSRF token on every request."""
    client = _login(app)
    token = client.get("/auth/csrf").json()["csrf_token"]
    client.headers.update({"X-CSRF-Token": token})

    return client


def _upload(client: TestClient, content: bytes, content_type: str):
    return client.post("/portrait", files={"file": ("upload", content, content_type)})


# --- upload and public reads ----------------------------------------------


@pytest.mark.parametrize(
    ("content", "content_type"),
    [(JPEG_BYTES, "image/jpeg"), (PNG_BYTES, "image/png"), (WEBP_BYTES, "image/webp")],
)
def test_upload_is_served_publicly(admin_client, client, content, content_type) -> None:
    response = _upload(admin_client, content, content_type)

    assert response.status_code == 201
    assert response.json() == UNCROPPED

    image = client.get("/portrait")

    assert image.status_code == 200
    assert image.content == content
    assert image.headers["content-type"] == content_type
    assert image.headers["x-content-type-options"] == "nosniff"
    assert image.headers["content-security-policy"] == "default-src 'none'"
    assert client.get("/portrait/crop").json() == UNCROPPED


def test_without_portrait_image_is_404_and_crop_empty(client) -> None:
    assert client.get("/portrait").status_code == 404
    assert client.get("/portrait/crop").json() is None


def test_upload_rejects_other_declared_type(admin_client) -> None:
    assert _upload(admin_client, JPEG_BYTES, "image/gif").status_code == 415


@pytest.mark.parametrize(
    ("content", "content_type"),
    [
        (b"<html>not an image</html>", "image/jpeg"),
        (PNG_BYTES, "image/jpeg"),
        (b"RIFF\x00\x00\x00\x00WAVEfmt ", "image/webp"),
    ],
)
def test_upload_rejects_bytes_that_do_not_match(
    admin_client, content, content_type
) -> None:
    assert _upload(admin_client, content, content_type).status_code == 422


def test_upload_rejects_oversized_file(admin_client, monkeypatch) -> None:
    from app.portrait import router

    monkeypatch.setattr(router, "MAX_IMAGE_BYTES", 4)

    assert _upload(admin_client, JPEG_BYTES, "image/jpeg").status_code == 413
    assert admin_client.get("/portrait").status_code == 404


# --- crop ------------------------------------------------------------------


@pytest.mark.parametrize(
    "crop", [{"x": 0, "y": 100, "zoom": 100}, {"x": 100, "y": 0, "zoom": 300}]
)
def test_crop_is_stored(admin_client, client, crop) -> None:
    _upload(admin_client, JPEG_BYTES, "image/jpeg")

    assert admin_client.put("/portrait/crop", json=crop).json() == crop
    assert client.get("/portrait/crop").json() == crop


def test_new_upload_resets_crop(admin_client, client) -> None:
    _upload(admin_client, JPEG_BYTES, "image/jpeg")
    admin_client.put("/portrait/crop", json={"x": 10, "y": 20, "zoom": 200})
    _upload(admin_client, PNG_BYTES, "image/png")

    assert client.get("/portrait/crop").json() == UNCROPPED
    assert client.get("/portrait").content == PNG_BYTES


@pytest.mark.parametrize(
    "crop",
    [
        {"x": -1, "y": 50, "zoom": 100},
        {"x": 50, "y": 101, "zoom": 100},
        {"x": 50, "y": 50, "zoom": 99},
        {"x": 50, "y": 50, "zoom": 301},
    ],
)
def test_crop_out_of_range_is_rejected(admin_client, crop) -> None:
    _upload(admin_client, JPEG_BYTES, "image/jpeg")

    assert admin_client.put("/portrait/crop", json=crop).status_code == 422


def test_crop_without_portrait_is_404(admin_client) -> None:
    assert admin_client.put("/portrait/crop", json=UNCROPPED).status_code == 404


# --- gating ----------------------------------------------------------------


def test_writes_without_session_are_401(client) -> None:
    assert _upload(client, JPEG_BYTES, "image/jpeg").status_code == 401
    assert client.put("/portrait/crop", json=UNCROPPED).status_code == 401


def test_writes_without_csrf_are_403(session_client) -> None:
    assert _upload(session_client, JPEG_BYTES, "image/jpeg").status_code == 403
    assert session_client.put("/portrait/crop", json=UNCROPPED).status_code == 403


# --- frontend --------------------------------------------------------------


def test_frontend_portrait_values_match_backend() -> None:
    source = (REPO_ROOT / "frontend" / "lib" / "portrait.ts").read_text(
        encoding="utf-8"
    )
    numbers = dict(re.findall(r"export const (\w+) = (\d+);", source))
    types = re.search(r"export const PORTRAIT_TYPES = \[(.*?)];", source)

    assert numbers == {
        "FOCUS_MAX": str(FOCUS_MAX),
        "ZOOM_MIN": str(ZOOM_MIN),
        "ZOOM_MAX": str(ZOOM_MAX),
    }
    assert types is not None
    assert tuple(re.findall(r'"([^"]+)"', types.group(1))) == ACCEPTED_TYPES
