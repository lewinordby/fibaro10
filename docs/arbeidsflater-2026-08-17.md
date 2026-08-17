# Nye arbeidsflater

Oppdatert 17.08.2026, build 1793.

Denne utvidelsen legger beslutnings- og kontrollflater oppå de eksisterende,
verifiserte datakildene. Den innfører ikke nye kopier av parkering, Sun2, energi
eller renholdsdata.

## Operasjonssentral

URL: `https://ny.lilletorget.net/operasjon/`

- **Arbeidskø** viser åpne saker som krever oppfølging.
- **Kritisk** begrenser visningen til høyeste alvorlighetsgrad.
- **Kontroller** viser aktive datakontroller og avvik.
- **Historikk** viser kvitterte saker.
- **Datakvalitet** samler eksisterende kvalitetskontroller fra systemet.
- **Automatisering** lagrer lesbare regler med trigger, vilkår og handling.
- **Søk** finner kjøretøy, soltimer, vedlikehold og tekniske eiendeler.

Automatiseringsverkstedet er bevisst delt i definisjon og utførelse. En regel kan
opprettes, aktiveres og dokumenteres, men nye friteksthandlinger sendes ikke direkte
til HC3 eller andre fysiske systemer. Utførende adaptere skal godkjennes og testes
per handlingstype før de kobles til regelmotoren.

## Eiendelsregister

URL: `https://ny.lilletorget.net/eiendeler/`

Registeret lagrer navn, kategori, plassering, produsent, modell, serienummer,
HC3-ID, status, installasjonsdato, garanti, serviceintervall, sist service og notat.
Knappen **Synkroniser kjente enheter** oppretter manglende poster for:

- Sun2-senger
- Roborock-roboter
- aktive energi- og Z-Wave-enheter

Synkroniseringen overskriver ikke manuelt vedlikeholdte poster.

## Rapportsenter

URL: `https://ny.lilletorget.net/rapporter/`

Rapportsenteret er en katalog med direkte innganger til nattrapport for renhold,
ukerapport, omsetningsutvikling, parkerings- og soloppgjør, Elvia-kontroll og
systemdokumentasjon. Rapportberegningene eies fortsatt av de respektive fagappene.

## Nye faglige innganger

| Område | URL | Formål |
| --- | --- | --- |
| Besøksanalyse | `/parkering/besoksanalyse` | Ankomst, oppholdstid og omsetning etter tid og ukedag. |
| Kapasitet og kø | `/parkering/kapasitet` | Belegg, toppbelastning og bruk av parkeringsplassene. |
| Pris og tiltak | `/parkering/pris-analyse` | Betaling og parkeringstid på tvers av uker og år. |
| Energiavvik | `/energi/avvik` | Sammenligning mellom HC3, Elvia og beregnet forbruk. |
| Renholdsleder | `/drift/renhold/leder` | Robotstatus, siste jobber, forbruksdeler og planer. |

## Data og avhengigheter

De nye appene kjører i samme Mantis-stack som de øvrige fagappene. API-kall for
Operasjonssentral, Eiendeler og Rapporter rutes til `system_app`, som igjen bruker
Fibaro10-kjernen og den felles PostgreSQL-databasen. Innloggingen er den samme som
for resten av `ny.lilletorget.net`.

Nye tabeller:

- `asset_registry_items`
- `automation_workbench_rules`

Begge inngår i lagringsoversikt, migrering og ordinær PostgreSQL-backup.
