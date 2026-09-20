# Mobilvisning, build 1856

## Bruk

- Dashboard viser en periode om gangen: I dag, Uke, Måned eller År.
- Total, sammenligninger, fordeling mellom soling og parkering, antall og snitt er synlige.
- Åpne «Forskjell per inntektskilde» for differansene for soling og parkering.
- Valgt periode og åpne sammenligninger beholdes ved automatisk oppdatering i samme nettleserfane.
- Oppdateringstidspunktet for hver kilde er fortsatt synlig. Tidspunkter, referanser og beregninger er uendret.
- Dør- og solromdetaljer viser status, sist endret, varighet, batteri, sist kontrollert og fysisk dørstatus i en kompakt liste over hendelsene.

## Avgrensning

Gjelder `online_dashboard` på https://online.lilletorget.net. Dette er ikke en
ombygging av Mantis, vedlikeholdsmobil eller alarmmobil. Felles AppKit-pakke,
API-er, innlogging, importplaner, HC3-styring, SUN2-romkobling og alarmgrenser
er uendret. Det publiseres bare en ny `online_dashboard`-container.
API og bakgrunnsarbeider fortsetter på build 1855.

Ingen nye nettverkskall, rammeverk eller avhengigheter er lagt til. Alle fire
perioder rendres fra samme API-svar. Uten JavaScript vises alle fire som før.
Nettlesere som ikke tillater sessionStorage kan fortsatt bytte periode, men
valget kan ikke beholdes ved omlasting.

## Kontroll

- Regresjonstester for omsetning, dører, soling, parkering, mobiltema og lokal forhåndsvisning.
- Nettleserkontroll i 320, 390, 430 og 744 CSS-pikslers bredde, lyst og mørkt tema.
- Kontroller av periodevalg, tastatur, åpne detaljer, omlasting og horisontal rulling.
- Visuell kontroll av omsetning og dørsider. Statusmerker bruker lesbare temafarger og beholder status som tekst.

Lokal forhåndsvisning: `python scripts/mobile_appkit_preview.py online --port 5199`.
Den benytter demodata og sender ingen styringskommandoer.

## Tilbakeføring

Publiseringsskriptet lagrer forrige kildekode, Compose-oppsett og containerbilde
under `/share/CACHEDEV3_DATA/fibaro10_archive/fibaro10_deploy_backups`.
Bare mobilcontaineren trenger tilbakeføring. Ingen databaseendringer inngår.
