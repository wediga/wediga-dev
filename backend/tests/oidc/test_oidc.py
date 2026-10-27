"""Tests for the protocol side of the login through authentik."""

import base64
import json
import time
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import pytest
from authlib.integrations.httpx_client import OAuthError
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from joserfc.jwk import OctKey, RSAKey

from app.auth import oidc
from tests.oidc.oidc_fake import (
    CLIENT_ID,
    ISSUER,
    KEY_ID,
    METADATA,
    SETTINGS,
    TOKEN_LIFETIME_SECONDS,
    FakeAuthentik,
    internal,
    make_id_token,
)

NONCE = "expected-nonce"


def _validate(id_token: str) -> dict:
    token = {"access_token": "access", "id_token": id_token}

    return oidc.validate_id_token(SETTINGS, METADATA, token, NONCE)


def _unsigned(claims: dict) -> str:
    def part(data: dict) -> str:
        raw = json.dumps(data).encode()

        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    return f"{part({'alg': 'none', 'kid': KEY_ID})}.{part(claims)}."


# --- discovery and addresses ----------------------------------------------


def test_metadata_is_fetched_internally_with_the_public_host(fake) -> None:
    assert oidc.load_metadata(SETTINGS) == METADATA
    assert fake.get_calls[0][0] == internal(ISSUER + oidc.DISCOVERY_PATH)


def test_without_internal_url_the_public_issuer_is_used(monkeypatch) -> None:
    settings = replace(SETTINGS, internal_url=None)
    fake = FakeAuthentik(monkeypatch, settings)

    oidc.load_metadata(settings)

    assert fake.get_calls[0][0] == ISSUER + oidc.DISCOVERY_PATH


def test_metadata_for_another_issuer_is_refused(fake) -> None:
    fake.metadata["issuer"] = "https://evil.example/"

    with pytest.raises(oidc.OidcProviderError):
        oidc.load_metadata(SETTINGS)


@pytest.mark.parametrize(
    "key", ["authorization_endpoint", "token_endpoint", "jwks_uri"]
)
@pytest.mark.parametrize(
    "value", [None, "https://evil.example/x/", "http://auth.example/x/"]
)
def test_endpoint_outside_the_issuer_origin_is_refused(fake, key, value) -> None:
    fake.metadata[key] = value

    with pytest.raises(oidc.OidcProviderError):
        oidc.load_metadata(SETTINGS)


def test_unreachable_authentik_is_a_provider_error(fake) -> None:
    fake.unreachable = True

    with pytest.raises(oidc.OidcProviderError):
        oidc.load_metadata(SETTINGS)


def test_end_session_url_must_be_on_the_issuer_origin() -> None:
    assert oidc.end_session_url(SETTINGS, METADATA) == METADATA["end_session_endpoint"]

    foreign = {**METADATA, "end_session_endpoint": "https://evil.example/"}

    with pytest.raises(oidc.OidcProviderError):
        oidc.end_session_url(SETTINGS, foreign)


def test_authorization_url_carries_state_nonce_and_pkce() -> None:
    url = oidc.authorization_url(SETTINGS, METADATA, "s", "n", "verifier")

    assert url.startswith(METADATA["authorization_endpoint"])
    query = parse_qs(urlsplit(url).query)
    assert query["response_type"] == ["code"]
    assert query["client_id"] == [CLIENT_ID]
    assert query["redirect_uri"] == [SETTINGS.redirect_uri]
    assert query["scope"] == [oidc.SCOPE]
    assert query["state"] == ["s"]
    assert query["nonce"] == ["n"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["code_challenge"] == [create_s256_code_challenge("verifier")]
    assert "client_secret" not in query


# --- token exchange --------------------------------------------------------


def test_code_is_exchanged_internally_with_the_verifier(fake) -> None:
    fake.id_token = make_id_token(nonce=NONCE)

    token = oidc.exchange_code(SETTINGS, METADATA, "the-code", "verifier")

    assert token["id_token"] == fake.id_token
    _, kwargs = fake.token_calls[0]
    assert kwargs["code"] == "the-code"
    assert kwargs["code_verifier"] == "verifier"


@pytest.mark.parametrize(
    "error", [OAuthError("invalid_grant"), oidc.httpx.ConnectError("down")]
)
def test_failed_exchange_is_a_provider_error(fake, error) -> None:
    fake.token_error = error

    with pytest.raises(oidc.OidcProviderError):
        oidc.exchange_code(SETTINGS, METADATA, "code", "verifier")


def test_response_without_id_token_is_a_provider_error(fake) -> None:
    with pytest.raises(oidc.OidcProviderError):
        oidc.exchange_code(SETTINGS, METADATA, "code", "verifier")


# --- ID token --------------------------------------------------------------


@pytest.mark.usefixtures("fake")
def test_valid_id_token_returns_its_claims() -> None:
    claims = _validate(make_id_token(nonce=NONCE, groups=["friends"]))

    assert claims["sub"] == "user-1"
    assert claims["groups"] == ["friends"]


@pytest.mark.usefixtures("fake")
@pytest.mark.parametrize(
    "claims",
    [
        {"nonce": "other-nonce"},
        {"nonce": None},
        {"iss": "https://evil.example/"},
        {"iss": None},
        {"aud": "other-client"},
        {"aud": None},
        {"aud": ["other-client"], "azp": "other-client"},
        {"aud": "other-client", "azp": CLIENT_ID},
        {"aud": [CLIENT_ID, "other-client"]},
        {"aud": [CLIENT_ID, "other-client"], "azp": "other-client"},
        {"exp": 1},
        {"exp": None},
        {"iat": None},
        {"sub": None},
    ],
    ids=lambda claims: json.dumps(claims),
)
def test_invalid_claims_are_refused(claims) -> None:
    with pytest.raises(oidc.OidcTokenError):
        _validate(make_id_token(**{"nonce": NONCE, **claims}))


@pytest.mark.usefixtures("fake")
def test_token_expired_beyond_the_leeway_is_refused() -> None:
    expired = make_id_token(
        nonce=NONCE, exp=int(time.time()) - oidc.CLOCK_LEEWAY_SECONDS - 1
    )

    with pytest.raises(oidc.OidcTokenError):
        _validate(expired)


@pytest.mark.usefixtures("fake")
def test_token_signed_with_another_key_is_refused() -> None:
    other = RSAKey.generate_key(2048, parameters={"kid": KEY_ID})

    with pytest.raises(oidc.OidcTokenError):
        _validate(make_id_token(nonce=NONCE, key=other))


@pytest.mark.usefixtures("fake")
def test_token_with_symmetric_algorithm_is_refused() -> None:
    key = OctKey.generate_key(256)

    with pytest.raises(oidc.OidcTokenError):
        _validate(make_id_token(nonce=NONCE, key=key, alg="HS256"))


@pytest.mark.usefixtures("fake")
def test_unsigned_token_is_refused() -> None:
    claims = {
        "iss": ISSUER,
        "sub": "user-1",
        "aud": CLIENT_ID,
        "exp": int(time.time()) + TOKEN_LIFETIME_SECONDS,
        "iat": int(time.time()),
        "nonce": NONCE,
    }

    with pytest.raises(oidc.OidcTokenError):
        _validate(_unsigned(claims))


@pytest.mark.usefixtures("fake")
def test_garbage_token_is_refused() -> None:
    with pytest.raises(oidc.OidcTokenError):
        _validate("not.a.token")
