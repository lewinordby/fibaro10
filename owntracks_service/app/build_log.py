from __future__ import annotations

import os
from typing import Any


OWNTRACKS_APP_VERSION = os.getenv("OWNTRACKS_APP_VERSION", "1")
OWNTRACKS_APP_BUILD = os.getenv("OWNTRACKS_APP_BUILD", "13")
OWNTRACKS_APP_COMMIT = os.getenv("OWNTRACKS_APP_COMMIT", "unknown")

OWNTRACKS_BUILD_LOG: list[dict[str, Any]] = [
    {
        "version": "1",
        "build": "13",
        "date": "04.07.2026",
        "headline": "Avstand fra forrige melding",
        "title": "OwnTracks Meldinger viser meter fra forrige oppdatering",
        "description": (
            "Build 13 legger til avstand fra forrige posisjonsoppdatering per enhet/topic i Meldinger-tabellen. "
            "Dette gjoer det lettere aa se om telefonen faktisk har flyttet seg mellom rapporteringene, og om "
            "en sonehendelse bygger paa en reell bevegelse eller bare en ny rapport fra samme sted."
        ),
        "applications": [
            "owntracks_service/app/main.py: beregner distanceFromPreviousM per topic i kronologisk rekkefolge.",
            "owntracks_service/frontend/src/App.tsx: Meldinger-tabellen viser Fra forrige i meter.",
            "tests/test_owntracks_service.py: test dekker at avstanden beregnes mellom to meldinger fra samme enhet.",
        ],
        "request": "kan vi legge inn i meldinger tabellen hvor mange meter det er fra forrige oppdatering?",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Foerste melding per enhet viser tom avstand.",
            "Neste meldinger viser meter fra forrige gyldige posisjon for samme topic.",
            "Samme felt finnes i kart-API og modul-API.",
        ],
    },
    {
        "version": "1",
        "build": "12",
        "date": "04.07.2026",
        "headline": "Bedre kartzoom og tidsfilter",
        "title": "OwnTracks-kartet zoomer tettere inn og kan filtreres paa konkret tidsrom",
        "description": (
            "Build 12 legger til egendefinert fra/til-filter for OwnTracks-data og forbedrer MapLibre-zoom. "
            "Kartet bruker posisjonssporet som primaert zoomgrunnlag, slik at waypoints og siste enhet ikke "
            "trekker utsnittet unodvendig langt ut naar man analyserer en bestemt periode."
        ),
        "applications": [
            "owntracks_service/app/main.py: kart, soneoppsummering og diagnose aksepterer start/end-filter.",
            "owntracks_service/frontend/src/App.tsx: ny tidsvelger og tettere MapLibre fitBounds-logikk.",
            "owntracks_service/frontend/src/styles.css: ryddig layout for tidsfilter.",
            "tests/test_owntracks_service.py: test dekker eksakt tidsfilter paa kart-API.",
        ],
        "request": "jeg oensker bedre zoom mulighet paa kartet og bedre filtrering paa tid.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Kartet zoomer naa inn paa punktene i valgt tidsrom saa tett som praktisk mulig.",
            "Egendefinert fra/til-filter sender lokal tid korrekt til API-et.",
            "Meldinger, sonebesok og diagnose bruker samme periodevalg.",
        ],
    },
    {
        "version": "1",
        "build": "11",
        "date": "04.07.2026",
        "headline": "Opprinnelse ogsaa paa meldinger",
        "title": "OwnTracks Meldinger viser om raadata kommer fra telefon eller server",
        "description": (
            "Build 11 legger samme opprinnelsesmerking inn paa Meldinger som allerede finnes paa Hendelser. "
            "Raameldinger fra OwnTracks-telefonen vises som Telefon og isSynthetic=false, slik at Meldinger, "
            "Hendelser og Diagnose kan leses med samme begrepsbruk."
        ),
        "applications": [
            "owntracks_service/app/main.py: row_location returnerer origin og isSynthetic, og module-tabellen inkluderer feltene.",
            "owntracks_service/frontend/src/App.tsx: Meldinger-tabellen viser Opprinnelse.",
            "tests/test_owntracks_service.py: test dekker at publiserte meldinger merkes som Telefon og ikke syntetiske.",
        ],
        "request": "du la inn det bare paa hendelser ikke paa meldinger",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Meldinger viser naa Telefon/Server paa samme maate som Hendelser.",
            "Raameldinger fra telefonen er eksplisitt satt til isSynthetic=false.",
            "Fallback-HTML viser samme opprinnelsesfelt.",
        ],
    },
    {
        "version": "1",
        "build": "10",
        "date": "04.07.2026",
        "headline": "Tydelig opprinnelse paa hendelser",
        "title": "OwnTracks Hendelser skiller telefonrapporterte og servergenererte hendelser",
        "description": (
            "Build 10 viser om en waypoint-hendelse kommer fra telefonens OwnTracks-melding eller er syntetisk "
            "generert av serveren. Dette gjoer det tydeligere aa lese Hendelser opp mot Sonebesok og Meldinger."
        ),
        "applications": [
            "owntracks_service/app/main.py: row_event faar origin-felt og module-tabellen inkluderer opprinnelse.",
            "owntracks_service/frontend/src/App.tsx: Hendelser viser Telefon/Server-kolonne.",
            "tests/test_owntracks_service.py: test dekker at transition fra telefon blir origin=phone og isSynthetic=false.",
        ],
        "request": "Vis om hendelser er synthetic og avklar hva synthetic betyr.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Hendelser-tabellen viser naa opprinnelse eksplisitt.",
            "Synthetic=true betyr servergenerert, ikke fra telefonappen.",
            "Telefonbaserte hendelser markeres som Telefon.",
        ],
    },
    {
        "version": "1",
        "build": "9",
        "date": "04.07.2026",
        "headline": "Diagnose for datakvalitet",
        "title": "OwnTracks viser stale posisjoner, rapporteringshull og sonegrunnlag",
        "description": (
            "Build 9 legger til en egen Diagnose-side og API for datakvalitet. Den viser hvor mange posisjoner "
            "som er gamle naar de mottas, om telefonen sender gjentatte posisjoner, hvor store hull det er mellom "
            "rapporteringene, og hvor godt hvert waypoint faktisk dekkes av posisjonsdata."
        ),
        "applications": [
            "owntracks_service/app/main.py: nytt diagnostics-API med stale/gap/accuracy/waypoint-analyse.",
            "owntracks_service/frontend/src/App.tsx: ny Diagnose-side med kort, anbefalinger og tabeller.",
            "tests/test_owntracks_service.py: test som dekker stale posisjoner og store rapporteringshull.",
        ],
        "request": "Kan du forbedre owntracks appen min med mer funksjoner.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Diagnose-siden viser om datagrunnlaget er godt nok til sonebesok og waypointforslag.",
            "Appen anbefaler OwnTracks-innstillinger ut fra minste waypoint-radius.",
            "Stale meldinger og store rapporteringshull er synlige uten aa lese raaloggen.",
        ],
    },
    {
        "version": "1",
        "build": "8",
        "date": "03.07.2026",
        "headline": "Soneoppsummering og bedre waypoint-admin",
        "title": "OwnTracks faar tydeligere kontroll over lokale soner og sonebesok",
        "description": (
            "Build 8 legger til et eget API for soneoppsummering, slik at dashboard og Sonebesok-siden kan vise "
            "aggregert tid, aktive soner og mest brukte soner uten aa tolke raadata i frontend. Lokale server-soner "
            "kan naa redigeres og deaktiveres direkte i grensesnittet."
        ),
        "applications": [
            "owntracks_service/app/main.py: nytt zone-summary API, varighetsberegning for aapne besok og ryddet tallhjelper.",
            "owntracks_service/frontend/src/App.tsx: rediger/deaktiver lokale soner, nytt dashboardgrunnlag og Sonebesok-oppsummering.",
            "tests/test_owntracks_service.py: tester for zone-summary, patch og deaktivering av lokale soner.",
        ],
        "request": "Gjor en grundig jobb paa aa forbedre OwnTracks.",
        "work_duration": "ca. 70 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Dashboardet viser aktiv sone, total sonetid, mest brukte sone og siste posisjon.",
            "Sonebesok-siden viser aggregert soneoppsummering foer detaljloggen.",
            "Lokale waypoints kan redigeres og deaktiveres med historikk-rebuild.",
        ],
    },
    {
        "version": "1",
        "build": "7",
        "date": "03.07.2026",
        "headline": "Lokale waypoints og stoppforslag",
        "title": "OwnTracks kan definere server-soner og foreslaa nye soner fra stoppmonster",
        "description": (
            "Build 7 videreutvikler OwnTracks til mer enn et rent mottak. Serveren kan naa ha egne lokale waypoints "
            "som ikke ligger i telefonappen, og appen kan foreslaa nye soner ut fra steder der posisjonsloggen viser "
            "at telefonen har staatt stille over tid. Forslag kan faa adresse via reverse geocoding og opprettes direkte."
        ),
        "applications": [
            "owntracks_service/app/main.py: lokale waypoints, API for oppretting/endring/deaktivering og stoppforslag.",
            "owntracks_service/frontend/src/App.tsx: egen Forslag-side, lokal waypoint-modal og forbedret kartzoom.",
            "owntracks_service/frontend/src/styles.css: markorer og kontrollflater for lokale soner og forslag.",
        ],
        "request": "Moderniser OwnTracks med nødvendige funksjoner, lokale waypoints og forslag basert paa stopp med navn/adresse.",
        "work_duration": "ca. 90 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Lokale server-waypoints kan opprettes uten aa ligge i OwnTracks-appen paa telefonen.",
            "Forslag beregnes fra posisjoner som har ligget stille over tid og filtreres mot eksisterende soner.",
            "Kartet zoomer tettere inn og skiller lokale soner visuelt fra telefonsoner.",
        ],
    },
    {
        "version": "1",
        "build": "6",
        "date": "03.07.2026",
        "headline": "Kartet bruker MapLibre GL JS",
        "title": "OwnTracks-kartet bygges med MapLibre i stedet for Leaflet-CDN",
        "description": (
            "Build 6 bytter kartkomponenten i OwnTracks-frontend fra Leaflet lastet via ekstern CDN til MapLibre GL JS "
            "som npm-avhengighet i React/Vite-builden. Kartet viser fortsatt spor, siste posisjon, enhetsmarkor og "
            "waypoint-radius, men biblioteket er naa kontrollert av applikasjonsbuilden."
        ),
        "applications": [
            "owntracks_service/frontend: legger til maplibre-gl og bygger kartet som React-komponent.",
            "owntracks_service/frontend/src/App.tsx: erstatter Leaflet-kode med MapLibre-kart, GeoJSON-lag og markorer.",
            "owntracks_service/frontend/index.html: fjerner eksterne Leaflet-ressurser.",
        ],
        "request": "Kan du skifte ut kartet paa kart siden til denne komponenten: MapLibre GL JS.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Kartet er ikke lenger avhengig av global window.L eller Leaflet-CDN.",
            "Spor tegnes som MapLibre GeoJSON-linje.",
            "Waypoints tegnes med radiusflater og tydelige sentermarkorer.",
        ],
    },
    {
        "version": "1",
        "build": "5",
        "date": "03.07.2026",
        "headline": "OwnTracks faar React-rammeverk",
        "title": "Venstremeny og appskall bygges med samme rammeverk som Fibaro10",
        "description": (
            "Build 5 flytter OwnTracks-grensesnittet fra innebygd HTML til et eget React/Vite/Ant Design-frontend. "
            "Appen faar venstremeny, toppfelt, dashboard, kart, sonebesok, waypoints, meldinger, hendelser og buildlogg "
            "i et mer strukturert appskall."
        ),
        "applications": [
            "owntracks_service/frontend: nytt React/Vite/Ant Design-frontendprosjekt.",
            "owntracks_service/app/main.py: server bygget frontend fra frontend_dist med gammel HTML som fallback.",
            "owntracks_service/Dockerfile: bygger frontend i Node-stage og kopierer dist inn i Python-imaget.",
        ],
        "request": "Kan du forbedre appen med venstremeny paa samme maate som Fibaro10, innfoere samme rammeverk.",
        "work_duration": "ca. 60 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "OwnTracks har naa eget appskall med venstremeny.",
            "Kart, tabeller og statuskort ligger i samme React/Ant Design-familie som Fibaro10.",
            "Docker-builden bygger og serverer frontend automatisk.",
        ],
    },
    {
        "version": "1",
        "build": "4",
        "date": "03.07.2026",
        "headline": "Transition lager ikke ekstra beregnede besok",
        "title": "OwnTracks enter/leave holdes adskilt fra radiusberegning",
        "description": (
            "Build 4 retter at transition-meldinger kunne gi korte ekstra sonebesok. Telefonens enter/leave "
            "brukes naa som eksplisitt sonehendelse, mens serverens radiusberegning bare kjoeres paa vanlige "
            "posisjonsmeldinger. Transition-meldinger oppdaterer heller ikke waypointets faste koordinater."
        ),
        "applications": [
            "owntracks_service/app/main.py: stopper computed-position paa transition og bevarer waypoint-koordinater.",
            "tests/test_owntracks_service.py: dekker leave-transition uten ekstra beregnet sonebesok.",
        ],
        "request": "Det ser riktig ut under waypoints, men vaare egne beregnede blir doble.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Transition enter/leave flytter ikke lenger waypoint-senteret.",
            "Transition-meldinger trigget ikke lenger serverens egen radiusberegning.",
            "Korte dobbeltbesok etter leave/enter unngaas.",
        ],
    },
    {
        "version": "1",
        "build": "3",
        "date": "03.07.2026",
        "headline": "Sonebesok dupliseres ikke lenger",
        "title": "Inregions og radiusberegning samles til samme apne besok",
        "description": (
            "Build 3 retter at samme posisjonsmelding kunne apne samme waypoint to ganger. Telefonens inregions "
            "og serverens radiusberegning kjoeres i samme database-session, og apne sonebesok caches naa i sessionen "
            "slik at den andre vurderingen oppdaterer eksisterende rad i stedet for aa opprette en ny."
        ),
        "applications": [
            "owntracks_service/app/main.py: cacher apne OwnTracksZoneVisit-rader per topic og waypoint.",
            "tests/test_owntracks_service.py: dekker posisjon med baade inregions og radiusmatch.",
        ],
        "request": "Hvorfor genererer den to poster med samme tidspunkt paa start?",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Samme posisjon kan ikke lenger apne samme sone to ganger.",
            "Eksisterende apen rad oppdateres med siste posisjon og hoeyeste confidence.",
            "Rebuild av sonebesok vil rydde historiske duplikater.",
        ],
    },
    {
        "version": "1",
        "build": "2",
        "date": "03.07.2026",
        "headline": "Gammel OwnTracks-adresse er fjernet",
        "title": "Publisering skjer kun via owntracks.lilletorget.net/pub",
        "description": (
            "Build 2 fjerner overgangsadressen via online.lilletorget.net/owntracks. OwnTracks publisering skal "
            "naa bare bruke /pub paa eget domene. Basen ble ogsaa klargjort for ren ny start i produksjon."
        ),
        "applications": [
            "Caddyfile: fjerner proxy-ruting for online.lilletorget.net/owntracks.",
            "owntracks_service/app/main.py: fjerner legacy publish-aliaset /owntracks/pub fra tjenesten.",
            "docker-compose.qnap.yml: oppdaterer OwnTracks-build til 2.",
            "docs/owntracks-http.md: fjerner overgangsadresse fra oppskriften.",
        ],
        "request": "Tom hele basen slik at jeg ser at det funker, fjern gammel adresse ogsaa.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Kun /pub er gyldig publiseringsendepunkt.",
            "online.lilletorget.net/owntracks rutes ikke lenger til OwnTracks.",
            "OwnTracks database kan startes tom med samme SQLite-oppsett.",
        ],
    },
    {
        "version": "1",
        "build": "1",
        "date": "03.07.2026",
        "headline": "OwnTracks skilles ut som egen app",
        "title": "Eget domene, egen buildinfo og eget administrasjonsgrensesnitt",
        "description": (
            "OwnTracks-tjenesten er gjort mer selvstendig uten databasebytte. Den kan eksponeres paa "
            "owntracks.lilletorget.net, har eget buildnummer og beholder SQLite-lagringen inntil "
            "mottak, visning og API er stabilt over tid."
        ),
        "applications": [
            "owntracks_service/app/main.py: root-grensesnitt, /pub-alias, buildstatus og egen buildlogg.",
            "Caddyfile: eget vhost-oppsett for owntracks.lilletorget.net.",
            "docker-compose.qnap.yml: eksplisitt OwnTracks build- og URL-konfig.",
            "docs/owntracks-http.md: oppdatert appadresse og overgang fra gammel URL.",
        ],
        "request": "Skill OwnTracks ut mer, flytt den til owntracks.lilletorget.net og gi den egen buildlogg uten databasebytte.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny anbefalt publiseringsadresse er https://owntracks.lilletorget.net/pub.",
            "Gammel online.lilletorget.net/owntracks-rute beholdes som overgang.",
            "Intern SQLite-database og eksisterende data beholdes uendret.",
        ],
    }
]


def normalized_owntracks_build_log_entry(row: dict[str, Any]) -> dict[str, Any]:
    build = str(row.get("build") or "")
    return {
        "version": str(row.get("version") or OWNTRACKS_APP_VERSION),
        "build": build,
        "date": str(row.get("date") or ""),
        "headline": str(row.get("headline") or row.get("title") or f"Build {build}"),
        "title": str(row.get("title") or row.get("headline") or f"Build {build}"),
        "description": str(row.get("description") or ""),
        "applications": list(row.get("applications") or []),
        "request": str(row.get("request") or ""),
        "workDuration": str(row.get("work_duration") or row.get("workDuration") or ""),
        "creditsUsed": str(row.get("credits_used") or row.get("creditsUsed") or ""),
        "changes": list(row.get("changes") or []),
    }


def owntracks_build_summary() -> dict[str, Any]:
    return {
        "name": "OwnTracks",
        "version": OWNTRACKS_APP_VERSION,
        "build": OWNTRACKS_APP_BUILD,
        "commit": OWNTRACKS_APP_COMMIT,
    }


def owntracks_build_log_payload() -> dict[str, Any]:
    return {
        "currentBuild": OWNTRACKS_APP_BUILD,
        "current": owntracks_build_summary(),
        "rows": [normalized_owntracks_build_log_entry(row) for row in OWNTRACKS_BUILD_LOG],
    }
