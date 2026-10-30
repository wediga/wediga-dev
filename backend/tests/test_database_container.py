"""The CI must test against the database image that production runs."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_CONTAINER = REPO_ROOT / "deploy/quadlet/wediga-db.container"
CI_WORKFLOW = REPO_ROOT / ".github/workflows/ci.yml"


def test_ci_tests_against_the_production_image() -> None:
    production = next(
        line.removeprefix("Image=")
        for line in DB_CONTAINER.read_text(encoding="utf-8").splitlines()
        if line.startswith("Image=")
    )
    ci_images = re.findall(
        r"^\s+image: (\S+)$", CI_WORKFLOW.read_text(encoding="utf-8"), re.MULTILINE
    )

    assert ci_images
    assert set(ci_images) == {production}
