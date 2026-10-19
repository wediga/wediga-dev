"""Prepare the test authentik from compose.yaml for logins.

Run it once the containers are up:

    AUTHENTIK_URL=http://localhost:9000 uv run --project backend \
        python deploy/authentik-test/setup.py

It waits until authentik has applied every blueprint, applies the example
recovery flow that production also uses and applies wediga.yaml again, so its
second-factor step lands in that flow. Every blueprint has to end up
successful, otherwise the script fails. Then it creates the test accounts, each
with a password and a TOTP device set up through the real login flow, and
prints their credentials. With AUTHENTIK_ACCOUNTS set, it also writes them to
that JSON file for Playwright.

Accounts from an earlier run are deleted and created again, so the script can
run any number of times.
"""

import json
import os
import re
import time
from collections.abc import Callable, Iterable
from pathlib import Path

import httpx
import pyotp

COMPOSE_FILE = Path(__file__).with_name("compose.yaml")

RECOVERY_BLUEPRINT = "example/flows-recovery-email-verification.yaml"
RECOVERY_INSTANCE_NAME = "Recovery flow"
SITE_BLUEPRINT = "custom/wediga.yaml"
LOGIN_FLOW = "default-authentication-flow"

STATUS_SUCCESSFUL = "successful"
STATUS_UNKNOWN = "unknown"

PASSWORD = "test-only-password"
ACCOUNTS = (
    ("test-admin", "wediga-admins"),
    ("test-friend", "friends"),
    ("test-nogroup", None),
)

READY_TIMEOUT_SECONDS = 600
APPLY_TIMEOUT_SECONDS = 180
POLL_SECONDS = 3
REQUEST_TIMEOUT_SECONDS = 30
# More than authentik ships, so one page holds every blueprint.
BLUEPRINT_PAGE_SIZE = 1000


def bootstrap_token() -> str:
    """Read the API key from compose.yaml, the only place it is defined."""
    match = re.search(
        r"AUTHENTIK_BOOTSTRAP_TOKEN: (\S+)", COMPOSE_FILE.read_text(encoding="utf-8")
    )

    if match is None:
        raise SystemExit(f"no AUTHENTIK_BOOTSTRAP_TOKEN in {COMPOSE_FILE}")

    return match.group(1)


def raise_on_error(response: httpx.Response) -> None:
    # The hook also sees each redirect on the way, which the client follows.
    if not response.is_redirect:
        response.raise_for_status()


def client(base_url: str, headers: dict[str, str] | None = None) -> httpx.Client:
    """An HTTP client that fails on every error response."""
    return httpx.Client(
        base_url=base_url,
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
        follow_redirects=True,
        event_hooks={"response": [raise_on_error]},
    )


def wait_for(description: str, check: Callable[[], bool], timeout: int) -> None:
    deadline = time.monotonic() + timeout

    while not check():
        if time.monotonic() > deadline:
            raise SystemExit(f"timed out waiting for {description}")

        time.sleep(POLL_SECONDS)


def is_ready(base_url: str) -> bool:
    try:
        response = httpx.get(f"{base_url}/-/health/ready/")
    except httpx.TransportError:
        return False

    return response.is_success


def blueprints(api: httpx.Client) -> list[dict]:
    response = api.get(
        "/managed/blueprints/", params={"page_size": BLUEPRINT_PAGE_SIZE}
    )

    return response.json()["results"]


def blueprint_by_path(api: httpx.Client, path: str) -> dict | None:
    return next((b for b in blueprints(api) if b["path"] == path), None)


def not_successful(api: httpx.Client) -> list[dict]:
    return [b for b in blueprints(api) if b["status"] != STATUS_SUCCESSFUL]


def startup_blueprints_done(api: httpx.Client) -> bool:
    instances = blueprints(api)

    return any(b["path"] == SITE_BLUEPRINT for b in instances) and all(
        b["status"] != STATUS_UNKNOWN for b in instances
    )


def apply_blueprint(api: httpx.Client, instance: dict) -> None:
    """Apply a blueprint and wait until the worker has finished it."""
    before = instance["last_applied"]
    api.post(f"/managed/blueprints/{instance['pk']}/apply/")

    def applied() -> bool:
        current = api.get(f"/managed/blueprints/{instance['pk']}/").json()

        return current["last_applied"] != before and current["status"] != STATUS_UNKNOWN

    wait_for(instance["path"], applied, APPLY_TIMEOUT_SECONDS)


def recovery_instance(api: httpx.Client) -> dict:
    existing = blueprint_by_path(api, RECOVERY_BLUEPRINT)

    if existing is not None:
        return existing

    def created() -> bool:
        # authentik has the worker check the path, and that check times out
        # with a 500 while the worker is still busy after a fresh start.
        try:
            api.post(
                "/managed/blueprints/",
                json={
                    "name": RECOVERY_INSTANCE_NAME,
                    "path": RECOVERY_BLUEPRINT,
                    "enabled": True,
                    "context": {},
                },
            )
        except httpx.HTTPStatusError as error:
            if error.response.is_server_error:
                return False

            raise

        return True

    wait_for("the recovery blueprint to be created", created, APPLY_TIMEOUT_SECONDS)

    return blueprint_by_path(api, RECOVERY_BLUEPRINT)


def prepare_blueprints(api: httpx.Client) -> None:
    wait_for(
        "the startup blueprints",
        lambda: startup_blueprints_done(api),
        READY_TIMEOUT_SECONDS,
    )
    apply_blueprint(api, recovery_instance(api))
    apply_blueprint(api, blueprint_by_path(api, SITE_BLUEPRINT))

    # On a fresh start the worker applies many blueprints at once, and two of
    # them can deadlock in the database. One more run clears that, a real
    # error in a file fails again.
    for instance in not_successful(api):
        apply_blueprint(api, instance)

    failed = [b["name"] for b in not_successful(api)]

    if failed:
        raise SystemExit(f"blueprints not successful: {failed}")

    brand = api.get("/core/brands/").json()["results"][0]

    if brand["flow_recovery"] is None:
        raise SystemExit("the brand has no recovery flow after applying wediga.yaml")


def create_user(api: httpx.Client, username: str, group: str | None) -> None:
    """Create the account from scratch, deleting one left by an earlier run."""
    for old in api.get("/core/users/", params={"username": username}).json()["results"]:
        api.delete(f"/core/users/{old['pk']}/")

    groups = []

    if group is not None:
        found = api.get("/core/groups/", params={"name": group}).json()["results"]
        groups = [found[0]["pk"]]

    user = api.post(
        "/core/users/",
        json={
            "username": username,
            "name": username,
            "type": "internal",
            "groups": groups,
            "attributes": {"settings": {"locale": "en"}},
        },
    ).json()
    api.post(f"/core/users/{user['pk']}/set_password/", json={"password": PASSWORD})


def enroll_totp(base_url: str, username: str) -> pyotp.TOTP:
    """Log in once through the login flow, which makes a new account set up a
    TOTP device, and return the device authentik generated for it."""
    with client(f"{base_url}/api/v3/flows/executor/{LOGIN_FLOW}/") as flow:
        # The first request starts the flow, every answer leads to the next
        # stage.
        flow.get("")
        flow.post(
            "", json={"component": "ak-stage-identification", "uid_field": username}
        )
        challenge = flow.post(
            "", json={"component": "ak-stage-password", "password": PASSWORD}
        ).json()
        totp_stage = next(
            s["pk"]
            for s in challenge["configuration_stages"]
            if s["meta_model_name"].endswith("authenticatortotpstage")
        )
        challenge = flow.post(
            "",
            json={
                "component": "ak-stage-authenticator-validate",
                "selected_stage": totp_stage,
            },
        ).json()
        totp = pyotp.parse_uri(challenge["config_url"])
        done = flow.post(
            "", json={"component": "ak-stage-authenticator-totp", "code": totp.now()}
        ).json()

    if done.get("component") != "xak-flow-redirect":
        raise SystemExit(f"TOTP setup for {username} did not finish: {done}")

    return totp


def wait_for_fresh_codes(devices: Iterable[pyotp.TOTP]) -> None:
    """authentik accepts each code only once. Waiting for the next one keeps a
    login right after this script from reusing the code of the setup."""
    interval = max(device.interval for device in devices)
    time.sleep(interval - time.time() % interval)


def main() -> None:
    base_url = os.environ.get("AUTHENTIK_URL", "").rstrip("/")
    output = os.environ.get("AUTHENTIK_ACCOUNTS")

    if not base_url:
        raise SystemExit("set AUTHENTIK_URL, e.g. http://localhost:9000")

    wait_for("authentik to be ready", lambda: is_ready(base_url), READY_TIMEOUT_SECONDS)
    devices = {}

    with client(
        f"{base_url}/api/v3", {"Authorization": f"Bearer {bootstrap_token()}"}
    ) as api:
        prepare_blueprints(api)

        for username, group in ACCOUNTS:
            create_user(api, username, group)
            devices[username] = enroll_totp(base_url, username)

    for username, device in devices.items():
        print(f"{username}  password {PASSWORD}  TOTP secret {device.secret}")

    if output:
        accounts = {
            username: {"password": PASSWORD, "totp_secret": device.secret}
            for username, device in devices.items()
        }
        Path(output).parent.mkdir(parents=True, exist_ok=True)
        Path(output).write_text(json.dumps(accounts, indent=2), encoding="utf-8")

    wait_for_fresh_codes(devices.values())


if __name__ == "__main__":
    main()
