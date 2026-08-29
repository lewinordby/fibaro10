# Intern HTTPS

Oppdatert 29.08.2026, build 1817.

Lilletorget bruker offentlig DNS og offentlig betrodde TLS-sertifikater, men
de interne navnene peker til den private HTTPS-adressen 192.168.20.219 på QNAP.
QNAP-administrasjonen beholder 192.168.20.218. Caddy alene bruker port 443 på
den dedikerte adressen. De interne appene kan derfor bare nås fra Lilletorget-
nettet eller via VPN.

## Primær brukerflate

| Flate | Adresse | Rolle |
| --- | --- | --- |
| Mantis | https://ny.lilletorget.net | Gjeldende brukerflate og PWA. |
| Kiosk | https://kiosk.lilletorget.net | Fast 1920 x 1080-statusflate for intern drift. |
| Fibaro10 | https://fibaro10.lilletorget.net | Kjerne/API og samlet reserveflate. |
| Forrige mikroappserie | https://app.lilletorget.net | Reserve og funksjonsreferanse. |

Mantis-appene bruker stier under samme origin:

- /omsetning/
- /parkering/
- /soling/
- /koble/
- /bygg/
- /renhold/
- /kontroll/
- /energi/
- /vedlikehold/
- /operasjon/
- /eiendeler/
- /rapporter/
- /system/

## Sertifikater og DNS

ACME-klienten lego v4 bruker Domeneshop DNS-01. Caddy leser det ferdige
sertifikatet fra en skrivebeskyttet mount. API-token og secret ligger bare i
QNAPs runtime-.env som DOMENESHOP_API_TOKEN og DOMENESHOP_API_SECRET.

DNS-postene vedlikeholdes idempotent med:

    python scripts/configure_domeneshop_internal_dns.py --apply

Utstedelse og fornyelse kjøres med scripts/renew-internal-https.sh. QNAP cron
kjører scriptet hver natt. Etter faktisk fornyelse restartes bare Caddy-proxyen;
tjenestene bak proxyen restartes ikke.

## VPN-rute

HTTPS-containeren har en eksplisitt returrute for det private VPN-nettet via
LAN-gatewayen. Standard er 192.168.0.0/16 via 192.168.20.1. Verdiene kan
overstyres med FIBARO10_VPN_ROUTE og FIBARO10_LAN_GATEWAY i QNAPs .env.

## Tilgangskontroll

- Caddy avviser trafikk til interne flater som ikke kommer fra privat LAN/VPN.
- Kiosken er tilgjengelig på kiosk.lilletorget.net og deler den sentrale
  lilletorget_session-innloggingen med de øvrige appene.
- Direkte HTTP-porter er tekniske reserveadresser og skal ikke videresendes fra
  internett eller publiseres som primære lenker.
- Offentlig DNS gir ikke offentlig tilgang når A-posten peker til privat IP og
  Caddy i tillegg håndhever privat kildeadresse.
- TLS, HSTS, nosniff og øvrige sikkerhetsheadere legges på av Caddy/Nginx.
- Innlogging bruker den samme opake lilletorget_session-cookien på
  .lilletorget.net, med Secure, HttpOnly og SameSite=Lax.

## Installert PWA

Installer bare https://ny.lilletorget.net som desktop-PWA. Alle tretten apper
ligger under samme origin og vanlig scope. Dette gir én innlogging og hindrer
out-of-scope-adresselinje ved appbytte.

Etter endring i manifest eller scope:

1. Avinstaller eldre Lilletorget-, Fibaro10- og fagappinstallasjoner i Chrome.
2. Lukk gamle appvinduer.
3. Åpne https://ny.lilletorget.net i en vanlig Chrome-fane.
4. Last siden på nytt og installer Lilletorget derfra.

app.lilletorget.net skal ikke installeres på nytt med mindre reserveflaten
testes eksplisitt.

## Feilsøking

| Symptom | Kontroller |
| --- | --- |
| Domenet svarer ikke | VPN/LAN, DNS til 192.168.20.219 og Caddy-container. |
| Sertifikatfeil | Fornyelseslogg, sertifikatmount og klokke på QNAP/klient. |
| Appen viser adresselinje | At bare ny.lilletorget.net-PWA er installert og at lenken bruker samme origin. |
| Ny innlogging per app | Cookie-domain .lilletorget.net, path / og at alle sider åpnes via ny.lilletorget.net. |
| IP-adresse virker, domene ikke | DNS, VPN-rute og Caddy-hostblokk. |

## Gjenoppretting

1. Gjenopprett runtime-.env fra backup.
2. Kontroller Domeneshop-token og DNS-poster.
3. Kjør renew-internal-https.sh.
4. Start fibaro10_proxy og bekreft at sertifikatene er lastet.
5. Test https://ny.lilletorget.net/system/ og en fagapp over LAN/VPN.
6. Kontroller anonym 401 på /api/auth/me og innlogging på tvers av appene.
