"""Tests for the CV layer: PDF upload, download and gating.

The CV is a single uploaded PDF. The upload needs an admin session and a valid
CSRF token, and it accepts only a real PDF (declared application/pdf and
starting with the %PDF signature) under the size cap. The download and the
status sit behind the recruiter gate, which an admin session also satisfies.
The client uses an https base URL so the Secure session cookie round-trips.
"""

import importlib

import pytest
from fastapi.testclient import TestClient

ADMIN_PASSWORD = "correct horse battery staple"

# A minimal valid PDF: the %PDF signature is what the upload check looks for.
PDF_BYTES = b"%PDF-1.4\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF\n"


@pytest.fixture()
def app(migrated_db, monkeypatch):
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")

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
    assert client.post("/auth/login", json={"password": ADMIN_PASSWORD}).status_code == 200
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


def _upload(client: TestClient, content: bytes, content_type: str = "application/pdf"):
    return client.post("/cv", files={"file": ("upload.pdf", content, content_type)})


# --- upload --------------------------------------------------------------


def test_upload_then_download_round_trips(admin_client) -> None:
    assert admin_client.get("/cv/status").json() == {"present": False}

    upload = _upload(admin_client, PDF_BYTES)
    assert upload.status_code == 201
    assert upload.json() == {"present": True}
    assert admin_client.get("/cv/status").json() == {"present": True}

    download = admin_client.get("/cv/download")
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
    assert "attachment" in download.headers["content-disposition"]
    # A polyglot upload must never be sniffed as HTML.
    assert download.headers["x-content-type-options"] == "nosniff"
    # The download serves exactly the uploaded bytes.
    assert download.content == PDF_BYTES


def test_download_inline_disposition(admin_client) -> None:
    # The preview asks for inline, so the browser embeds it instead of saving.
    _upload(admin_client, PDF_BYTES)
    response = admin_client.get("/cv/download", params={"inline": "true"})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].startswith("inline")


def test_upload_replaces_existing(admin_client) -> None:
    _upload(admin_client, PDF_BYTES)
    replacement = b"%PDF-1.7\nreplaced\n%%EOF\n"
    assert _upload(admin_client, replacement).status_code == 201
    assert admin_client.get("/cv/download").content == replacement


def test_upload_rejects_non_pdf_content_type(admin_client) -> None:
    # A PDF body but a wrong declared type is refused on the type allowlist.
    response = _upload(admin_client, PDF_BYTES, content_type="image/png")
    assert response.status_code == 415


def test_upload_rejects_pdf_signature_mismatch(admin_client) -> None:
    # Declared as PDF but the bytes are not, so the signature check refuses it.
    response = _upload(admin_client, b"GIF89a not a pdf at all")
    assert response.status_code == 422


def test_upload_rejects_oversized_file(admin_client, monkeypatch) -> None:
    from app.cv import router

    monkeypatch.setattr(router, "MAX_PDF_BYTES", 16)
    response = _upload(admin_client, PDF_BYTES)
    assert response.status_code == 413
    # The oversized upload was never stored.
    assert admin_client.get("/cv/status").json() == {"present": False}


# --- gating --------------------------------------------------------------


def test_upload_without_session_is_401(client) -> None:
    assert _upload(client, PDF_BYTES).status_code == 401


def test_upload_without_csrf_is_403(session_client) -> None:
    assert _upload(session_client, PDF_BYTES).status_code == 403


def test_download_and_status_need_recruiter_session(client) -> None:
    assert client.get("/cv/download").status_code == 401
    assert client.get("/cv/status").status_code == 401


def test_download_without_upload_is_404(admin_client) -> None:
    assert admin_client.get("/cv/download").status_code == 404
