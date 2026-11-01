#!/usr/bin/env bash
# Forced command of the SSH key that may only create recruiter links. Whatever
# the caller sends becomes the label and reaches Python through stdin, so no
# shell ever reads it as a command.
set -euo pipefail

printf '%s\n' "${SSH_ORIGINAL_COMMAND:-}" |
  podman exec -i backend python -m app.recruiter.create_link
