"""Tests for the settings of the login through authentik."""

import pytest
from fastapi.testclient import TestClient

from app.auth.oidc_settings import (
    API_TOKEN_VAR,
    CLIENT_ID_VAR,
    CLIENT_SECRET_VAR,
    ENABLED_VAR,
    INTERNAL_URL_VAR,
    ISSUER_VAR,
    REDIRECT_URI_VAR,
    REQUIRED_VARS,
    OidcConfigError,
    load_oidc_settings,
)
from app.main import app

SECRET = "a-secret-that-must-never-be-printed"
API_TOKEN = "an-api-token-that-must-never-be-printed"

VALID_ENV = {
    ENABLED_VAR: "true",
    ISSUER_VAR: "https://auth.wediga.dev/application/o/wediga-dev/",
    CLIENT_ID_VAR: "wediga-dev",
    CLIENT_SECRET_VAR: SECRET,
    REDIRECT_URI_VAR: "https://www.wediga.dev/auth/callback",
    API_TOKEN_VAR: API_TOKEN,
}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Start every test without login settings from the developer's shell."""
    for name in (ENABLED_VAR, INTERNAL_URL_VAR, *REQUIRED_VARS):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture()
def valid_env(monkeypatch):
    for name, value in VALID_ENV.items():
        monkeypatch.setenv(name, value)


@pytest.mark.parametrize("value", [None, "", "false", "1", "yes"])
def test_login_is_off_unless_enabled_is_true(monkeypatch, value) -> None:
    if value is not None:
        monkeypatch.setenv(ENABLED_VAR, value)
    assert load_oidc_settings() is None


def test_off_ignores_incomplete_values(monkeypatch) -> None:
    """With the switch off, a stray or broken value does not block the start."""
    monkeypatch.setenv(ISSUER_VAR, "http://evil.example/")
    assert load_oidc_settings() is None


@pytest.mark.usefixtures("valid_env")
def test_complete_settings_are_loaded() -> None:
    settings = load_oidc_settings()

    assert settings is not None
    assert settings.issuer == VALID_ENV[ISSUER_VAR]
    assert settings.client_id == VALID_ENV[CLIENT_ID_VAR]
    assert settings.client_secret == SECRET
    assert settings.redirect_uri == VALID_ENV[REDIRECT_URI_VAR]
    assert settings.internal_url is None
    assert settings.api_token == API_TOKEN


@pytest.mark.usefixtures("valid_env")
def test_switch_is_case_insensitive(monkeypatch) -> None:
    monkeypatch.setenv(ENABLED_VAR, " TRUE ")
    assert load_oidc_settings() is not None


@pytest.mark.usefixtures("valid_env")
def test_secrets_are_not_in_repr() -> None:
    settings = repr(load_oidc_settings())

    assert SECRET not in settings
    assert API_TOKEN not in settings


@pytest.mark.usefixtures("valid_env")
@pytest.mark.parametrize("name", REQUIRED_VARS)
@pytest.mark.parametrize("value", ["", "   "])
def test_missing_value_is_refused(monkeypatch, name, value) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(OidcConfigError, match=name):
        load_oidc_settings()


@pytest.mark.usefixtures("valid_env")
def test_error_never_contains_the_secret(monkeypatch) -> None:
    monkeypatch.setenv(ISSUER_VAR, SECRET)

    with pytest.raises(OidcConfigError) as excinfo:
        load_oidc_settings()

    assert SECRET not in str(excinfo.value)


@pytest.mark.usefixtures("valid_env")
@pytest.mark.parametrize("name", [ISSUER_VAR, REDIRECT_URI_VAR])
@pytest.mark.parametrize(
    "value",
    [
        "http://auth.wediga.dev/application/o/wediga-dev/",
        "http://localhost.evil.example/",
        "ftp://localhost/",
        "https://",
        "not a url",
    ],
)
def test_unsafe_public_url_is_refused(monkeypatch, name, value) -> None:
    monkeypatch.setenv(name, value)

    with pytest.raises(OidcConfigError, match=name):
        load_oidc_settings()


@pytest.mark.usefixtures("valid_env")
@pytest.mark.parametrize("name", [ISSUER_VAR, REDIRECT_URI_VAR])
@pytest.mark.parametrize(
    "value", ["http://localhost:9000/path/", "http://127.0.0.1:3000/path"]
)
def test_http_is_allowed_on_localhost(monkeypatch, name, value) -> None:
    monkeypatch.setenv(name, value)
    assert load_oidc_settings() is not None


@pytest.mark.usefixtures("valid_env")
@pytest.mark.parametrize(
    "value", ["http://authentik-server:9000", "https://authentik-server:9443"]
)
def test_internal_url_is_optional_and_may_use_http(monkeypatch, value) -> None:
    monkeypatch.setenv(INTERNAL_URL_VAR, value)

    settings = load_oidc_settings()

    assert settings is not None
    assert settings.internal_url == value


@pytest.mark.usefixtures("valid_env")
@pytest.mark.parametrize("value", ["authentik-server:9000", "ftp://authentik-server"])
def test_invalid_internal_url_is_refused(monkeypatch, value) -> None:
    monkeypatch.setenv(INTERNAL_URL_VAR, value)

    with pytest.raises(OidcConfigError, match=INTERNAL_URL_VAR):
        load_oidc_settings()


@pytest.mark.usefixtures("valid_env")
def test_backend_does_not_start_with_a_half_configured_login(monkeypatch) -> None:
    monkeypatch.delenv(CLIENT_SECRET_VAR)

    with pytest.raises(OidcConfigError), TestClient(app):
        pass
