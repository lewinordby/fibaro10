# Kvalitetsstatus 7. august 2026

## Konklusjon

Fibaro10-stakken er funksjonelt frisk og tryggere å videreutvikle enn før dette arbeidet. Lokal kvalitetssjekk, produksjonsdeploy og live-kontroll er fullført uten funksjonsfeil. Alle 25 forventede tjenester kjører, alle rapporterer riktig helse, og både hovedappen og mikroappene svarer på alle registrerte ruter.

Deploy er nå vesentlig raskere og mindre risikofylt: en endring som bare berører Fibaro10 bygget og startet kun denne tjenesten. EasyPark, Roborock og resten av stakken fortsatte uforstyrret.

## Gjennomførte trinn

| Trinn | Build | Resultat |
| --- | --- | --- |
| Databaseøkter | 1652 | Felles, avgrensede og testbare databaseøkter reduserer risikoen for lekkasjer og hengende transaksjoner. |
| Varslinger | 1653 | Ntfy har varig utkø, retry og kontrollert levering ved midlertidige feil. |
| Avhengigheter | 1654 | Python- og npm-avhengigheter er kontrollert og låst; audit inngår i kvalitetssjekken. |
| QNAP-drift | 1655-1656 | Atomisk backup, restore-verifikasjon, lagringsgrenser, sannferdig datakildestatus og trygg Docker-retention. |
| Grensesnitt | 1657 | Hovedappen utnytter iPad-bredden uten horisontal scrolling og har innholdsbasert dashboardgrid. |
| Applivssyklus og deploy | 1658-1659 | Moderne FastAPI-lifespan, kontrollert start/stopp av sju jobber og selektiv QNAP-deploy. |
| Sluttkontroll | 1660 | Samlet lokal, produksjonsmessig og dokumentert verifikasjon. |

## Verifisert 7. august 2026

- 204 Python-tester bestått.
- Alle aktive frontendflater bygget uten feil.
- Sikkerhetsaudit, CSS-parse, CSS-audit, bundlebudsjett og rutekontroll bestått.
- Automatisk iPad-test ved 1024 piksler bestått med meny både synlig og skjult, uten horisontal scrolling.
- 25 HTTP- og containerkontroller på QNAP bestått.
- 23 operative datakilder rapporterte OK uten varsler.
- 113 innloggede ruter i hovedappen bestått.
- 235 readiness- og rutekontroller for mikroappene bestått.
- Innlogging, appskall, pullertbilder, AI-varmekart, bilbilder, kjøretøyfiltre og redigering av energitopologi kontrollert live.
- Selektiv deploy bygget bare `fibaro10`; `EasyPark=0`, `Roborock=0` og `full=0` ble bekreftet i produksjon.

## Driftsvern

- Uklassifiserte kodeendringer utløser fortsatt full rebuild, slik at optimalisering aldri prioriteres foran korrekthet.
- Deploy tar runtimebackup før containeren erstattes og avslutter dersom helse- eller rutekontroll feiler.
- Nattbackup publiseres først etter validerte databasedumper og kontrollsummer.
- Helsevakten kontrollerer tjenester, datakilder, backupalder og ledig plass på alle tre volumene.
- Tekniske logger og sendt varslingskø har kontrollert retention; virksomhetsdata slettes ikke automatisk.
- Alle bakgrunnsjobber stoppes og avventes kontrollert ved omstart av hovedappen.

## Ytelse

Mikroappkontrollen målte p50 til 26 ms og p95 til 641 ms. Bare energiforsiden var over varselgrensen på 1500 ms i denne runden, med 1703 ms. I den innloggede hovedappen var `Energi / forbruk per seng` tregest med 3270 ms. Begge er funksjonelt korrekte, men er naturlige kandidater for videre spørringsoptimalisering dersom de oppleves trege i praktisk bruk.

## Ikke-blokkerende videre arbeid

- Fortsett gradvis oppdeling av den store hovedmodulen når et konkret fagområde likevel skal endres. Unngå en ny total omskriving.
- Profilér databasekallet bak energiforbruk per seng før eventuell indeks eller materialisert aggregering innføres.
- Behold full lokal kvalitetssjekk i CI, men bruk den selektive deployplanen til den faktiske QNAP-utrullingen.
- Kjør restore-test regelmessig og etter endringer i databaseskjema, lagringsplassering eller backupskript.

Ingen av disse punktene hindrer dagens bruk eller videre funksjonsutvikling.
