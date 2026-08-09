# Porter for Lilletorget-mikroapper

Brukergrensesnittene reserveres på QNAP-adressen `192.168.20.218` fra port 8150.

| Port | Applikasjon | Status |
|---:|---|---|
| 8150 | Lilletorget-skall og appvelger | I drift |
| 8151 | Omsetning | I drift |
| 8152 | Parkering | I drift |
| 8153 | Soling | I drift |
| 8154 | Energi | I drift |
| 8155 | Bygg og drift | I drift |
| 8156 | Vedlikehold | I drift |
| 8157 | System og administrasjon | I drift |
| 8158 | Koble | I drift |

Portene gjelder vertsmaskinen. En intern containerport med samme nummer gir ingen
konflikt så lenge den ikke er publisert på QNAP-adressen. Serien 8150-8159 er likevel
valgt for å holde alle brukerrettede mikroapper tydelig adskilt fra grunn- og
datatjenestene.

## Felles designgrunnlag

Alle brukerrettede mikroapper fra port 8150 bruker den interne npm-pakken
`packages/mosaic-theme`. Den er eneste kilde for Mosaic-farger, typografi,
komponentmønstre og lokal Inter-font. Nye apper skal kobles til pakken i stedet
for å kopiere CSS fra en eksisterende app.

Alle fagappene på 8151-8158 bruker i tillegg `packages/microapp-ui` for felles
innlogging, API-cache, navigasjon, layout, tema, formatering, tabeller, grafer og
redigeringsmønstre. Menystruktur, apprekkefølge og porter har én autoritativ kilde
i `packages/microapp-ui/src/navigation.json`.

Navigasjonen har tre faste roller: appfeltet i toppen bytter fagapp,
venstremenyen bytter hovedområde og den horisontale menyen bytter mellom
beslektede sider i aktivt område. Detaljsider åpnes fra innholdet og er ikke
egne hovedmenyvalg. Hver app bygger fortsatt egne, versjonerte statiske filer.
Chart.js og spesialiserte fagflater lastes ved behov, slik at førstegangslasten
holdes liten.

I brukergrensesnittet presenteres appene som `/omsetning/`, `/parkering/`,
`/soling/`, `/energi/`, `/drift/`, `/vedlikehold/`, `/system/` og `/koble/` under
`https://app.lilletorget.net`. Caddy fjerner bare app-prefikset før forespørselen
sendes til den tilhørende porten. Appene forblir dermed teknisk og byggmessig
separate, samtidig som den installerte PWA-en har én origin.

## Utvikling og utrulling

- En enkelt fagapp: `scripts/deploy-domain-app-qnap.ps1 -App <appnavn>`
- Alle fagappene: `scripts/deploy-all-domain-apps-qnap.ps1`
- Alle levende ruter: `scripts/smoke-domain-apps.ps1`

`deploy-revenue-app-qnap.ps1` og `deploy-parking-app-qnap.ps1` er korte
kompatibilitetsinnganger som bruker det samme felles deployløpet.

Samlet deploy bygger og sikkerhetskontrollerer alle frontender, kjører
kontrakttestene én gang og oppdaterer deretter containerne sekvensielt. Den
starter ikke Fibaro10 eller andre fagapper på nytt mens en enkelt app bygges.

Rotfilen `BUILD` er buildnummeret for Fibaro10. Hver fagapp har tilsvarende en
egen `<app>/BUILD`. Standard deploy leser disse filene og sender verdiene til
Compose, slik at grensesnitt, health-endepunkt og bygglogg viser samme versjon.
