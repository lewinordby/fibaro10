# OwnTracks MQTT

Fibaro10 kan ta imot OwnTracks paa to maater:

- anbefalt ekstern inngang: HTTP mot Fibaro10 med vanlige Fibaro10-brukere
- MQTT-inngang: Mosquitto-broker for intern drift og MQTT-klienter

Bruk HTTP-modus naar OwnTracks skal brukes uten VPN, fordi Fibaro10 da autentiserer med samme brukere som resten av appen.

## OwnTracks app uten VPN, anbefalt

Sett appen i HTTP-modus:

- Mode: `HTTP`
- URL: `https://online.lilletorget.net/owntracks/pub`
- Authentication: paa
- Username/User ID: vanlig Fibaro10-brukernavn
- Password: vanlig Fibaro10-passord
- Device ID: f.eks. `iphone`
- Tracker ID: f.eks. initialer eller kort navn

Fibaro10 lagrer meldingen som `owntracks/<fibaro10-bruker>/<device>`.

Denne ruten gaar gjennom Caddy paa eksisterende offentlig HTTPS-port 443 og videre til Fibaro10. Vanlig Fibaro10 auth/middleware validerer brukernavn og passord.

## Waypoints / soner

Alle OwnTracks-meldinger lagres fortsatt som raadata i `owntracks_locations`.

Waypoints gjores i tillegg lettere tilgjengelig i egne tabeller:

- `owntracks_waypoints`: siste kjente status per bruker/enhet/waypoint
- `owntracks_waypoint_events`: inn/ut-hendelser og waypoint-definisjoner

Vanlige location-meldinger med `inregions` oppdaterer siste kjente sone. Hvis appen sender eksplisitte `transition`-meldinger, lagres disse som egne `enter`/`leave`-hendelser. Hvis appen bare sender `inregions`, lager Fibaro10 syntetiske inn/ut-hendelser naar sonestatus endrer seg.

Kontroll:

- `/admin/owntracks`
- JSON-endepunkt: `/api/owntracks/waypoints`

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

## OwnTracks app uten VPN, MQTT-alternativ

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
- `owntracks_waypoints`: siste kjente waypoint-/sonestatus
- `owntracks_waypoint_events`: waypoint-hendelser

Kontrollside:

- `/admin/owntracks`
- JSON-endepunkt: `/api/owntracks/devices`
- JSON-endepunkt: `/api/owntracks/waypoints`
