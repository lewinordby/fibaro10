# OwnTracks MQTT

Fibaro10 kjører en intern Mosquitto MQTT-broker for OwnTracks.

## Broker

- Host internt nett: `192.168.20.218`
- Port: `1883`
- TLS: ikke aktivert på LAN-porten
- Topic-filter som Fibaro10 leser: `owntracks/#`
- Anonym tilgang: deaktivert

Broker er bundet til QNAP sin interne IP i `docker-compose.qnap.yml`. Ikke port-forward denne direkte til internett uten TLS/VPN.

## Brukere

Passord settes i QNAP sin `.env`, ikke i git.

- `OWNTRACKS_MQTT_USERNAME`: brukeren som OwnTracks-appen bruker for å publisere
- `OWNTRACKS_MQTT_PASSWORD`: passord for OwnTracks-appen
- `FIBARO10_MQTT_USERNAME`: intern Fibaro10-abonnent
- `FIBARO10_MQTT_PASSWORD`: passord for intern Fibaro10-abonnent

Mosquitto lager passordfil og ACL ved containerstart.

## OwnTracks app

Sett appen i MQTT-modus:

- Mode: MQTT private
- Host: `192.168.20.218`
- Port: `1883`
- WebSockets: av
- TLS: av på internt LAN
- Username: verdien i `OWNTRACKS_MQTT_USERNAME`
- Password: verdien i `OWNTRACKS_MQTT_PASSWORD`

Fibaro10 lagrer meldinger i:

- `owntracks_devices`: siste kjente status per topic/enhet
- `owntracks_locations`: historikk over mottatte OwnTracks-meldinger

Kontrollside:

- `/admin/owntracks`
- JSON-endepunkt: `/api/owntracks/devices`
