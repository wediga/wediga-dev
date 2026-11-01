"""Tests for creating a recruiter link over the SSH key's command."""

import io
from datetime import UTC, datetime
from pathlib import Path

import pytest
from sqlalchemy import select

from app.db.connection import get_session
from app.recruiter import repository as repo
from app.recruiter.create_link import LINK_BASE, main
from app.recruiter.models import RecruiterLink
from app.recruiter.schemas import DEFAULT_LINK_LIFETIME, LABEL_MAX

REDEEM_ROUTE = (
    Path(__file__).resolve().parents[2] / "frontend" / "app" / "r" / "[token]"
)


def _run(label: str) -> int:
    return main(io.StringIO(label))


def _links() -> list[RecruiterLink]:
    with get_session() as session:
        return list(session.scalars(select(RecruiterLink)))


def test_prints_a_redeemable_address_for_the_label(migrated_db, capsys) -> None:
    assert _run("Acme Corp\n") == 0

    address = capsys.readouterr().out.strip()
    token = address.removeprefix(LINK_BASE)
    (link,) = _links()

    assert address.startswith(LINK_BASE)
    assert repo.validate_token(token) == (repo.LinkStatus.OK, link.id)
    assert link.label == "Acme Corp"
    assert token not in link.token_hash


def test_link_gets_the_default_lifetime(migrated_db) -> None:
    _run("Acme Corp")

    (link,) = _links()
    expected = (datetime.now(UTC) + DEFAULT_LINK_LIFETIME).date()

    assert link.expires_at is not None
    assert link.expires_at.date() == expected


def test_shell_characters_stay_part_of_the_label(migrated_db) -> None:
    assert _run("Acme; rm -rf / $(id) `id`") == 0

    assert _links()[0].label == "Acme; rm -rf / $(id) `id`"


@pytest.mark.parametrize(
    "label",
    ["", "   \n", "x" * (LABEL_MAX + 1), "Acme\nCorp", "Acme\x07Corp", "Acme\x7f"],
)
def test_refuses_a_bad_label_and_writes_nothing(migrated_db, capsys, label) -> None:
    assert _run(label) == 1

    assert capsys.readouterr().err.startswith("invalid label:")
    assert _links() == []


def test_link_base_points_at_the_redeem_route() -> None:
    assert LINK_BASE.endswith(f"/{REDEEM_ROUTE.parent.name}/")
    assert (REDEEM_ROUTE / "route.ts").is_file()
