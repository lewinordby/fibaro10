# Batterioversikt

Side: https://app.lilletorget.net/system/batterier
API: GET /api/system/batteries (samme autentisering/områdetilgang som System).

## Datagrunnlag

- HC3s lagrede enhetsliste, med batteri-interface eller batteryLevel. Ingen
  kommandoer sendes til sensorene. Eksisterende enhetscache kan være opptil ett
  minutt gammel; batterisnapshot mellomlagres i ytterligere inntil ett minutt.
- Navn viser funksjon og kjent sted, som «Dørføler – Solrom 3». Dørkatalogen gir
  de aktive dørnavnene. HC3-romlisten og eksisterende avdelingskoblinger gir
  plassering. «Default» vises som «Plassering må avklares», ikke som et romnavn.
- HC3-ID og Z-Wave-node vises i tabellen, og alle originalnavn beholdes i
  detaljene. En Netatmo-stasjons navn forveksles ikke med modulens plassering.
- Z-Wave-kanaler grupperes under fysisk zwaveDevice. QuickApp-kanaler samles
  bare når parentId, device_id og module_id identifiserer samme modul.
- Roborock og Dreame er ikke med. Robotbatterier finnes fortsatt under Renhold.
  Batterisiden gjør ingen databasekall til robottabellene.
- Alle eksisterende batterienheter tas med, også deaktiverte og uten kontakt.
  Dette er ikke et nettverkssøk etter ukjente enheter eller telefoner.

## Tolkning

- 0 er gyldig batterinivå. Ukjent eller ugyldig nivå blir aldri 0.
- <=20 % er lavt og <=10 % kritisk lavt i denne oversikten. Ingen nye alarmer.
- Z-Wave 255 (0xFF) betyr lavt batterivarsel uten eksakt prosent.
  Referanse: https://docs.silabs.com/z-wave/latest/zwave-api/battery
- batteryLowNotification er en varslingsinnstilling og er ikke aktuell alarm.
- Ulike kanalverdier merkes; laveste kjente nivå vises. Z-Wave-varsel prioriteres.
- Tidligere inngangsfølere 499 (node 120) og 541 (node 131) er merket erstattet,
  basert på dokumentert utskifting. Aktiv inngangsføler er 545 (node 149),
  byttet 03.09.2026 i build 1850. Tidligere følere sorteres nederst og er ikke
  med i telleren/filteret for lavt batteri. De er ikke slettet fra HC3.
  En ny aktiv katalogkobling overstyrer merket dersom en føler tas i bruk igjen.
- HC3 oppgir ikke når batteryLevel sist ble rapportert. modified, lastBreached
  og lastChanged brukes derfor IKKE som batterirapporttid. Kontrolltid er når
  backend leste det mellomlagrede HC3-grunnlaget, ikke sensorens siste kontakt.
- Manglende kontakt bygger på HC3 dead. Sovende
  batterisensorer erklæres ikke frakoblet bare fordi de ikke har sendt noe nylig.

## Feil og sikkerhet

Lesing er låst til ett HC3-kall om gangen og mellomlagres i 60 sekunder, også
ved feil. Sist vellykkede snapshot bevares og merkes ved feil. Uten noe tidligere
snapshot er HC3-listen tom med eksplisitt feilmelding, aldri en falsk friskmelding.
Romlistefeil skjuler ikke batteriene. Ingen databaseendringer, migrering,
HC3-navneendringer eller nye planlagte jobber.
QuickApp-variabler, tokens, råtelemetri og HC3-autentisering sendes ikke til klient.

Tester: tests/test_batteries.py, eksisterende ruter/komposisjon/manualtester,
Mantis typekontroll, enhetstester, meny/build-audit og nettleserkontroll i begge tema.
