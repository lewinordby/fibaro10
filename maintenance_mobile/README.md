# Lilletorget Vedlikehold mobil

Egen mobilflate for vedlikeholdsregistrering.

- Bruker samme brukernavn/passord som Fibaro10.
- Skriver til samme `maintenance_log_entries`-grunnlag via Fibaro10 API.
- Kjører som egen Docker-container og eksponeres via `vedl.lilletorget.net`.

Miljøvariabler:

- `FIBARO10_BASE_URL`: intern URL til Fibaro10, normalt `http://fibaro10:8110`.
- `MAINTENANCE_MOBILE_SESSION_SECRET`: HMAC-secret for mobilappens egen sesjonscookie.

