#!/usr/bin/env bash
# Fail when CI and the frontend image run different Node versions. The image
# pins NODE_VERSION in Dockerfile.frontend, and every setup-node step in ci.yml
# must name exactly the same version.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKERFILE="$SCRIPT_DIR/Dockerfile.frontend"
WORKFLOW="$SCRIPT_DIR/../.github/workflows/ci.yml"

image="$(sed -n 's/^ARG NODE_VERSION=//p' "$DOCKERFILE")"

if [ -z "$image" ]; then
  echo "Dockerfile.frontend names no NODE_VERSION"

  exit 1
fi

status=0
ci_versions="$(sed -n 's/^ *node-version: *//p' "$WORKFLOW")"

if [ -z "$ci_versions" ]; then
  echo "ci.yml names no node-version"

  exit 1
fi

while read -r ci; do
  if [ "$ci" != "$image" ]; then
    echo "ci.yml runs Node '$ci', Dockerfile.frontend '$image'"
    status=1
  fi
done <<< "$ci_versions"

exit "$status"
