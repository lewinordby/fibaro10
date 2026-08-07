#!/bin/sh
set -eu

LOG_FILE="${LOG_FILE:-/share/CACHEDEV1_DATA/Public/containerdata/logs/fibaro10-health.log}"
STATUS_FILE="${STATUS_FILE:-/share/CACHEDEV1_DATA/Public/containerdata/logs/fibaro10-health-status.txt}"
DOCKER="${DOCKER:-/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker}"
BACKUP_ROOT="${BACKUP_ROOT:-/share/CACHEDEV3_DATA/fibaro10_archive/fibaro10_backups}"
FULL_BACKUP_STATUS="${FULL_BACKUP_STATUS:-/share/CACHEDEV3_DATA/fibaro10_archive/full_restore_backup/latest/BACKUP_STATUS.txt}"
MAX_LOG_BYTES="${MAX_LOG_BYTES:-5242880}"

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$STATUS_FILE")"
if [ -f "$LOG_FILE" ] && [ "$(wc -c < "$LOG_FILE")" -gt "$MAX_LOG_BYTES" ]; then
    mv "$LOG_FILE" "$LOG_FILE.1"
fi

status_tmp="$STATUS_FILE.tmp.$$"
: > "$status_tmp"
status=0

check() {
    name="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        result="OK"
    else
        result="FAIL"
        status=1
    fi
    printf '%s %s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$result" "$name" | tee -a "$LOG_FILE" >> "$status_tmp"
}

check fibaro10 curl -fsS --max-time 15 http://192.168.20.218:8110/health
check shell_app curl -fsS --max-time 15 http://192.168.20.218:8150/ready
check revenue_app curl -fsS --max-time 15 http://192.168.20.218:8151/ready
check parking_app curl -fsS --max-time 15 http://192.168.20.218:8152/ready
check sun_app curl -fsS --max-time 15 http://192.168.20.218:8153/ready
check energy_app curl -fsS --max-time 15 http://192.168.20.218:8154/ready
check operations_app curl -fsS --max-time 15 http://192.168.20.218:8155/ready
check maintenance_app curl -fsS --max-time 15 http://192.168.20.218:8156/ready
check system_app curl -fsS --max-time 15 http://192.168.20.218:8157/ready
check link_app curl -fsS --max-time 15 http://192.168.20.218:8158/ready
check online_dashboard curl -fsS --max-time 15 -H "Host: online.lilletorget.net" http://127.0.0.1:8081/health
check maintenance_mobile curl -fsS --max-time 15 -H "Host: vedl.lilletorget.net" http://127.0.0.1:8081/health
check fibaro10ipad curl -fsS --max-time 15 -H "Host: ipad.lilletorget.net" http://127.0.0.1:8081/health
check owntracks_service curl -fsS --max-time 15 -H "Host: owntracks.lilletorget.net" http://127.0.0.1:8081/health
check alarm_mobile curl -fsS --max-time 15 http://192.168.20.218:8114/health
check axis_camera_snapshots curl -fsS --max-time 15 http://192.168.20.218:8125/health
check car_info_lookup curl -fsS --max-time 15 http://192.168.20.218:8126/health
check parking_sun_linker curl -fsS --max-time 15 http://192.168.20.218:8127/health
check unifi_protect_events curl -fsS --max-time 15 http://192.168.20.218:8130/health
check visual_anomaly_service "$DOCKER" exec visual_anomaly_service python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8140/health', timeout=10).read()"
check easypark_downloader curl -fsS --max-time 15 http://192.168.20.218:8109/health
check roborock_logger curl -fsS --max-time 15 http://192.168.20.218:8095/health
check sun2_backfill_downloader curl -fsS --max-time 15 http://192.168.20.218:8097/json
check sun2_importer curl -fsS --max-time 15 http://192.168.20.218:8096/json
check sun2_session_scraper curl -fsS --max-time 15 http://192.168.20.218:8099/json
check nightly_backup sh -c "test -f '$BACKUP_ROOT/LATEST_STATUS.txt' && grep -Eq '^status=(ok|warning)$' '$BACKUP_ROOT/LATEST_STATUS.txt' && find '$BACKUP_ROOT/LATEST_STATUS.txt' -mmin -1560 -print -quit | grep -q ."
check full_restore_backup sh -c "test -f '$FULL_BACKUP_STATUS' && grep -Eq '^status=(ok|warning)$' '$FULL_BACKUP_STATUS' && find '$FULL_BACKUP_STATUS' -mmin -2940 -print -quit | grep -q ."
check volume_1_free sh -c "test \$(df -Pk /share/CACHEDEV1_DATA | awk 'NR==2 {print 100-\$5}') -ge 10"
check volume_2_free sh -c "test \$(df -Pk /share/CACHEDEV2_DATA | awk 'NR==2 {print 100-\$5}') -ge 10"
check volume_3_free sh -c "test \$(df -Pk /share/CACHEDEV3_DATA | awk 'NR==2 {print 100-\$5}') -ge 10"

printf 'checked=%s\nstatus=%s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$([ "$status" -eq 0 ] && echo ok || echo error)" >> "$status_tmp"
mv "$status_tmp" "$STATUS_FILE"
exit "$status"
