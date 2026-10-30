#!/bin/sh
# Daily dump of the wediga.dev database, run by wediga-db-backup.timer.
#
# pg_dump runs inside the database container over the local socket, so no
# password is needed here. The dump is written to a temporary name first and
# only renamed once it is complete, so a failed run never leaves a file that
# looks like a valid backup.
set -eu

dir="$HOME/wediga-dev/backups"
keep_days=14

mkdir -p "$dir"
chmod 700 "$dir"

day="$(date +%F)"
tmp="$dir/.wediga-$day.dump.tmp"
out="$dir/wediga-$day.dump"

podman exec wediga-db pg_dump -U wediga -Fc wediga > "$tmp"
mv "$tmp" "$out"

find "$dir" -name 'wediga-*.dump' -mtime "+$keep_days" -delete
