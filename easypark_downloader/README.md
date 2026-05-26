# EasyPark downloader

Liten QNAP-container som logger inn i EasyPark, laster ned CSV-rapport og sender filen til Fibaro10.

## Drift

- `GET /health` viser om appen lever.
- `GET /status` viser siste kjøring, siste fil og eventuell feil.
- `POST /sync-now` starter en nedlasting med en gang.

Containeren bruker persistent browserprofil i `./data/browser-profile`, slik at EasyPark-sesjonen kan gjenbrukes. Hvis EasyPark krever ny sikkerhetskontroll, forsøker appen å hente verifikasjonskode fra Gmail.
