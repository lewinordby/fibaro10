# Intern HTTPS

Oppdatert 29.08.2026.

Lilletorget bruker offentlig DNS og offentlig betrodde TLS-sertifikater, men
de interne navnene peker til QNAPs private HTTPS-adresse `192.168.20.219`.
QNAP-administrasjon og direkte tekniske porter ligger på `192.168.20.218`.
Interne apper kan derfor bare nås fra LAN eller VPN.

## Interne brukerflater

| Flate | Adresse | Rolle |
| --- | --- | --- |
| Mantis | `https://ny.lilletorget.net` | Eneste PC-flate og installert PWA. |
| Kiosk | `https://kiosk.lilletorget.net` | Fast robotstatus. |

Mobil- og lokasjonsappene beholder egne HTTPS-navn:
`online.lilletorget.net`, `vedl.lilletorget.net`, `alarm.lilletorget.net` og
`owntracks.lilletorget.net`.

Gamle desktop-, app-, fagsubdomene- og iPad-navn er fjernet fra Caddy og den
interne DNS-konfigurasjonen. De skal ikke brukes som reserveadresser.

## Sertifikat og DNS

ACME-klienten lego bruker Domeneshop DNS-01. Det interne sertifikatet har
`ny.lilletorget.net` som hovednavn og `kiosk.lilletorget.net` som SAN. Caddy
leser sertifikatet skrivebeskyttet fra SSD-runtimeområdet.

```powershell
python scripts/configure_domeneshop_internal_dns.py --apply
```

Kommandoen oppretter eller retter de to aktive private A-postene og fjerner
navngitte, utfasete private A-poster. Den berører ikke andre DNS-poster.

Utstedelse og fornyelse kjøres med `scripts/renew-internal-https.sh`. QNAP cron
kjører scriptet hver natt. Caddy restartes bare når sertifikatet faktisk endres.

## Tilgang og sesjon

- Caddy avviser intern trafikk som ikke kommer fra privat LAN/VPN.
- Offentlig DNS gir ikke offentlig tilgang når A-posten peker til privat IP.
- `lilletorget_session` gjelder `.lilletorget.net` og er `Secure`, `HttpOnly`
  og `SameSite=Lax`.
- Mantis-appene ligger under samme origin og krever bare én innlogging.
- Direkte HTTP-porter er tekniske health/API-adresser og skal ikke publiseres.

## PWA

Installer bare `https://ny.lilletorget.net`. Alle Mantis-appene ligger i samme
manifest-scope, slik at appbytte skjer uten ekstra adresselinje. Etter en
manifestendring avinstalleres den eksisterende PWA-en før den installeres på
nytt fra vanlig Chrome-fane.

## Feilsøking

| Symptom | Kontroller |
| --- | --- |
| Domenet svarer ikke | VPN/LAN, A-post til `192.168.20.219` og Caddy. |
| Sertifikatfeil | QNAP-klokke, fornyelseslogg og `ny.lilletorget.net`-sertifikatet. |
| Adresselinje i PWA | At bare `ny.lilletorget.net` er installert. |
| Gjentatt innlogging | Cookie-domain `.lilletorget.net`, path `/` og HTTPS. |

## Gjenoppretting

1. Gjenopprett runtime `.env` og sertifikatdata fra backup.
2. Kjør DNS-scriptet med `--apply`.
3. Kjør `scripts/renew-internal-https.sh`.
4. Start `fibaro10_proxy` og test Mantis og kiosk over LAN/VPN.
5. Kontroller anonym `401` på API-auth og én innlogging gjennom Mantis.
