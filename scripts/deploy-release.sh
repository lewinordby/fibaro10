#!/bin/sh
set -eu
umask 077
ROOT=${1:?repo}; BACKUPS=${2:?backup root}; DOCKER=${3:?docker}
PREVIOUS=${4:?previous commit}; TARGET=${5:?target commit}; BRANCH=${6:?branch}
shift 6
if [ -f /opt/etc/profile ]; then . /opt/etc/profile; fi
cd "$ROOT"
test "$(git rev-parse HEAD)" = "$PREVIOUS"
test -z "$(git status --porcelain --untracked-files=no)"
mkdir -p "$BACKUPS"
LOCK="$BACKUPS/deploy.lock"
mkdir "$LOCK" || { echo 'Another deployment is active; inspect deploy.lock before retrying.' >&2; exit 1; }
trap 'rmdir "$LOCK"' EXIT
test "$(git rev-parse HEAD)" = "$PREVIOUS"
git fetch origin "$BRANCH"
git merge-base --is-ancestor "$PREVIOUS" "$TARGET"
git cat-file -e "$TARGET^{commit}"
BACKUP="$BACKUPS/$(date +%Y%m%d-%H%M%S)-${TARGET%????????????????????????????}"
mkdir "$BACKUP"
printf '%s\n' "$PREVIOUS" > "$BACKUP/previous-commit.txt"
printf '%s\n' "$TARGET" > "$BACKUP/target-commit.txt"
git archive --format=tar HEAD > "$BACKUP/previous-source.tar"
service_config() {
    case "$1" in
        easypark_downloader) directory=easypark_downloader; compose=docker-compose.yml ;;
        roborock_logger|dreame_logger) directory=$1; compose=docker-compose.qnap.yml ;;
        owntracks_service|revenue_app|parking_app|sun_app|energy_app|operations_app|maintenance_app|system_app|link_app|unifi_protect_events|visual_anomaly_service|online_dashboard|maintenance_mobile|alarm_mobile|axis_camera_snapshots|car_info_lookup|sun2_backfill_downloader|sun2_importer|sun2_session_scraper|parking_sun_linker|fibaro10_proxy)
            directory=.; compose=docker-compose.qnap.yml ;;
        *) echo "Unapproved service: $1" >&2; exit 1 ;;
    esac
}
for service in "$@"; do
    [ "$service" != fibaro10 ] || continue
    service_config "$service"
    # Preserve resolved environment and mounts, not only the old image.
    (cd "$directory"; "$DOCKER" compose -f "$compose" --profile unifi-protect config --format json) > "$BACKUP/$service.compose.json"
done
# No runtime files are deleted, restored over live files, or modified here.
git merge --ff-only "$TARGET"
export APP_COMMIT=$(git rev-parse --short HEAD)
export APP_BUILD=$(cat BUILD)
for app in owntracks_service revenue_app parking_app sun_app energy_app operations_app maintenance_app maintenance_mobile alarm_mobile system_app link_app; do
    if [ -f "$app/BUILD" ]; then
        prefix=$(printf '%s' "$app" | tr '[:lower:]' '[:upper:]')
        [ "$app" != owntracks_service ] || prefix=OWNTRACKS_APP
        export "${prefix}_BUILD=$(cat "$app/BUILD")"
    fi
done
export PROTECT_LEDGER_BUILD=$(cat unifi_protect_events/BUILD)

for service in "$@"; do
    if [ "$service" = fibaro10 ]; then sh scripts/deploy-core-qnap.sh "$DOCKER"; continue; fi
    service_config "$service"
    (
        cd "$directory"
        if [ "$service" = fibaro10_proxy ]; then
            DOCKER_BIN="$DOCKER" sh scripts/renew-internal-https.sh
        fi
        old_image=$("$DOCKER" inspect --format '{{.Image}}' "$service" 2>/dev/null || true)
        if [ -n "$old_image" ]; then
            "$DOCKER" tag "$old_image" "fibaro10-rollback/$service:$PREVIOUS"
            printf '%s %s\n' "$service" "$old_image" >> "$BACKUP/previous-images.txt"
        fi
        "$DOCKER" compose -f "$compose" --profile unifi-protect config --quiet
        "$DOCKER" compose -f "$compose" --profile unifi-protect build "$service"
        started=0
        wait_healthy() {
            attempt=0
            while [ "$attempt" -lt "${DEPLOY_HEALTH_ATTEMPTS:-90}" ]; do
                state=$("$DOCKER" inspect --format '{{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{end}}' "$service" 2>/dev/null || true)
                [ "$state" != 'running healthy' ] || return 0
                attempt=$((attempt + 1))
                sleep "${DEPLOY_POLL_SECONDS:-2}"
            done
            return 1
        }
        rollback() {
            code=$?
            trap - EXIT
            if [ "$code" -ne 0 ] && [ "$started" = 1 ] && [ -n "$old_image" ]; then
                echo "Restoring image for $service after failed rollout" >&2
                printf 'services:\n  %s:\n    image: %s\n' "$service" "$old_image" > "$BACKUP/$service.rollback.yml"
                if "$DOCKER" compose --project-directory "$ROOT/$directory" -f "$BACKUP/$service.compose.json" -f "$BACKUP/$service.rollback.yml" --profile unifi-protect up -d --no-build --no-deps "$service" && wait_healthy; then
                    echo "Restored $service; source checkout remains at $TARGET" > "$BACKUP/$service.rollback-result.txt"
                else
                    echo "ROLLBACK FAILED: $service requires intervention. Evidence: $BACKUP" >&2
                    echo 'rollback failed' > "$BACKUP/$service.rollback-result.txt"
                fi
            fi
            exit "$code"
        }
        trap rollback EXIT
        started=1
        "$DOCKER" compose -f "$compose" --profile unifi-protect up -d --no-build --no-deps "$service"
        wait_healthy
    )
done
printf 'Verified deployment of %s\n' "$TARGET" > "$BACKUP/result.txt"
echo "Backup and rollback images: $BACKUP"
