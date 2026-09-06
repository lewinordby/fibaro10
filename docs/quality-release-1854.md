# Build 1854: fullført forbedringsrunde

Bestilling: «gjør alt da», som oppfølging av restlisten etter build 1853.

## Leveranse

- System har søkbar kapittelinngang og egne flater for tekniske kilder og
  varslingsoppsett. Operasjon skiller arbeidskø, behandlede hendelser og
  kontrollregler; det samme oppsettet gjentas ikke på hver underside.
- Elvia-kontrollen bruker døgnets faktiske 23/24/25 timer. Estimerte verdier,
  manglende grunnlag og tellerreset fremgår. Effektintegrasjonen beholdes ved
  reset i den separate akkumulerte telleren.
- Kontroll viser innhentingsproblemer separat fra bildeanalysen. Ingen
  beskjæring, bildebehandling eller alarmregel er endret.
- Vedlikehold beholder besøksvalg og søk i adressen, varsler før besøksnotater
  forkastes og har råkildedata tilgjengelig ved behov.
- Parkering sammenligner faktisk observert tidsrom med kjente betalte
  parkeringsintervaller. Overlapp summeres bare én gang. Ufullstendig
  importgrunnlag og manglende sluttid er egne tilstander. Kun full dekning
  utelates fra kontrollisten. Retur fra bilen tar deg tilbake til utvalget.
- Soling beholder eksisterende funksjoner, bildevalg og fullskjerm gjennom
  oppdatering; dette er kontrollert på nytt.
- Omsetning/Måned viser registrerte dager og siste vellykkede import separat
  per kilde i et kompakt detaljvalg. Ingen eksisterende summer endres.
- Renhold viser kommende planlagte nattjobber, vannpauser, batteri og
  kontrollbehov. Manuelt deaktiverte planer tas ikke med som vannpauser.
- Mantis bygger etter faktisk avhengighetsgraf, gjenbruker uendrede apper og
  kontrollerer en parallell kandidat før containerbytte. En tidligere release
  beholder gamle lazy-load-ressurser for åpne faner.

## Tester

710 backendtester bestått før utrulling, inkludert nye regel- og integrasjonstester.
69 nettlesertilfeller bestått lokalt i lyst/mørkt tema; åpen kladd, valgt post,
vanlig polling, feil/retry, bilder, grafvalg, manual, nattplan og datadekning.
Åtte frontend-enhetstester. Mantis-leverandørfiler er uendret.
De fire bevisst endrede funksjonskontraktene og Renhold-modulens kontrakt er
oppdatert. Kontrakttestene er ikke deaktivert.

Ingen databasemigrering, nye innhentingsplaner, robotkommandoer, alarmgrenser
eller fysiske tester inngår. Kildekoden for innsamlerne er urørt.

## Viktige begrensninger

- Historisk vintertid er lagret med lokale tidsstempler uten entydig skille
  mellom de to 02-timene. Tapte skiller kan ikke rekonstrueres. Den tvetydige
  timen er synlig, men ikke med i avviket. Fremtidig UTC-migrering er separat.
- To kameraobservasjoner beviser ikke sammenhengende opphold eller betalingsplikt.
  Delvis dekning er en oppgave til kontroll, ikke en automatisk konklusjon.
- Importtidspunkt alene beviser ikke fullstendig måned. Null aktivitet er
  mulig; visningen kaller derfor ikke tomme dager for sikre importfeil.
- Nattplanen viser gjeldende forventning og status, ikke en garanti for batteri,
  vann eller ferdigstilling. Eksisterende faktisk nattrapport beholdes.
- Kladdvern er ikke serverversjonering for samtidige redigeringer.

Publiserte versjoner og etterkontroll føres i Mantis-dokumentet
`docs/QUALITY-2026-09-07.md` etter utrulling.
