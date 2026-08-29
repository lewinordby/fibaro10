#!/bin/sh
set -eu

REPO_ROOT="${FIBARO10_REPO_ROOT:-/share/CACHEDEV1_DATA/Public/containerdata/fibaro10}"
ENV_FILE="${FIBARO10_ENV_FILE:-$REPO_ROOT/.env}"
DOCKER="${DOCKER_BIN:-/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker}"
CERT_DIR="${FIBARO10_TLS_CERT_DIR:-/share/CACHEDEV2_DATA/fibaro10_runtime/caddy/lego}"
LEGO_IMAGE="${FIBARO10_LEGO_IMAGE:-goacme/lego:v4.26.0}"
PROXY_LAN_IP="${FIBARO10_PROXY_LAN_IP:-192.168.20.219}"
PROXY_LAN_INTERFACE="${FIBARO10_PROXY_LAN_INTERFACE:-eth1}"
PRIMARY_DOMAIN="ny.lilletorget.net"
CERT_FILE="$CERT_DIR/certificates/$PRIMARY_DOMAIN.crt"

if [ ! -f "$ENV_FILE" ]; then
    echo "Mangler miljofil: $ENV_FILE" >&2
    exit 1
fi

email="$(sed -n 's/^LETSENCRYPT_EMAIL=//p' "$ENV_FILE" | tail -n 1)"
if [ -z "$email" ]; then
    echo "LETSENCRYPT_EMAIL mangler i $ENV_FILE" >&2
    exit 1
fi

mkdir -p "$CERT_DIR"
before="missing"
renew_days=30
force_domains=0
if [ -f "$CERT_FILE" ]; then
    before="$(sha256sum "$CERT_FILE" | awk '{print $1}')"
    for required_san in ny.lilletorget.net kiosk.lilletorget.net; do
        if ! openssl x509 -in "$CERT_FILE" -noout -text | grep -q "DNS:$required_san"; then
            renew_days=365
            force_domains=1
            echo "Sertifikatet mangler $required_san og fornyes derfor nå."
        fi
    done
fi

set -- \
    --path /data \
    --email "$email" \
    --accept-tos \
    --dns domeneshop \
    --dns.resolvers 1.1.1.1:53 \
    --domains ny.lilletorget.net \
    --domains kiosk.lilletorget.net

if [ -f "$CERT_FILE" ]; then
    action="renew"
    if [ "$force_domains" -eq 1 ]; then
        "$DOCKER" run --rm \
            --env-file "$ENV_FILE" \
            -v "$CERT_DIR:/data" \
            "$LEGO_IMAGE" "$@" renew --days "$renew_days" \
            --force-cert-domains --no-random-sleep
    else
        "$DOCKER" run --rm \
            --env-file "$ENV_FILE" \
            -v "$CERT_DIR:/data" \
            "$LEGO_IMAGE" "$@" renew --days "$renew_days"
    fi
else
    action="issue"
    "$DOCKER" run --rm \
        --env-file "$ENV_FILE" \
        -v "$CERT_DIR:/data" \
        "$LEGO_IMAGE" "$@" run
fi

after="$(sha256sum "$CERT_FILE" | awk '{print $1}')"
if [ "$before" != "$after" ]; then
    echo "HTTPS-sertifikatet er oppdatert ($action)."
    if "$DOCKER" inspect fibaro10_proxy >/dev/null 2>&1; then
        "$DOCKER" restart fibaro10_proxy >/dev/null
        sleep 3
        "$DOCKER" exec fibaro10_proxy /usr/sbin/arping \
            -U -c 5 -I "$PROXY_LAN_INTERFACE" "$PROXY_LAN_IP" >/dev/null 2>&1 || true
        "$DOCKER" exec fibaro10_proxy /usr/sbin/arping \
            -A -c 5 -I "$PROXY_LAN_INTERFACE" "$PROXY_LAN_IP" >/dev/null 2>&1 || true
        echo "Caddy-proxyen er restartet kontrollert med det nye sertifikatet."
    fi
else
    echo "HTTPS-sertifikatet er fortsatt gyldig; ingen omlasting nødvendig."
fi
