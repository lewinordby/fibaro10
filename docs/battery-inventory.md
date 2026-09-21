# Batterioversikt

Side: https://app.lilletorget.net/system/batterier
API: GET /api/system/batteries (samme autentisering/områdetilgang som System).

## Datagrunnlag

- HC3s lagrede enhetsliste, med batteri-interface eller batteryLevel. Ingen
  kommandoer sendes til sensorene. Eksisterende enhetscache kan være opptil ett
  minutt gammel; batterisnapshot mellomlagres i ytterligere inntil ett minutt.
- HC3-romlisten gir plassering. Solrom og dørenes navn hentes fra eksisterende
  katalog. Ukonfigurerte rom får HC3s navn; vi gjetter ikke plassering.
- Z-Wave-kanaler grupperes under fysisk zwaveDevice. QuickApp-kanaler samles
  bare når parentId, device_id og module_id identifiserer samme modul.
- Roborock og Dreame leses fra eksisterende robottabeller. Siste batteriprøve
  fra telemetri eller status velges etter timestamp, som innlesingen lagrer i
  lokal Oslo-tid. Ingen nye kall til robotleverandørene.
- Alle eksisterende batterienheter tas med, også deaktiverte og uten kontakt.
  Dette er ikke et nettverkssøk etter ukjente enheter eller telefoner.

## Tolkning

- 0 er gyldig batterinivå. Ukjent eller ugyldig nivå blir aldri 0.
- <=20 % er lavt og <=10 % kritisk lavt i denne oversikten. Ingen nye alarmer.
- Z-Wave 255 (0xFF) betyr lavt batterivarsel uten eksakt prosent.
  Referanse: https://docs.silabs.com/z-wave/latest/zwave-api/battery
- batteryLowNotification er en varslingsinnstilling og er ikke aktuell alarm.
- Ulike kanalverdier merkes; laveste kjente nivå vises. Z-Wave-varsel prioriteres.
- Robotens oppladbare batteri/lading vises separat. Lavt nivå er ikke en
  konklusjon om at robotbatteriet må skiftes. Eldre enn 30 minutter merkes.
- HC3 oppgir ikke når batteryLevel sist ble rapportert. modified, lastBreached
  og lastChanged brukes derfor IKKE som batterirapporttid. Kontrolltid er når
  backend leste det mellomlagrede HC3-grunnlaget, ikke sensorens siste kontakt.
- Manglende kontakt bygger på HC3 dead eller robotens cloud_online. Sovende
  batterisensorer erklæres ikke frakoblet bare fordi de ikke har sendt noe nylig.

## Feil og sikkerhet

Lesing er låst til ett HC3-kall om gangen og mellomlagres i 60 sekunder, også
ved feil. Sist vellykkede snapshot bevares og merkes ved feil. Uten noe tidligere
snapshot er HC3-listen tom med eksplisitt feilmelding, aldri en falsk friskmelding.
Roboter kan fortsatt vises når HC3 er utilgjengelig, og omvendt. Romlistefeil
skjuler ikke batteriene. Ingen databaseendringer, migrering eller planlagte jobber.
QuickApp-variabler, tokens, råtelemetri og HC3-autentisering sendes ikke til klient.

Tester: tests/test_batteries.py, eksisterende ruter/komposisjon/manualtester,
Mantis typekontroll, enhetstester, meny/build-audit og nettleserkontroll i begge tema.
