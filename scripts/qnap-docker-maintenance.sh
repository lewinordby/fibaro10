#!/bin/sh
set -eu

DOCKER="${DOCKER:-/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker}"
LOG_FILE="${LOG_FILE:-/share/CACHEDEV1_DATA/Public/containerdata/logs/fibaro10-docker-maintenance.log}"
STATUS_FILE="${STATUS_FILE:-/share/CACHEDEV1_DATA/Public/containerdata/logs/fibaro10-docker-maintenance-status.txt}"
KEEP_HOURS="${KEEP_HOURS:-336}"
LOCK_DIR="${LOCK_DIR:-/tmp/fibaro10-docker-maintenance.lock}"

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$STATUS_FILE")"
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "Docker maintenance is already running: $LOCK_DIR" >&2
    exit 0
fi
trap 'rm -rf "$LOCK_DIR"' EXIT
trap 'exit 130' INT TERM

started="$(date +%Y%m%d-%H%M%S)"
printf 'started=%s\nstatus=running\n' "$started" > "$STATUS_FILE"
{
    echo "$(date '+%Y-%m-%d %H:%M:%S') Docker maintenance started"
    "$DOCKER" system df
    "$DOCKER" builder prune -af --filter "until=${KEEP_HOURS}h"
    "$DOCKER" image prune -af --filter "until=${KEEP_HOURS}h"
    "$DOCKER" system df
    echo "$(date '+%Y-%m-%d %H:%M:%S') Docker maintenance completed"
} >> "$LOG_FILE" 2>&1
printf 'started=%s\nfinished=%s\nstatus=ok\nkeep_hours=%s\n' \
    "$started" "$(date +%Y%m%d-%H%M%S)" "$KEEP_HOURS" > "$STATUS_FILE"
