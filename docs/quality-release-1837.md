# Kvalitetsrunde 1837

## Omfang

Bestilling: «gjør alt», knyttet til de seks etappene etter oppsplittingen av
`main.py`: deploy, testhull, ytelse, frontendstruktur, kodeopprydding og datastatus.
Ingen endringer i importplaner, robotplaner, alarmgrenser, HC3 eller databaseformat.

## Deploy og tilbakeføring

`scripts/deploy-qnap.ps1 -PlanOnly` viser hvilke tjenester som blir berørt.
Deploy krever ren, committet lokal kode og ren sporet kode på QNAP. QNAPs
commit må være en forgjenger til målet. Koden oppdateres med fast-forward;
runtimefiler overskrives ikke. Verktøyet bruker aldri reset, clean, generell
compose down eller automatisk synkronisering av robotene.

En lås i backupkatalogen hindrer samtidige kjøringer. Hver utgivelse lagrer
forrige kildearkiv, commit-ID-er og nødvendige image-referanser. Andre tjenester
enn kjernen får også et ferdig oppløst Compose-oppsett til eventuell tilbakeføring.
Dette inneholder hemmeligheter og er beskyttet med umask 077.

Kjernen testes i inaktiv blå/grønn slot før trafikken flyttes. Arbeideren skiftes
deretter; den kjører alene med bakgrunnsjobber aktivert. Ved feil startes forrige
webslot og arbeiderimage igjen. Andre tjenester tilbakeføres med forrige image,
miljø og mounts dersom oppstart eller helsesjekk feiler. Feilet tilbakeføring
rapporteres eksplisitt og krever manuell oppfølging.

Dette er **ikke** en databasetilbakeføring eller en transaksjon over flere apper.
Allerede godkjente tjenester beholdes hvis en senere tjeneste feiler. Checkout
blir stående på målcommit, mens en tilbakeført container kan kjøre eldre kode.
Etter retting må den feilede tjenesten derfor velges med `-ForceServices`, eller
tilsvarende eksplisitt flagg for en innsamler. Kontroller faktisk `/health` og
containerimage, ikke bare Git HEAD. Fjern aldri deploy-låsen før det er bekreftet
at ingen utrulling kjører. Første gangs oppsett må gjøres etter restore-manualen.

## Test og ytelse

- Hele kjernesuiten kjøres av pytest én gang. Testavhengigheter inkluderer den
  faktisk brukte Roborock-SDK-en og EasyPark-klienten; manglende SDK er en feil,
  ikke en hoppet test.
- EasyPark: køklikk samles, lås frigjøres ved feil, siste vellykkede import bevares,
  tidsavbrudd og Oslo-kjøreplan testes. Ingen ekte import trigges av testene.
- Begge slotretninger testes med normal oppstart, feil i kandidat og feil i worker.
- Fast-forward, feil revisjon, skitten arbeidskopi, deploy-lås og bevaring av `.env`
  testes i midlertidige Git-repoer.
- Samtidige sammendragskall for samme nøkkel deler én beregning. En pågående
  beregning får ikke gjeninnføre gammel cache etter invalidering. Andre nøkler
  blokkeres ikke. Cachen er fortsatt prosesslokal med eksisterende TTL.
- Strømanalysen er kontrollert mot frosset beregningskode i 24 variasjoner.
  På samme faktiske QNAP-datasett gav tre repetisjoner median 650 ms før og
  357 ms etter for beregningsdelen, ca. 45 % mindre tid, med identiske resultater.
  Dette er ikke en påstand om 45 % raskere API eller hele appen.

## Opprydding

836 eksisterende buildoppføringer er flyttet fra Python-kode til
`build_history/entries.json`; kontrollsum sikrer identisk historikk. `build_log.py`
har samme offentlige liste og funksjoner. Nye oppføringer legges i JSON-filen.
Kjernespecifikt Docker-filter utelater arkiver, testfiler og midlertidige filer
uten å endre byggekonteksten for innsamlerne. En test hindrer at dette filteret
mister de felles ekskluderingene fra `.dockerignore`.

Klassiske ressurser som fortsatt brukes av API, manual eller mobilforhåndsvisning
beholdes. De slettes ikke bare fordi PC-grensesnittet er erstattet av Mantis.
Frontendens flytting beskrives i Mantis-repoets `docs/domain-structure.md`.

## Datakilder: tre forskjellige spørsmål

1. **Svar fra tjenesten:** Systemstatus og helsesjekker sier om tjenesten svarer.
2. **Vellykket innhenting:** Datakilder viser siste vellykkede kjøring, siste feil
   og neste planlagte kjøring der denne er kjent. Ellers vises en kontrollgrense,
   ikke et oppdiktet kjøretidspunkt basert på tillatt dataalder. EasyParks neste
   kjøring kommer fra innsamleren. Et tidspunkt hentet fra lagrede data uten
   importlogg merkes særskilt. Feil gjør ikke en tidligere vellykket kjøring ny.
3. **Måletidspunkt:** Detaljsiden viser separat siste lagrede måling/hendelse
   for HC3 energi, lux, temperatur, dører, Sun2 enkelttimer, EasyPark og Elvia.
   Roborock og Dreame vises per aktiv robot slik at én fersk robot ikke skjuler
   en annen uten fersk status.

Periodiske målinger varsles ved overskredet kildegrense. Hendelser som solinger
og parkeringer kan være gamle uten feil: ingen nye kunder er ikke en importfeil.
Tidspunkt mer enn to minutter frem i tid markeres for kontroll. Alle tider
presenteres med Europe/Oslo-offset, ikke ved å legge to timer til alle verdier.

Siste hendelse er **ikke** en garanti for komplett datadekning frem til dette
tidspunktet. Et eget bekreftet dekningsvannmerke finnes ikke i dagens kontrakt og
vises derfor som ukjent. Kilder uten separat måletidspunkt får ikke et oppdiktet
datatidspunkt fra siste kjøring. Detaljvisningen gjør bare avgrensede database-
lesinger; den starter aldri innsamleren eller logger inn hos eksterne leverandører.

## Restgrenser

Testene dekker ikke fysisk kjøring av robot, faktiske SMS-/Gmail-koder eller
HC3-utganger. Det ville hatt virkninger i lokalet. Det er heller ikke innført
en ny distribuert cache eller sanntidsvannmerker i alle innsamlerne. Eksisterende
avhengigheters deprecation-varsler og enkelte store frontendpakker må vurderes
ved senere, avgrensede oppgraderinger; rammeverket oppgraderes ikke som en bieffekt.
