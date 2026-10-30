"""Tests for the hub's route, which asks authentik for the applications.

The hub sits on the login through authentik, so it uses the same fake.
"""

from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.auth import dependencies
from app.auth.sessions import OIDC_SESSION_KEY
from app.hub import router as hub_router
from app.hub.authentik import OWN_APPLICATION, PAGE_SIZE
from tests.oidc.login import ADMIN_PASSWORD, log_in
from tests.oidc.oidc_fake import ACCOUNT_ID, APPLICATIONS_URL, internal

BLUEPRINT = (
    Path(__file__).resolve().parents[3] / "deploy/authentik/blueprints/wediga.yaml"
)

GAME = {
    "name": "Game server",
    "slug": "game",
    "launch_url": "https://game.example/",
    "meta_icon": "https://game.example/icon.png",
    "meta_description": "Our server",
    "group": "Games",
    "provider": None,
}
GAME_SHOWN = {
    "name": "Game server",
    "url": "https://game.example/",
    "icon": "https://game.example/icon.png",
    "description": "Our server",
    "group": "Games",
}


@pytest.fixture(autouse=True)
def _empty_cache():
    hub_router._cache.clear()


def applications(client):
    return client.get("/hub/applications")


# --- access ------------------------------------------------------------------


@pytest.mark.parametrize("groups", [["friends"], ["wediga-admins"]])
def test_hub_lists_what_authentik_allows(client, fake, groups) -> None:
    log_in(client, fake, groups)
    fake.applications = {"results": [GAME]}

    response = applications(client)

    assert response.status_code == 200
    assert response.json() == [GAME_SHOWN]
    assert fake.application_calls == [
        {"for_user": int(ACCOUNT_ID), "page_size": PAGE_SIZE}
    ]
    assert fake.get_calls[-1][0] == internal(APPLICATIONS_URL)


def test_hub_needs_a_login(client, fake) -> None:
    assert applications(client).status_code == 401
    assert fake.application_calls == []


def test_password_login_does_not_open_the_hub(client, fake) -> None:
    assert client.post("/auth/login", json={"password": ADMIN_PASSWORD}).is_success

    assert applications(client).status_code == 401


def test_expired_login_does_not_open_the_hub(client, fake, monkeypatch) -> None:
    log_in(client, fake, ["friends"])
    later = dependencies.time.time() + dependencies.OIDC_LOGIN_LIFETIME_SECONDS + 1
    monkeypatch.setattr(dependencies.time, "time", lambda: later)

    assert applications(client).status_code == 401


@pytest.mark.parametrize(
    "login",
    [
        # A login from before the account ID was kept in the session.
        {"roles": ["hub"]},
        # No group gives such a login yet, but a later one may.
        {"user_id": int(ACCOUNT_ID), "roles": ["admin"]},
    ],
)
def test_login_that_does_not_open_the_hub(login) -> None:
    login = {**login, "login_at": int(dependencies.time.time())}
    request = Request({"type": "http", "session": {OIDC_SESSION_KEY: login}})

    with pytest.raises(HTTPException) as excinfo:
        dependencies.require_hub(request)

    assert excinfo.value.status_code == 401


def test_hub_does_not_answer_while_switched_off(app, client, monkeypatch) -> None:
    monkeypatch.setattr(app.state, "oidc", None)

    assert applications(client).status_code == 404


# --- what is shown -----------------------------------------------------------


@pytest.mark.parametrize(
    "entry",
    [
        {**GAME, "slug": OWN_APPLICATION},
        {**GAME, "launch_url": "http://game.example/"},
        {**GAME, "launch_url": "javascript:alert(1)"},
        {**GAME, "launch_url": "/relative"},
        {**GAME, "launch_url": "https://"},
        {**GAME, "launch_url": "https://[broken"},
        {**GAME, "launch_url": None},
        {**GAME, "launch_url": ""},
        {**GAME, "name": None},
        "not an application",
    ],
)
def test_entry_that_is_not_shown(client, fake, entry) -> None:
    log_in(client, fake, ["friends"])
    fake.applications = {"results": [entry, GAME]}

    assert applications(client).json() == [GAME_SHOWN]


@pytest.mark.parametrize(
    "icon", ["", None, "http://game.example/i.png", "/media/i.png", "data:x"]
)
def test_icon_that_is_not_https_is_left_out(client, fake, icon) -> None:
    log_in(client, fake, ["friends"])
    fake.applications = {"results": [{**GAME, "meta_icon": icon}]}

    assert applications(client).json() == [{**GAME_SHOWN, "icon": None}]


def test_missing_description_and_group_are_empty(client, fake) -> None:
    log_in(client, fake, ["friends"])
    entry = {**GAME, "meta_description": None}
    del entry["group"]
    fake.applications = {"results": [entry]}

    shown = applications(client).json()[0]

    assert shown["description"] == ""
    assert shown["group"] == ""


def test_own_application_is_the_one_in_the_blueprint() -> None:
    assert f"slug: {OWN_APPLICATION}\n" in BLUEPRINT.read_text(encoding="utf-8")


# --- cache -------------------------------------------------------------------


def test_answer_is_kept_for_a_minute(client, fake, monkeypatch) -> None:
    log_in(client, fake, ["friends"])
    now = hub_router.time.monotonic()
    monkeypatch.setattr(hub_router.time, "monotonic", lambda: now)
    applications(client)
    fake.applications = {"results": [GAME]}

    assert applications(client).json() == []
    assert len(fake.application_calls) == 1

    later = now + hub_router.CACHE_SECONDS
    monkeypatch.setattr(hub_router.time, "monotonic", lambda: later)

    assert applications(client).json() == [GAME_SHOWN]
    assert len(fake.application_calls) == 2


def test_each_account_gets_its_own_answer(app, client, fake) -> None:
    log_in(client, fake, ["friends"])
    applications(client)
    other = TestClient(app, base_url="https://testserver")
    log_in(other, fake, ["friends"], sub="22")

    applications(other)

    assert [call["for_user"] for call in fake.application_calls] == [21, 22]


# --- authentik fails ---------------------------------------------------------


def test_unreachable_authentik_answers_502_and_is_not_kept(client, fake) -> None:
    log_in(client, fake, ["friends"])
    fake.unreachable = True

    response = applications(client)

    assert response.status_code == 502
    assert response.json() == {"detail": "Hub unavailable"}

    fake.unreachable = False
    fake.applications = {"results": [GAME]}

    assert applications(client).json() == [GAME_SHOWN]


@pytest.mark.parametrize(
    ("status", "body"),
    [
        (400, {"for_user": "User not found"}),
        (403, {"detail": "Token invalid/expired"}),
        (200, {"no": "results"}),
        (200, {"results": "not a list"}),
        (200, ["not", "an", "object"]),
    ],
)
def test_unusable_answer_from_authentik_gives_502(client, fake, status, body) -> None:
    log_in(client, fake, ["friends"])
    fake.applications_status = status
    fake.applications = body

    assert applications(client).status_code == 502
