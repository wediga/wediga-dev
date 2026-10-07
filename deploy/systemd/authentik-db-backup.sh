#!/bin/sh
# Daily dump of the authentik database, run by authentik-db-backup.timer.
#
# pg_dump runs inside the database container over the local socket, so no
# password is needed here. The dump is written to a temporary name first and
# only renamed once it is complete, so a failed run never leaves a file that
# looks like a valid backup.
set -eu

dir="$HOME/authentik/backups"
keep_days=14

mkdir -p "$dir"
chmod 700 "$dir"

day="$(date +%F)"
tmp="$dir/.authentik-$day.dump.tmp"
out="$dir/authentik-$day.dump"

podman exec authentik-db pg_dump -U authentik -Fc authentik > "$tmp"
mv "$tmp" "$out"

find "$dir" -name 'authentik-*.dump' -mtime "+$keep_days" -delete
