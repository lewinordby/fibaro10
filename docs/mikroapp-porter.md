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

Fagspesifikke komponenter, typer og arbeidsflyter skal ligge under appen som eier
dem. Roborock-visningen ligger derfor i `operations_app/frontend`, ikke i
`packages/microapp-ui`. Fellespakken tilbyr et generelt utvidelsespunkt, men skal
ikke importere fagkomponenten. Denne grensen er viktig: en endring i Roborock skal
bygge `operations_app`, ikke alle fagappene.

| Kodeområde | Eier | Normal påvirkning |
|---|---|---|
| Omsetningsvisninger og -typer | `revenue_app` | Bare `revenue_app` |
| Parkering, kjøretøy og oppgjør | `parking_app` | Bare `parking_app` |
| Soltimer, bilder, dagslinje og soloppgjør | `sun_app` | Bare `sun_app` |
| Energi, Elvia og kurs/last | `energy_app` | Bare `energy_app` |
| Roborock, dører, pullerter og ventilasjon | `operations_app` | Bare `operations_app` |
| Besøk og vedlikehold | `maintenance_app` | Bare `maintenance_app` |
| Admin, manual, mobilvisning og ideer | `system_app` | Bare `system_app` |
| Koblingskontroll | `link_app` | Bare `link_app` |
| Layout, innlogging, navigasjon og generiske tabeller/grafer | `packages/microapp-ui` | Alle fagapper og skallet |

Typer og API-hjelpere som bare brukes av ett fagområde følger samme eierskap som
komponenten. En app skal ikke importere kildekode fra en annen app. Dersom en
endring også krever en ny eller endret kjerne-API-kontrakt, rulles kjernen og den
aktuelle fagappen ut sammen; de øvrige fagappene skal fortsatt stå urørt.

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
- Bare berørte tjenester: `scripts/check-affected.ps1` og `scripts/smoke-affected.ps1`

`deploy-revenue-app-qnap.ps1` og `deploy-parking-app-qnap.ps1` er korte
kompatibilitetsinnganger som bruker det samme felles deployløpet.

Standard deploy bruker endringslisten til å velge tjenester. Ved inntil fire
berørte tjenester bygges og testes bare disse og deres relevante kontrakter og
ruter. Full kontroll av alle apper er forbeholdt brede endringer, som selve
fellespakken, Compose eller mer enn fire tjenester. En enkelt app starter ikke
Fibaro10 eller andre fagapper på nytt.

Denne grensen regresjonstestes av `scripts/test-deploy-plan.ps1` og av testen som
avviser domeneeide spesialkomponenter i `packages/microapp-ui`. En appspesifikk
endring skal derfor stoppe kvalitetssjekken dersom den ved en feil blir klassifisert
som en endring i hele appstakken.

Rotfilen `BUILD` er buildnummeret for Fibaro10. Hver fagapp har tilsvarende en
egen `<app>/BUILD`. Standard deploy leser disse filene og sender verdiene til
Compose, slik at grensesnitt, health-endepunkt og bygglogg viser samme versjon.
