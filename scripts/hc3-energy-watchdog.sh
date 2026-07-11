#!/bin/sh
set -eu

PROJECT_DIR="${FIBARO10_PROJECT_DIR:-/share/CACHEDEV1_DATA/Public/containerdata/fibaro10}"
ENV_FILE="${HC3_WATCHDOG_ENV_FILE:-$PROJECT_DIR/.env.hc3-watchdog}"
DOCKER="${DOCKER:-/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker}"
CONTAINER="${FIBARO10_CONTAINER:-fibaro10}"
LOG_FILE="${HC3_ENERGY_WATCHDOG_LOG:-/share/CACHEDEV3_DATA/fibaro10_archive/logs/hc3-energy-watchdog.log}"

if [ -f "$ENV_FILE" ]; then
  # shellcheck disable=SC1090
  . "$ENV_FILE"
fi

: "${HC3_BASE_URL:?HC3_BASE_URL mangler}"
: "${HC3_USER:?HC3_USER mangler}"
: "${HC3_PASS:?HC3_PASS mangler}"

HC3_ENERGY_SCENE_ID="${HC3_ENERGY_SCENE_ID:-365}"
HC3_ENERGY_STALE_SECONDS="${HC3_ENERGY_STALE_SECONDS:-300}"
FIBARO10_HEALTH_URL="${FIBARO10_HEALTH_URL:-http://127.0.0.1:8110/health?details=true}"

mkdir -p "$(dirname "$LOG_FILE")"

"$DOCKER" exec -i \
  -e HC3_BASE_URL="$HC3_BASE_URL" \
  -e HC3_USER="$HC3_USER" \
  -e HC3_PASS="$HC3_PASS" \
  -e HC3_ENERGY_SCENE_ID="$HC3_ENERGY_SCENE_ID" \
  -e HC3_ENERGY_STALE_SECONDS="$HC3_ENERGY_STALE_SECONDS" \
  -e FIBARO10_HEALTH_URL="$FIBARO10_HEALTH_URL" \
  "$CONTAINER" python - <<'PY' >> "$LOG_FILE" 2>&1
import base64
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone


def stamp() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def parse_dt(value: str | None):
    if not value:
        return None
    text = str(value).replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.now().astimezone().tzinfo)
    return parsed.astimezone(timezone.utc)


def fetch_json(url: str):
    with urllib.request.urlopen(url, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def post_hc3(path: str):
    base_url = os.environ["HC3_BASE_URL"].rstrip("/")
    user = os.environ["HC3_USER"]
    password = os.environ["HC3_PASS"]
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(
        base_url + path,
        data=b"{}",
        method="POST",
        headers={
            "Authorization": f"Basic {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        response.read()
        return response.status


health_url = os.environ.get("FIBARO10_HEALTH_URL", "http://127.0.0.1:8110/health?details=true")
scene_id = os.environ.get("HC3_ENERGY_SCENE_ID", "365")
stale_seconds = int(os.environ.get("HC3_ENERGY_STALE_SECONDS", "300"))

try:
    health = fetch_json(health_url)
    sources = health.get("sources") or []
    source = next((item for item in sources if item.get("jobName") == "hc3_energy_1min"), None)
    last_success = parse_dt((source or {}).get("lastSuccessAt"))
    age_seconds = None
    if last_success:
        age_seconds = (datetime.now(timezone.utc) - last_success).total_seconds()

    if not source or last_success is None or age_seconds is None or age_seconds > stale_seconds:
        status = post_hc3(f"/api/scenes/{scene_id}/execute")
        print(
            f"{stamp()} restart scene={scene_id} status={status} "
            f"age_seconds={age_seconds if age_seconds is not None else 'unknown'}"
        )
    else:
        print(f"{stamp()} ok age_seconds={int(age_seconds)}")
except urllib.error.HTTPError as exc:
    print(f"{stamp()} error http={exc.code} detail={exc.read().decode('utf-8', errors='replace')[:400]}")
    raise
except Exception as exc:
    print(f"{stamp()} error {type(exc).__name__}: {exc}")
    raise
PY
