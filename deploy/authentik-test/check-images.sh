#!/usr/bin/env bash
# Fail when the test environment and production run different authentik or
# PostgreSQL images. Each service in compose.yaml has a Quadlet file of the same
# name, and both must name the same image with the same digest. The authentik
# server and worker must also run the same image.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUADLET_DIR="$SCRIPT_DIR/../quadlet"

status=0

for service in authentik-db authentik-server authentik-worker; do
  production="$(sed -n 's/^Image=//p' "$QUADLET_DIR/$service.container")"
  test_env="$(awk -v service="  $service:" '
    $0 == service { found = 1; next }
    found && /^    image:/ { print $2; exit }
  ' "$SCRIPT_DIR/compose.yaml")"

  if [ "$production" != "$test_env" ]; then
    echo "$service: production runs '$production', the test environment '$test_env'"
    status=1
  fi
done

server="$(sed -n 's/^Image=//p' "$QUADLET_DIR/authentik-server.container")"
worker="$(sed -n 's/^Image=//p' "$QUADLET_DIR/authentik-worker.container")"

if [ "$server" != "$worker" ]; then
  echo "authentik-server runs '$server', authentik-worker '$worker'"
  status=1
fi

exit "$status"
