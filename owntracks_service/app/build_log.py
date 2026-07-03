from __future__ import annotations

import os
from typing import Any


OWNTRACKS_APP_VERSION = os.getenv("OWNTRACKS_APP_VERSION", "1")
OWNTRACKS_APP_BUILD = os.getenv("OWNTRACKS_APP_BUILD", "5")
OWNTRACKS_APP_COMMIT = os.getenv("OWNTRACKS_APP_COMMIT", "unknown")

OWNTRACKS_BUILD_LOG: list[dict[str, Any]] = [
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
