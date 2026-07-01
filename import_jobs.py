"""Import job metadata used by the API, health checks and admin views."""

IMPORT_JOB_DEFINITIONS = {
    "hc3_light_5min": {
        "title": "Lys / lux fra HC3",
        "category": "Lys",
        "source": "HC3",
        "expected_interval_minutes": 7,
        "warning_after_minutes": 15,
        "description": "5-minutters luxlogg og status for utelys.",
    },
    "hc3_ventilation_5min": {
        "title": "Ventilasjon / temperatur fra HC3",
        "category": "Ventilasjon",
        "source": "HC3",
        "expected_interval_minutes": 7,
        "warning_after_minutes": 15,
        "description": "5-minutters temperatur, effekt og viftestatus.",
    },
    "yr_weather_refresh": {
        "title": "Yr API",
        "category": "Vær",
        "source": "MET/Yr",
        "expected_interval_minutes": 70,
        "warning_after_minutes": 130,
        "description": "Værvarsel hentet fra Yr/MET når forrige varsel går ut.",
    },
    "hc3_energy_1min": {
        "title": "Energi fra HC3",
        "category": "Energi",
        "source": "HC3",
        "expected_interval_minutes": 2,
        "warning_after_minutes": 5,
        "description": "30-sekunders logging av realtime effekt og akkumulert kWh fra Fibaro.",
    },
    "roborock_sync": {
        "title": "Roborock logger",
        "category": "Renhold",
        "source": "QNAP",
        "expected_interval_minutes": 10,
        "warning_after_minutes": 30,
        "description": "Robotstatus, planlagte jobber og siste lokale/cloud-data.",
    },
    "owntracks_mqtt": {
        "title": "OwnTracks MQTT",
        "category": "Mobil",
        "source": "Mosquitto",
        "expected_interval_minutes": 30,
        "warning_after_minutes": 120,
        "description": "Siste posisjonsmelding fra OwnTracks via intern MQTT-broker.",
    },
    "sun2_daily_download": {
        "title": "Sun2 dagsfil nedlasting",
        "category": "Soling",
        "source": "QNAP",
        "expected_interval_minutes": 36 * 60,
        "warning_after_minutes": 72 * 60,
        "description": "Nattlig nedlasting av SUN2 dagsfil for import.",
    },
    "sun2_room_daily_import": {
        "title": "Sun2 dagsimport rom",
        "category": "Soling",
        "source": "QNAP",
        "expected_interval_minutes": 36 * 60,
        "warning_after_minutes": 72 * 60,
        "description": "Daglige summer per rom fra Sun2.",
    },
    "sun2_sessions_import": {
        "title": "Sun2 enkelttimer",
        "category": "Soling",
        "source": "QNAP",
        "expected_interval_minutes": 7,
        "warning_after_minutes": 20,
        "description": "Import av enkeltsolinger fra Sun2.",
    },
    "sun2_beds_import": {
        "title": "Sun2 senger",
        "category": "Soling",
        "source": "QNAP",
        "expected_interval_minutes": 7 * 24 * 60,
        "warning_after_minutes": 14 * 24 * 60,
        "description": "Seng-/rommetadata fra Sun2.",
    },
    "sun2_members_import": {
        "title": "Sun2 medlemmer",
        "category": "Soling",
        "source": "QNAP",
        "expected_interval_minutes": 7 * 24 * 60,
        "warning_after_minutes": 14 * 24 * 60,
        "description": "Medlemsregister og profilfelter fra Sun2.",
    },
    "sun2_product_sales_daily_import": {
        "title": "Sun2 produktsalg daglig",
        "category": "Soling",
        "source": "QNAP",
        "expected_interval_minutes": 36 * 60,
        "warning_after_minutes": 72 * 60,
        "description": "Daglig import av produktsalg fra Sun2 for dagsfordeling.",
    },
    "sun2_product_sales_monthly_import": {
        "title": "Sun2 produktsalg maanedskontroll",
        "category": "Soling",
        "source": "QNAP",
        "expected_interval_minutes": 40 * 24 * 60,
        "warning_after_minutes": 55 * 24 * 60,
        "description": "Maanedlig import av hele forrige maaned fra Sun2 for kontroll mot solingsoppgjor.",
    },
    "sun2_finance_settlement_monthly_import": {
        "title": "Sun2 finansoppgjor",
        "category": "Soling",
        "source": "QNAP",
        "expected_interval_minutes": 40 * 24 * 60,
        "warning_after_minutes": 55 * 24 * 60,
        "description": "Maanedlig import av Sun2 finanshistorikk for solomsetning og uregistrerte solinger.",
    },
    "elvia_monthly_import": {
        "title": "Elvia månedsfil",
        "category": "Energi",
        "source": "Manuell opplasting",
        "expected_interval_minutes": 40 * 24 * 60,
        "warning_after_minutes": 55 * 24 * 60,
        "description": "Månedlig import av strømforbruk fra Elvia.",
    },
    "easypark_parking_import": {
        "title": "EasyPark import",
        "category": "Parkering",
        "source": "EasyPark",
        "expected_interval_minutes": 26 * 60,
        "warning_after_minutes": 50 * 60,
        "description": "Automatisk nedlasting og import av parkeringsliste fra EasyPark.",
    },
    "parking_history_import": {
        "title": "Parkering historikk",
        "category": "Parkering",
        "source": "QNAP appdb",
        "expected_interval_minutes": None,
        "warning_after_minutes": None,
        "description": "Migrert EasyPark-historikk med kjøretøydata fra Statens vegvesen.",
    },
    "parking_vehicle_svv_sync": {
        "title": "Kjøretøydata fra SVV",
        "category": "Parkering",
        "source": "Statens vegvesen",
        "expected_interval_minutes": 30,
        "warning_after_minutes": 90,
        "description": "Løpende berikelse av registreringsnummer som mangler tekniske kjøretøydata.",
    },
    "parking_vehicle_biluppgifter_sync": {
        "title": "Biluppgifter Sverige",
        "category": "Parkering",
        "source": "Biluppgifter.se",
        "expected_interval_minutes": None,
        "warning_after_minutes": None,
        "description": "Oppslag av svenske registreringsnummer der SVV ikke fant kjøretøydata.",
    },
    "parking_vehicle_tjekbil_sync": {
        "title": "Tjekbil Danmark",
        "category": "Parkering",
        "source": "Tjekbil.dk",
        "expected_interval_minutes": None,
        "warning_after_minutes": None,
        "description": "Oppslag av danske registreringsnummer der SVV ikke fant kjøretøydata.",
    },
    "parking_sun_link_worker": {
        "title": "Koble parkering/SUN2",
        "category": "Koble",
        "source": "parking_sun_linker",
        "expected_interval_minutes": 10,
        "warning_after_minutes": 30,
        "description": "Sideapp som finner sannsynlige koblinger mellom parkering og soltimer.",
    },
}

IMPORT_JOB_NUMBER_BY_NAME = {
    job_name: index + 1
    for index, job_name in enumerate(IMPORT_JOB_DEFINITIONS)
}

IMPORT_JOB_DETAILS = {
    "hc3_light_5min": {
        "data_flow": "HC3 QuickApp sender luxmålinger og lysstatus til Fibaro10 sitt event-endepunkt. Fibaro10 lagrer sample i lysloggen og bruker samme grunnlag i status, dagslogg og datakildehelse.",
        "dependencies": ["HC3", "Fibaro QuickApp", "Fibaro10 API", "PostgreSQL"],
    },
    "hc3_ventilation_5min": {
        "data_flow": "HC3 QuickApp sender temperatur, fuktighet, modus og viftestatus til Fibaro10. Data lagres i ventilasjonsloggen og brukes i ventilasjonssider, dashboard og friskhetskontroll.",
        "dependencies": ["HC3", "Fibaro QuickApp", "Fibaro10 API", "PostgreSQL"],
    },
    "yr_weather_refresh": {
        "data_flow": "Fibaro10 henter oppdaterte værdata fra MET/Yr og lagrer siste relevante varsel sammen med lys- og ventilasjonssamples. Verdiene brukes til værvisning, sammenligning og senere analyse.",
        "dependencies": ["MET/Yr API", "Fibaro10 backend", "PostgreSQL"],
    },
    "hc3_energy_1min": {
        "data_flow": "HC3 sender realtime effektverdier fra hovedmåler og undermålere til Fibaro10. Systemet bruker realtime målingene som grunnlag for energisider, differanse og akkumulert forbruk.",
        "dependencies": ["HC3", "Fibaro energimåler/QuickApp", "Fibaro10 API", "PostgreSQL"],
    },
    "roborock_sync": {
        "data_flow": "Roborock-loggeren på QNAP henter robotstatus, jobber, kart og vedlikeholdsdata og poster resultatet til Fibaro10. Fibaro10 lagrer status og viser renholdsdata i drift/admin.",
        "dependencies": ["roborock_logger", "Roborock cloud/lokal robot", "Fibaro10 API", "PostgreSQL"],
    },
    "owntracks_mqtt": {
        "data_flow": "OwnTracks publiserer posisjoner og waypoint-hendelser til Mosquitto. Fibaro10 abonnerer på MQTT-topicene og lagrer både råposisjoner og egne waypoint-tabeller.",
        "dependencies": ["OwnTracks app", "Mosquitto MQTT", "Fibaro10 MQTT-worker", "PostgreSQL"],
    },
    "sun2_daily_download": {
        "data_flow": "Sun2 backfill/downloader laster ned dagsfil fra Sun2 og legger filgrunnlaget klart for import. Dette er kildefilen for daglige romsummer.",
        "dependencies": ["sun2_backfill_downloader", "Sun2", "QNAP filområde", "Fibaro10 API"],
    },
    "sun2_room_daily_import": {
        "data_flow": "Sun2-importeren leser dagsfilene og lagrer summer per rom, dato, tid og omsetning. Dette brukes til historiske dags- og romsummer.",
        "dependencies": ["sun2_importer", "Sun2 dagsfil", "Fibaro10 API", "PostgreSQL"],
    },
    "sun2_sessions_import": {
        "data_flow": "Sun2 session scraper henter enkeltsolinger fra Sun2 og poster nye eller endrede timer til Fibaro10. Fibaro10 kobler i tillegg relevante Axis-bilder til soltimene.",
        "dependencies": ["sun2_session_scraper", "Sun2", "Axis snapshot-arkiv", "Fibaro10 API", "PostgreSQL"],
    },
    "sun2_beds_import": {
        "data_flow": "Sun2 session scraper henter rom- og sengmetadata fra Sun2 og oppdaterer lokal sengtabell. Metadata brukes for visningsnavn, romkobling og energiberegning.",
        "dependencies": ["sun2_session_scraper", "Sun2", "Fibaro10 API", "PostgreSQL"],
    },
    "sun2_members_import": {
        "data_flow": "Sun2 session scraper henter medlemsregister fra Sun2 og lagrer bruker-/profilfelter lokalt. Brukes for enkelttimer, søk og historikk der Sun2-bruker finnes.",
        "dependencies": ["sun2_session_scraper", "Sun2", "Fibaro10 API", "PostgreSQL"],
    },
    "sun2_product_sales_daily_import": {
        "data_flow": "Sun2 session scraper henter produktsalg for forrige dag og lagrer salgene med dato, produkt og beløp. Daglig import brukes for fordeling per dag og kontrollgrunnlag.",
        "dependencies": ["sun2_session_scraper", "Sun2", "Fibaro10 API", "PostgreSQL"],
    },
    "sun2_product_sales_monthly_import": {
        "data_flow": "Sun2 session scraper henter hele forrige måneds produktsalg som kontrollimport. Resultatet brukes til avstemming mot solingsoppgjør og daglige produktsalg.",
        "dependencies": ["sun2_session_scraper", "Sun2", "Fibaro10 API", "PostgreSQL"],
    },
    "sun2_finance_settlement_monthly_import": {
        "data_flow": "Sun2 session scraper henter finanshistorikk/oppgjør fra Sun2 og lagrer solomsetning, produktsalg, kostnader og utbetalt beløp. Brukes til oppgjørskontroll.",
        "dependencies": ["sun2_session_scraper", "Sun2", "Fibaro10 API", "PostgreSQL"],
    },
    "elvia_monthly_import": {
        "data_flow": "Elvia-fil lastes opp manuelt i energi-grensesnittet. Fibaro10 leser timesverdier fra filen og bruker dem til kontroll mot egne HC3-målinger.",
        "dependencies": ["Elvia eksportfil", "Fibaro10 opplasting", "PostgreSQL"],
    },
    "easypark_parking_import": {
        "data_flow": "EasyPark-downloaderen logger inn via lagret Google/OAuth-sesjon, laster ned parkeringsliste for nyere dager og poster importstatus til Fibaro10. Fibaro10 importerer parkeringer, oppdaterer prognose og beriker kjøretøydata etterpå.",
        "dependencies": ["easypark_downloader", "EasyPark portal", "Google/OAuth-token", "Fibaro10 API", "PostgreSQL"],
    },
    "parking_history_import": {
        "data_flow": "Historiske parkeringsdata er migrert fra tidligere QNAP/appdb-oppsett til Fibaro10. Dette er ikke en løpende jobb, men et arkivgrunnlag som brukes i rapporter og historikk.",
        "dependencies": ["QNAP appdb backup", "Fibaro10 migrering", "PostgreSQL"],
    },
    "parking_vehicle_svv_sync": {
        "data_flow": "Fibaro10 finner norske registreringsnummer som mangler tekniske data og slår dem opp mot Statens vegvesen. Resultatet lagres på kjøretøy og brukes i parkeringslister og områdekontroll.",
        "dependencies": ["Fibaro10 bakgrunnsjobb", "Statens vegvesen API", "PostgreSQL"],
    },
    "parking_vehicle_biluppgifter_sync": {
        "data_flow": "Nordisk kjøretøyoppslag sjekker svenske registreringsnummer som ikke fikk treff hos SVV. Data brukes til å markere Sverige og fylle tekniske kjøretøyfelter der kilden gir svar.",
        "dependencies": ["car_info_lookup", "Biluppgifter.se", "Fibaro10 API", "PostgreSQL"],
    },
    "parking_vehicle_tjekbil_sync": {
        "data_flow": "Nordisk kjøretøyoppslag sjekker danske registreringsnummer som ikke fikk treff hos SVV. Data brukes til å markere Danmark og fylle tekniske kjøretøyfelter der kilden gir svar.",
        "dependencies": ["car_info_lookup", "Tjekbil.dk", "Fibaro10 API", "PostgreSQL"],
    },
    "parking_sun_link_worker": {
        "data_flow": "parking_sun_linker kjører som egen QNAP-container. Den henter parametere fra Fibaro10, leser parkeringer og soltimer direkte fra PostgreSQL, og rapporterer behandlet status, treffgrunnlag og kandidater tilbake til Fibaro10. Bruker bekrefter eller avviser koblingene i Koble-siden.",
        "dependencies": ["parking_sun_linker", "Fibaro10 worker-API", "PostgreSQL", "Parkering", "Sun2 enkelttimer"],
    },
}

for job_name, details in IMPORT_JOB_DETAILS.items():
    if job_name in IMPORT_JOB_DEFINITIONS:
        IMPORT_JOB_DEFINITIONS[job_name].update(details)
