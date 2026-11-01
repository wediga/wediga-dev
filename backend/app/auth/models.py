"""Models of the accounts from authentik, the sessions with their parts and the
single admin row behind the password login."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import ACCESS_SCHEMA, UUID_DEFAULT, Base

# Every part of a session points at it and goes away together with it.
SESSION_ID = f"{ACCESS_SCHEMA}.session.id"


class Account(Base):
    __tablename__ = "account"
    __table_args__ = ({"schema": ACCESS_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    authentik_user_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    name: Mapped[str]
    first_login_at: Mapped[datetime]
    last_login_at: Mapped[datetime]


class BrowserSession(Base):
    __tablename__ = "session"
    __table_args__ = ({"schema": ACCESS_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    token_hash: Mapped[bytes] = mapped_column(unique=True)
    csrf_token: Mapped[str]
    created_at: Mapped[datetime]
    last_seen_at: Mapped[datetime]
    user_agent: Mapped[str | None] = mapped_column(default=None)


class Role(Base):
    __tablename__ = "role"
    __table_args__ = ({"schema": ACCESS_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    key: Mapped[str] = mapped_column(unique=True)


class AuthentikLogin(Base):
    __tablename__ = "authentik_login"
    __table_args__ = ({"schema": ACCESS_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(SESSION_ID, ondelete="CASCADE"), unique=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{ACCESS_SCHEMA}.account.id")
    )
    logged_in_at: Mapped[datetime]


class AuthentikLoginRole(Base):
    __tablename__ = "authentik_login_role"
    __table_args__ = (
        UniqueConstraint("authentik_login_id", "role_id"),
        {"schema": ACCESS_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    authentik_login_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(f"{ACCESS_SCHEMA}.authentik_login.id", ondelete="CASCADE")
    )
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey(f"{ACCESS_SCHEMA}.role.id"))


class LoginFlow(Base):
    __tablename__ = "login_flow"
    __table_args__ = ({"schema": ACCESS_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(SESSION_ID, ondelete="CASCADE"), unique=True
    )
    state: Mapped[str]
    nonce: Mapped[str]
    verifier: Mapped[str]
    started_at: Mapped[datetime]
    target: Mapped[str | None] = mapped_column(default=None)


class LegacyAdminLogin(Base):
    __tablename__ = "legacy_admin_login"
    __table_args__ = ({"schema": ACCESS_SCHEMA},)

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey(SESSION_ID, ondelete="CASCADE"), unique=True
    )
    second_factor_done: Mapped[bool]


class Admin(Base):
    __tablename__ = "admin"
    # A unique index on a constant allows at most one row.
    __table_args__ = (
        Index("admin_single_row", text("(true)"), unique=True),
        {"schema": ACCESS_SCHEMA},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=UUID_DEFAULT, init=False
    )
    password_hash: Mapped[str]
    created_at: Mapped[datetime]
    updated_at: Mapped[datetime]
    totp_secret: Mapped[str | None] = mapped_column(default=None)
    totp_enabled: Mapped[bool] = mapped_column(default=False)
