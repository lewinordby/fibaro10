#!/bin/sh
set -eu

repo_dir=${1:-/share/CACHEDEV1_DATA/Public/containerdata/fibaro10}
import_file=${2:-.env.unifi.deploy}
snapshot_dir=${3:-/share/CACHEDEV3_DATA/fibaro10_archive/unifi_protect/snapshots}

cd "$repo_dir"
test -f .env
test -f "$import_file"

merge_file=".env.merge.$$"
next_file=".env.next.$$"
trap 'rm -f "$merge_file" "$next_file"' EXIT HUP INT TERM
cp .env "$merge_file"

set_value() {
    key=$1
    value=$2
    grep -v "^${key}=" "$merge_file" > "$next_file" || true
    mv "$next_file" "$merge_file"
    printf '%s=%s\n' "$key" "$value" >> "$merge_file"
}

while IFS= read -r line; do
    case "$line" in
        ''|'#'*) continue ;;
    esac
    key=${line%%=*}
    value=${line#*=}
    set_value "$key" "$value"
done < "$import_file"

read_token=$(grep '^UNIFI_PROTECT_READ_API_TOKEN=' "$merge_file" 2>/dev/null | tail -1 | cut -d= -f2- || true)
webhook_token=$(grep '^UNIFI_PROTECT_WEBHOOK_TOKEN=' "$merge_file" 2>/dev/null | tail -1 | cut -d= -f2- || true)
test -n "$read_token" || read_token=$(openssl rand -hex 32)
test -n "$webhook_token" || webhook_token=$(openssl rand -hex 32)

set_value UNIFI_PROTECT_READ_API_TOKEN "$read_token"
set_value UNIFI_PROTECT_WEBHOOK_TOKEN "$webhook_token"
set_value UNIFI_PROTECT_WEBHOOK_ALLOWED_IPS 192.168.1.1,192.168.20.1
set_value UNIFI_PROTECT_CONSOLE_KEY lilletorget
set_value UNIFI_PROTECT_HOST_SNAPSHOT_DIR "$snapshot_dir"
set_value UNIFI_PROTECT_SNAPSHOT_WORKERS 2
set_value UNIFI_PROTECT_SNAPSHOT_QUEUE_SIZE 1000
set_value UNIFI_PROTECT_API_TIMEOUT_SECONDS 10

mv "$merge_file" .env
chmod 600 .env
mkdir -p "$snapshot_dir"
rm -f "$import_file"
trap - EXIT HUP INT TERM

configured_count=$(grep -E '^UNIFI_PROTECT_(NVR_URL|API_KEY|VERIFY_SSL|CONSOLE_KEY|READ_API_TOKEN|WEBHOOK_TOKEN|HOST_SNAPSHOT_DIR|SNAPSHOT_WORKERS|SNAPSHOT_QUEUE_SIZE|API_TIMEOUT_SECONDS)=' .env | cut -d= -f1 | wc -l)
printf 'configured_keys=%s\n' "$configured_count"
