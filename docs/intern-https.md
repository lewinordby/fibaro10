# Intern HTTPS

Fibaro10 og mikroappene bruker offentlig DNS og offentlig betrodde sertifikater,
men DNS-postene peker til den private QNAP-adressen `192.168.20.218`. Tjenestene
kan derfor bare nås fra Lilletorget-nettet eller via VPN.

| Tjeneste | Adresse |
| --- | --- |
| Fibaro10 | `https://fibaro10.lilletorget.net:8443` |
| Appvelger | `https://app.lilletorget.net:8443` |
| Omsetning | `https://omsetning.lilletorget.net:8443` |
| Parkering | `https://parkering.lilletorget.net:8443` |
| Soling | `https://soling.lilletorget.net:8443` |
| Energi | `https://energi.lilletorget.net:8443` |
| Bygg og drift | `https://drift.lilletorget.net:8443` |
| Vedlikehold | `https://vedlikehold.lilletorget.net:8443` |
| System | `https://system.lilletorget.net:8443` |
| Koble | `https://koble.lilletorget.net:8443` |

## Sertifikater

ACME-klienten `lego` v4 bruker Domeneshop DNS-01. Denne stabile CLI-serien er
pin-et fordi v5 bruker et nytt konfigurasjonsformat. Caddy leser
det ferdige sertifikatet fra en skrivebeskyttet mount. API-token og secret
ligger bare i QNAPs `.env` som `DOMENESHOP_API_TOKEN` og
`DOMENESHOP_API_SECRET`.

DNS-postene vedlikeholdes idempotent med:

```bash
python scripts/configure_domeneshop_internal_dns.py --apply
```

Scriptet oppretter bare de dokumenterte A-postene og stopper ved konfliktende
CNAME- eller ANAME-poster.

Utstedelse og fornyelse kjøres med `scripts/renew-internal-https.sh`. QNAP cron
kjører scriptet hver natt. Etter en faktisk fornyelse sender scriptet Caddy et
grasiøst reload-signal, slik at det nye sertifikatet tas i bruk uten nedetid.

## Sikkerhet

I tillegg til at DNS peker til en privat adresse, avviser Caddy forespørsler som
ikke kommer fra private LAN- eller VPN-adresser. De direkte HTTP-portene er kun
tekniske reserveadresser og skal ikke publiseres i DNS eller portvideres.
