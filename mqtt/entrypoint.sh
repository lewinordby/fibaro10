#!/bin/sh
set -eu

OWNTRACKS_MQTT_USERNAME="${OWNTRACKS_MQTT_USERNAME:-owntracks}"
FIBARO10_MQTT_USERNAME="${FIBARO10_MQTT_USERNAME:-fibaro10}"

if [ -z "${OWNTRACKS_MQTT_PASSWORD:-}" ] || [ -z "${FIBARO10_MQTT_PASSWORD:-}" ]; then
  echo "OWNTRACKS_MQTT_PASSWORD and FIBARO10_MQTT_PASSWORD must be set"
  exit 1
fi

chown -R mosquitto:mosquitto /mosquitto/data
chmod 750 /mosquitto/data

rm -f /mosquitto/data/passwords /mosquitto/data/acl
mosquitto_passwd -b -c /mosquitto/data/passwords "$OWNTRACKS_MQTT_USERNAME" "$OWNTRACKS_MQTT_PASSWORD"
mosquitto_passwd -b /mosquitto/data/passwords "$FIBARO10_MQTT_USERNAME" "$FIBARO10_MQTT_PASSWORD"

{
  echo "user $OWNTRACKS_MQTT_USERNAME"
  echo "topic readwrite owntracks/#"
  echo ""
  echo "user $FIBARO10_MQTT_USERNAME"
  echo "topic read owntracks/#"
} > /mosquitto/data/acl

chown mosquitto:mosquitto /mosquitto/data/passwords /mosquitto/data/acl
chmod 640 /mosquitto/data/passwords /mosquitto/data/acl

exec mosquitto -c /mosquitto/config/mosquitto.conf
