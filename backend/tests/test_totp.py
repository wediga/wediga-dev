"""Tests for the admin TOTP second factor.

The code path is exercised against pyotp directly (generate a secret, compute a
valid code) rather than a real authenticator app, which keeps the suite
deterministic while covering setup, the two-step login and the rate limit.
"""

import importlib

import pyotp
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

ADMIN_PASSWORD = "correct horse battery staple"


@pytest.fixture()
def client(migrated_db, monkeypatch):
    """A TestClient with a bootstrapped admin and a TOTP encryption key set."""
    monkeypatch.setenv("ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("SESSION_SECRET", "test-session-secret")
    monkeypatch.setenv("TOTP_ENC_KEY", Fernet.generate_key().decode())

    from app.auth.bootstrap import ensure_admin

    ensure_admin()

    main = importlib.import_module("app.main")
    return TestClient(main.app, base_url="https://testserver")


def _password_login(client) -> None:
    response = client.post("/auth/login", json={"password": ADMIN_PASSWORD})
    assert response.status_code == 200


def _csrf_token(client) -> str:
    response = client.get("/auth/csrf")
    assert response.status_code == 200
    return response.json()["csrf_token"]


def _enable_totp(client) -> str:
    """Run setup and confirm, returning the secret for later code generation."""
    token = _csrf_token(client)
    setup = client.post("/auth/totp/setup", headers={"X-CSRF-Token": token})
    assert setup.status_code == 200
    secret = setup.json()["secret"]
    assert setup.json()["otpauth_uri"].startswith("otpauth://totp/")
    assert setup.json()["qr_svg"].startswith("data:image/svg+xml;base64,")

    code = pyotp.TOTP(secret).now()
    confirm = client.post(
        "/auth/totp/confirm",
        json={"code": code},
        headers={"X-CSRF-Token": token},
    )
    assert confirm.status_code == 200
    assert confirm.json() == {"ok": True, "enabled": True}
    return secret


def test_fernet_round_trip(monkeypatch) -> None:
    """A stored secret decrypts back to the original plaintext."""
    monkeypatch.setenv("TOTP_ENC_KEY", Fernet.generate_key().decode())
    from app.auth import totp

    secret = totp.generate_secret()
    assert totp.decrypt_secret(totp.encrypt_secret(secret)) == secret


def test_missing_key_raises(monkeypatch) -> None:
    """Encrypting without a key raises the handled key error, not a fallback."""
    monkeypatch.delenv("TOTP_ENC_KEY", raising=False)
    from app.auth import totp

    with pytest.raises(totp.TotpKeyError):
        totp.encrypt_secret("ABC")


def test_verify_code_small_case() -> None:
    """A code from pyotp verifies and a different one does not."""
    from app.auth import totp

    secret = totp.generate_secret()
    code = pyotp.TOTP(secret).now()
    assert totp.verify_code(secret, code) is True
    # A guaranteed-wrong code: flip the first digit away from the real one.
    wrong = ("1" if code[0] != "1" else "2") + code[1:]
    assert totp.verify_code(secret, wrong) is False
    assert totp.verify_code(secret, "") is False


def test_verify_code_accepts_one_step_drift() -> None:
    """A code from the neighbouring window passes, two steps away does not."""
    import time

    from app.auth import totp

    secret = totp.generate_secret()
    generator = pyotp.TOTP(secret)
    assert totp.verify_code(secret, generator.at(time.time() - 30)) is True
    assert totp.verify_code(secret, generator.at(time.time() - 90)) is False


def test_setup_requires_admin_session(client) -> None:
    """Setup is gated by the admin session, so a fresh client is rejected."""
    response = client.post("/auth/totp/setup", headers={"X-CSRF-Token": "x"})
    assert response.status_code == 401


def test_setup_requires_csrf(client) -> None:
    """Setup is a write, so a missing CSRF token is a 403."""
    _password_login(client)
    response = client.post("/auth/totp/setup")
    assert response.status_code == 403


def test_setup_and_confirm_enables_factor(client) -> None:
    """A confirmed code flips the factor on, reported by the status route."""
    _password_login(client)
    _enable_totp(client)
    status_response = client.get("/auth/totp/status")
    assert status_response.json() == {"enabled": True}


def test_setup_rejected_when_already_enabled(client) -> None:
    """Setup is refused once the factor is active, so it cannot disable it."""
    _password_login(client)
    _enable_totp(client)
    token = _csrf_token(client)
    response = client.post("/auth/totp/setup", headers={"X-CSRF-Token": token})
    assert response.status_code == 409
    # The factor stays on after the rejected setup.
    assert client.get("/auth/totp/status").json() == {"enabled": True}


def test_confirm_rejects_wrong_code(client) -> None:
    """A wrong confirmation code leaves the factor disabled."""
    _password_login(client)
    token = _csrf_token(client)
    setup = client.post("/auth/totp/setup", headers={"X-CSRF-Token": token})
    assert setup.status_code == 200
    confirm = client.post(
        "/auth/totp/confirm",
        json={"code": "000000"},
        headers={"X-CSRF-Token": token},
    )
    assert confirm.status_code == 401
    assert client.get("/auth/totp/status").json() == {"enabled": False}


def test_login_with_factor_demands_code(client) -> None:
    """With the factor on, the password alone grants no admin rights."""
    _password_login(client)
    _enable_totp(client)
    client.post("/auth/logout")

    login = client.post("/auth/login", json={"password": ADMIN_PASSWORD})
    assert login.status_code == 200
    assert login.json()["totp_required"] is True
    # pending_2fa carries no admin rights.
    assert client.get("/auth/me").status_code == 401


def test_login_totp_valid_code_opens_admin(client) -> None:
    """A valid code after the password promotes the session to admin."""
    _password_login(client)
    secret = _enable_totp(client)
    client.post("/auth/logout")

    client.post("/auth/login", json={"password": ADMIN_PASSWORD})
    code = pyotp.TOTP(secret).now()
    step = client.post("/auth/login/totp", json={"code": code})
    assert step.status_code == 200
    assert client.get("/auth/me").status_code == 200


def test_login_totp_invalid_code_stays_locked(client) -> None:
    """A wrong code keeps the session at pending and out of the admin area."""
    _password_login(client)
    _enable_totp(client)
    client.post("/auth/logout")

    client.post("/auth/login", json={"password": ADMIN_PASSWORD})
    step = client.post("/auth/login/totp", json={"code": "000000"})
    assert step.status_code == 401
    assert client.get("/auth/me").status_code == 401


def test_totp_step_requires_pending_state(client) -> None:
    """The code step rejects a request that never passed the password."""
    _password_login(client)
    secret = _enable_totp(client)
    client.post("/auth/logout")

    # No password step, so no pending_2fa marker.
    code = pyotp.TOTP(secret).now()
    step = client.post("/auth/login/totp", json={"code": code})
    assert step.status_code == 401


def test_login_totp_wrong_key_is_server_error(client, monkeypatch) -> None:
    """A stored secret that no longer decrypts is a 500, not a wrong-code 401."""
    _password_login(client)
    secret = _enable_totp(client)
    client.post("/auth/logout")
    # Rotate the encryption key so the stored ciphertext can no longer be read.
    monkeypatch.setenv("TOTP_ENC_KEY", Fernet.generate_key().decode())
    client.post("/auth/login", json={"password": ADMIN_PASSWORD})
    code = pyotp.TOTP(secret).now()
    step = client.post("/auth/login/totp", json={"code": code})
    assert step.status_code == 500


def test_logout_clears_pending_state(client) -> None:
    """A logout during the pending step drops the marker, so no code is taken."""
    _password_login(client)
    secret = _enable_totp(client)
    client.post("/auth/logout")
    client.post("/auth/login", json={"password": ADMIN_PASSWORD})
    client.post("/auth/logout")
    code = pyotp.TOTP(secret).now()
    step = client.post("/auth/login/totp", json={"code": code})
    assert step.status_code == 401


def test_code_attempts_are_rate_limited(client) -> None:
    """The sixth wrong code in a window is throttled with a 429."""
    _password_login(client)
    _enable_totp(client)
    client.post("/auth/logout")
    client.post("/auth/login", json={"password": ADMIN_PASSWORD})

    for _ in range(5):
        attempt = client.post("/auth/login/totp", json={"code": "000000"})
        assert attempt.status_code == 401
    throttled = client.post("/auth/login/totp", json={"code": "000000"})
    assert throttled.status_code == 429
