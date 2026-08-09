# Intern HTTPS

Fibaro10 og mikroappene bruker offentlig DNS og offentlig betrodde sertifikater,
men DNS-postene peker til den dedikerte HTTPS-adressen `192.168.20.219` på QNAP.
QNAP-administrasjonen beholder `192.168.20.218`, mens Caddy alene bruker
standardport `443` på den dedikerte adressen. Tjenestene kan derfor bare nås
fra Lilletorget-nettet eller via VPN.

| Tjeneste | Adresse |
| --- | --- |
| Fibaro10 | `https://fibaro10.lilletorget.net` |
| Appvelger | `https://app.lilletorget.net` |
| Omsetning | `https://app.lilletorget.net/omsetning/` |
| Parkering | `https://app.lilletorget.net/parkering/` |
| Soling | `https://app.lilletorget.net/soling/` |
| Energi | `https://app.lilletorget.net/energi/` |
| Bygg og drift | `https://app.lilletorget.net/drift/` |
| Vedlikehold | `https://app.lilletorget.net/vedlikehold/` |
| System | `https://app.lilletorget.net/system/` |
| Koble | `https://app.lilletorget.net/koble/` |

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
Port `8443` på hovedadressen beholdes bare som teknisk HTTPS-reserve.

## Installert hovedapp

`https://app.lilletorget.net` er den eneste PWA-en som skal installeres for den
interne desktopløsningen. Manifestet heter `Lilletorget`, og Caddy presenterer hver
fagapp som en sti under samme origin. Eksempelvis går `/parkering/` fortsatt til den
separate `parking_app`-containeren, mens `/energi/` går til `energy_app`.

Alle sider ligger dermed naturlig innenfor manifestets vanlige scope `/`. Løsningen
er ikke avhengig av den eksperimentelle `scope_extensions`-funksjonen, lokal DNS
eller lokale sertifikater, og Chrome viser ingen out-of-scope-adresselinje ved
appbytte. De gamle fagappsubdomenene beholdes som tekniske reserveadresser.

Etter denne omleggingen skal gamle separate installasjoner av Fibaro10 og fagappene
avinstalleres. Åpne deretter `https://app.lilletorget.net` i Chrome og installer bare
denne appen på nytt.
