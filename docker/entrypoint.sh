#!/bin/sh
# Starts as root only to give the data folder to the CastHome user, then runs
# CastHome as that user. PUID/PGID pick the user (default 1000:1000), e.g. to
# match the owner of the mounted folder on a NAS.
set -e

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"
DATA_DIR="${DATA_DIR:-/data}"

if [ "$(id -u)" = "0" ]; then
  mkdir -p "$DATA_DIR"
  if ! chown -R "$PUID:$PGID" "$DATA_DIR" 2>/dev/null; then
    echo "Warning: could not change the owner of $DATA_DIR; CastHome may not be able to write to it." >&2
  fi
  exec setpriv --reuid="$PUID" --regid="$PGID" --clear-groups "$@"
fi

# Already started as a given user (e.g. `user:` in docker-compose.yml).
exec "$@"
