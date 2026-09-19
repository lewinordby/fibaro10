# Lilletorget Mobil: omsetningsdashboard

Oppdatert 19. september 2026.

## Bestilling

«kan du se på mobil appen min, kan du sørge for at den får samme opplysninger som vi har på omsetning dashboard»

## Resultat

Dashboard og `/omsetning` viser samme fire perioder som Mantis: i dag, denne uke,
denne måned og dette år. Hvert kort inneholder omsetning, historisk rangering,
to sammenligninger med kr/prosent, fordeling på soling/parkering, antall,
gjennomsnittsbeløp og hele referanseperioder med beløpet som gjenstår.

Perioder, dynamiske årstall og datatidspunkter hentes fra kjernens
`GET /api/overview?scope=revenue`. Mobilen beregner ikke egne periodesummer eller
historiske rangeringer. Sammenligningene beholder separate datakutt for soling og
parkering. Neste parkeringsimport kommer fra samme API. Hele referanseperioder
holdes adskilt fra sammenligningene ved tilsvarende datatidspunkt.

## Teknikk og tilgang

- `app/revenue.py`: API-klient og mobilpresentasjon av kjernens datakontrakt.
- `app/static/revenue-dashboard.css`: avgrenset mobil-CSS med eksisterende AppKit-temavariabler.
- `app/main.py`: kobler inn kortene uten å endre øvrige driftsvisninger eller ukediagram.
- Brukerens eksisterende økt sendes internt i `X-Session-Token`; ingen ekstra tjenestebruker.
- API-adresse: `FIBARO10_BASE_URL`, standard `http://fibaro10:8110`.
- API-kall følger ikke omdirigeringer og har åtte sekunders tidsgrense.
- Bare master/innstillingsbrukere får omsetning, som tidligere. Lesebrukere får ikke kortene.
- Ved API-feil vises utilgjengelig datagrunnlag, ikke null som omsetning.
- Eldre, separat snapshot-modus beholder eksisterende funksjonalitet. Den kjører ikke i dagens kildebaserte installasjon.

## Kontroll og publisering

Regresjonstester:

```powershell
python -m pytest tests/test_online_dashboard_revenue.py tests/test_online_dashboard_performance.py tests/test_online_dashboard_soling.py tests/test_online_dashboard_parking.py tests/test_online_dashboard_doors.py tests/test_mobile_appkit_theme.py -q
```

Visuell lokal forhåndsvisning med syntetiske data:

```powershell
python scripts/mobile_appkit_preview.py online --port 5198
```

Kontroller 320, 390, 430, 744 og 1024 px bredde i lyst/mørkt tema, inkludert
årsbeløp, tabeller, rulling og ukediagramlenken. Sammenlign de fire periodene mot
kjernens API etter publisering. Kun `online_dashboard` skal bygges og startes på
nytt; kjernen, innhentere og andre mobilapper skal ikke berøres.
