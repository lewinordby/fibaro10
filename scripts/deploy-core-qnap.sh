#!/bin/sh
set -eu

DOCKER=${1:?Docker binary path is required}
COMPOSE_FILE=${COMPOSE_FILE:-docker-compose.qnap.yml}
STATE_DIR=${FIBARO10_DEPLOY_STATE_DIR:-/share/CACHEDEV3_DATA/fibaro10_runtime}
STATE_FILE="$STATE_DIR/active-slot"
EXPECTED_BUILD=${APP_BUILD:?APP_BUILD is required}

compose() {
    "$DOCKER" compose -f "$COMPOSE_FILE" "$@"
}

is_running() {
    [ "$("$DOCKER" inspect --format '{{.State.Running}}' "$1" 2>/dev/null || true)" = "true" ]
}

is_healthy() {
    [ "$("$DOCKER" inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$1" 2>/dev/null || true)" = "healthy" ]
}

wait_healthy() {
    wait_name=$1
    wait_count=0
    while [ "$wait_count" -lt 90 ]; do
        if is_running "$wait_name" && is_healthy "$wait_name"; then
            return 0
        fi
        wait_count=$((wait_count + 1))
        sleep 2
    done
    "$DOCKER" logs --tail=120 "$wait_name" || true
    echo "$wait_name did not become healthy" >&2
    return 1
}

verify_core() {
    verify_name=$1
    verify_role=$2
    "$DOCKER" exec "$verify_name" python -c \
        "import json, urllib.request; p=json.load(urllib.request.urlopen('http://127.0.0.1:8110/health', timeout=5)); assert str(p['app']['build']) == '$EXPECTED_BUILD', p['app']; assert str(p['runtime']['role']).startswith('$verify_role'), p['runtime']"
}

wait_gateway_build() {
    gateway_count=0
    while [ "$gateway_count" -lt 60 ]; do
        gateway_build=$(curl -fsS --max-time 5 http://192.168.20.218:8110/health 2>/dev/null \
            | sed -n 's/.*"build":"\([^"]*\)".*/\1/p' || true)
        if [ "$gateway_build" = "$EXPECTED_BUILD" ]; then
            return 0
        fi
        gateway_count=$((gateway_count + 1))
        sleep 1
    done
    echo "Fibaro10 gateway did not switch to build $EXPECTED_BUILD" >&2
    return 1
}

mkdir -p "$STATE_DIR"
active=""
if [ -f "$STATE_FILE" ]; then
    active=$(cat "$STATE_FILE" 2>/dev/null || true)
fi
case "$active" in
    blue|green)
        if ! is_running "fibaro10_$active" || ! is_healthy "fibaro10_$active"; then
            active=""
        fi
        ;;
    *) active="" ;;
esac
if [ -z "$active" ]; then
    if is_running fibaro10_blue && is_healthy fibaro10_blue; then
        active=blue
    elif is_running fibaro10_green && is_healthy fibaro10_green; then
        active=green
    fi
fi

if [ "$active" = "blue" ]; then
    candidate=green
else
    candidate=blue
fi
candidate_name="fibaro10_$candidate"
active_name=""
if [ -n "$active" ]; then
    active_name="fibaro10_$active"
fi

echo "Core rollout: active=${active:-legacy}, candidate=$candidate, build=$EXPECTED_BUILD"
compose build "$candidate_name"
compose up -d --no-deps --force-recreate "$candidate_name"
wait_healthy "$candidate_name"
verify_core "$candidate_name" "web-$candidate"

gateway_image=$("$DOCKER" inspect --format '{{.Config.Image}}' fibaro10 2>/dev/null || true)
case "$gateway_image" in
    caddy:*)
        "$DOCKER" exec fibaro10 caddy validate --config /etc/caddy/Caddyfile
        "$DOCKER" exec fibaro10 caddy reload --config /etc/caddy/Caddyfile
        ;;
    *)
        "$DOCKER" rm -f fibaro10 >/dev/null 2>&1 || true
        compose up -d --no-deps fibaro10
        wait_healthy fibaro10
        ;;
esac

if [ "$active" = "blue" ]; then
    compose stop "$active_name"
fi
wait_gateway_build
if [ "$active" = "green" ]; then
    compose stop "$active_name"
fi

compose up -d --no-deps --force-recreate fibaro10_worker
wait_healthy fibaro10_worker
verify_core fibaro10_worker worker

printf '%s\n' "$candidate" > "$STATE_FILE"
echo "Core rollout complete: active=$candidate, build=$EXPECTED_BUILD"
