#!/usr/bin/env bash
# Deploys one commit of wediga.dev. GitHub Actions runs it over SSH with a key
# whose line in authorized_keys of web forces this script, so the key can do
# nothing else. The commit SHA arrives as the SSH command, and every file comes
# from that commit, so a deploy and any later restart are reproducible.
set -euo pipefail

REPOSITORY=https://raw.githubusercontent.com/wediga/wediga-dev
IMAGE_PREFIX=ghcr.io/wediga/wediga-dev
PARTS=(backend frontend)
# Every unit in deploy/quadlet, a test keeps both the same.
UNITS=(
  authentik-data.volume
  authentik-db.container
  authentik-db.volume
  authentik-server.container
  authentik-worker.container
  authentik.network
  backend-migrate.container
  backend.container
  frontend.container
  wediga-db.container
  wediga-db.volume
  wediga.network
)
APP_DIR="$HOME/wediga-dev"
UNIT_DIR="$HOME/.config/containers/systemd"
BLUEPRINT="$HOME/authentik/blueprints/wediga.yaml"

sha="${SSH_ORIGINAL_COMMAND:-}"

if [[ ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
  echo "expected a commit SHA, got '$sha'" >&2

  exit 1
fi

# A forced command gets no login session, and systemctl --user needs this.
XDG_RUNTIME_DIR="/run/user/$(id -u)"
export XDG_RUNTIME_DIR

# Everything is downloaded before anything is replaced, so a failed download
# leaves the server as it was.
base="$REPOSITORY/$sha/deploy"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

for unit in "${UNITS[@]}"; do
  curl -fsSL "$base/quadlet/$unit" -o "$work/$unit"
done

curl -fsSL "$base/authentik/blueprints/wediga.yaml" -o "$work/wediga.yaml"
curl -fsSL "$base/deploy.sh" -o "$work/deploy.sh"

for part in "${PARTS[@]}"; do
  image="$IMAGE_PREFIX-$part:$sha"
  sed -i "s#^Image=$IMAGE_PREFIX-$part:.*#Image=$image#" "$work"/*.container
  podman pull --quiet "$image" >/dev/null
done

for unit in "${UNITS[@]}"; do
  cp "$work/$unit" "$UNIT_DIR/$unit"
done

cp "$work/wediga.yaml" "$BLUEPRINT"

# authentik and the database are left running, so a routine deploy cannot take
# the login or the data down.
systemctl --user daemon-reload
systemctl --user restart backend-migrate.service backend.service frontend.service

# Only images of this repository, because NuviraLabs and the CR Predictor run
# under the same user.
for part in "${PARTS[@]}"; do
  podman images --format '{{.Repository}}:{{.Tag}}' \
    --filter "reference=$IMAGE_PREFIX-$part" --filter dangling=false |
    while read -r image; do
      if [ "$image" != "$IMAGE_PREFIX-$part:$sha" ]; then
        podman rmi "$image" >/dev/null
      fi
    done
done

# Replaced last and by renaming, because bash keeps reading this file while it
# runs and must not see the new version halfway.
install -m 700 "$work/deploy.sh" "$APP_DIR/.deploy.sh.new"
mv "$APP_DIR/.deploy.sh.new" "$APP_DIR/deploy.sh"
echo "deployed $sha"
