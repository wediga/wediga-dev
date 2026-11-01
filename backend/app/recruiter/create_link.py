"""Create a recruiter link from the command line and print its address.

Runs inside the backend container as the forced command of the SSH key that
may only create links (``deploy/create-recruiter-link.sh``). The label arrives
on stdin, so no shell interprets it, and it is checked here before anything is
written. The link gets the default lifetime.
"""

import sys
from typing import TextIO

from pydantic import ValidationError

from app.recruiter import repository as repo
from app.recruiter.schemas import RecruiterLinkFromKey

# The public address of the redeem route in frontend/app/r/[token].
LINK_BASE = "https://www.wediga.dev/r/"


def main(stdin: TextIO = sys.stdin) -> int:
    """Read the label, create the link and print its address, or refuse."""
    try:
        body = RecruiterLinkFromKey(label=stdin.read().strip())
    except ValidationError as error:
        print(f"invalid label: {error.errors()[0]['msg']}", file=sys.stderr)

        return 1

    _, token = repo.create_link(body.label, body.expires_on)
    print(f"{LINK_BASE}{token}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
