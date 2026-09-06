# Build 1853: arbeidsro og etterprøvbare data

Bestilling: «rett feilene som du fant også, så starter du på forbedringen av alle mikro appene slik du foreslo».

## Backend

- Vedlikehold henter alle åpne oppfølgingspunkter, uavhengig av de 300 siste
  historikkradene. Dags- og månedstall beregnes over hele perioden i databasen.
- Koble har serverpaginering med stabile sorteringsnøkler og korrekt totaltall.
  Hvert kandidatpar får inntil seks egne dokumentasjonstreff, også når andre
  kandidater har mange nyere treff.
- Avvisning av en bekreftet kobling kan eksplisitt tilbakekalle bilens Sun2-ID.
  Den fjernes bare når både ID og oppdateringstid fremdeles tilsvarer denne
  bekreftelsen. Senere registreringer beholdes og forklares i svaret.
  Tilbakekallingen logges i eksisterende tilgangslogg.
- En gammel betalt parkering uten sluttid dekker ikke automatisk alle senere
  observasjonsdager. Den dekker startdagen; avsluttede perioder bruker faktisk
  datointervall. Dette er fortsatt en dagsbasert kontroll, ikke bevis på at
  hver observasjon innen dagen er betalt.
- Elvia-kontrollen skiller manglende målinger fra reelt nullforbruk. Avviket
  gjelder felles timer. Ufullstendige timeserier kan ikke gi grønn OK-status.
  Akkumulerte linjer brytes ved første datagap.
- Pullertoversikten vurderer innhentingsfeil, deaktivert/stoppet kontroll,
  utdaterte/fremtidige tidspunkt og kameraoppkobling separat fra bildeanalysen.
  Kamerastatus som sier frakoblet er et kontrollbehov, ikke bevis på fysisk feil.

## Frontend, egen Mantis-leveranse

Felles datahenting beholder sist hentede data ved bakgrunnsoppdatering og viser
en tydelig feilmelding hvis oppdateringen feiler. Første feil har retry.
Grafvalg, utvidede soltimer, valgt bilde/fullskjerm, robotfane, besøksnotater og
innstillingskladder beholdes. Nedlastingslenker håndteres ikke som sider.
System bevarer kildefilter ved detaljvisning og retur.

## Verifikasjon og kontrakter

`python -m pytest -q --disable-warnings` kontrollerer hele backend.
`tests/test_microapp_quality_fixes.py` bruker syntetisk database, aldri
produksjonsdata eller robotkommandoer.

De tre endrede rute-/funksjonsfingeravtrykkene, vedlikeholds-/koblingsmodulene og
det additive forespørselsfeltet `revoke_vehicle_link` er bevisst oppdatert i
kontraktfilene. Øvrige kontrakter er uendret; kontrollene er ikke slått av.

Ingen databaseendring, importplan, robotplan eller alarmgrense inngår.
Publisering bruker eksisterende selektive deploy og verifisert core-bytte.

## Avgrensninger

- Elvia-visningen har fortsatt 24 lokale klokktimefelt. Døgn med 23/25 timer
  trenger en egen gjennomgang; de skal ikke friskmeldes som komplette.
- En komplett HC3-time krever konservativt 120 gyldige 30-sekundersmålinger.
  Delvise timer kan vises, men klassifiseres ikke som et komplett kontrollgrunnlag.
- Eksplisitt navigasjon ut av et skjema er ikke et universelt konfliktvern.
  Backend-versjonering for samtidige redigeringer er fortsatt en senere etappe.
- Historisk avviste koblinger endres ikke automatisk.
