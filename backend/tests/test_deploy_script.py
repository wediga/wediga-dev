"""Runs deploy/deploy.sh against fake podman, systemctl and curl.

The fakes write every call to a log. Fake curl serves the files of this
working copy in place of GitHub, and fake podman lists the images of a file.
"""

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DEPLOY_DIR = ROOT / "deploy"
QUADLET_DIR = DEPLOY_DIR / "quadlet"
BLUEPRINT = DEPLOY_DIR / "authentik/blueprints/wediga.yaml"
SCRIPT = DEPLOY_DIR / "deploy.sh"
SCRIPT_TEXT = SCRIPT.read_text(encoding="utf-8")
SHA = "0123456789abcdef0123456789abcdef01234567"
OLD_SHA = "89abcdef0123456789abcdef0123456789abcdef"
EXECUTABLE = 0o755


def script_value(name: str) -> str:
    match = re.search(rf"^{name}=(.*)$", SCRIPT_TEXT, re.MULTILINE)
    assert match

    return match.group(1)


def script_list(name: str) -> list[str]:
    match = re.search(rf"^{name}=\((.*?)\)$", SCRIPT_TEXT, re.MULTILINE | re.DOTALL)
    assert match

    return match.group(1).split()


REPOSITORY = script_value("REPOSITORY")
IMAGE_PREFIX = script_value("IMAGE_PREFIX")
PARTS = script_list("PARTS")
UNITS = script_list("UNITS")

FAKE_CURL = """#!/usr/bin/env bash
echo "curl $2" >> "$FAKE_LOG"
path="${2#"$FAKE_REPOSITORY"/"$FAKE_SHA"/}"
[ "$path" != "$FAKE_MISSING" ] || exit 22
cp "$FAKE_ROOT/$path" "$4"
"""
FAKE_PODMAN = """#!/usr/bin/env bash
echo "podman $*" >> "$FAKE_LOG"

for arg in "$@"; do
  case "$arg" in
    reference=*) grep "^${arg#reference=}:" "$FAKE_IMAGES" || true ;;
  esac
done
"""
FAKE_SYSTEMCTL = """#!/usr/bin/env bash
echo "systemctl $*" >> "$FAKE_LOG"
"""


@dataclass(frozen=True)
class Server:
    home: Path
    unit_dir: Path
    env: dict[str, str]
    log: Path

    def calls(self) -> list[str]:
        return (
            self.log.read_text(encoding="utf-8").splitlines()
            if self.log.exists()
            else []
        )

    def deploy(
        self, sha: str = SHA, missing: str = ""
    ) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["bash", SCRIPT.as_posix()],
            env=self.env
            | {"SSH_ORIGINAL_COMMAND": sha, "FAKE_SHA": sha, "FAKE_MISSING": missing},
            capture_output=True,
            check=False,
        )


def image(part: str, sha: str) -> str:
    return f"{IMAGE_PREFIX}-{part}:{sha}"


@pytest.fixture
def server(tmp_path: Path) -> Server:
    """A home of web with an older deploy and the images of other apps."""
    home = tmp_path / "home"
    unit_dir = home / ".config/containers/systemd"
    bin_dir = tmp_path / "bin"

    for folder in (
        unit_dir,
        home / "wediga-dev",
        home / "authentik/blueprints",
        bin_dir,
    ):
        folder.mkdir(parents=True)

    for name, fake in (
        ("curl", FAKE_CURL),
        ("podman", FAKE_PODMAN),
        ("systemctl", FAKE_SYSTEMCTL),
    ):
        (bin_dir / name).write_text(fake, encoding="utf-8", newline="\n")
        (bin_dir / name).chmod(EXECUTABLE)

    images = tmp_path / "images"
    images.write_text(
        "\n".join(
            [*(image(part, sha) for part in PARTS for sha in (OLD_SHA, SHA))]
            + ["ghcr.io/nuviralabs/nuviralabs-backend:deployed"]
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    log = tmp_path / "calls.log"
    env = {
        "HOME": home.as_posix(),
        "PATH": f"{bin_dir.as_posix()}:/usr/bin:/bin",
        "FAKE_LOG": log.as_posix(),
        "FAKE_ROOT": ROOT.as_posix(),
        "FAKE_REPOSITORY": REPOSITORY,
        "FAKE_IMAGES": images.as_posix(),
    }

    return Server(home, unit_dir, env, log)


@pytest.mark.parametrize("command", ["", "main", SHA.upper(), f"{SHA}; true"])
def test_anything_but_a_sha_is_refused(server: Server, command: str) -> None:
    result = server.deploy(command)

    assert result.returncode != 0
    assert server.calls() == []


def test_every_unit_in_the_folder_is_deployed() -> None:
    expected = {path.name for path in QUADLET_DIR.iterdir()} - {
        path.name for path in QUADLET_DIR.glob("*.env.example")
    }

    assert sorted(UNITS) == sorted(expected)


def test_files_of_the_commit_are_installed(server: Server) -> None:
    result = server.deploy()

    assert result.returncode == 0, result.stderr
    assert f"curl {REPOSITORY}/{SHA}/deploy/deploy.sh" in server.calls()
    assert (server.home / "authentik/blueprints/wediga.yaml").read_bytes() == (
        BLUEPRINT.read_bytes()
    )
    assert (server.home / "wediga-dev/deploy.sh").read_text(encoding="utf-8") == (
        SCRIPT_TEXT
    )

    for unit in UNITS:
        installed = (server.unit_dir / unit).read_text(encoding="utf-8").splitlines()
        source = (QUADLET_DIR / unit).read_text(encoding="utf-8").splitlines()
        assert [line for line in installed if not line.startswith("Image=")] == [
            line for line in source if not line.startswith("Image=")
        ]


@pytest.mark.parametrize(
    ("unit", "part"),
    [
        ("backend.container", "backend"),
        ("backend-migrate.container", "backend"),
        ("frontend.container", "frontend"),
    ],
)
def test_app_units_start_the_images_of_the_commit(
    server: Server, unit: str, part: str
) -> None:
    server.deploy()
    lines = (server.unit_dir / unit).read_text(encoding="utf-8").splitlines()

    assert f"Image={image(part, SHA)}" in lines
    assert f"podman pull --quiet {image(part, SHA)}" in server.calls()


def test_app_is_restarted_and_older_images_are_deleted(server: Server) -> None:
    server.deploy()
    calls = server.calls()
    restart = calls.index(
        "systemctl --user restart backend-migrate.service backend.service frontend.service"
    )
    deleted = [call for call in calls if call.startswith("podman rmi")]

    assert deleted == [f"podman rmi {image(part, OLD_SHA)}" for part in PARTS]
    assert all(calls.index(call) > restart for call in deleted)


def test_failed_download_leaves_the_server_as_it_was(server: Server) -> None:
    result = server.deploy(missing="deploy/quadlet/wediga.network")

    assert result.returncode != 0
    assert list(server.unit_dir.iterdir()) == []
    assert not any(call.startswith(("podman", "systemctl")) for call in server.calls())
