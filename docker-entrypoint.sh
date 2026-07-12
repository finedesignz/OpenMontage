#!/bin/sh
# Start as root only long enough to hand the mounted volumes to the app user,
# then drop privileges for good.
#
# Docker creates a named volume's mountpoint owned by root, so /app/jobs and
# /app/projects arrive root-owned no matter what the image says. The app must
# write both — job records, the stored agent token, and every render.
set -e

if [ "$(id -u)" = "0" ]; then
    for d in /app/jobs /app/projects; do
        mkdir -p "$d"
        chown -R agent:agent "$d" 2>/dev/null || true
    done
    exec gosu agent "$@"
fi

exec "$@"
