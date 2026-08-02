#!/bin/sh
set -eu

LOG_FILE="${LOG_FILE:-/share/CACHEDEV1_DATA/Public/containerdata/logs/fibaro10-health.log}"
DOCKER="${DOCKER:-/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker}"
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
check shell_app curl -fsS --max-time 15 http://192.168.20.218:8150/ready || status=1
check revenue_app curl -fsS --max-time 15 http://192.168.20.218:8151/ready || status=1
check parking_app curl -fsS --max-time 15 http://192.168.20.218:8152/ready || status=1
check sun_app curl -fsS --max-time 15 http://192.168.20.218:8153/ready || status=1
check energy_app curl -fsS --max-time 15 http://192.168.20.218:8154/ready || status=1
check operations_app curl -fsS --max-time 15 http://192.168.20.218:8155/ready || status=1
check maintenance_app curl -fsS --max-time 15 http://192.168.20.218:8156/ready || status=1
check system_app curl -fsS --max-time 15 http://192.168.20.218:8157/ready || status=1
check link_app curl -fsS --max-time 15 http://192.168.20.218:8158/ready || status=1
check online_dashboard curl -fsS --max-time 15 -H "Host: online.lilletorget.net" http://127.0.0.1:8081/health || status=1
check fibaro10ipad curl -fsS --max-time 15 -H "Host: ipad.lilletorget.net" http://127.0.0.1:8081/health || status=1
check unifi_protect_events curl -fsS --max-time 15 http://192.168.20.218:8130/health || status=1
check visual_anomaly_service "$DOCKER" exec visual_anomaly_service python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8140/health', timeout=10).read()" || status=1

exit "$status"
