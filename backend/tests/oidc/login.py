"""Helpers that drive the login through authentik in the tests.

The client uses an https base URL so the Secure session cookie round-trips,
and the session content is read from the database by the token in the cookie.
"""

from datetime import timedelta
from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import InstrumentedAttribute

from app.auth.csrf import CSRF_HEADER_NAME
from app.auth.models import (
    Account,
    AuthentikLogin,
    AuthentikLoginRole,
    BrowserSession,
    LegacyAdminLogin,
    LoginFlow,
    Role,
)
from app.auth.sessions import SESSION_COOKIE_NAME, hash_token
from app.db.connection import get_session
from app.recruiter.models import RecruiterAccess
from tests.oidc.oidc_fake import make_id_token

ADMIN_PASSWORD = "correct horse battery staple"

PARTS = (AuthentikLogin, LoginFlow, LegacyAdminLogin, RecruiterAccess)


def read_session(client: TestClient) -> dict:
    """Return the client's session as stored, with every part it has under
    its table name, whatever its age. The login through authentik also
    carries its roles and the account."""
    token = client.cookies.get(SESSION_COOKIE_NAME)

    if token is None:
        return {}

    with get_session() as db:
        row = db.scalar(
            select(BrowserSession).where(BrowserSession.token_hash == hash_token(token))
        )

        if row is None:
            return {}

        stored = row.as_dict()

        for model in PARTS:
            part = db.scalar(select(model).where(model.session_id == row.id))

            if part is not None:
                stored[model.__tablename__] = part.as_dict()

        login = stored.get(AuthentikLogin.__tablename__)

        if login is not None:
            login["roles"] = list(
                db.scalars(
                    select(Role.key)
                    .join(AuthentikLoginRole, AuthentikLoginRole.role_id == Role.id)
                    .where(AuthentikLoginRole.authentik_login_id == login["id"])
                    .order_by(Role.key)
                )
            )
            account = db.get_one(Account, login["account_id"])
            login["account"] = account.as_dict()

    return stored


def age(column: InstrumentedAttribute, by: timedelta) -> None:
    """Move a time in every row back by ``by``, as if that much had passed."""
    with get_session() as db:
        db.execute(
            update(column.property.parent.class_).values({column.key: column - by})
        )
        db.commit()


def start_login(client: TestClient, target: str | None = None) -> dict[str, str]:
    """Start a login and return the query authentik would receive."""
    params = {} if target is None else {"next": target}
    response = client.get("/auth/oidc/login", params=params, follow_redirects=False)
    assert response.status_code == 303
    query = parse_qs(urlsplit(response.headers["location"]).query)

    return {name: values[0] for name, values in query.items()}


def finish_login(client: TestClient, state: str, code: str = "the-code"):
    return client.get(
        "/auth/oidc/callback",
        params={"code": code, "state": state},
        follow_redirects=False,
    )


def log_in(client, fake, groups, target=None, **claims):
    """Run a whole login with the given groups and return the callback."""
    query = start_login(client, target)
    fake.id_token = make_id_token(
        **{"nonce": query["nonce"], "groups": groups, **claims}
    )

    return finish_login(client, query["state"])


def redeem_recruiter_link(app, client: TestClient) -> None:
    admin = TestClient(app, base_url="https://testserver")
    assert admin.post("/auth/login", json={"password": ADMIN_PASSWORD}).is_success
    admin.headers[CSRF_HEADER_NAME] = admin.get("/auth/csrf").json()["csrf_token"]
    token = admin.post("/recruiter/links", json={"label": "r"}).json()["token"]

    assert client.post("/recruiter/redeem", json={"token": token}).is_success


def log_out(client: TestClient):
    csrf = read_session(client).get("csrf_token", "")

    return client.post("/auth/oidc/logout", headers={CSRF_HEADER_NAME: csrf})
