#!/bin/sh
set -eu

REMOTE_DIR="${REMOTE_DIR:-/share/CACHEDEV1_DATA/Public/containerdata/fibaro10}"
BACKUP_ROOT="${BACKUP_ROOT:-/share/CACHEDEV3_DATA/fibaro10_archive/fibaro10_backups}"
DOCKER="${DOCKER:-/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-postgres-1}"
POSTGRES_USER="${POSTGRES_USER:-app}"
POSTGRES_DB="${POSTGRES_DB:-fibaro10_local}"
BACKUP_SNAPSHOTS="${BACKUP_SNAPSHOTS:-0}"

stamp="$(date +%Y%m%d-%H%M%S)"
backup_dir="$BACKUP_ROOT/$stamp"
mkdir -p "$backup_dir"

cd "$REMOTE_DIR"

set -a
[ -f .env ] && . ./.env
[ -f easypark_downloader/.env ] && . ./easypark_downloader/.env
set +a

copy_dir() {
    source_dir="$1"
    target_dir="$2"
    [ -n "$source_dir" ] || return 0
    [ -d "$source_dir" ] || return 0
    mkdir -p "$(dirname "$target_dir")"
    cp -a "$source_dir" "$target_dir"
}

for file in .env .env.* easypark_downloader/.env easypark_downloader/.env.*; do
    [ -f "$file" ] || continue
    target="$backup_dir/$file"
    mkdir -p "$(dirname "$target")"
    cp -p "$file" "$target"
done

copy_dir "${EASYPARK_HOST_DATA_DIR:-easypark_downloader/data}" "$backup_dir/easypark_downloader/data"
copy_dir "${AXIS_HOST_DATA_DIR:-axis_camera_snapshots/data}" "$backup_dir/axis_camera_snapshots/data"
copy_dir "${OWNTRACKS_HOST_DATA_DIR:-owntracks_service/data}" "$backup_dir/owntracks_service/data"
copy_dir "${CAR_INFO_HOST_DATA_DIR:-car_info_lookup/data}" "$backup_dir/car_info_lookup/data"
copy_dir "${SUN2_SESSION_SCRAPER_HOST_DATA_DIR:-sun2_session_scraper/data}" "$backup_dir/sun2_session_scraper/data"
copy_dir "${FIBARO10_CADDY_DATA_DIR:-}" "$backup_dir/caddy/data"
copy_dir "${FIBARO10_CADDY_CONFIG_DIR:-}" "$backup_dir/caddy/config"

if [ "$BACKUP_SNAPSHOTS" != "0" ] && [ -d axis_camera_snapshots/snapshots ]; then
    mkdir -p "$backup_dir/axis_camera_snapshots"
    tar -czf "$backup_dir/axis_camera_snapshots/snapshots.tgz" axis_camera_snapshots/snapshots
fi

if "$DOCKER" inspect "$POSTGRES_CONTAINER" >/dev/null 2>&1; then
    "$DOCKER" exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$backup_dir/${POSTGRES_DB}.sql"
fi

find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d | sort | head -n -20 | xargs -r rm -rf

echo "$backup_dir"
