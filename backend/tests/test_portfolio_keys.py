"""The frontend knows the same text fields and status keys as the backend."""

import re

from sqlalchemy import select

from app.db.connection import get_session
from app.github.schemas import TEXT_FIELDS
from app.portfolio.models import ProjectStatus
from tests.conftest import REPO_ROOT

FRONTEND_LIB = REPO_ROOT / "frontend" / "lib"


def _block(file: str, opening: str) -> str:
    source = (FRONTEND_LIB / file).read_text(encoding="utf-8")
    block = re.search(re.escape(opening) + r"(.*?)[]}]", source, re.DOTALL)

    assert block is not None

    return block.group(1)


def test_frontend_text_fields_match_backend() -> None:
    block = _block("types.ts", "export const TEXT_FIELDS = [")

    assert re.findall(r'"(\w+)"', block) == list(TEXT_FIELDS)


def test_frontend_status_colours_match_the_migrated_statuses(_schema) -> None:
    block = _block("projectStatus.ts", "export const STATUS_CLASS = {")

    with get_session() as session:
        keys = session.scalars(
            select(ProjectStatus.key).order_by(ProjectStatus.sort_order)
        ).all()

    assert re.findall(r"^\s*(\w+):", block, re.MULTILINE) == keys
