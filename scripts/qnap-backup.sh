#!/bin/sh
set -eu

REMOTE_DIR="${REMOTE_DIR:-/share/CACHEDEV1_DATA/Public/containerdata/fibaro10}"
BACKUP_ROOT="${BACKUP_ROOT:-/share/CACHEDEV3_DATA/fibaro10_archive/fibaro10_backups}"
DOCKER="${DOCKER:-/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-postgres-1}"
POSTGRES_USER="${POSTGRES_USER:-app}"
POSTGRES_DB="${POSTGRES_DB:-fibaro10_local}"
OWNTRACKS_POSTGRES_CONTAINER="${OWNTRACKS_POSTGRES_CONTAINER:-owntracks_postgres}"
ROBOROCK_CONTAINER="${ROBOROCK_CONTAINER:-roborock_logger}"
BACKUP_SNAPSHOTS="${BACKUP_SNAPSHOTS:-0}"
BACKUP_RETENTION_COUNT="${BACKUP_RETENTION_COUNT:-20}"
BACKUP_REPLICA_TARGET="${BACKUP_REPLICA_TARGET:-}"
LOCK_DIR="${LOCK_DIR:-/tmp/fibaro10-qnap-backup.lock}"

source /opt/etc/profile 2>/dev/null || true
mkdir -p "$BACKUP_ROOT"
status_file="$BACKUP_ROOT/LATEST_STATUS.txt"
stamp="$(date +%Y%m%d-%H%M%S)"
partial_dir="$BACKUP_ROOT/.partial-$stamp"
backup_dir="$BACKUP_ROOT/$stamp"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "Backup is already running: $LOCK_DIR" >&2
    exit 0
fi

cleanup() {
    exit_code=$?
    if [ "$exit_code" -ne 0 ]; then
        rm -rf "$partial_dir"
        printf 'started=%s\nfinished=%s\nstatus=error\nbackup_dir=%s\n' \
            "$stamp" "$(date +%Y%m%d-%H%M%S)" "$backup_dir" > "$status_file"
    fi
    rm -rf "$LOCK_DIR"
}
trap cleanup EXIT
trap 'exit 130' INT TERM

printf 'started=%s\nstatus=running\nbackup_dir=%s\n' "$stamp" "$backup_dir" > "$status_file"
mkdir -p "$partial_dir"
cd "$REMOTE_DIR"

env_value() {
    file="$1"
    key="$2"
    [ -f "$file" ] || return 0
    line="$(grep -m 1 "^${key}=" "$file" || true)"
    [ -n "$line" ] || return 0
    printf '%s' "${line#*=}"
}

copy_dir() {
    source_dir="$1"
    target_dir="$2"
    [ -n "$source_dir" ] || return 0
    [ -d "$source_dir" ] || return 0
    mkdir -p "$(dirname "$target_dir")"
    cp -a "$source_dir" "$target_dir"
}

EASYPARK_HOST_DATA_DIR="${EASYPARK_HOST_DATA_DIR:-$(env_value easypark_downloader/.env EASYPARK_HOST_DATA_DIR)}"
AXIS_HOST_DATA_DIR="${AXIS_HOST_DATA_DIR:-$(env_value .env AXIS_HOST_DATA_DIR)}"
AXIS_HOST_SNAPSHOT_DIR="${AXIS_HOST_SNAPSHOT_DIR:-$(env_value .env AXIS_HOST_SNAPSHOT_DIR)}"
OWNTRACKS_HOST_DATA_DIR="${OWNTRACKS_HOST_DATA_DIR:-$(env_value .env OWNTRACKS_HOST_DATA_DIR)}"
CAR_INFO_HOST_DATA_DIR="${CAR_INFO_HOST_DATA_DIR:-$(env_value .env CAR_INFO_HOST_DATA_DIR)}"
SUN2_DAILY_DATA_DIR="${SUN2_DAILY_DATA_DIR:-$(env_value .env SUN2_DAILY_DATA_DIR)}"
SUN2_DAILY_DATA_DIR="${SUN2_DAILY_DATA_DIR:-$(env_value sun2_backfill_downloader/.env SUN2_DAILY_DATA_DIR)}"
SUN2_DAILY_DATA_DIR="${SUN2_DAILY_DATA_DIR:-$(env_value sun2_importer/.env SUN2_DAILY_DATA_DIR)}"
SUN2_SESSION_SCRAPER_HOST_DATA_DIR="${SUN2_SESSION_SCRAPER_HOST_DATA_DIR:-$(env_value .env SUN2_SESSION_SCRAPER_HOST_DATA_DIR)}"
FIBARO10_CADDY_DATA_DIR="${FIBARO10_CADDY_DATA_DIR:-$(env_value .env FIBARO10_CADDY_DATA_DIR)}"
FIBARO10_CADDY_CONFIG_DIR="${FIBARO10_CADDY_CONFIG_DIR:-$(env_value .env FIBARO10_CADDY_CONFIG_DIR)}"
VISUAL_AI_HOST_DATA_DIR="${VISUAL_AI_HOST_DATA_DIR:-$(env_value .env VISUAL_AI_HOST_DATA_DIR)}"
OWNTRACKS_POSTGRES_USER="${OWNTRACKS_POSTGRES_USER:-$(env_value .env OWNTRACKS_POSTGRES_USER)}"
OWNTRACKS_POSTGRES_USER="${OWNTRACKS_POSTGRES_USER:-owntracks}"
OWNTRACKS_POSTGRES_DB="${OWNTRACKS_POSTGRES_DB:-$(env_value .env OWNTRACKS_POSTGRES_DB)}"
OWNTRACKS_POSTGRES_DB="${OWNTRACKS_POSTGRES_DB:-owntracks}"

for file in .env .env.* easypark_downloader/.env easypark_downloader/.env.* car_info_lookup/.env car_info_lookup/.env.* sun2_backfill_downloader/.env sun2_backfill_downloader/.env.* sun2_importer/.env sun2_importer/.env.* sun2_session_scraper/.env sun2_session_scraper/.env.* roborock_logger/.env roborock_logger/.env.* hc3_vedlikehold/.env hc3_vedlikehold/.env.*; do
    case "$file" in .env.example|.env.qnap.example|*/.env.example) continue ;; esac
    [ -f "$file" ] || continue
    target="$partial_dir/$file"
    mkdir -p "$(dirname "$target")"
    cp -p "$file" "$target"
done

copy_dir "${EASYPARK_HOST_DATA_DIR:-easypark_downloader/data}" "$partial_dir/easypark_downloader/data"
copy_dir "${AXIS_HOST_DATA_DIR:-axis_camera_snapshots/data}" "$partial_dir/axis_camera_snapshots/data"
copy_dir "${OWNTRACKS_HOST_DATA_DIR:-owntracks_service/data}" "$partial_dir/owntracks_service/data"
copy_dir "${CAR_INFO_HOST_DATA_DIR:-car_info_lookup/data}" "$partial_dir/car_info_lookup/data"
copy_dir "${SUN2_DAILY_DATA_DIR:-sun2_daily_data}" "$partial_dir/sun2_daily_data"
copy_dir "${SUN2_SESSION_SCRAPER_HOST_DATA_DIR:-sun2_session_scraper/data}" "$partial_dir/sun2_session_scraper/data"
copy_dir "${FIBARO10_CADDY_DATA_DIR:-}" "$partial_dir/caddy/data"
copy_dir "${FIBARO10_CADDY_CONFIG_DIR:-}" "$partial_dir/caddy/config"
copy_dir "${VISUAL_AI_HOST_DATA_DIR:-visual_anomaly_service/data}" "$partial_dir/visual_anomaly_service/data"

if [ "$BACKUP_SNAPSHOTS" != "0" ] && [ -n "$AXIS_HOST_SNAPSHOT_DIR" ] && [ -d "$AXIS_HOST_SNAPSHOT_DIR" ]; then
    mkdir -p "$partial_dir/axis_camera_snapshots"
    tar -czf "$partial_dir/axis_camera_snapshots/snapshots.tgz" -C "$AXIS_HOST_SNAPSHOT_DIR" .
fi

"$DOCKER" inspect "$POSTGRES_CONTAINER" >/dev/null 2>&1
"$DOCKER" exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$partial_dir/${POSTGRES_DB}.sql"
test -s "$partial_dir/${POSTGRES_DB}.sql"

"$DOCKER" inspect "$OWNTRACKS_POSTGRES_CONTAINER" >/dev/null 2>&1
"$DOCKER" exec "$OWNTRACKS_POSTGRES_CONTAINER" pg_dump -U "$OWNTRACKS_POSTGRES_USER" "$OWNTRACKS_POSTGRES_DB" > "$partial_dir/owntracks.sql"
test -s "$partial_dir/owntracks.sql"

if "$DOCKER" inspect "$ROBOROCK_CONTAINER" >/dev/null 2>&1; then
    mkdir -p "$partial_dir/roborock_logger/data"
    "$DOCKER" cp "$ROBOROCK_CONTAINER:/data/." "$partial_dir/roborock_logger/data"
fi

printf 'created=%s\nbuild=%s\ncommit=%s\n' \
    "$stamp" "$(cat BUILD 2>/dev/null || echo unknown)" "$(git rev-parse --short HEAD 2>/dev/null || echo unknown)" \
    > "$partial_dir/BACKUP_MANIFEST.txt"
(
    cd "$partial_dir"
    find . -type f ! -name CHECKSUMS.sha256 -print | sort | while IFS= read -r file; do
        sha256sum "$file"
    done > CHECKSUMS.sha256
)
mv "$partial_dir" "$backup_dir"
printf '%s\n' "$backup_dir" > "$BACKUP_ROOT/LATEST_BACKUP.txt"

replica_status="not_configured"
if [ -n "$BACKUP_REPLICA_TARGET" ]; then
    replica_status="ok"
    if ! rsync -a "$backup_dir/" "$BACKUP_REPLICA_TARGET/$stamp/"; then
        replica_status="error"
    fi
fi

if [ "$BACKUP_RETENTION_COUNT" -gt 0 ]; then
    find "$BACKUP_ROOT" -mindepth 1 -maxdepth 1 -type d -name '20[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]' \
        | sort | head -n -"$BACKUP_RETENTION_COUNT" | xargs -r rm -rf
fi

final_status="ok"
[ "$replica_status" = "error" ] && final_status="warning"
printf 'started=%s\nfinished=%s\nstatus=%s\nbackup_dir=%s\nreplica_status=%s\n' \
    "$stamp" "$(date +%Y%m%d-%H%M%S)" "$final_status" "$backup_dir" "$replica_status" > "$status_file"
echo "$backup_dir"
