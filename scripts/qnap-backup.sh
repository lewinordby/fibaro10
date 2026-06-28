#!/bin/sh
set -eu

REMOTE_DIR="${REMOTE_DIR:-/share/CACHEDEV1_DATA/Public/containerdata/fibaro10}"
BACKUP_ROOT="${BACKUP_ROOT:-/share/CACHEDEV1_DATA/Public/containerdata/backups/fibaro10}"
DOCKER="${DOCKER:-/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-postgres-1}"
POSTGRES_USER="${POSTGRES_USER:-app}"
POSTGRES_DB="${POSTGRES_DB:-fibaro10_local}"
BACKUP_SNAPSHOTS="${BACKUP_SNAPSHOTS:-1}"

stamp="$(date +%Y%m%d-%H%M%S)"
backup_dir="$BACKUP_ROOT/$stamp"
mkdir -p "$backup_dir"

cd "$REMOTE_DIR"

for file in .env .env.* easypark_downloader/.env easypark_downloader/.env.*; do
    [ -f "$file" ] || continue
    target="$backup_dir/$file"
    mkdir -p "$(dirname "$target")"
    cp -p "$file" "$target"
done
[ -d easypark_downloader/data ] && mkdir -p "$backup_dir/easypark_downloader" && cp -a easypark_downloader/data "$backup_dir/easypark_downloader/data"
[ -d axis_camera_snapshots/data ] && mkdir -p "$backup_dir/axis_camera_snapshots" && cp -a axis_camera_snapshots/data "$backup_dir/axis_camera_snapshots/data"
if [ "$BACKUP_SNAPSHOTS" != "0" ] && [ -d axis_camera_snapshots/snapshots ]; then
    mkdir -p "$backup_dir/axis_camera_snapshots"
    tar -czf "$backup_dir/axis_camera_snapshots/snapshots.tgz" axis_camera_snapshots/snapshots
fi

if "$DOCKER" inspect "$POSTGRES_CONTAINER" >/dev/null 2>&1; then
    "$DOCKER" exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$backup_dir/${POSTGRES_DB}.sql"
fi

find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d | sort | head -n -20 | xargs -r rm -rf

echo "$backup_dir"
