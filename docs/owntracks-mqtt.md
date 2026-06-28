# OwnTracks MQTT

Fibaro10 kjorer en Mosquitto MQTT-broker for OwnTracks. Broker har to innganger:

- intern MQTT paa LAN for testing og intern drift
- offentlig MQTT over WebSocket via eksisterende Caddy/TLS paa `online.lilletorget.net/mqtt`

## Broker

Internt nett:

- Host: `192.168.20.218`
- Port: `1883`
- TLS: av paa LAN-porten
- WebSockets: av
- Topic-filter som Fibaro10 leser: `owntracks/#`
- Anonym tilgang: deaktivert

Offentlig tilgang:

- Host: `online.lilletorget.net`
- Port: `443`
- TLS: paa
- WebSockets: paa
- WebSocket path: `/mqtt`

Offentlig trafikk gaar gjennom Caddy paa samme HTTPS-endepunkt som online-dashboardet. Caddy sender bare `/mqtt` videre til Mosquitto sin interne WebSocket-listener paa port `9001`.

Ikke port-forward vanlig MQTT-port `1883` direkte til internett.

## Brukere

Passord settes i QNAP sin `.env`, ikke i git.

- `OWNTRACKS_MQTT_USERNAME`: brukeren som OwnTracks-appen bruker for aa publisere
- `OWNTRACKS_MQTT_PASSWORD`: passord for OwnTracks-appen
- `FIBARO10_MQTT_USERNAME`: intern Fibaro10-abonnent
- `FIBARO10_MQTT_PASSWORD`: passord for intern Fibaro10-abonnent

Mosquitto lager passordfil og ACL ved containerstart.

## OwnTracks app uten VPN

Sett appen i MQTT-modus:

- Mode: MQTT private
- Host: `online.lilletorget.net`
- Port: `443`
- TLS: paa
- WebSockets: paa
- WebSocket path: `/mqtt` hvis appen viser eget felt for dette
- Username: verdien i `OWNTRACKS_MQTT_USERNAME`
- Password: verdien i `OWNTRACKS_MQTT_PASSWORD`

Hvis appen bare har en WebSockets-bryter og ikke eget path-felt, bruk standard path. OwnTracks Android bruker normalt `/mqtt` som standard for MQTT over WebSocket.

## OwnTracks app paa internt LAN

Dette kan brukes ved lokal test:

- Mode: MQTT private
- Host: `192.168.20.218`
- Port: `1883`
- WebSockets: av
- TLS: av
- Username: verdien i `OWNTRACKS_MQTT_USERNAME`
- Password: verdien i `OWNTRACKS_MQTT_PASSWORD`

## Fibaro10

Fibaro10 abonnerer internt paa `owntracks/#` og lagrer meldinger i:

- `owntracks_devices`: siste kjente status per topic/enhet
- `owntracks_locations`: historikk over mottatte OwnTracks-meldinger

Kontrollside:

- `/admin/owntracks`
- JSON-endepunkt: `/api/owntracks/devices`
