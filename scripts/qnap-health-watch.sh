#!/bin/sh
set -eu

LOG_FILE="${LOG_FILE:-/share/CACHEDEV1_DATA/Public/containerdata/logs/fibaro10-health.log}"
mkdir -p "$(dirname "$LOG_FILE")"

check() {
    name="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') OK $name" >> "$LOG_FILE"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') FAIL $name" >> "$LOG_FILE"
        return 1
    fi
}

status=0
check fibaro10 curl -fsS --max-time 15 http://192.168.20.218:8110/health || status=1
check online_dashboard curl -fsS --max-time 15 -H "Host: online.lilletorget.net" http://127.0.0.1:8081/health || status=1

exit "$status"
