"""The frontend lists the same kinds of profile link as the backend."""

import re

from app.content.schemas import LINK_KINDS
from tests.conftest import REPO_ROOT

FRONTEND_TYPES = REPO_ROOT / "frontend" / "lib" / "types.ts"


def test_frontend_link_labels_match_backend_link_kinds() -> None:
    source = FRONTEND_TYPES.read_text(encoding="utf-8")
    block = re.search(r"export const LINK_LABELS = \{(.*?)}", source, re.DOTALL)

    assert block is not None
    assert re.findall(r"^\s*(\w+):", block.group(1), re.MULTILINE) == list(LINK_KINDS)
