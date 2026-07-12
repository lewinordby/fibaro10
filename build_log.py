import os
from typing import Any, Dict, Optional

from api_types import BuildLogEntryPayload, BuildLogListRowPayload, BuildLogTableRowPayload


APP_VERSION = os.getenv("APP_VERSION", "1")
APP_BUILD = os.getenv("APP_BUILD", "1532")
BUILD_LOG = [
    {
        "version": "1",
        "build": "1532",
        "date": "12.07.2026",
        "headline": "Ryddigere romkontroll",
        "title": "Gjør Dører / Romkontroll raskere å lese",
        "description": (
            "Build 1532 strammer opp Dører / Romkontroll med tydeligere toppstatus, egen liste for rom som "
            "krever oppfølging, og mer kompakte romkort. Kortene prioriterer nå dørstatus, hvor lenge rommet "
            "har stått slik, forventet ut-tid, Sun2-kobling og strømstatus."
        ),
        "applications": [
            "desktop_v2/src/pages/DoorsPage.tsx: bygger om Romkontroll til mer operativ oversikt med prioriteringsliste og ryddigere romkort.",
            "desktop_v2/src/styles/doors.css: strammer opp layout, spacing, fargebruk og responsive regler for Romkontroll.",
            "desktop_v2/src/styles/dark-theme.css: legger mørkt-tema-støtte for nye Romkontroll-elementer.",
            "build_log.py: dokumenterer build 1532 og setter APP_BUILD til 1532.",
        ],
        "request": "jeg synes fortsatt at Dører/Romkontroll er lite oversiktelig. vanskelig å få rask og god oversikt",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Romkontroll har nå kompakt toppfelt med oppdatert-tid og periodevalg.",
            "Nøkkeltallene viser ledige rom, rom i bruk, varsler, dørmatch, strøm OK og soltimer uten dørmatch.",
            "Ny oppfølgingsliste løfter frem rom med varsel, manglende Sun2-match eller soltimer uten dørmatch.",
            "Romkortene er lavere og viser først dørstatus, varighet, forventet ut og aktuell soltime.",
            "Mørkt tema er justert for de nye romkontroll-elementene.",
        ],
    },
    {
        "version": "1",
        "build": "1531",
        "date": "12.07.2026",
        "headline": "Manualruter i drift",
        "title": "Retter serverruting for Manual som eget hovedvalg",
        "description": (
            "Build 1531 fullfører flyttingen av Manual ved å legge de nye /manual-rutene inn i serverens "
            "SPA-fallback. Direkte åpning og refresh av /manual/oversikt og de andre manualundersidene fungerer "
            "dermed likt som øvrige hovedmenyvalg."
        ),
        "applications": [
            "main.py: legger /manual og /manual/{path} inn i desktop-appens HTML-fallback.",
            "build_log.py: dokumenterer build 1531 og setter APP_BUILD til 1531.",
        ],
        "request": "Flytt manual ut i eget hovedmeny valg med egne undersider",
        "work_duration": "ca. 5 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Direkte åpning av /manual/oversikt serverer nå hovedappen i stedet for 404.",
            "Alle manualundersider kan refreshes direkte uten å gå via en annen side først.",
            "Buildnummeret er løftet til 1531 slik at deployrettingen vises i Build-loggen.",
        ],
    },
    {
        "version": "1",
        "build": "1530",
        "date": "12.07.2026",
        "headline": "Manual som eget hovedområde",
        "title": "Flytter manualen ut av Admin og gir den egne undersider",
        "description": (
            "Build 1530 gjør Manual til et eget hovedmenyvalg under System. Manualen er delt opp i egne "
            "undersider for oversikt, daglig bruk, menyvalg, økonomi, bygg og drift, system, datagrunnlag, "
            "rutiner og feilsøking. Gammel /admin/manual videresender til ny manualoversikt."
        ),
        "applications": [
            "desktop_v2/src/moduleViews.ts og appNavigation.tsx: legger Manual som egen hovedmodul med undersider.",
            "desktop_v2/src/pages/ManualPage.tsx: flytter manualsiden ut av Admin og renderer én underside per kapittel.",
            "desktop_v2/src/AppRoutes.tsx: legger /manual og /manual/:view, og redirecter /admin/manual til /manual/oversikt.",
            "desktop_v2/src/api.ts: flytter frontend til /api/manual.",
            "desktop_v2/src/styles/*.css og designTokens.ts: legger egen Manual-farge og domain-manual.",
            "main.py: legger /api/manual og oppdaterer interne manual-lenker.",
            "desktop_v2/scripts/smoke-routes.mjs og smoke-ui.mjs: tester alle nye manualundersider.",
            "docs/*.md: oppdaterer dokumentasjon fra Admin -> Manual til eget Manual-hovedvalg.",
            "build_log.py: dokumenterer build 1530 og setter APP_BUILD til 1530.",
        ],
        "request": "Flytt manual ut i eget hovedmeny valg med egne undersider",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Manual ligger nå som eget hovedvalg i venstremenyen under System.",
            "Manual har egne undersider: Oversikt, Daglig bruk, Menyvalg, Økonomi, Bygg og drift, System, Datagrunnlag, Rutiner og Feilsøking.",
            "Admin-menyen har ikke lenger Manual som underspunkt.",
            "Gammel /admin/manual redirecter til ny /manual/oversikt.",
            "Manual har egen indigo fargetone i lyst og mørkt tema.",
            "Route-audit og smoke-testene dekker de nye manualrutene.",
        ],
    },
    {
        "version": "1",
        "build": "1529",
        "date": "12.07.2026",
        "headline": "Tydeligere manualfarger",
        "title": "Gjør fargekodingen i manualen mer synlig per fagområde",
        "description": (
            "Build 1529 gjør fargene tydeligere på områdene i webmanualen. Alle manuelle områdekort får nå "
            "eksplisitt egen domenefarge, sterkere kantmarkering, tydeligere ikonfelt og bedre kontrast i mørkt tema."
        ),
        "applications": [
            "desktop_v2/src/styles/manual.css: gir alle manualområder eksplisitt tonefarge og tydeligere kort, ikon og mørkt tema.",
            "build_log.py: dokumenterer build 1529 og setter APP_BUILD til 1529.",
        ],
        "request": "gjør fargene litt tydligre for de forskjellige områdene",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Omsetning, parkering, soling, energi, ventilasjon, lys, kobling, bygg/drift, vedlikehold, mobil, ideer og admin har nå egne eksplisitte manualfarger.",
            "Manualkortene har sterkere venstrekant, mer synlig farget bakgrunn og tydeligere ramme.",
            "Ikonfeltene bruker sterkere områdefarge og bedre kontrast.",
            "Mørkt tema er justert slik at fargene fortsatt er tydelige uten å bli for harde.",
        ],
    },
    {
        "version": "1",
        "build": "1528",
        "date": "12.07.2026",
        "headline": "Finjustert webmanual",
        "title": "Utvider manualen med menykart, rutiner og strammere leseflyt",
        "description": (
            "Build 1528 finjusterer Admin -> Manual. Manualen får et eget menykart som forklarer alle hovedmenyer "
            "og viktige undersider, et eget kapittel for daglige, ukentlige og månedlige kontrollrutiner, og CSS "
            "som gjør de nye delene mer lesbare som oppslagsverk."
        ),
        "applications": [
            "main.py: utvider /api/admin/manual med kapitlene Menyvalg og Rutiner og kontroll.",
            "desktop_v2/src/api.ts: legger typer for menuGroups og checklists i manualresponsen.",
            "desktop_v2/src/pages/AdminManualPage.tsx: renderer menykart og sjekklister som klikkbare manualseksjoner.",
            "desktop_v2/src/styles/manual.css: legger egne grid-regler for menykart og rutiner.",
            "docs/kort-brukermanual.md: oppdaterer tekstversjonen med henvisning til nytt menykart og rutiner.",
            "build_log.py: dokumenterer build 1528 og setter APP_BUILD til 1528.",
        ],
        "request": "finjuster alt",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Manualen forklarer nå alle hovedmenyene, inkludert hvilke undersider som ligger under hvert fagområde.",
            "Rutiner og kontroll er lagt inn som egen del for daglig økonomi, parkering, soling, datakilder, uke, måned, vedlikehold og buildlogg.",
            "Innholdslisten og kapittelnummereringen er oppdatert til ni kapitler.",
            "Frontend-rendereren støtter nå egne manualfelter for menykart og sjekklister.",
            "CSS er finjustert slik at menykartet kan leses raskt i tre kolonner på brede skjermer.",
        ],
    },
    {
        "version": "1",
        "build": "1527",
        "date": "12.07.2026",
        "headline": "Kapitteldelt webmanual",
        "title": "Gjør Admin -> Manual til en lesbar webside med kapitler",
        "description": (
            "Build 1527 erstatter den tabellpregede manualflaten med en egen webmanual. Manualen har "
            "innholdsmeny, kapitler, forklaring av daglig bruk, hovedområder, underapper, datagrunnlag "
            "og feilsøking, med lenker direkte til relevante sider i Fibaro10."
        ),
        "applications": [
            "main.py: legger /api/admin/manual som leverer kapitteldelt manualinnhold fra backend.",
            "desktop_v2/src/api.ts: legger typekontrakt og fetcher for webmanualen.",
            "desktop_v2/src/pages/AdminManualPage.tsx: ny kapitteldelt manualsider med innholdsmeny og forklaringer fra API.",
            "desktop_v2/src/styles/manual.css: ny dokument-CSS for manualen, inkludert mørkt tema.",
            "desktop_v2/src/AppRoutes.tsx: ruter /admin/manual til den nye manualsiden før generisk admin-view.",
            "docs/kort-brukermanual.md: oppdatert tekstversjon som peker på webmanualen.",
            "build_log.py: dokumenterer build 1527 og setter APP_BUILD til 1527.",
        ],
        "request": "jeg vil ha en manual som du kan lese som en web side med flere kapitler og forklaring av alt",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Admin -> Manual åpner nå en egen lesbar dokumentflate i stedet for en kompakt tabell.",
            "Manualen har kapitlene Hva løsningen er, Slik bruker du den daglig, Økonomi, Bygg og drift, System og underapper, Datagrunnlag og Feilsøking.",
            "Hvert hovedområde forklares med formål, hva du kan se og hva du kan gjøre.",
            "Underapper og datakilder er forklart samlet med tydelige driftslenker videre.",
            "Manualen har egen CSS som følger eksisterende Fibaro10-design og fungerer i mørkt tema.",
        ],
    },
    {
        "version": "1",
        "build": "1526",
        "date": "12.07.2026",
        "headline": "Kort operativ manual",
        "title": "Gir Admin -> Manual et ryddig overblikk over hele losningen",
        "description": (
            "Build 1526 rydder opp i manualflaten. Admin -> Manual viser na en kort operativ oversikt over hvor man "
            "starter, hva hvert hovedomrade brukes til, hva man kan se og gjore, og hvor man feilsoker vanlige avvik. "
            "Samme oversikt er lagt inn i docs slik at den folger git og backup."
        ),
        "applications": [
            "main.py: legger ny API-helper for kort manualinnhold og kobler Admin -> Manual til den.",
            "desktop_v2/src/pages/module/moduleTableUtils.tsx: gir manualtabellen bedre kolonneetikett for forste sjekk.",
            "docs/kort-brukermanual.md: ny kort brukermanual i repoet.",
            "docs/README.md: peker til den nye korte manualen.",
            "build_log.py: dokumenterer build 1526 og setter APP_BUILD til 1526.",
        ],
        "request": "Rydd opp og lag en ny god kortfattet manual som gir et overblikk over alt du kan se/gjore med losningen.",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Admin -> Manual starter na med konkrete lenker til Dashboard, Datakilder, Systemkart, Buildlogg og Brukere.",
            "Manualen viser alle hovedomrader med hva du kan se, hva du kan gjore og nar siden brukes.",
            "Manualen har en egen feilsokingsdel for gamle data, parkering, soling, energi, lys/ventilasjon og underapper.",
            "Underapper med webgrensesnitt ligger fortsatt med klikkbare URL-er og health-lenker.",
            "Repoet har faatt docs/kort-brukermanual.md som kort tekstversjon av manualen.",
        ],
    },
    {
        "version": "1",
        "build": "1525",
        "date": "11.07.2026",
        "headline": "Ytelsesoptimalisering i hovedlosningen",
        "title": "Reduserer unodvendig henting, CPU-bruk og treg tabellbehandling",
        "description": (
            "Build 1525 er en ytelsesrunde for Fibaro10. Store og historiske visninger faar mer presis React Query-cache, "
            "parameterbytter beholder forrige datasett mens ny henting pagar, server-side paginerte tabeller filtreres ikke "
            "ekstra i browseren, parkering/kjoretoy og parkering/parkeringer hopper over unodvendig oversiktsbygging, "
            "gzip bruker lavere komprimeringsnivaa, og databasen faar indekser som matcher faktisk sporringsmonster "
            "for parkering og kjoretoy."
        ),
        "applications": [
            "main.py: setter GZipMiddleware compresslevel til 5 og legger til indekser for kompakt parkeringsskilt/starttid og kjoretoy last_seen/plate.",
            "main.py: gir parkering/kjoretoy og parkering/parkeringer tidlig retur, lavere standardbatch og samler kjoretoy-counts i en database-sporring.",
            "desktop_v2/src/hooks.ts og queryClient.ts: beholder forrige query-data ved parameterbytte og lar cache leve lenger mellom navigeringer.",
            "desktop_v2/src/pages/ModulePage.tsx: gir tunge historikk-, oppgjor-, analyse- og registervisninger egne staleTime-verdier.",
            "desktop_v2/src/pages/module/ModuleTablePane.tsx: unngar dobbel klientfiltrering for server-side paginerte tabeller.",
            "desktop_v2/src/pages/*Comparison*, RevenueMonthPage, ParkingTimeDistributionPage, oppgjors- og detaljsider: lengre cache paa tunge analyse- og detaljvisninger.",
            "build_log.py: dokumenterer build 1525 og setter APP_BUILD til 1525.",
        ],
        "request": "Optimaliser ytelse i hele losningen.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Store historikk- og analysevisninger gjenbrukes i cache i 1-5 minutter der data ikke ma vaere sekundferske.",
            "Live-nare visninger som energi/status beholder kortere staleTime.",
            "React Query viser forrige datasett under ny lasting i stedet for a blinke til tom lasteskjerm ved periode- og filterbytte.",
            "Server-side paginerte tabeller bruker backend-resultatet direkte og slipper ekstra filterpass i browseren.",
            "Gzip-komprimering bruker lavere CPU-kost, bedre egnet for store JSON-svar paa QNAP.",
            "Nye databaseindekser gir bedre grunnlag for parkeringshistorikk per bil og kjoretoylisten sortert paa sist sett.",
            "Kjoretoy- og parkeringer-view bygger ikke lenger oversiktskort, ukegraf og siste-parkeringer-grunnlag forst.",
            "Kjoretoy-listen henter 250 rader som standard og gjenbruker samlet count-statistikk naar det ikke er aktivt sok.",
            "Full lokal kvalitetssjekk er kjort gront, inkludert Python-tester, desktop-build, OwnTracks-build, CSS-audit, bundle-audit, route-audit og UI-smoke.",
        ],
    },
    {
        "version": "1",
        "build": "1524",
        "date": "11.07.2026",
        "headline": "Lesbare grafer i lyst og morkt tema",
        "title": "Strammer opp grafpalett, backend-fargemapping og mork-tema-kontrast",
        "description": (
            "Build 1524 er en graf- og fargekvalitetsrunde. Backend-farger som tidligere kunne bli for morke "
            "i morkt tema, blir na oversatt sentralt i chartTheme. Akkumulerte grafer setter linjefarge, "
            "markorer og flater eksplisitt, datazoom og legend har bedre kontrast, og ventilasjon/Yr/heatmap "
            "har tydeligere lesbarhet i morkt tema."
        ),
        "applications": [
            "desktop_v2/src/chartTheme.ts: utvider mork-tema-mapping for gamle backend-paletter, legger til chartAreaOpacity og bedre legend/datazoom-kontrast.",
            "desktop_v2/src/pages/StatusComparisonPage.tsx, RevenueYearComparisonPage.tsx, SunYearComparisonPage.tsx og ParkingYearComparisonPage.tsx: setter serie-, linje- og flatefarger eksplisitt.",
            "desktop_v2/src/pages/module/ModuleChartPanel.tsx: bruker felles flate-opacity og eksplisitt farge pa enlinje-grafer.",
            "desktop_v2/src/pages/ventilation/VentilationCharts.tsx: gjor viftehendelser og Yr-serier tydeligere, spesielt i morkt tema.",
            "desktop_v2/src/styles/parking-time-distribution.css og ventilation-charts.css: styrker lesbarhet i heatmap og viftebaner i morkt tema.",
            "build_log.py: dokumenterer build 1524 og setter APP_BUILD til 1524.",
        ],
        "request": "Ta en gjennomgang spesielt med hensyn til fargebruk pa grafer. Sjekk ogsa dette pa morkt tema, slik at alt er leselig.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Morke backend-farger som #071943, gamle ventilasjonsfarger og eldre ukes-/prognosepaletter mappes na til lesbare mork-tema-varianter.",
            "Akkumulerte omsetnings-, soling- og parkeringsgrafer bruker na samme farge eksplisitt pa linje, markor og flate.",
            "Yr-grafen bruker stabile semantiske farger for temperatur, fukt, vind, skydekke og nedbor.",
            "Ventilasjonsdagslogg har tydeligere stiplete hendelseslinjer og viftebaner i morkt tema.",
            "Parkeringstid-heatmap har bedre tekstkontrast i morkt tema.",
            "Lokal frontend-build, CSS-parser, CSS-audit og graf-rute-smoke er kjort gront.",
        ],
    },
    {
        "version": "1",
        "build": "1523",
        "date": "11.07.2026",
        "headline": "CSS-opprydding og bedre tema-tokens",
        "title": "Rydder fargebruk, radius og morkt tema i hovedgrensesnittet",
        "description": (
            "Build 1523 er en CSS-kvalitetsrunde. Felles radiusverdier og flere fargetokens er lagt inn, "
            "morkt tema bruker en samlet palett, og flere hardkodede farger i soling, parkering, ventilasjon, "
            "ideer og app-skall er flyttet over til tokens eller domenefarger. CSS-audit viser betydelig lavere "
            "antall hardkodede farger, og produksjonsbuilden bygger gront."
        ),
        "applications": [
            "desktop_v2/src/styles/tokens.css: legger til felles radius-tokens, orange-token og en samlet mork-tema-palett.",
            "desktop_v2/src/styles/dark-theme.css: bruker mork-paletten konsekvent for flater, tekst, grafer og Ant Design-overstyringer.",
            "desktop_v2/src/styles/doors.css: retter udefinert var(--orange)-bruk og bruker felles radius/fargevariabler.",
            "desktop_v2/src/styles/sun-timeline.css, ventilation.css og ventilation-charts.css: flytter graf- og tidslinjefarger over til tokens/color-mix.",
            "desktop_v2/src/styles/ideas.css, app-shell.css, layout.css, parking-timeline.css og records-settlements.css: rydder hardkodede flater, piller og skygger.",
            "build_log.py: dokumenterer build 1523 og setter APP_BUILD til 1523.",
        ],
        "request": "Ta en gjennomgang av CSS, gjor det sa bra som mulig.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "CSS-parseren er gronn etter endringene.",
            "Hardkodede farger i CSS-audit er redusert fra 175 til 24.",
            "Felles --radius-lg og --radius-pill er definert og tatt i bruk pa tvers av kort, piller og tidslinjer.",
            "Morkt tema har na en tydeligere samlet tokenpalett for tekst, flater, grenser, skygger og statusfarger.",
            "Dorer-siden bruker ikke lenger en udefinert --orange-variabel for warning-tone.",
        ],
    },
    {
        "version": "1",
        "build": "1522",
        "date": "11.07.2026",
        "headline": "Kontroll av funksjonalitet og manual",
        "title": "Verifiserer live-systemet og rydder bort utdatert ventilasjonstekst i manualen",
        "description": (
            "Build 1522 er en kontrollbuild. Lokal kvalitetssjekk, live smoke, QNAP-status og live health ble kontrollert. "
            "Alle ruter laster, alle automatiserte tester er gronne, og 22 av 22 datakilder rapporterer OK. "
            "Driftsmanualen er samtidig oppdatert slik at den ikke lenger omtaler en gammel planlagt ventilasjonsflis."
        ),
        "applications": [
            "scripts/build_user_manual.py: fjerner utdatert Loft > 1.etg-linje fra ventilasjonsdelen.",
            "static/manualer/sun2_driftsmanual.pdf: regenerert driftsmanual uten utdatert dummytekst.",
            "build_log.py: dokumenterer build 1522 og setter APP_BUILD til 1522.",
        ],
        "request": "Ta en runde og kontroller at all funksjonalitet er pa plass.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Full lokal kvalitetssjekk er kjort og bestatt etter endringen.",
            "Live health er kontrollert med database OK og 22/22 datakilder OK.",
            "QNAP-containere og live smoke er kontrollert som OK.",
            "Driftsmanualen viser ikke lenger den gamle dummyflis-teksten.",
        ],
    },
    {
        "version": "1",
        "build": "1521",
        "date": "11.07.2026",
        "headline": "Kvalitetspass og sterkere Romkontroll-test",
        "title": "Reduserer unødvendige dørkall og gjør smoke-testen mer innholdsnær",
        "description": (
            "Build 1521 er en kvalitetspass etter gjennomgang av løsning, drift og tester. Dører-siden gjør nå færre "
            "unødvendige API-kall, og både lokal og live smoke-test kontrollerer at Romkontroll faktisk viser sentrale "
            "romdata i stedet for bare å sjekke at ruten laster."
        ),
        "applications": [
            "desktop_v2/src/pages/DoorsPage.tsx: henter bare Sun2-romlisten når Dør og soltime-listen faktisk vises.",
            "desktop_v2/scripts/smoke-routes.mjs: legger inn forventet innhold for /dorer/romkontroll.",
            "desktop_v2/scripts/smoke-ui.mjs: legger til realistiske mockdata for dørstatus, solrom, energivurdering og romkontroll.",
            "desktop_v2/scripts/smoke-live.mjs: bruker samme forventede innhold i live-smoke.",
            "build_log.py: dokumenterer build 1521.",
        ],
        "request": "Ta en runde på hele løsningen, bruk logisk sans og forbedre det som kan forbedres.",
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Romkontroll slipper nå ekstra kall til /api/hc3/doors/sunroom-sessions når siden bare trenger samlet romoversikt.",
            "Lokal smoke-test har nå egne dør- og romkontrollmockdata i stedet for generisk modulsvar.",
            "Smoke-testen kontrollerer at Romkontroll viser Rom 1, Forventet ut og Strøm OK.",
            "Live smoke ble kjørt med strengere innholdssjekk mot eksisterende produksjon før deploy.",
            "QNAP-status ble kontrollert; relevante containere og health-watch rapporterte OK.",
        ],
    },
    {
        "version": "1",
        "build": "1520",
        "date": "11.07.2026",
        "headline": "Tydeligere romkontroll",
        "title": "Gjør Romkontroll bredere, mer lesbar og mer komplett for solrom 1-12",
        "description": (
            "Build 1520 forbedrer Dører/Romkontroll visuelt. Rommene vises i to brede kolonner der kortene har mer "
            "plass til dørstatus, romstatus, valgt periode, tidslinje for dør og soltime, energivurdering "
            "og siste historikk."
        ),
        "applications": [
            "desktop_v2/src/pages/DoorsPage.tsx: deler romkortene opp i tydelige metrikker, tidslinje, Sun2-time, energiblokk og siste historikk.",
            "desktop_v2/src/styles/doors.css: endrer Romkontroll til to brede kolonner, rydder gamle regler og strammer responsive regler.",
            "build_log.py: dokumenterer build 1520.",
        ],
        "request": (
            "Gjør en enda bedre oversikt over rommene, gjerne bare 2 i bredden, og bruk god nok plass slik at alle "
            "data kan komme tydelig frem på Romkontroll-siden."
        ),
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Romkontroll viser nå normalt to brede kort i bredden i stedet for tre smale kort.",
            "Hvert romkort viser Dør nå, Romstatus og Valgt periode som egne tydelige felt.",
            "Tidslinjen viser Dør igjen, Betalt, Solstart, Sol slutt, Forventet ut og Dør opp i samme visuelle rad.",
            "Sun2-time og energivurdering er gjort mer lesbar med startavvik, netto effekt og samplegrunnlag.",
            "Siste historikk viser de to siste periodene direkte på kortet, slik at man slipper å åpne detaljsiden for rask kontroll.",
        ],
    },
    {
        "version": "1",
        "build": "1519",
        "date": "11.07.2026",
        "headline": "Romkontroll for solrom",
        "title": "Legger til samlet oversikt for rom 1-12 med dør, Sun2-time og strømindikasjon",
        "description": (
            "Build 1519 legger til Dører/Romkontroll. Siden viser rom 1-12 samlet med når døren gikk igjen og opp, "
            "koblet Sun2-time, forventet ut-tid og en energivurdering som forsøker å bekrefte at solsengen faktisk "
            "starter omtrent tre minutter etter betaling."
        ),
        "applications": [
            "main.py: legger til API for samlet romkontroll og energivurdering per Sun2-time.",
            "desktop_v2/src/api.ts: legger til typedata og klientkall for romkontroll.",
            "desktop_v2/src/queryKeys.ts: legger til cache-nøkkel for romkontroll.",
            "desktop_v2/src/moduleViews.ts: legger Romkontroll inn i Dører-menyen.",
            "desktop_v2/src/pages/DoorsPage.tsx: bygger ny romoversikt for rom 1-12.",
            "desktop_v2/src/styles/doors.css: styler kompakte romkort, status og energiblokk.",
            "tests/test_hc3_door_events.py: tester forventet ut-tid og energibekreftet 3-minutters start.",
            "build_log.py: dokumenterer build 1519.",
        ],
        "request": (
            "Lag en egen oversikt over rom 1-12 med data for når dør går igjen og opp, hvilken soltime som hører til, "
            "forventede tider og strømvurdering for å se om solen starter omtrent tre minutter etter betaling."
        ),
        "work_duration": "ca. 1 t 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Ny side /dorer/romkontroll med alle 12 solrom samlet.",
            "Romkort viser dørstatus, siste dørperiode, koblet soltime og forventet ut-tid.",
            "Energibloggen markerer ren måling, overlapp, startavvik eller bekreftet start.",
            "Periodevalg for siste 24 timer, 2 dager, 7 dager og 14 dager.",
        ],
    },
    {
        "version": "1",
        "build": "1518",
        "date": "11.07.2026",
        "headline": "Riktig forventet ut-tid for solrom",
        "title": "Skiller betalingstid, solstart, solslutt og forventet ut-tid i dør/soltime-visningen",
        "description": (
            "Build 1518 korrigerer forventet ut-tid på Dører/Dør og soltime. Sun2-start behandles som betalingstid, "
            "sengen starter etter tre minutter, betalt soltid løper derfra, og forventet ut-tid beregnes med normal "
            "utgangstid etter solslutt."
        ),
        "applications": [
            "main.py: beregner solstart, solslutt og forventet ut-tid separat for solromdører.",
            "desktop_v2/src/api.ts: eksponerer ny regel for normal utgangstid.",
            "desktop_v2/src/pages/DoorsPage.tsx: viser betaling, solstart, solslutt og forventet ut tydeligere.",
            "tests/test_hc3_door_events.py: legger test for beregningen betaling + oppstart + soltid + utgangstid.",
            "build_log.py: dokumenterer build 1518.",
        ],
        "request": (
            "Historikk på rom 4 viste rar forventning. En soltime-start er når timen betales, sengen starter tre "
            "minutter etter, betalt tid løper derfra, og kunden bruker normalt 1-3 minutter på å komme ut."
        ),
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Forventet ut er nå betalingstid + 3 min oppstart + betalt soltid + 3 min normal utgangstid.",
            "Oransje og rød grense vurderes mot solslutt, ikke mot teknisk vifteettergang.",
            "Historikken viser nå Betalt, Solstart og Slutt i soltimekolonnen.",
        ],
    },
    {
        "version": "1",
        "build": "1517",
        "date": "11.07.2026",
        "headline": "Romdetalj for dør og soltime",
        "title": "Gjør solromkort klikkbare og viser dørperioder mot Sun2-timer per rom",
        "description": (
            "Build 1517 gjør kortene i Dører/Dør og soltime klikkbare. Hvert solrom får en egen detaljvisning "
            "med pågående dørperiode, historiske lukke-/åpneperioder, koblet Sun2-time, forventet ut-tid og "
            "eventuelle soltimer som ikke har matchende dørperiode."
        ),
        "applications": [
            "main.py: legger til API for romhistorikk med dørperioder, Sun2-match og forventede tider.",
            "desktop_v2/src/api.ts: legger til typedata og klientkall for romdetalj.",
            "desktop_v2/src/queryKeys.ts: legger til cache-nøkkel for romdetalj.",
            "desktop_v2/src/pages/DoorsPage.tsx: gjør romkort klikkbare og viser pågående/historisk romdetalj.",
            "desktop_v2/src/styles/doors.css: styler romdetalj, nøkkeltall, pågående-rad og historikktabell.",
            "desktop_v2/src/styles/dark-theme.css: legger mørk-tema-støtte for romdetaljen.",
            "build_log.py: dokumenterer build 1517.",
        ],
        "request": (
            "Gjør kortene på oversiktssiden klikkbare. Når man går inn på et rom skal man se åpne/lukke-tidspunkter, "
            "soltimer og forventede tider ryddig, både pågående og historisk."
        ),
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Romkortene i /dorer/soltimer åpner nå /dorer/soltimer?room=rom-xx.",
            "Detaljvisningen viser pågående periode med dør lukket, koblet soltime og forventet ut-tid.",
            "Historikken viser dør lukket, dør åpnet, varighet, soltime, forventet ut og status.",
            "Soltimer uten matchende dørperiode listes separat for enklere feilsøking.",
        ],
    },
    {
        "version": "1",
        "build": "1516",
        "date": "11.07.2026",
        "headline": "Dør koblet mot soltime",
        "title": "Legger til egen solromvisning med Sun2-kobling, forventet ut-tid og dørvarsler",
        "description": (
            "Build 1516 kobler solromdører mot Sun2-enkelttimer. Visningen beregner forventet ut-tid fra "
            "soltime slutt pluss tre minutters vifteettergang, viser venter-/varselstatus når Sun2-data mangler "
            "eller kunden blir sittende etter timen, og publiserer røde dørvarsler på et samlet ntfy-tema."
        ),
        "applications": [
            "main.py: legger til API, beregning og bakgrunnsmonitor for solromdør mot Sun2-time.",
            "desktop_v2/src/api.ts: legger til typedata og klientkall for ny solromstatus.",
            "desktop_v2/src/pages/DoorsPage.tsx: legger til Dører/Dør og soltime med romkort, regler og varslingslenke.",
            "desktop_v2/src/styles/doors.css: styler ny solromvisning.",
            "desktop_v2/src/styles/dark-theme.css: gir ny visning mørk-tema-kontrast.",
            "desktop_v2/src/moduleViews.ts: legger ny underside inn i Dører-menyen.",
            "desktop_v2/scripts/smoke-routes.mjs: legger ny side inn i smoke-test.",
            "build_log.py: dokumenterer build 1516.",
        ],
        "request": (
            "Koble dør og enkelttime i en egen visning, ta hensyn til 3 min forsinket solstart og 3 min vifteettergang, "
            "vis forventet tidspunkt for å gå ut og varsle samlet når kunde er mer enn 10 min over."
        ),
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Ny underside /dorer/soltimer viser alle solrom med dørstatus, koblet Sun2-time og forventet ut-tid.",
            "Et rom venter inntil 5 minutter på Sun2-data før manglende soltime markeres.",
            "Oransje status brukes etter 5 minutter over forventet ut-tid, rød etter 10 minutter.",
            "Røde statusrom publiseres som samlet dørvarsel via ntfy med nedkjøling for å unngå varslingsspam.",
        ],
    },
    {
        "version": "1",
        "build": "1515",
        "date": "11.07.2026",
        "headline": "Polert ny døroversikt",
        "title": "Viser Fibaro10-navn i siste-endringer-listen på Oversikt - ny",
        "description": (
            "Build 1515 polerer den nye døroversikten ved å bruke de ryddige Fibaro10-navnene i listen over "
            "siste dørendringer. Dermed vises Solrom 4, Inngang og andre kjente dørtitler i stedet for tekniske "
            "HC3-navn der dette kan slås opp."
        ),
        "applications": [
            "desktop_v2/src/pages/DoorsPage.tsx: slår opp dørnavn for siste-endringer-listen på Oversikt - ny.",
            "build_log.py: dokumenterer build 1515.",
        ],
        "request": "Polering av den nye Dører/Oversikt - ny før ferdigstilling.",
        "work_duration": "ca. 5 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Siste-endringer-listen viser nå Fibaro10-tittel når dør-id finnes i konfigurasjonen.",
            "Tekniske HC3-navn brukes bare som fallback dersom døren ikke kan matches.",
        ],
    },
    {
        "version": "1",
        "build": "1514",
        "date": "11.07.2026",
        "headline": "Alternativ døroversikt",
        "title": "Legger til Dører/Oversikt - ny med statusmatrise og siste endringer",
        "description": (
            "Build 1514 legger inn en alternativ døroversikt ved siden av dagens visning. Den nye siden viser "
            "dørene som en driftsmatrise gruppert etter soner, med korte statusbrikker, stått-slik-varighet, "
            "siste endring med sekunder og en egen liste over siste statusendringer."
        ),
        "applications": [
            "desktop_v2/src/pages/DoorsPage.tsx: legger til visningen oversikt-ny og ny statusmatrise for dører.",
            "desktop_v2/src/styles/doors.css: styler statusmatrise, oppsummering og siste-endringer-listen.",
            "desktop_v2/src/styles/dark-theme.css: gir den nye døroversikten mørk-tema-kontrast.",
            "desktop_v2/src/moduleViews.ts: legger Oversikt - ny inn i dørmenyen.",
            "desktop_v2/scripts/smoke-routes.mjs: legger ny dørside inn i smoke-testen.",
            "build_log.py: dokumenterer build 1514.",
        ],
        "request": "Er det andre måter å vise oversikten over dører på? Lag et annet forslag og kall siden Oversikt - ny.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Ny underside /dorer/oversikt-ny viser dørene som en kompakt statusmatrise.",
            "Solrom grupperes etter avdeling, mens andre dører ligger i egen seksjon.",
            "Hver dør viser status, hvor lenge den har stått slik og eksakt tidspunkt for siste endring.",
            "Siste statusendringer vises i egen høyrekolonne for rask kontroll.",
        ],
    },
    {
        "version": "1",
        "build": "1513",
        "date": "11.07.2026",
        "headline": "Sekunder på dørhendelser",
        "title": "Viser døråpninger og dørstatus med sekundpresisjon",
        "description": (
            "Build 1513 gjør dør-API-et mer presist ved å sende full dato og klokkeslett med sekunder for "
            "råhendelser, siste statusendring og åpne/lukkeperioder. Oversikten kan dermed vise nøyaktig når "
            "en dør åpnet eller lukket, samtidig som varigheten fortsatt beregnes som før."
        ),
        "applications": [
            "main.py: bruker format_source_datetime for dørhendelser, siste endring og åpne/lukkeperioder.",
            "build_log.py: dokumenterer build 1513.",
        ],
        "request": "Er det mulig å få med sekunder for når dørene åpnes og lukkes?",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Dører/Oversikt viser siste statusendring med sekunder.",
            "Dører/Solrom og Dører/Andre dører viser åpnet/lukket-tidspunkt med sekunder.",
            "Dører/Rådata viser hendelsestidspunkt med sekunder.",
        ],
    },
    {
        "version": "1",
        "build": "1512",
        "date": "11.07.2026",
        "headline": "Ryddigere dÃ¸roversikt",
        "title": "Forenkler DÃ¸rer/Oversikt med tydelig status, siste endring og varighet",
        "description": (
            "Build 1512 rydder DÃ¸rer/Oversikt slik at hvert kort har samme faste struktur: dÃ¸rnavn, operativ "
            "status, hvor lenge dÃ¸ren har stÃ¥tt slik, tidspunkt for siste endring og sekundÃ¦r HC3-/batteriinfo. "
            "Dette gjÃ¸r oversikten raskere Ã¥ lese nÃ¥r mange solrom og byggdÃ¸rer er montert."
        ),
        "applications": [
            "desktop_v2/src/pages/DoorsPage.tsx: forenkler kortdata og markup for kompakt dÃ¸roversikt.",
            "desktop_v2/src/styles/doors.css: strammer opp kortlayout, tidspunktsfelter og metadatafelter.",
            "desktop_v2/src/styles/dark-theme.css: gir de nye status- og tidsfeltene riktig mÃ¸rk-tema-kontrast.",
            "build_log.py: dokumenterer build 1512.",
        ],
        "request": (
            "DÃ¸roversikten skal vÃ¦re ryddigere og enklere Ã¥ lese, med tydelig visning av nÃ¥r status pÃ¥ en dÃ¸r "
            "ble endret og hvor lenge den har stÃ¥tt i den posisjonen."
        ),
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjÃ¸ring",
        "changes": [
            "Kortene pÃ¥ DÃ¸rer/Oversikt viser nÃ¥ status, stÃ¥tt-slik-varighet og siste endring i faste felt.",
            "Solrom og andre dÃ¸rer beholder hver sin semantikk, men presenteres med samme leserytme.",
            "HC3-id og batteri er flyttet ned som sekundÃ¦re metadata slik at hovedstatusen blir tydeligere.",
            "MÃ¸rkt tema er oppdatert for de nye feltene.",
        ],
    },
    {
        "version": "1",
        "build": "1511",
        "date": "11.07.2026",
        "headline": "HC3-dører koblet til Fibaro10",
        "title": "Kobler monterte HC3-dørsensorer til Fibaro10 og klargjør per-dør-triggerne",
        "description": (
            "Build 1511 kobler de monterte magnetfølerne i HC3 til Dører-modulen i Fibaro10. Solrom 1 og "
            "Solrom 4-12, byggdørene og de tre eksisterende sensorene har nå faste device-id-er. Solrom 2 og "
            "Solrom 3 står fortsatt som klargjort fordi HC3 ikke rapporterer monterte doorSensor-enheter for dem."
        ),
        "applications": [
            "main.py: oppdaterer DOOR_SENSOR_CONFIG med faktiske HC3 device-id-er og legger inn Toalett/Vaktmesterlager som byggdører.",
            "scripts/upsert_hc3_single_door_logger_scenes.py: oppretter/oppdaterer en Lua-logger og en block-trigger per montert dør.",
            "scripts/hc3_door_event_logger.lua: utvider den manuelle statussyncen med alle monterte dørsensorer.",
            "docs/hc3-dorer.md: dokumenterer endelig dørkart, manglende Solrom 2/3 og installasjonsmodell.",
            "tests/test_hc3_door_events.py: tester at de monterte HC3-id-ene finnes i logger-script og upsert-script.",
            "build_log.py: dokumenterer build 1511.",
        ],
        "request": "Nå er sensorene for dørene montert, kan du fikse slik at det fungerer?",
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Fibaro10 viser monterte sensorer som koblet i stedet for klargjort der HC3-id finnes.",
            "HC3-oppsettet bruker én trigger-scene og én tynn logger-scene per dør, slik at en dørendring ikke leser alle dører.",
            "Solrom 2 og Solrom 3 blir stående som planlagte til HC3 får faktiske sensor-id-er.",
            "Toalett og Vaktmesterlager er tatt med fordi HC3 rapporterer dem som monterte doorSensor-enheter.",
        ],
    },
    {
        "version": "1",
        "build": "1510",
        "date": "10.07.2026",
        "headline": "Masterpassord i brukeradministrasjon",
        "title": "Master kan sette nytt masterpassord fra brukeradministrasjonen",
        "description": (
            "Build 1510 gjør masterbrukeren redigerbar i Admin/Brukere for passordbytte. Eksisterende "
            "masterpassord vises ikke, fordi master er lagret som hash. Når masterpassordet endres, oppdateres "
            "innloggingscookien i samme svar slik at aktiv masterøkt fortsetter å fungere."
        ),
        "applications": [
            "main.py: legger felles hash-hjelpere for master og vanlige brukere.",
            "main.py: API-et /api/admin/users/{id} tillater passordbytte for master, men låser navn, rolle og aktiv-status.",
            "main.py: brukertabellen viser passordstatus i stedet for hemmelige verdier.",
            "desktop_v2/src/pages/module/moduleTableUtils.tsx: masterraden kan åpnes i redigeringsdialogen.",
            "tests/test_access_keys.py: tester masterhash, vanlig brukerhash og at masterpassord ikke eksponeres.",
            "build_log.py: dokumenterer build 1510.",
        ],
        "request": "Legg inn slik at master kan endre passord eller se passord på masterbrukeren når man er logget inn som master.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Masterpassord kan settes på nytt via Admin -> Brukere.",
            "Eksisterende masterpassord vises ikke, siden det er lagret som hash og ikke kan leses tilbake.",
            "Etter passordbytte blir master fortsatt innlogget fordi cookien oppdateres med nytt passord.",
            "Vanlige brukere beholder eksisterende passordlogikk.",
        ],
    },
    {
        "version": "1",
        "build": "1509",
        "date": "10.07.2026",
        "headline": "Koble-kandidater strammet inn",
        "title": "Koble viser bare kandidater når samme bil og SUN2-ID har minst to ulike parkeringer",
        "description": (
            "Build 1509 rydder definisjonen av kandidat i Koble. Et enkelt sammenfall mellom en bil og en SUN2-ID "
            "innen tidsvinduet vises fortsatt som råtreff, men blir ikke kandidat eller konkurrerende alternativ før "
            "samme par har minst min_matches ulike parkeringer."
        ),
        "applications": [
            "main.py: kandidatfilter, kandidat-tellinger, kvalifiserte totaler og konkurranseberegning krever nå min_matches ulike parkeringer.",
            "main.py: historisk Koble-helper teller ulike parkeringer i stedet for bare antall soltimer.",
            "desktop_v2/src/pages/module/KobleReviewPanel.tsx: Koble-grensesnittet forklarer kandidatregelen og skiller enkelttreff fra kandidater.",
            "desktop_v2/src/api.ts: Koble-kontrakt utvidet med råtall for par/enkelttreff.",
            "tests/test_parking_sun_link_logic.py: regresjonstester for at ett parkeringstreff ikke blir kandidat.",
            "build_log.py: dokumenterer build 1509.",
        ],
        "request": (
            "Koble skal kreve sammenfall mellom at en bestemt bil kommer og at samme SUN2-ID starter soltime innen "
            "3 minutter etter ankomst minst to ganger. Ett treff skal ikke være kandidat."
        ),
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Kandidater, sterke kandidater, Biltreff og SUN2-kontroll filtreres på minst min_matches ulike parkeringer.",
            "Enkelttreff påvirker ikke lenger alternativtelling eller konkurrerende kandidat.",
            "Koble-oversikten viser nå enkelttreff som rågrunnlag, ikke som kandidater.",
            "Kandidatkort viser kvalifiserende parkeringer tydeligere.",
        ],
    },
    {
        "version": "1",
        "build": "1508",
        "date": "10.07.2026",
        "headline": "Parkering tidspunktanalyse",
        "title": "Ny parkeringsanalyse viser omsetning og parkeringstid per ukedag og starttidspunkt",
        "description": (
            "Build 1508 legger til en egen side under Parkering for tidsfordeling. Siden viser heatmap for "
            "ukedag og time, timeprofil, topp tidspunkt og snittberegninger for valgt periode."
        ),
        "applications": [
            "main.py: nytt API for parkeringsfordeling etter starttidspunkt, med periodevalg og snitt per dag/parkering.",
            "desktop_v2/src/pages/ParkingTimeDistributionPage.tsx: ny analyseflate for heatmap, nøkkeltall, timeprofil og tabeller.",
            "desktop_v2/src/api.ts og queryKeys.ts: frontend-kontrakter og henting for den nye siden.",
            "desktop_v2/src/moduleViews.ts og AppRoutes.tsx: nytt menyvalg og rute under Parkering.",
            "desktop_v2/src/styles/parking-time-distribution.css: kompakt design tilpasset eksisterende parkeringsprofil og mørkt tema.",
            "desktop_v2/scripts/smoke-routes.mjs og smoke-ui.mjs: ny side tatt inn i smoke-testgrunnlaget.",
            "build_log.py: dokumenterer build 1508.",
        ],
        "request": (
            "Jeg ønsker også på parkering å ha en side som viser parkeringstid og omsetningen fordelt på "
            "tidspunkt pr ukedag, med mulighet for å velge tidsperiode, denne mnd, dette året osv.. og utregning av snitt."
        ),
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Parkering får ny underside Tidspunkt.",
            "Perioder støtter denne måneden, dette året, siste 90 dager, forrige måned, i fjor og egendefinert datointervall.",
            "Heatmap viser 7 ukedager x 24 timer med valg mellom omsetning, parkeringstid, antall og snitt.",
            "Siden beregner totaler, snitt per dag, snitt per parkering, ukedagstabell og topp tidspunkt.",
            "Fordelingen er basert på starttidspunktet for parkeringen slik at salgsmønsteret blir tydelig.",
        ],
    },
    {
        "version": "1",
        "build": "1507",
        "date": "10.07.2026",
        "headline": "Koble-worker health",
        "title": "Koble-worker friskmelder seg etter forbigående oppstartsfeil",
        "description": (
            "Build 1507 retter en health-feil som ble synlig i etterkontroll av dokumentasjonsdeployen. "
            "Hvis Koble-worker startet før Fibaro10 var klar, ble oppstartsfeilen liggende i workerens egen "
            "health-status selv etter at den senere rapporterte ajour til Fibaro10."
        ),
        "applications": [
            "parking_sun_linker/app/main.py: vellykket statusrapport nullstiller stale last_error og setter last_success_at.",
            "tests/test_parking_sun_linker.py: legger regresjonstest for oppstartsfeil som ryddes ved senere ajour-status.",
            "build_log.py: dokumenterer build 1507.",
        ],
        "request": "Etter deploy-kontroll viste Koble-worker ok=false selv om Fibaro10 var frisk. Dette ble rettet før avslutning.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Koble-worker health blir nå grønn igjen når worker faktisk får rapportert en vellykket status.",
            "Forbigående connection refused ved containeroppstart blir ikke hengende som permanent feil.",
            "Regresjonstest dekker at en gammel last_error fjernes når statusrapporten lykkes.",
        ],
    },
    {
        "version": "1",
        "build": "1506",
        "date": "10.07.2026",
        "headline": "Dokumentasjon ajourført",
        "title": "Dokumentasjon, systemkart og utviklingsoppsett er synket mot faktisk drift",
        "description": (
            "Build 1506 er en helhetlig dokumentasjonsrunde. Repo-dokumentene, den levende manualstrukturen og "
            "systemkartet er kontrollert mot dagens Docker-compose, Caddy-oppsett, importjobber, hovedmeny og "
            "underapper."
        ),
        "applications": [
            "docs/README.md: oppdatert dokumentasjonsindeks og levende dokumentasjon i appen.",
            "docs/systemoversikt.md: ny samlet systemoversikt for komponenter, webflater, proxy, datakilder, backup og kvalitetssjekk.",
            "docs/desktop-v2.md og docs/funksjonsstruktur.md: dokumenterer faktisk V2-meny, ruter og funksjonsdeling.",
            "docs/api-kontrakter.md: dokumenterer sentrale backend/frontend-kontrakter og buildlogg-splitt.",
            "docs/utviklingsoppsett.md og docs/gjennomgang_2026-05-23.md: oppdatert mot dagens deploy-, backup- og adminstruktur.",
            "docs/owntracks-http.md, docs/axis-camera-snapshots.md, docs/car-info-oppslag.md, docs/roborock*.md, docs/hc3-*.md og docs/sun2-enkeltimer.md: oppdatert dato og driftsdetaljer.",
            "maintenance_mobile/README.md og parking_sun_linker/README.md: dokumenterer underappene som kjører ved siden av Fibaro10.",
            "system_inventory.py: korrigerer runtime/URL for online dashboard, EasyPark og SUN2-importverktøy.",
            "v2_navigation.py: kompletterer backendtitler for Dashboard, Dører, Mobil og Vedlikehold/Besøk.",
            "build_log.py: dokumenterer build 1506.",
        ],
        "request": "Du ba om en helhetlig sjekk av alt slik at all dokumentasjon er oppdatert.",
        "work_duration": "ca. 1 time",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Dokumentasjonsindeksen peker nå til dagens Admin -> Manual, Systemkart, Datakilder, Buildlogg og Teknisk.",
            "Systemoversikten viser dagens QNAP-tjenester, Caddy-domener, lokale webflater og alle 22 datakilder.",
            "Desktop-dokumentasjonen beskriver dagens menystruktur uten gamle V1/V2-prefix-antakelser.",
            "Utviklingsoppsettet dokumenterer dagens deployløp, live-smoke, backup, restore-test og V1-referanse som isolert historikk.",
            "Axis-dokumentasjonen peker nå på arkivvolum via AXIS_HOST_SNAPSHOT_DIR, og Roborock er dokumentert som egen webflate.",
            "Underappene vedlikehold mobil og Koble worker har nå egne README-er med formål, drift og avhengigheter.",
            "Admin/Systemkart får mer presis informasjon om hvilke tjenester som faktisk kjører som containere.",
        ],
    },
    {
        "version": "1",
        "build": "1505",
        "date": "09.07.2026",
        "headline": "Koble-totaler raskere",
        "title": "Koble beregner soltreff-totaler med database-join i stedet for stor IN-liste",
        "description": (
            "Build 1505 fortsetter ytelsesrunden fra 1504. Koble-oversikt og Koble-undersider beregner naa "
            "parkert ved soltreff direkte i databasen, uten aa hente eller sende hele listen med kvalifiserte par "
            "inn i totalberegningen."
        ),
        "applications": [
            "main.py: legger til join-basert totalberegning for kvalifisert parkering ved soltreff.",
            "main.py: fjerner gammel ubrukt Koble-totalfunksjon med stor IN-liste.",
            "build_log.py: dokumenterer build 1505.",
        ],
        "request": "Du ba om aa sorge for at ytelsen er saa bra som mulig.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Koble-totalen for parkert ved soltreff regnes naa via join mellom kandidater og treff.",
            "API-et slipper aa bygge stor liste med alle kvalifiserte bil/SUN2-par for totalberegning.",
            "Synlige Koble-rader henter fortsatt parvise belop for de radene som faktisk vises.",
        ],
    },
    {
        "version": "1",
        "build": "1504",
        "date": "09.07.2026",
        "headline": "Ytelsesoptimalisering",
        "title": "API-payloads trimmes for raskere admin og Koble-visninger",
        "description": (
            "Build 1504 er en maalrettet ytelsesrunde etter live maaling av API-storrelser og svartider. "
            "Endringen reduserer unodvendig data i buildloggen og lar Koble-tabeller respektere valgt antall rader, "
            "samtidig som totaler fortsatt beregnes paa komplett grunnlag."
        ),
        "applications": [
            "api_contracts.py og build_log.py: bruker en lett buildliste for /api/admin/builds og beholder full detalj paa enkeltbuild.",
            "api_types.py og desktop_v2/src/api.ts: skiller mellom buildliste og builddetalj i kontraktene.",
            "desktop_v2/src/pages/BuildLogPage.tsx: bruker den smalere buildliste-typen.",
            "main.py: begrenser Koble-detaljrader etter valgt Antall uten aa endre totalberegningene.",
            "build_log.py: dokumenterer build 1504.",
        ],
        "request": "Du ba om aa sorge for at ytelsen er saa bra som mulig.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Buildlogg-listen sender naa bare dato, build, overskrift, path og aktiv-markering.",
            "Builddetaljer hentes fortsatt separat med hele bestillingen, endringslisten og applikasjonslisten.",
            "Koble/treffgrunnlag sender ikke lenger flere rader enn valgt Antall.",
            "Koble/biltreff og Koble/SUN2 sender bare viste detaljrader, mens korttotaler fortsatt regnes paa hele kvalifiserte grunnlaget.",
        ],
    },
    {
        "version": "1",
        "build": "1503",
        "date": "09.07.2026",
        "headline": "Funksjonsgjennomgang",
        "title": "Full funksjonssjekk retter mobil-preview og reduserer Koble-payload",
        "description": (
            "Build 1503 er en systematisk funksjonsgjennomgang av Fibaro10 etter designoppryddingen. "
            "Gjennomgangen avdekket at mobil-preview kunne vise omsetningsskjermer til brukere uten belopstilgang, "
            "og at Koble-oversikten sendte store datasett som bare trengs paa undersidene."
        ),
        "applications": [
            "main.py: filtrerer mobil-preview-skjermer etter faktisk tilgang til omsetning og beskytter direkte frame-kall.",
            "main.py: deler Koble-data per underside slik at oversikt, kandidater, biltreff, SUN2-kontroll, treffgrunnlag og jobb ikke laster unodvendige tabeller.",
            "desktop_v2/scripts/smoke-live.mjs: fanger naa ogsaa 4xx-feil i live smoke-testen, ikke bare 5xx.",
            "tests/test_mobile_preview.py: legger testdekning for mobil-preview-tilgang.",
            "build_log.py: dokumenterer build 1503.",
        ],
        "request": "Du ba om en grundig gjennomgang av all funksjonalitet.",
        "work_duration": "ca. 50 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Mobil-preview viser ikke lenger omsetningsframes for brukere som ikke har belopstilgang.",
            "Koble-oversikten sender betydelig mindre data og laster bare detaljer paa de relevante undersidene.",
            "Live-smoke er skjerpet slik at skjulte 403/404-feil i API/frames blir fanget opp.",
            "Full lokal kvalitetssjekk er kjort med 104 Python-tester, frontend-build, OwnTracks-build, CSS, bundle, route-audit og UI-smoke.",
        ],
    },
    {
        "version": "1",
        "build": "1502",
        "date": "09.07.2026",
        "headline": "Helhetlig appdesign",
        "title": "Hovedappen får dashboard-inspirert designsystem på tvers av modulene",
        "description": (
            "Build 1502 viderefører uttrykket fra dashboardkortene til resten av Fibaro10. "
            "Felles panel-, tabell-, filter-, chart-, modal- og nøkkeltallsflater bruker nå samme tokens for "
            "dybde, aksent, borders, hover og mørkt tema."
        ),
        "applications": [
            "desktop_v2/src/styles/tokens.css og dark-theme.css: utvider designsystemet med generiske panel-, tabell- og portal-tokens.",
            "desktop_v2/src/styles/layout.css: strammer globale AntD-kort, tabeller, tabs, pagination, alerts og modaler.",
            "desktop_v2/src/styles/module-content.css, module-metrics.css, module-filters.css og module-charts.css: gir modulsider samme kort-, filter- og chartuttrykk som dashboard.",
            "desktop_v2/src/styles/records.css, status-comparison.css, doors.css, energy.css, maintenance.css og ideas.css: harmoniserer lokale detalj-, tabell- og summary-flater.",
            "build_log.py: dokumenterer build 1502.",
        ],
        "request": "Du ønsket en grundig forbedring av design i hele appen med utgangspunkt i designet på dashboard.",
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Felles kort og modulkort har nå samme dashboard-inspirerte flate, aksent og skyggenivå.",
            "Tabeller, filterlinjer, chartverktøylinjer og tomtilstander er gjort mer kompakte og konsekvente.",
            "Dører, energi, vedlikehold, ideer og sammenligningssider er harmonisert mot samme designsystem.",
            "Mørkt tema og portaler/modaler bruker samme paneltokens som resten av appen.",
        ],
    },
    {
        "version": "1",
        "build": "1501",
        "date": "09.07.2026",
        "headline": "Mørke inputfelt",
        "title": "Mørkt tema får lesbare AntD-felt i innstillingsskjema",
        "description": (
            "Build 1501 retter en kontrastfeil som ble synlig i visuell kontroll av CSS-oppryddingen. "
            "Indre AntD-felt for tall, tid og valg får nå eksplisitt tekstfarge i mørkt tema, også i dropdowns og portaler."
        ),
        "applications": [
            "desktop_v2/src/styles/dark-theme.css: setter tekstfarge for InputNumber, Date/TimePicker og Select sine indre felt i mørkt tema.",
            "build_log.py: dokumenterer build 1501.",
        ],
        "request": "Oppfølgende visuell kvalitetssjekk etter CSS-gjennomgangen avdekket for mørke feltverdier i mørkt tema.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Tall- og tidsfelt i mørkt tema er gjort lesbare.",
            "Select- og picker-verdier følger samme teksttoken som øvrig mørkt tema.",
            "CSS parse og frontend-produksjonsbuild er kontrollert etter rettingen.",
        ],
    },
    {
        "version": "1",
        "build": "1500",
        "date": "09.07.2026",
        "headline": "CSS-opprydding",
        "title": "Hovedappen får strammere tokens og mer konsistent mørkt tema",
        "description": (
            "Build 1500 rydder i CSS-laget i hovedappen. Gjentatte overflate-, skygge- og statusfarger er flyttet "
            "til felles tokens, og aktive flater som dashboard, oppgjør, tidslinjer, ventilasjon og bildemodaler bruker "
            "samme stilgrunnlag i lys og mørk visning."
        ),
        "applications": [
            "desktop_v2/src/styles/tokens.css: utvider designsystemet med tokens for glassflater, svake linjer, highlights, skygger og statusfarger.",
            "desktop_v2/src/styles/dark-theme.css: kobler mørkt tema til samme tokens og reduserer gjentatte lokale alpha-farger.",
            "desktop_v2/src/styles/layout.css og app-shell.css: normaliserer AntD-kort, knapper, tabeller, toppfelt og venstremeny mot tokens.",
            "desktop_v2/src/styles/status-periods.css og status-overview.css: samler dashboardkort og sammenligningsfarger rundt status- og flate-tokens.",
            "desktop_v2/src/styles/records-settlements.css, sun-settlements.css og settlement-detail.css: rydder oppgjørsflater og dokumentkort.",
            "desktop_v2/src/styles/sun-timeline.css, parking-timeline.css og ventilation-charts.css: normaliserer tidslinje- og markørskygger.",
            "build_log.py: dokumenterer build 1500.",
        ],
        "request": "Du ønsket en grundig gjennomgang av CSS.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Hardkodede farger i CSS-auditen ble redusert fra 249 til 166 uten å endre hovedlayout.",
            "Mørkt tema bruker nå samme status- og overflate-tokens som lys variant.",
            "Dashboard, oppgjør, tidslinjer, ventilasjonsmarkører og bildemodaler har mer konsistent skygge- og panelbruk.",
            "CSS parse, CSS audit og produksjonsbuild er kontrollert etter oppryddingen.",
        ],
    },
    {
        "version": "1",
        "build": "1499",
        "date": "09.07.2026",
        "headline": "Lysinnstillinger i V2",
        "title": "Lys/innstillinger får direkte redigering av regler og grenser",
        "description": (
            "Build 1499 løfter lysstyringens gamle regel- og innstillingsskjema inn i V2. "
            "Siden viser nå aktiv versjon, oppsummering av gjeldende regler, redigerbare luxgrenser, driftstider, "
            "lagrenotat, forklaring og historikk uten å gå via klassisk skjema."
        ),
        "applications": [
            "main.py: eksponerer controlSettings for Lys/innstillinger og gjør siden til en ren innstillingsflate.",
            "desktop_v2/src/api.ts: legger til typekontrakt for generiske styringsinnstillinger.",
            "desktop_v2/src/pages/module/ControlSettingsPanel.tsx: ny redigeringsflate for config-grupper, regler og historikk.",
            "desktop_v2/src/pages/ModulePage.tsx: viser controlSettings-panelet på relevante modulsider.",
            "desktop_v2/src/styles/module-content.css: styling for den nye innstillingsflaten.",
            "build_log.py: dokumenterer build 1499.",
        ],
        "request": (
            "Du fant ikke grensesnittet for å endre regler og settinger under Lys/innstillinger og ønsket dette tilbake."
        ),
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Lys/innstillinger viser nå redigerbare felt for driftstid, bekreftelsestid og luxgrenser.",
            "Aktive lysregler vises som en ryddig tabell før skjemaet.",
            "Endringer lagres mot samme /api/config/lights som HC3-runneren leser.",
            "Dagsgraf og gamle klassiske verktøyrader er tatt bort fra innstillingssiden.",
        ],
    },
    {
        "version": "1",
        "build": "1498",
        "date": "09.07.2026",
        "headline": "Solhøyde i lysgraf",
        "title": "Lys/dagslogg viser solhøyde sammen med lux og skydekke",
        "description": (
            "Build 1498 legger inn beregnet solhøyde for Lilletorget i Dagslogg lys. Grafen starter nå med Lux, "
            "Skydekke og Solhøyde aktivert, slik at lux-nivå kan vurderes mot både skydekke og hvor høyt solen står."
        ),
        "applications": [
            "solar_position.py: ny isolert beregning av solhøyde basert på tidspunkt og koordinater.",
            "main.py: legger Solhøyde inn som egen serie i Lys/dagslogg.",
            "desktop_v2/src/pages/module/ModuleChartPanel.tsx: gjør høyre akse korrekt når blandede enheter vises.",
            "tests/test_solar_position.py: tester solhøyde for Lillehammer sommer, vinter og natt.",
            "build_log.py: dokumenterer build 1498.",
        ],
        "request": "Du ønsket en graf som viser hvor høyt solen står på himmelen sammen med lysdataene.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Solhøyde beregnes for valgt døgn med 10-minutters punkter.",
            "Solhøyde vises i grader og klippes til 0 når solen er under horisonten.",
            "Lux, Skydekke og Solhøyde er alle aktivert som standard på Lys/dagslogg.",
            "Høyre akse viser nøytral Vær / sol-etikett når prosent og grader ligger på samme akse.",
        ],
    },
    {
        "version": "1",
        "build": "1497",
        "date": "09.07.2026",
        "headline": "Luxgraf forenklet",
        "title": "Lys/dagslogg starter med Lux og Skydekke direkte i grafen",
        "description": (
            "Build 1497 fjerner segmentvalgene ved datovelgeren på Lys/dagslogg. Grafen viser nå Lux og Skydekke "
            "som ordinære serier med begge aktivert som standard, slik at av/på styres fra grafens egen forklaring."
        ),
        "applications": [
            "main.py: forenkler Dagslogg lys til Lux og Skydekke som standardserier.",
            "build_log.py: dokumenterer build 1497.",
        ],
        "request": (
            "Du ønsket å fjerne valgene på linjen med datovelgeren, la Lux og Skydekke styres fra grafen, "
            "og starte med begge aktivert."
        ),
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Segmentknappene på grafverktøylinjen for Lys/dagslogg fjernes.",
            "Lux og Skydekke vises samtidig som standard.",
            "Skydekke beholder høyre prosentakse.",
        ],
    },
    {
        "version": "1",
        "build": "1496",
        "date": "09.07.2026",
        "headline": "Skydekke i luxgraf",
        "title": "Lys/dagslogg kan vise Yr-skydekke sammen med lux",
        "description": (
            "Build 1496 legger skydekke fra Yr-loggen inn som et tilleggsvalg på Lys/dagslogg. "
            "Grafen kan nå vise lux og skydekke samtidig med separat høyre prosentakse, slik at sammenhengen "
            "mellom dagslys/lux og skydekke kan vurderes direkte."
        ),
        "applications": [
            "main.py: henter skydekke fra yr_forecast_samples og legger til grafvalget Lux + skydekke.",
            "desktop_v2/src/pages/module/ModuleChartPanel.tsx: støtter sekundær Y-akse for prosentserier.",
            "build_log.py: dokumenterer build 1496.",
        ],
        "request": (
            "Du ønsket skydekke-data fra Ventilasjon/Yr-logg som tilleggsvalg på Lys/dagslogg, slik at dette "
            "kan vises sammen med lux-grafen."
        ),
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Nytt grafvalg: Lux + skydekke.",
            "Skydekke hentes fra Yr-samples for valgt dag.",
            "Lux vises på venstre akse og skydekke på høyre akse i prosent.",
        ],
    },
    {
        "version": "1",
        "build": "1495",
        "date": "09.07.2026",
        "headline": "Dørikoner ryddet",
        "title": "Dørstatus får egne semantiske symboler uten overlapp",
        "description": (
            "Build 1495 legger inn egne SVG-symboler for dørstatus. Solrom viser tydelig ledig eller i bruk, "
            "mens øvrige dører viser normaltilstand eller avvik. Ikonene er bygget uten tekst inne i symbolet, "
            "og kortene har fått fast ikonkolonne slik at lange navn og statustekster ikke skriver oppå hverandre."
        ),
        "applications": [
            "desktop_v2/src/pages/DoorsPage.tsx: erstatter generiske låsikoner med semantiske dørikoner.",
            "desktop_v2/src/styles/doors.css: legger fast ikonlayout og SVG-styling for lys visning.",
            "desktop_v2/src/styles/dark-theme.css: gir ikonene riktig kontrast i mørkt tema.",
            "build_log.py: dokumenterer build 1495.",
        ],
        "request": (
            "Du likte retningen på forslag C, men ville at det skulle bygges riktig uten at tekst eller symboler "
            "skriver oppå hverandre."
        ),
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Solrom får egne symboler for ledig og i bruk.",
            "Andre dører får egne symboler for normaltilstand og avvik.",
            "Kompakte dørkort bruker nå fast ikonkolonne og separat tekstkolonne.",
            "Symbolene følger både lyst og mørkt tema uten ekstra bildefiler.",
        ],
    },
    {
        "version": "1",
        "build": "1494",
        "date": "09.07.2026",
        "headline": "Dører visuelt løftet",
        "title": "Dørseksjonen får et mer helhetlig dashboard-inspirert design",
        "description": (
            "Build 1494 oppfrisker alle Dører-sidene med samme visuelle prinsipper som hoveddashboardet: "
            "roligere paneler, tydeligere statusstripe, mer presise kortflater, bedre tabeller og mørkt-tema-dekning."
        ),
        "applications": [
            "desktop_v2/src/pages/DoorsPage.tsx: gir gruppe- og tabellkort felles panelklasse.",
            "desktop_v2/src/styles/doors.css: oppgraderer kort, paneler, statusruter, historikk og tabeller.",
            "desktop_v2/src/styles/dark-theme.css: legger inn mørkt-tema-støtte for det nye dørdesignet.",
            "build_log.py: dokumenterer build 1494.",
        ],
        "request": (
            "Du ønsket å oppfriske designet på alle Dører-sidene og pekte på at uttrykket på hoveddashboardet "
            "hadde blitt ganske bra."
        ),
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Dører/Oversikt, Solrom, Andre dører og Rådata bruker nå et mer konsistent paneluttrykk.",
            "Statuskortene har fått dashboard-inspirert toppstripe, lettere flater og bedre hover.",
            "Tabellene for døråpninger og rådata har fått strammere hoder og roligere radmarkering.",
            "Mørkt tema har fått egne overstyringer for dørpaneler og dørkort.",
        ],
    },
    {
        "version": "1",
        "build": "1493",
        "date": "09.07.2026",
        "headline": "Døroversikt strammet",
        "title": "Dører/Oversikt får bredere statusruter og fjerner detaljtabellen",
        "description": (
            "Build 1493 justerer den kompakte dørstatusen etter praktisk bruk. Statusrutene på oversikten er gjort "
            "bredere slik at innholdet får bedre plass, og tabellen Døråpninger er fjernet fra oversikten."
        ),
        "applications": [
            "desktop_v2/src/pages/DoorsPage.tsx: skjuler Døråpninger-tabellen på Dører/Oversikt.",
            "desktop_v2/src/styles/doors.css: øker minimumsbredden på kompakte dørkort.",
            "build_log.py: dokumenterer build 1493.",
        ],
        "request": (
            "Du ønsket bredere kort på Dører/Oversikt og foreslo å fjerne feltet nederst med Døråpninger, "
            "siden detaljene kan ses via Solrom eller Andre dører."
        ),
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Statusrutene på oversikten bruker nå bredere gridkolonner.",
            "Døråpninger vises ikke lenger på Dører/Oversikt.",
            "Døråpninger beholdes på Solrom og Andre dører for detaljkontroll.",
        ],
    },
    {
        "version": "1",
        "build": "1492",
        "date": "09.07.2026",
        "headline": "Døroversikt komprimert",
        "title": "Dører/Oversikt blir en kompakt statusflate for solrom og øvrige dører",
        "description": (
            "Build 1492 gjør Dører/Oversikt om til en rask statusflate. Solrom tolkes operativt som ledig eller "
            "i bruk basert på om døren er åpen eller lukket, mens øvrige dører farges etter normaltilstand eller avvik."
        ),
        "applications": [
            "desktop_v2/src/pages/DoorsPage.tsx: legger til egen kompakt oversiktskomponent for dører.",
            "desktop_v2/src/styles/doors.css: legger til tett statusgrid med kontekststyrte farger.",
            "build_log.py: dokumenterer build 1492.",
        ],
        "request": (
            "Du ønsket en mye mer kompakt Dører/Oversikt der man raskt ser om døren er åpen eller lukket, "
            "med rød lukket/grønn åpen for solrom og motsatt eller normalbasert visning for andre dører."
        ),
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Dører/Oversikt viser nå små statusruter i stedet for store detaljkort.",
            "Solrom viser I bruk når døren er lukket og Ledig når døren er åpen.",
            "Andre dører viser grønt ved normaltilstand og rødt ved avvik.",
            "Sist endret ligger fortsatt synlig, men som kompakt sekundærinformasjon.",
        ],
    },
    {
        "version": "1",
        "build": "1491",
        "date": "09.07.2026",
        "headline": "Dørkort ryddet",
        "title": "Dørkortene får mer hensiktsmessig statusinformasjon",
        "description": (
            "Build 1491 rydder opp i dørkortene. Den gamle raden med likeverdige felter for siste endring, siden, "
            "batteri, normal og sensor er erstattet med en tydelig sist-endret-blokk og kompakte metadatachips."
        ),
        "applications": [
            "desktop_v2/src/pages/DoorsPage.tsx: erstatter dørkortets tekniske feltgrid med DoorStatusFacts.",
            "desktop_v2/src/styles/doors.css: ny kompakt layout for sist endret, batteri, normaltilstand og HC3-id.",
            "build_log.py: dokumenterer build 1491.",
        ],
        "request": (
            "Du pekte på at feltene siste endring, siden, batteri, normal og sensor på dørkortene var lite "
            "hensiktsmessig designet."
        ),
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Sist endret vises nå som primær informasjon med tidspunkt og alder samlet.",
            "Batteri, normaltilstand og HC3-id vises som kompakte chips.",
            "Klargjorte sensorer uten HC3-id har egen enkel oppsettflate.",
        ],
    },
    {
        "version": "1",
        "build": "1490",
        "date": "09.07.2026",
        "headline": "Dører klargjort",
        "title": "Fibaro10 klargjør solrom og øvrige dører før nye HC3-sensorer monteres",
        "description": (
            "Build 1490 legger inn alle planlagte dører i Fibaro10 før sensorene har fått HC3-id. Solrommene er "
            "samlet som egen visning og delt i 1.etg, 2.etg og VIP, mens øvrige dører ligger samlet under Andre dører."
        ),
        "applications": [
            "main.py: utvider dørkonfigurasjonen med 12 solrom og fire planlagte bygningsdører uten HC3-id.",
            "main.py: gjør dørstatus-API-et robust for planlagte sensorer og eksponerer gruppe, avdeling og normaltilstand.",
            "desktop_v2/src/pages/DoorsPage.tsx: legger inn egne visninger for Oversikt, Solrom, Andre dører og Rådata.",
            "desktop_v2/src/styles/doors.css: kompakterer dørkort og markerer planlagte sensorer tydelig.",
            "desktop_v2/src/api.ts og desktop_v2/src/moduleViews.ts: oppdaterer frontend-kontrakt og undermeny.",
            "build_log.py: dokumenterer build 1490.",
        ],
        "request": (
            "Du ønsket å forberede dørgrensesnittet for 12 solrom, de tre eksisterende dørene og Inngang, "
            "Massasjestudio, Vaskerom og Papirlager. Du presiserte også avdelingene for solrom 1-12."
        ),
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Solrom 1, 2, 3 og 9 ligger under 1.etg.",
            "Solrom 4, 5, 6, 7 og 8 ligger under 2.etg.",
            "Solrom 10, 11 og 12 ligger under VIP.",
            "Nye sensorer uten HC3-id vises som Klargjort i Fibaro10.",
            "Når du gir HC3 device-id senere, trenger vi bare å koble id-en mot eksisterende nøkkel og kjøre HC3-installer på nytt.",
        ],
    },
    {
        "version": "1",
        "build": "1489",
        "date": "09.07.2026",
        "headline": "Tynne dørloggere",
        "title": "Fibaro10 forbereder en dørlogger per HC3-sensor",
        "description": (
            "Build 1489 legger grunnlaget for å erstatte modellen der én dørendring leser alle dører. Det er laget "
            "et HC3-installasjonsscript som oppretter én liten Lua-logger per eksisterende dør. Disse er beregnet "
            "for å startes fra hver sin HC3 block scene, slik at hver hendelse sender bare aktuell dør til Fibaro10."
        ),
        "applications": [
            "scripts/upsert_hc3_single_door_logger_scenes.py: nytt installer-script for tynne Lua-logger-scener per dør.",
            "docs/hc3-dorer.md: dokumenterer anbefalt modell med én block scene og én logger per dør.",
            "docs/README.md: lenker inn ny dørdokumentasjon og installer-script.",
            "scripts/check-local.ps1: tar med det nye HC3-scriptet i Python syntakssjekk.",
            "build_log.py: dokumenterer build 1489.",
        ],
        "request": (
            "Du ba om å bygge om oppsettet for de tre eksisterende dørene først, slik at vi kan teste stabilitet før "
            "de 16 nye dørene legges inn."
        ),
        "work_duration": "ca. 40 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Ny installer kan opprette scenene Dorlogger 453, Dorlogger 447 og Dorlogger 413 i HC3.",
            "Hver genererte Lua-scene har hardkodet device_id, device_key og navn, og poster bare sin egen sensor.",
            "Payloaden merkes med trigger_model=block_scene_per_door for enklere feilsøking i rådata.",
            "Scriptet skriver scene-map med hvilke logger-scener block-scenene skal starte.",
            "Den gamle felles dørloggeren beholdes som manuell sync/test, ikke som ønsket fast trigger ved 19 dører.",
        ],
    },
    {
        "version": "1",
        "build": "1488",
        "date": "09.07.2026",
        "headline": "Dørhistorikk i kort",
        "title": "Fibaro10 viser siste åpninger direkte på dørkortene",
        "description": (
            "Build 1488 gjør Dører/Oversikt mer nyttig når flere magnetfølere legges inn. Hvert dørkort viser nå "
            "de to siste åpne/lukke-periodene med åpnet tidspunkt, lukket tidspunkt og hvor lenge døren stod åpen. "
            "HC3-scriptet er samtidig gjort enklere å utvide, slik at manuell statussync bruker den samme "
            "dørlisten som de automatiske triggerne."
        ),
        "applications": [
            "main.py: grupperer de siste åpne/lukke-periodene per dør og sender recentPeriods i status-API-et.",
            "desktop_v2/src/api.ts: utvider dørkontrakten med recentPeriods.",
            "desktop_v2/src/pages/DoorsPage.tsx: viser siste to åpninger inne i hvert dørkort.",
            "desktop_v2/src/styles/doors.css: gjør dørkortene mer skalerbare og legger til kompakt historikkstyling.",
            "scripts/hc3_door_event_logger.lua: bruker konfigurert enhetsliste også ved manuell statussync.",
            "build_log.py: dokumenterer build 1488.",
        ],
        "request": (
            "Du ba om at dørboksene viser de to siste hendelsene, både åpnet og lukket samt hvor lenge døren var "
            "åpen, og om vurdering av hvordan 16 nye dører bør trigge HC3-scriptet."
        ),
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Hvert dørkort viser nå siste to åpne/lukke-perioder i en kompakt historikkdel.",
            "Pågående åpninger vises med lukket-status 'Åpen nå' og løpende varighet.",
            "Status-API-et henter et større rågrunnlag når flere dører finnes, slik at historikken ikke forsvinner for stille sensorer.",
            "Dørkort-gridet bruker automatisk kolonnebredde og tåler flere dører bedre.",
            "HC3 Lua-scenen krever fortsatt bare én felles scene; automatisk trigger sender bare endret sensor.",
        ],
    },
    {
        "version": "1",
        "build": "1487",
        "date": "08.07.2026",
        "headline": "CSS-konsolidering",
        "title": "Fibaro10 optimaliserer status- og mørktema-CSS",
        "description": (
            "Build 1487 rydder CSS etter dashboardendringene. Statusvisningene bruker nå færre separate CSS-lag, "
            "mørkt tema har mer felles fargetokens, og gamle periodkort-regler som ikke lenger brukes er fjernet."
        ),
        "applications": [
            "desktop_v2/src/pages/OverviewPage.tsx: fjerner import av et separat status-refinement-lag.",
            "desktop_v2/src/styles/status-widgets.css: tar inn de faktiske status-widget-verdiene direkte.",
            "desktop_v2/src/styles/status-overview.css: fjerner ubrukte regler for gamle ikke-revenue periodkort.",
            "desktop_v2/src/styles/status-periods.css: forenkler selectors for dagens felles periodekort.",
            "desktop_v2/src/styles/dark-theme.css: tokeniserer gjentatte mørktema-farger og fjerner døde periodkort-overstyringer.",
            "build_log.py: dokumenterer build 1487.",
        ],
        "request": "Du ba om å optimalisere CSS på nytt.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Slettet status-refinements.css og flyttet relevante regler inn i status-widgets.css.",
            "Reduserte antall CSS-filer som OverviewPage laster fra 5 til 4 for statusdelen.",
            "Fjernet ubrukte selectors for gamle status-periodkort som ikke lenger finnes i dashboardene.",
            "Reduserte hardkodede CSS-farger i audit fra 282 til 244 ved å bruke felles mørktema-tokens.",
            "Reduserte status-overview.css fra 422 til 397 linjer og status-periods.css fra 649 til 644 linjer.",
        ],
    },
    {
        "version": "1",
        "build": "1486",
        "date": "08.07.2026",
        "headline": "Like dashboardkort",
        "title": "Fibaro10 gjør parkering- og solingdashboard like omsetningsdashboardet",
        "description": (
            "Build 1486 gjør dashboardene for parkering og soling mer konsekvente med omsetning. De bruker nå samme "
            "firekort-struktur, samme interne oppbygning og samme kompakte sammenligningsflate, med antall som hovedtall."
        ),
        "applications": [
            "desktop_v2/src/pages/OverviewPage.tsx: bygger parkering- og solingkortene med samme struktur som omsetningskortene.",
            "desktop_v2/src/styles/status-periods.css: fjerner lavere spesialhøyde for aktivitetskort og legger til omsetningsmarkør i kortstripen.",
            "build_log.py: dokumenterer build 1486.",
        ],
        "request": "Du ba om å endre dashboard parkering og soling så de blir som omsetning.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Parkering og soling viser nå bare de fire periodekortene, slik omsetningsdashboardet gjør.",
            "De ekstra boksene med siste hendelse og arbeidsflater er tatt bort fra disse to dashboardene.",
            "Kortene har samme høyde og rytme som omsetning, inkludert informasjonsstripe under toppfeltet.",
            "Antall er fortsatt hovedtall, mens omsetning og snitt vises som støtteinformasjon i kortet.",
        ],
    },
    {
        "version": "1",
        "build": "1485",
        "date": "08.07.2026",
        "headline": "Funksjonskontroll",
        "title": "Fibaro10 tester appskallet bedre og rydder runtime-data fra Git-status",
        "description": (
            "Build 1485 er en systematisk kontrollrunde av funksjoner og drift. Alle automatiske tester, UI-ruter, "
            "live-ruter, datakilder og containere er kontrollert. Smoke-testene er utvidet slik at de også verifiserer "
            "meny skjul/vis, temabytter, buildlogg-lenke og toppnavigasjon, ikke bare at sider laster."
        ),
        "applications": [
            "desktop_v2/scripts/smoke-ui.mjs: tester appskall-handlinger lokalt i tillegg til ruter.",
            "desktop_v2/scripts/smoke-live.mjs: tester samme appskall-handlinger mot live-instansen etter innlogging.",
            ".gitignore: ignorerer runtime-data både som kataloger og som QNAP-symlinker.",
            "build_log.py: dokumenterer build 1485.",
        ],
        "request": "Du ba om å teste alle funksjoner, vurdere om de er hensiktsmessige og forbedre der det trengs.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Full lokal kvalitetssjekk kjører fortsatt backendtester, typecheck, build, CSS-audit, bundle-audit, route-audit og UI-smoke.",
            "UI-smoke dekker nå grunnleggende brukerhandlinger i appskallet: hovedmeny, mørkt/standard tema, buildlogg og status-fanenavigasjon.",
            "Live-smoke gjør den samme appskallkontrollen mot QNAP etter innlogging.",
            "QNAP-runtime-data som ligger som symlinker blir ignorert eksplisitt, slik at Git-status ikke blir støyete.",
            "Driftskontroll viste healthy containere og 22 av 22 datakilder OK før endringen.",
        ],
    },
    {
        "version": "1",
        "build": "1484",
        "date": "08.07.2026",
        "headline": "CSS-optimalisering",
        "title": "Fibaro10 rydder status- og mørktema-CSS etter dashboardarbeidet",
        "description": (
            "Build 1484 gjør en ny målrettet CSS-opprydding. Statusfarger er flyttet til felles tokens, gamle "
            "mørktema-regler for utgåtte komponentklasser er fjernet, og status/dashboard-flater bruker nå mer av "
            "den felles skygge- og tekstskalaen."
        ),
        "applications": [
            "desktop_v2/src/styles/tokens.css: legger inn semantiske tokens for ok, varsel og feil-status.",
            "desktop_v2/src/styles/status-widgets.css: bruker status-tokens og felles tekst-/skyggetokens.",
            "desktop_v2/src/styles/status-overview.css: bruker felles skyggeskala på dashboardhandlinger.",
            "desktop_v2/src/styles/dark-theme.css: fjerner gamle selektorer for utgåtte kortklasser og definerer mørke status-tokens.",
            "build_log.py: dokumenterer build 1484.",
        ],
        "request": "Du ba om å optimalisere CSS på nytt.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Mulige ubrukte CSS-klasser i audit ble redusert ved å fjerne reelt utgåtte mørktema-selektorer.",
            "Hardkodede statusfarger er samlet i tokens i stedet for å ligge direkte i status-widgetene.",
            "Dashboard- og statusflater bruker eksisterende skygge- og teksttokens der det tidligere lå lokale verdier.",
            "Endringen er teknisk rydding uten tilsiktet funksjonsendring.",
        ],
    },
    {
        "version": "1",
        "build": "1483",
        "date": "08.07.2026",
        "headline": "Logoekte kortikoner",
        "title": "Fibaro10 dashboard bruker sol og P hentet direkte fra Lilletorget-logoen",
        "description": (
            "Build 1483 bytter ut de håndtegnede sol- og parkeringsikonene i dashboardkortene med egne symbolassets "
            "generert direkte fra Lilletorget-logoen. Dermed brukes samme farge, geometri og visuelle uttrykk som i logoen."
        ),
        "applications": [
            "static/lilletorget-symbol-sun.png: nytt solsymbol hentet fra de gyldne pikslene i logoens mark.",
            "static/lilletorget-symbol-parking.png: nytt P-symbol hentet fra den mørkeblå P-en i logoens mark.",
            "desktop_v2/src/pages/OverviewPage.tsx: bruker de nye logoavledede symbolene på soling- og parkeringsradene.",
            "desktop_v2/src/styles/status-periods.css: fjerner gamle SVG-regler og tilpasser størrelsen på de nye symbolene.",
            "build_log.py: dokumenterer build 1483.",
        ],
        "request": "Du ba om at symbolene for soling og parkering på kortene skulle hentes nøyaktig fra logoen.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Solikonet er ikke lenger en egen SVG-tegning, men et asset-uttrekk fra logoens sol.",
            "P-ikonet er hentet fra logoens P i stedet for å være fontbasert eller tegnet separat.",
            "De nye ikonene brukes både på omsetningskortene og på antallkortene for soling og parkering.",
            "Gamle CSS-regler for SVG-stroke er fjernet fra dashboardkortene.",
        ],
    },
    {
        "version": "1",
        "build": "1482",
        "date": "08.07.2026",
        "headline": "Kortere dashboardtitler",
        "title": "Fibaro10 hoveddashboard bruker kortere iPad-lignende periodetitler",
        "description": (
            "Build 1482 rydder i toppen av dashboardkortene. De fire periodekortene bruker nå de korte "
            "periodenavnene fra API-et, og rangeringen for dagen er flyttet bort fra hovedtallet slik at "
            "kortet får et roligere visuelt hierarki."
        ),
        "applications": [
            "desktop_v2/src/pages/OverviewPage.tsx: bruker periodens korte tittel og flytter dagsrangering inn i metadata-linjen.",
            "desktop_v2/src/styles/status-periods.css: fjerner den gamle rangering-badgen og legger inn en diskret inline-variant.",
            "desktop_v2/src/styles/dark-theme.css: tilpasser den nye inline-rangeringen til mørkt tema.",
            "build_log.py: dokumenterer build 1482.",
        ],
        "request": "Du ba om kortere overskrifter som i iPad-boksene og en annen løsning for rangeringen på dagens kort.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Omsetning, parkering og soling-dashboardene bruker nå korte titler som I dag, Denne uken, Denne måneden og I år.",
            "Dagsrangeringen vises ikke lenger som en egen pill ved siden av hovedtallet.",
            "Rangeringen ligger nå diskret i oppdateringslinjen med tooltip for forklaring.",
            "Hovedtallet på dagens omsetningskort får dermed samme rene vekt som de andre kortene.",
        ],
    },
    {
        "version": "1",
        "build": "1481",
        "date": "08.07.2026",
        "headline": "Referansefelt på dashboardkort",
        "title": "Fibaro10 hoveddashboard får iPad-lignende nederste referansefelt",
        "description": (
            "Build 1481 gjør nederste del av de fire dashboardkortene mer lik iPad-appen. Referanseperiodene vises "
            "nå som egne klikkbare felt med total, gjenstår/over og progressindikator, i stedet for en kompakt tekststripe."
        ),
        "applications": [
            "desktop_v2/src/pages/OverviewPage.tsx: splitter full referanseperiode ut i egne komponenter for omsetning og antall.",
            "desktop_v2/src/styles/status-periods.css: lager to nederste referansefelt med total, avvik og progresslinje.",
            "desktop_v2/src/styles/dark-theme.css: tilpasser de nye referansefeltene til mørkt tema.",
            "build_log.py: dokumenterer build 1481.",
        ],
        "request": "Du ba om nederste felt på de fire dashboardkortene slik som i iPad-appen.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Hver referanseperiode nederst på kortet er nå et eget klikkbart felt.",
            "Feltene viser totalen for hele referanseperioden tydeligere.",
            "Gjenstår/over står høyrejustert og får samme positiv/negativ-logikk som før.",
            "Progresslinjen gir en rask visuell følelse av hvor langt valgt periode er mot referansen.",
            "Samme komponentmønster brukes på omsetning, parkering og soling-dashboardene.",
        ],
    },
    {
        "version": "1",
        "build": "1480",
        "date": "08.07.2026",
        "headline": "Dashboardkortene strammes videre",
        "title": "Fibaro10 fjerner overlappende periode-CSS og gjør dashboardkortene roligere",
        "description": (
            "Build 1480 optimaliserer videre etter iPad-inspirert dashboardrunde. Gamle generelle periodekortregler "
            "er fjernet fra refinement-laget, og de fire dashboardflatene er gjort litt lavere, mer nøytrale og "
            "mindre varselpregede uten at datalogikken endres."
        ),
        "applications": [
            "desktop_v2/src/styles/status-refinements.css: fjerner gamle status-period-card-regler som overlappet status-periods.css.",
            "desktop_v2/src/styles/status-periods.css: strammer kortenes høyde, spacing, sammenligningsfelt og referansefelt.",
            "build_log.py: dokumenterer build 1480.",
        ],
        "request": "Du ba om å optimalisere videre etter dashboardendringen.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Periodekortene har nå én tydelig CSS-kilde i stedet for overlapp mellom status-periods og status-refinements.",
            "Omsetningskortene bruker mindre rød/rosa flate slik at minus/varsel-farger får tydeligere betydning.",
            "Sammenligningsboksene og referansefeltet er komprimert litt for bedre 2x2-dashboard på vanlig skjerm.",
            "Kortene beholder iPad-inspirert accent og fordeling, men uttrykket er roligere og mer presist.",
        ],
    },
    {
        "version": "1",
        "build": "1479",
        "date": "08.07.2026",
        "headline": "Dashboardkortene henter iPad-grep",
        "title": "Fibaro10 hoveddashboard får tydeligere periodeflater inspirert av iPad-appen",
        "description": (
            "Build 1479 viderefører de beste grepene fra iPad-flaten til hovedappens fire dashboardkort. "
            "Periodene får tydeligere toppaccent, kompakt fordelingsmeter for soling og parkering, mer ryddige "
            "sammenligningsfelt og strammere tabellrader."
        ),
        "applications": [
            "desktop_v2/src/pages/OverviewPage.tsx: legger inn sol/parkering-fordeling som CSS-variabel og kompakt meter på omsetningskortene.",
            "desktop_v2/src/styles/status-periods.css: polerer periodekortene med iPad-inspirert accent, spacing, sammenligningsflater og driver-tabell.",
            "desktop_v2/src/styles/dark-theme.css: gir de nye periodeflatene kontrasttilpasset mørkt tema.",
            "build_log.py: dokumenterer build 1479.",
        ],
        "request": "Du ba om å hente inspirasjon fra iPad-appen på de fire flatene på dashboardet.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "De fire dashboardflatene får et mer markert, men fortsatt kontrollert visuelt hierarki.",
            "Omsetningskortene viser nå en diskret fordeling mellom soling og parkering slik iPad-appen gjør.",
            "Sammenligningsboksene er større og enklere å lese uten at datalogikken er endret.",
            "Soling- og parkeringsdashboardene bruker samme kortsystem og samme accentlogikk.",
            "Mørkt tema er oppdatert slik at nye meter- og accentflater holder god kontrast.",
        ],
    },
    {
        "version": "1",
        "build": "1478",
        "date": "08.07.2026",
        "headline": "Hovedappens CSS ryddes og optimaliseres",
        "title": "Fibaro10 hovedapp får mer strukturert CSS, færre overstyringer og mer token-basert styling",
        "description": (
            "Build 1478 rydder i CSS-laget i hovedappen etter designrunden. Vedlikeholdsstyling er skilt ut fra "
            "den globale modulfilen, gamle dublettregler er slått sammen, og flere hardkodede farger er erstattet "
            "med design-tokens slik at lyst og mørkt tema henger bedre sammen."
        ),
        "applications": [
            "desktop_v2/src/styles/module-content.css: fjerner vedlikeholdsspesifikk styling fra felles modul-CSS.",
            "desktop_v2/src/styles/maintenance.css: ny egen CSS-fil for vedlikeholdsvisninger.",
            "desktop_v2/src/main.tsx: importerer maintenance.css før dark-theme.css for riktig override-rekkefølge.",
            "desktop_v2/src/styles/status.css, energy.css, records.css og status-comparison.css: fjerner reelle dubletter og samler gamle overstyringer.",
            "desktop_v2/src/styles/parking-timeline.css, sun-timeline.css, status-overview.css og status-periods.css: rydder refinement-regler og bruker tokens for status- og domene-farger.",
            "build_log.py: dokumenterer build 1478.",
        ],
        "request": "Du ba om opprydding og optimalisering av CSS i Fibaro10 hovedappen.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Felles module-content.css er redusert betydelig og inneholder ikke lenger vedlikeholdsflaten.",
            "Vedlikeholds-CSS ligger nå i egen fil, men lastes før mørkt tema slik at temaoverstyringer fortsatt vinner.",
            "Gamle dupliserte tabell-, status- og grafregler er slått sammen til én autoritativ regel per komponent.",
            "Flere hardkodede blå, røde og gule farger er erstattet med eksisterende design-tokens.",
            "CSS-parseren håndterer nå 32 stilark inkludert den nye vedlikeholdsfilen.",
        ],
    },
    {
        "version": "1",
        "build": "1477",
        "date": "08.07.2026",
        "headline": "Hovedappen får visuell opprydding",
        "title": "Fibaro10 hovedapp strammer opp appskall, kort, tabeller, dashboard og mørkt tema",
        "description": (
            "Build 1477 er en kontrollert designopprydding i hovedappen. Endringen gjør appen roligere og mer "
            "systematisk ved å justere globale tokens, toppmeny, venstremeny, kort, tabeller, dashboardrammer og "
            "graf-tema. Funksjonslogikk er ikke endret."
        ),
        "applications": [
            "desktop_v2/src/styles/tokens.css: justerer bakgrunnsflate og skyggetokens for et roligere grunnuttrykk.",
            "desktop_v2/src/styles/layout.css: forbedrer Ant Design-kort, segmenterte menyer og tabeller globalt.",
            "desktop_v2/src/styles/app-shell.css: strammer opp venstremeny, toppmeny, aktivmarkering, profil og buildfelt.",
            "desktop_v2/src/styles/module-content.css og module-metrics.css: gir felles kort og nøkkeltall bedre hierarki.",
            "desktop_v2/src/styles/status-overview.css og status-periods.css: fjerner unødvendig dashboardramme og polerer periodekort.",
            "desktop_v2/src/styles/dark-theme.css: matcher endringene i mørkt tema og forbedrer kontrast.",
            "desktop_v2/src/chartTheme.ts: gjør grafaksene og tooltipene mer lesbare, spesielt i mørkt tema.",
            "build_log.py: dokumenterer build 1477.",
        ],
        "request": "Du ba om en gjennomgang av Fibaro10 hovedappen og forbedring av designet.",
        "work_duration": "ca. 50 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Venstremeny og toppmeny har fått mer konsekvent kontrast, aktivmarkering og dybde.",
            "Kort og paneler har fått roligere bakgrunn, mindre hard rammestøy og mer konsistent skyggebruk.",
            "Dashboardets skjulte seksjoner tegner ikke lenger en ekstra ytre ramme rundt periodekortene.",
            "Tabeller har fått bedre scanbarhet med tabulære tall, diskret zebra og bedre hover.",
            "Mørkt tema er justert slik at samme komponenter har bedre kontrast og mindre slitasje.",
            "Graf-temaet har fått bedre akse-/tooltip-lesbarhet.",
        ],
    },
    {
        "version": "1",
        "build": "1476",
        "date": "08.07.2026",
        "headline": "iPad-status flyttes inn i toppbaren",
        "title": "Fibaro10 iPad samler datakilder, siste soling og siste parkering i første rad",
        "description": (
            "Build 1476 fjerner den ekstra statusraden over periodekortene i iPad-appen. Informasjonen fra "
            "rad 2 er flyttet opp i toppbaren sammen med åpning, slik at oversikten starter direkte med de "
            "fire hovedkortene for dag, uke, måned og år."
        ),
        "applications": [
            "fibaro10ipad/app/main.py: flytter statusfeltene inn i toppbaren og fjerner heroGrid fra oversikten.",
            "fibaro10ipad/app/static/ipad.js: rendrer datakilder, siste soling og siste parkering som små toppmålinger.",
            "fibaro10ipad/app/static/ipad.css: gjør toppbaren bredere og fjerner gammel hero/statusrad-CSS som ikke lenger brukes.",
            "docker-compose.qnap.yml og .env.qnap.example: oppdaterer iPad-build til 1476.",
            "build_log.py: dokumenterer build 1476.",
        ],
        "request": "Du ønsket å flytte informasjonen fra rad 2 opp i rad 1, slik at hele rad 2 kunne fjernes.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Datakilder, siste soling og siste parkering ligger nå i toppbaren.",
            "Ekstra statusrad over periodekortene er fjernet fra HTML og JavaScript.",
            "Oversikten starter nå direkte med de fire periodekortene.",
            "Død CSS fra tidligere hero/statusrad er ryddet bort.",
        ],
    },
    {
        "version": "1",
        "build": "1475",
        "date": "08.07.2026",
        "headline": "iPad-oversikten går tilbake til fire hovedkort",
        "title": "Fibaro10 iPad fjerner stor omsetningshero og bruker fire periodekort som hovedflate",
        "description": (
            "Build 1475 gjør iPad-oversikten mer konsistent etter vurdering av duplisering mellom toppflaten "
            "og 'I dag'-kortet. Den store sorte omsetningsboksen er fjernet som hovedflate. Oversikten viser "
            "igjen fire like periodekort for i dag, uke, måned og år, med en lav statusrad over."
        ),
        "applications": [
            "fibaro10ipad/app/static/ipad.js: rendrer alle fire perioder igjen og gjør toppområdet til en kompakt statusrad.",
            "fibaro10ipad/app/static/ipad.css: erstatter den store hero-layouten med små statuskort og fjerner trio-spesiallayout.",
            "fibaro10ipad/app/main.py, docker-compose.qnap.yml og .env.qnap.example: oppdaterer iPad-build til 1475.",
            "build_log.py: dokumenterer build 1475.",
        ],
        "request": "Du ønsket heller å beholde de fire kortene under, siden den sorte boksen og I dag-kortet ble dupliserende.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Fire periodekort er tilbake i oversikten.",
            "Den store sorte omsetningsboksen er fjernet fra toppområdet.",
            "Datakilder, siste soling og siste parkering vises som en lav statusrad.",
            "Spesiallayouten for tre kort er fjernet.",
        ],
    },
    {
        "version": "1",
        "build": "1474",
        "date": "08.07.2026",
        "headline": "iPad-oversikten fjerner dobbelt visning av dagen",
        "title": "Fibaro10 iPad bruker toppkortet som dagens omsetningsflate og viser uke, måned og år under",
        "description": (
            "Build 1474 rydder i iPad-oversikten etter at dagens tall ble vist to ganger. Den sorte "
            "toppflaten eier nå 'I dag', mens periodekortene under starter på uke, måned og år. "
            "Dette gir mindre repetisjon og tydeligere informasjonsstruktur."
        ),
        "applications": [
            "fibaro10ipad/app/static/ipad.js: filtrerer bort dagens periode fra detaljkortene etter at hero er rendret.",
            "fibaro10ipad/app/static/ipad.css: legger inn en trio-layout der årskortet kan bruke full bredde når tre kort vises.",
            "fibaro10ipad/app/main.py, docker-compose.qnap.yml og .env.qnap.example: oppdaterer iPad-build til 1474.",
            "build_log.py: dokumenterer build 1474.",
        ],
        "request": "Du påpekte at innholdet i den øverste sorte boksen var det samme som boksen under.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Den sorte toppboksen er nå eneste visning av dagens tall.",
            "Kortrekken under viser ikke lenger et eget 'I dag'-kort.",
            "Uke, måned og år vises som detaljkort under toppflaten.",
            "Layouten tilpasses når det bare er tre periodekort.",
        ],
    },
    {
        "version": "1",
        "build": "1473",
        "date": "08.07.2026",
        "headline": "iPad-tallene blir mer visuelle",
        "title": "Fibaro10 iPad får sprekere tallkort med fordelingsbarer, deltafelt og fremdriftsmålere",
        "description": (
            "Build 1473 videreutvikler iPad-grensesnittet visuelt. Omsetningstallene vises nå mer som en "
            "driftsflate for iPad, med tydeligere hovedsum, fargekodet fordeling mellom soling og parkering, "
            "deltaindikatorer mot referanseperioder og små fremdriftsmålere i periodekortene."
        ),
        "applications": [
            "fibaro10ipad/app/static/ipad.js: legger til fordelingsprosent, deltaikoner, fremdriftsberegninger og ny markup for tallkort.",
            "fibaro10ipad/app/static/ipad.css: legger til visuell tallgrafikk, fordelingsbarer, referansechips og kompaktere periodepresentasjon.",
            "fibaro10ipad/app/main.py, docker-compose.qnap.yml og .env.qnap.example: oppdaterer iPad-build til 1473.",
            "build_log.py: dokumenterer build 1473.",
        ],
        "request": "Du ønsket en sprekere måte å vise tallene på i iPad-appen.",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Dagens omsetning har nå en mer markant totalsum med egen tallstack.",
            "Soling og parkering vises med fargekodet fordelingsbar og prosentandel.",
            "Sammenligning mot i går og samme ukedag forrige uke har tydeligere deltafelt.",
            "Periodekortene viser nå fordeling, totalavvik og fremdrift mot hele referanseperioder.",
            "Kortene beholder samme datagrunnlag og samme 2x2-struktur på iPad.",
        ],
    },
    {
        "version": "1",
        "build": "1472",
        "date": "08.07.2026",
        "headline": "iPad-grensesnittet får moderne appflate",
        "title": "Fibaro10 iPad bygges om med venstrerail, hero-dashboard og tydeligere iPad-layout",
        "description": (
            "Build 1472 tar iPad-grensesnittet et godt steg videre visuelt. Flaten får en egen appstruktur "
            "med mørk venstrerail, sticky kontrollinje, stor omsetningshero, mer moderne periodkort og "
            "bedre fargekodet drift/status for bruk på 13 tommer iPad Pro."
        ),
        "applications": [
            "fibaro10ipad/app/main.py: bygger om HTML-skallet til venstrerail, app-stage, statuspiller og heroområde.",
            "fibaro10ipad/app/static/ipad.css: erstatter første CSS med et nytt iPad-orientert designsystem.",
            "fibaro10ipad/app/static/ipad.js: legger inn hero-dashboard, datasource-oppsummering, toppstatus og tryggere HTML-rendering.",
            "docker-compose.qnap.yml og .env.qnap.example: oppdaterer iPad-build til 1472.",
            "build_log.py: dokumenterer build 1472.",
        ],
        "request": "Du ønsket et mer moderne iPad-grensesnitt og ba om å ta det helt ut.",
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "iPad-appen har nå en tydelig app-rail i venstre side i stedet for en enkel toppmeny.",
            "Oversikt starter med en stor omsetningshero for dagens tall.",
            "Dagens soling og parkering fremheves med egne driverkort og domene-farger.",
            "Periodkortene er strammet opp med bedre tabeller og referansefelt.",
            "Parkering, soling og drift har mer app-aktige paneler og bedre touchflater.",
        ],
    },
    {
        "version": "1",
        "build": "1471",
        "date": "08.07.2026",
        "headline": "Eget iPad-grensesnitt for Fibaro10",
        "title": "Fibaro10 iPad er lagt opp som separat underapp på ipad.lilletorget.net",
        "description": (
            "Build 1471 legger til en egen FastAPI-underapp for iPad. Appen bruker samme brukerbase som "
            "Fibaro10, henter data via hovedappens API og viser en stor berøringsvennlig driftsflate for "
            "omsetning, parkering, soling og drift."
        ),
        "applications": [
            "fibaro10ipad/: ny separat FastAPI-app med login, PWA-manifest, iPad-tilpasset CSS og dashboard-JavaScript.",
            "docker-compose.qnap.yml og Caddyfile: legger til fibaro10ipad-container og ruter ipad.lilletorget.net til port 8113.",
            "scripts/deploy-qnap.ps1, scripts/check-local.ps1 og scripts/qnap-health-watch.sh: tar med iPad-appen i bygg, syntax-sjekk og QNAP health-watch.",
            "system_inventory.py og docs/utviklingsoppsett.md: dokumenterer ny underapp og klikkbar webflate.",
            "build_log.py: dokumenterer build 1471.",
        ],
        "request": "Du ønsket å lage en ny app ved siden av Fibaro10, kalt fibaro10ipad, med moderne iPad-tilpasset grensesnitt på ipad.lilletorget.net. Du presiserte at primærflaten er en ny 13 tommer iPad Pro.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Ny egen iPad-app med samme innlogging som Fibaro10.",
            "Oversikten viser fire store perioder i 2x2-grid på 13 tommer iPad Pro.",
            "Egne faner for Oversikt, Parkering, Soling og Drift.",
            "Appen henter data fra Fibaro10 API og kopierer ikke databasen eller forretningslogikken.",
            "Produksjonsoppsettet inkluderer Caddy-ruting for ipad.lilletorget.net.",
        ],
    },
    {
        "version": "1",
        "build": "1470",
        "date": "08.07.2026",
        "headline": "Parkeringsavvik regnes mot betalt 30-minutters slot",
        "title": "Parkering/Parkeringer viser avreiseavvik mot neste betalte parkeringsslot",
        "description": (
            "Build 1470 korrigerer beregningen av avviket i Parkering/Parkeringer. "
            "Avviket regnes nå mot betalte 30-minutters slotter, slik at en parkering på 45 minutter "
            "sammenlignes mot 60 minutter og vises som -15."
        ),
        "applications": [
            "main.py: legger inn parking_departure_slot_delta_minutes og bruker 30-minutters slotter for end_delta_min.",
            "desktop_v2/src/pages/module/moduleTableUtils.tsx: endrer tabelllabelen til Slot-avvik min.",
            "tests/test_parking_row_api.py: tester at 45 minutter gir -15 og at pågående parkeringer ikke får avreiseavvik.",
            "build_log.py: dokumenterer build 1470.",
        ],
        "request": "Du presiserte at slot-tiden alltid er 30 minutter, og at avviket skal være mellom avreise og siste betalte slot. Eksempel: drar man etter 45 minutter, er avviket -15 minutter.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Avvik beregnes mot 30, 60, 90 osv. minutter.",
            "45 minutter gir nå -15.",
            "Pågående parkeringer får blank verdi fordi bilen ikke har reist ennå.",
            "Kolonnen heter nå Slot-avvik min.",
        ],
    },
    {
        "version": "1",
        "build": "1469",
        "date": "08.07.2026",
        "headline": "Parkeringer har mer kompakt topp og sluttavvik",
        "title": "Parkering/Parkeringer flytter EasyPark-oppdatering til datolinjen og viser sluttavvik i minutter",
        "description": (
            "Build 1469 rydder toppen på Parkering/Parkeringer. Den separate handlingsboksen fjernes, "
            "EasyPark-oppdateringen flyttes ned til datovelgeren, og venstre statusfelt viser sist vellykkede "
            "import i stedet for valgt dato. Tabellen får også et sluttavvik i minutter."
        ),
        "applications": [
            "main.py: sender sist oppdatert-import inn i dayNavigation og legger end_delta_min på parkeringsradene.",
            "desktop_v2/src/pages/module/ModuleDayNavigationBar.tsx: støtter kontekstfelt og handlinger på datolinjen.",
            "desktop_v2/src/pages/ModulePage.tsx: flytter EasyPark-refresh fra egen handlingsboks til datolinjen for Parkering/Parkeringer.",
            "desktop_v2/src/pages/module/moduleTableUtils.tsx: legger lesbart kolonnenavn for sluttavvik.",
            "desktop_v2/src/styles/module-content.css: justerer komprimert visning av kontekstfeltet.",
            "build_log.py: dokumenterer build 1469.",
        ],
        "request": "På siden Parkering/Parkeringer ønsket du Oppdater-knappen ned på linjen med datovelger, toppfeltet fjernet, venstre datofelt erstattet med sist oppdatert og et felt for hvor mange minutter bilen dro før/etter forventet slutt.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Separat handlingsfelt over datovelgeren er fjernet på Parkering/Parkeringer.",
            "Oppdater EasyPark ligger nå på samme linje som dagvelgeren.",
            "Venstre felt viser sist oppdatert EasyPark-import.",
            "Tabellen viser Slutt-avvik min, der negativ verdi betyr før forventet slutt.",
        ],
    },
    {
        "version": "1",
        "build": "1468",
        "date": "08.07.2026",
        "headline": "Dører har ryddig oversikt og egen rådataside",
        "title": "Dørmenyen viser åpneperioder med varighet og flytter HC3-rådata til egen fane",
        "description": (
            "Build 1468 gjør Dører/Oversikt til en faktisk arbeidsflate. Den viser bare reelle "
            "statusendringer, beregner hvor lenge dørene har vært åpne, og lar råmeldinger fra HC3 "
            "ligge på en egen Rådata-side for kontroll og feilsøking."
        ),
        "applications": [
            "main.py: beregner statusendringer, åpneperioder, varighet og siste faktiske dørendring i /api/hc3/doors/status.",
            "desktop_v2/src/api.ts: utvider dørtypene med perioder, endringer og siste endringstekst.",
            "desktop_v2/src/pages/DoorsPage.tsx: deler Dører i Oversikt og Rådata, og viser åpnet/lukket/varighet i en ryddig tabell.",
            "desktop_v2/src/moduleViews.ts og desktop_v2/scripts/smoke-routes.mjs: legger Rådata inn som egen verifisert underside.",
            "desktop_v2/src/styles/doors.css: strammer visningen av dørperioder og statusfelt.",
            "build_log.py: dokumenterer build 1468.",
        ],
        "request": "På menyen Dører ønsket du rådata på egen side, og en første side Oversikt som viser når en dør går opp og igjen, bare statusendringer og hvor lenge døren var åpen.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Dører/Oversikt viser nå døråpninger med åpnet, lukket og varighet.",
            "Toppen viser sist faktiske statusendring og hva som skjedde.",
            "Rå HC3-hendelser ligger på Dører/Rådata.",
            "Ruteaudit dekker nå begge dørsidene.",
        ],
    },
    {
        "version": "1",
        "build": "1467",
        "date": "08.07.2026",
        "headline": "Parkering oversikt er tilbake som første fane",
        "title": "Ukesstatistikken under Parkering er gjeninnført som standardflate",
        "description": (
            "Build 1467 legger Parkering/Oversikt tilbake som første underside i parkeringsmenyen. "
            "Parkeringer ligger nå som nummer to, mens Bilstatistikk fortsatt er skjult fra normal meny."
        ),
        "applications": [
            "desktop_v2/src/moduleViews.ts: flytter Oversikt tilbake som første synlige parkeringsfane.",
            "desktop_v2/src/pages/OverviewPage.tsx og desktop_v2/src/domainModel.ts: gjeninnfører oversikt som første parkeringssnarvei og standardlenke.",
            "main.py: sender /parkering og EasyPark-refresh tilbake til /parkering/oversikt.",
            "docs/desktop-v2.md og docs/funksjonsstruktur.md: oppdaterer dokumentert parkeringsstruktur.",
            "build_log.py: dokumenterer build 1467.",
        ],
        "request": "Du mistet ukesstatestikken den som het oversikt under parkering, hadde ikke tenkt å ta bort den. Kan du legge den tilbake og den kan være den første så kan parkeringer være nr 2.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Parkering/Oversikt er igjen første fane og standard for /parkering.",
            "Parkeringer er andre fane.",
            "Dashboard-snarveien for parkering peker igjen først til oversikten.",
        ],
    },
    {
        "version": "1",
        "build": "1466",
        "date": "08.07.2026",
        "headline": "Kortere kolonneoverskrifter i parkeringslisten",
        "title": "Parkering/Parkeringer bruker smalere kolonnenavn for tidligere historikk",
        "description": (
            "Build 1466 gjør parkeringslisten smalere ved å forkorte kolonneoverskriftene "
            "for tidligere parkeringer og tidligere betalt beløp."
        ),
        "applications": [
            "desktop_v2/src/pages/module/moduleTableUtils.tsx: endrer labelene previous_parking_count og previous_paid_total til P før og B før.",
            "build_log.py: dokumenterer build 1466.",
        ],
        "request": "På parkering/parkeringer gjør endre overskriftene Parkeringer før og betalt før i tabellen til p før og b før for å spare plass i bredden.",
        "work_duration": "ca. 5 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Kolonnen Parkeringer før heter nå P før.",
            "Kolonnen Betalt før heter nå B før.",
        ],
    },
    {
        "version": "1",
        "build": "1465",
        "date": "08.07.2026",
        "headline": "Parkering har ryddigere menystruktur",
        "title": "Parkeringer er standardflaten, og overlappende undersider er skjult fra menyen",
        "description": (
            "Build 1465 rydder parkeringsområdet i V2. Parkeringer er nå første og naturlige side, "
            "synlige undersider er sortert etter arbeidsflyt, og gamle overlappende flater er skjult "
            "fra fanemenyen uten at underliggende ruter fjernes."
        ),
        "applications": [
            "desktop_v2/src/moduleViews.ts: gjør Parkeringer til standardvisning og skjuler Oversikt/Bilstatistikk fra normal meny.",
            "desktop_v2/src/App.tsx: skiller mellom kjente ruter og synlige faner slik at skjulte ruter ikke forstyrrer vanlig meny.",
            "desktop_v2/src/pages/OverviewPage.tsx og desktop_v2/src/domainModel.ts: oppdaterer snarveier til nye parkeringsflater.",
            "main.py: flytter operative parkeringslenker og redirect etter EasyPark-oppdatering til Parkeringer.",
            "docs/desktop-v2.md og docs/funksjonsstruktur.md: dokumenterer ny struktur.",
        ],
        "request": "Kan du gjøre en grundig opprydding på menystruktur og undersider på parkering. Det er en del overlapp og parkeringer burde ant være default side.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Parkering åpner nå på /parkering/parkeringer.",
            "Fanemenyen for parkering viser Parkeringer, Dagslinje, Kjøretøy, Områder, Prognose, Årssammenligning, Oppgjør og Datakvalitet.",
            "Gammel Oversikt og Bilstatistikk er skjult fra normal meny for å redusere overlapp.",
            "Dashboard, manual og backend-kort peker til de nye operative parkeringssidene.",
        ],
    },
    {
        "version": "1",
        "build": "1464",
        "date": "08.07.2026",
        "headline": "Kjøretøyfelt får fallback-data",
        "title": "Kjøretøy vises også når full tittel mangler",
        "description": (
            "Build 1464 retter kjøretøyoppsummeringen slik at Kjøretøy-feltet kan bygges av merke, "
            "modell/type og farge selv om kilden ikke har et ferdig vehicle_title-felt."
        ),
        "applications": [
            "main.py: fyller vehicle_title direkte fra vehicle_make, vehicle_type og vehicle_color når samlet tittel mangler.",
            "parking_vehicle_helpers.py: bygger kjøretøylabel fra car_info make/model/vehicle_type når ferdig tittel mangler.",
            "build_log.py: dokumenterer build 1464.",
        ],
        "request": "Feltet kjøretøy fylles fortsatt ikke med data på parkering/parkeringer slik det gjør på parkering/kjøretøy siden.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Kjøretøyoppsummering faller nå tilbake til merke, modell/type og fargegrunnlag.",
            "Parkering/Parkeringer får tekst i Kjøretøy-kolonnen også for delvis berikede biler.",
        ],
    },
    {
        "version": "1",
        "build": "1463",
        "date": "08.07.2026",
        "headline": "Parkeringer viser alle rader og kjøretøy",
        "title": "Kjøretøyfelt og paginering er rettet på parkeringslisten",
        "description": (
            "Build 1463 retter Parkering/Parkeringer slik at kjøretøyfeltet faktisk fylles fra "
            "kjøretøydetaljene, og fjerner tabellpagineringen på akkurat denne dagslisten. "
            "Siden viser nå alle parkeringer for valgt dag samlet."
        ),
        "applications": [
            "main.py: joiner kjøretøydetaljer på normalisert reg.nr, fjerner dagslimit og sender disablePagination for Parkeringer-tabellen.",
            "desktop_v2/src/api.ts: utvider tabellmeta med disablePagination.",
            "desktop_v2/src/pages/module/ModuleTablePane.tsx: respekterer disablePagination per tabell.",
        ],
        "request": "Det kom ingen data i feltet kjøretøy. Jeg ønsker også å ta bort pagingen akkurat på den siden da den alltid skal vise alle på en dag.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Kjøretøyfeltet på Parkering/Parkeringer bruker nå samme normaliserte reg.nr som resten av parkeringsoppslagene.",
            "API-et henter alle parkeringer for valgt dag i stedet for å begrense listen med Antall.",
            "Tabellpagineringen er slått av kun for Parkering/Parkeringer.",
        ],
    },
    {
        "version": "1",
        "build": "1462",
        "date": "08.07.2026",
        "headline": "Parkeringer viser kjøretøy",
        "title": "Kjøretøyfelt er lagt inn i parkeringslisten",
        "description": (
            "Build 1462 legger samlet kjøretøyinformasjon inn i tabellen på Parkering/Parkeringer. "
            "Listen henter nå også kjøretøydetaljer for hver parkering og viser feltet Kjøretøy etter reg.nr."
        ),
        "applications": [
            "main.py: utvider parkeringer-visningen med ParkingVehicleDetails og kolonnen vehicle_title.",
        ],
        "request": "På parkering\\parkeringer i den tabellen ønsker jeg å ha med feltet Kjøretøy.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Parkering/Parkeringer viser nå Kjøretøy som egen kolonne etter reg.nr.",
            "Kjøretøyverdien kommer fra samme oppsummeringslogikk som brukes på kjøretøysidene.",
            "Parkeringer uten registrerte kjøretøydetaljer faller tilbake til tom/verdi mangler uten å stoppe tabellen.",
        ],
    },
    {
        "version": "1",
        "build": "1461",
        "date": "07.07.2026",
        "headline": "Grafvalg fjerner skjulte serier",
        "title": "Ekstra grafer ryddes bort når de slås av",
        "description": (
            "Build 1461 retter en ECharts-mergefeil der en ekstra grafserie kunne bli liggende igjen "
            "visuelt etter at valget ble slått av. Felles chart-wrapper erstatter nå series-listen rent "
            "ved oppdatering, slik at grafvalg følger avkryssingene konsekvent."
        ),
        "applications": [
            "desktop_v2/src/components/AppChart.tsx: setter replaceMerge for series som standard på alle ECharts-grafer.",
        ],
        "request": "Når man klikker på en ekstra graf for å vise den så går den ikke alltid bort igjen når man slår av valget - fiks det.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Gamle ECharts-serier fjernes nå når serie-listen blir kortere.",
            "Grafvalg som år, sammenligninger og ekstra linjer skal ikke lenger etterlate skjulte restgrafer.",
            "Endringen er lagt sentralt i AppChart slik at alle ECharts-flater får samme oppførsel.",
        ],
    },
    {
        "version": "1",
        "build": "1460",
        "date": "07.07.2026",
        "headline": "Mørkt tema får tydeligere grafer",
        "title": "Grafpaletten er strammet for mørkt tema",
        "description": (
            "Build 1460 retter fargebruken i mørkt tema, spesielt i ECharts-grafene. Akser, grid, "
            "tooltips, marklinjer og seriefarger har fått høyere kontrast, og grafer som får farger "
            "fra API-et normaliseres nå til en mørk palett."
        ),
        "applications": [
            "desktop_v2/src/designTokens.ts: oppdaterer mørke domenefarger for omsetning, parkering, soling, energi, ventilasjon og sammenligning.",
            "desktop_v2/src/chartTheme.ts: legger inn felles mørk grafpalett, tydeligere grid/akser/tooltips, datazoom-stil og normalisering av API-seriefarger.",
            "desktop_v2/src/components/AppShell.tsx: sørger for at temabytte oppdaterer grafene umiddelbart.",
            "desktop_v2/src/pages/*ComparisonPage.tsx og RevenueMonthPage.tsx: bruker felles akse- og seriestiler i sammenligningsgrafene.",
            "desktop_v2/src/pages/module/ModuleChartPanel.tsx og ventilation/VentilationCharts.tsx: gir generiske modulgrafene og ventilasjonsgrafene bedre kontrast i mørkt tema.",
            "desktop_v2/src/styles/dark-theme.css: synkroniserer mørke CSS-variabler og Recharts-kontrast med den nye grafpaletten.",
        ],
        "request": "Se over fargebruken spesielt på mørkt tema; noen av grafene sliter med å være synlige.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Mørke grafakser, gridlinjer, tooltips og legendetekster er gjort tydeligere.",
            "Seriefarger fra backend mappes til en lysere mørk-tema-palett når appen står i mørkt tema.",
            "Års-, måneds-, status-, ventilasjons- og generiske modulgrafene bruker samme kontrastregler.",
            "Temabytte oppdaterer grafopsjoner uten at siden må lastes manuelt på nytt.",
            "TypeScript, CSS-parse, produksjonsbuild, bundle-audit og UI smoke er kjørt lokalt.",
        ],
    },
    {
        "version": "1",
        "build": "1459",
        "date": "07.07.2026",
        "headline": "Manualer, systemkart og underapper er ryddet",
        "title": "Admin får klikkbare underapp-lenker og strammere CSS-lasting",
        "description": (
            "Build 1459 er en ekstra kvalitetsrunde med fokus på manualer, systemkart, CSS-lasting og "
            "profesjonell driftsoverflate. Systeminventoryen er utvidet til å være felles kilde for "
            "underapper, webflater, lokale URL-er og health-lenker."
        ),
        "applications": [
            "system_inventory.py: legger inn web_url, local_url, health_url og manglende underapper som vedlikehold mobil, OwnTracks database, proxy og koblingsmotor.",
            "main.py: oppdaterer Admin/Systemkart og Admin/Manual med klikkbare underapp-lenker og nye V2-ruter.",
            "desktop_v2/src/pages/module/moduleTableUtils.tsx: legger tydelige tabellnavn for drift, URL og systemkolonner.",
            "desktop_v2/src/pages/module/*.tsx: flytter spesialsider sin CSS til komponentene som faktisk bruker dem.",
            "templates/*.html: fjerner synlige lenker til gamle konto- og statusruter der V2-ruter finnes.",
            "tests/test_system_inventory.py: dekker at kjernekomponenter og webgrensesnitt er registrert.",
        ],
        "request": "Kjør igjennom en ekstra gang alt med CSS, ytelse og kvalitetsfølelse. Sørg for at manualene fungerer, har gode lenker, og at underappene har klikkbare webgrensesnitt.",
        "work_duration": "ca. 1 t",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Admin/Systemkart viser nå først underapper med webgrensesnitt, inkludert offentlig URL, lokal URL og health-lenke.",
            "Admin/Manual har direkte innganger til daglige arbeidsflater og underapper.",
            "Gamle synlige /konto- og /status/dashboard-lenker er erstattet med V2-ruter.",
            "Modulsiden laster mindre spesial-CSS på generiske sider ved at timeline-, soltime- og koble-CSS er flyttet til respektive komponenter.",
        ],
    },
    {
        "version": "1",
        "build": "1458",
        "date": "07.07.2026",
        "headline": "Nattlig kvalitetssjekk og frontend-opprydding",
        "title": "CSS-pakken er delt opp og ventilasjonsgrafen er ryddet",
        "description": (
            "Build 1458 er en systematisk kontrollrunde av Fibaro10 med fokus på drift, testdekning, "
            "frontendytelse, CSS og visuelle feil. Hoved-CSS er delt opp slik at V2 laster mindre "
            "global stilpakke, og ventilasjon/dagslogg viser nå bare faktiske av/på-skifter som "
            "vertikale markeringer."
        ),
        "applications": [
            "desktop_v2/src/main.tsx og sidekomponenter: flytter sidespesifikk CSS fra global import til lazy-loaded sider.",
            "desktop_v2/src/pages/ventilation/VentilationCharts.tsx: bruker filtrerte viftetransisjoner i diagram og hendelseslinjer.",
            "desktop_v2/src/pages/ventilation/ventilationHelpers.tsx: legger til stabil filtrering av reelle fan state transitions.",
            "main.py, import_jobs.py og owntracks_service/app/main.py: retter synlige norske tekster i oppgjør, Sun2-jobber og OwnTracks.",
            "desktop_v2/scripts/audit-bundle.mjs, route smoke og live smoke: verifiserer at CSS, routing og liveflater fortsatt er friske.",
        ],
        "request": "Ta en grundig gjennomgang av hele løsningen, sjekk funksjon, design og CSS, og fiks alt som trygt kan fikses uten å spørre.",
        "work_duration": "ca. 3 t",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Hoved-CSS er redusert fra rundt 155 KB til rundt 59 KB ved å flytte modulstiler til relevante lazy-ruter.",
            "Bundle-audit er grønn igjen uten unntak for stor CSS-fil.",
            "Ventilasjon/dagslogg viser ikke lenger en stripe av dupliserte viftehendelser.",
            "Norske tekster rundt oppgjør, Sun2-jobber og OwnTracks er ryddet for synlige ASCII-erstatninger.",
            "Full lokal test-, build-, route- og smoke-runde er kjørt før deploy.",
        ],
    },
    {
        "version": "1",
        "build": "1457",
        "date": "07.07.2026",
        "headline": "Dørstatus får egen side i V2",
        "title": "HC3 magnetfølere vises som dørstatus",
        "description": (
            "Build 1457 legger inn en egen Dører-side under Bygg og drift. "
            "Siden viser nåstatus for magnetfølerne 453, 447 og 413, siste endring, batteri og hendelseshistorikk."
        ),
        "applications": [
            "main.py: legger til /api/hc3/doors/status med nåstatus per dør og siste dørhendelser.",
            "desktop_v2/src/pages/DoorsPage.tsx: ny V2-side med statuskort og hendelsestabell.",
            "desktop_v2/src/api.ts og queryKeys.ts: legger til typed fetch for dørstatus.",
            "desktop_v2/src/moduleViews.ts, appNavigation.tsx og AppRoutes.tsx: legger Dører inn i meny og routing.",
            "desktop_v2/src/styles/doors.css og tokens.css: legger til kompakt statusdesign og domenefarge.",
            "desktop_v2/scripts/smoke-routes.mjs og tests/test_hc3_door_events.py: dekker ny rute/API.",
        ],
        "request": "Lag en faktisk statusvisning for dørene etter at HC3-magnetfølerne er koblet inn.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Ny meny: Bygg og drift → Dører.",
            "Tre statuskort viser Bod/kjøkken, Kjeller luke og Arbeidsrom.",
            "Åpen/lukket/ukjent vises tydelig med farge, sist endret, alder, batteri og råverdi.",
            "Siste dørhendelser vises i tabell med lenke videre til datakilden.",
        ],
    },
    {
        "version": "1",
        "build": "1456",
        "date": "07.07.2026",
        "headline": "HC3 dørhendelser logges i Fibaro10",
        "title": "Magnetfølere får egen dørhendelseslogg",
        "description": (
            "Build 1456 legger inn dedikert logging av magnetfølere fra HC3 til Fibaro10. "
            "Fibaro10 får egen door_events-tabell, API-endepunkt for HC3, datakildestatus og JSON-uttrekk. "
            "HC3-scenen logger device 453, 447 og 413 ved åpning/lukking."
        ),
        "applications": [
            "main.py: legger til DoorEvent-modell, DoorEventIn, /api/hc3/door-events og /api/hc3/door-events/json.",
            "import_jobs.py og observability.py: registrerer dørhendelser som datakilde og lagringstabell.",
            "scripts/hc3_door_event_logger.lua: ny HC3 Lua-scene for magnetfølere 453, 447 og 413.",
            "scripts/upsert_hc3_door_event_logger_scene.py: oppretter eller oppdaterer scenen i HC3 via API.",
            "migrations/versions/20260707_2130_add_hc3_door_events.sql: idempotent databaseskjema for door_events.",
            "tests/test_hc3_door_events.py: dekker API-rute, datakilde og Lua-scriptets enhetsliste.",
        ],
        "request": "Lag script og Fibaro10-støtte for å skrive til databasen hver gang magnetfølere 453, 447 og 413 åpnes/lukkes. Legg Lua-scenen rett inn i HC3.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Dørhendelser lagres i egen tabell med device, action, state, råverdi og batterinivå.",
            "HC3 kan poste direkte til /api/hc3/door-events uten brukerinnlogging, på samme måte som øvrige interne HC3-ingester.",
            "Datakilder viser siste mottatte dørhendelse.",
            "HC3-scenen kan kjøres manuelt for å sende nåværende status for alle tre sensorer.",
        ],
    },
    {
        "version": "1",
        "build": "1455",
        "date": "07.07.2026",
        "headline": "Varmepumper far egne mobilvalg",
        "title": "Vedlikehold mobil kan velge varmepumpe og tiltak",
        "description": (
            "Build 1455 utvider Varmepumper i vedlikeholdsappen. Registreringen viser naa tre valg for "
            "1.etg, 2.etg og VIP, med samme flervalgsmønster som robotvaskere. I tillegg kan brukeren "
            "velge tiltakene Renset filter og Endret innstilling, der Renset filter er valgt som standard."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: legger inn eget felt for generiske enhetsvalg og oppdaterer asset-versjon.",
            "maintenance_mobile/app/static/maintenance-mobile.js: legger varmepumpevalg, standardoppgaver, validering, tagger og automatisk sammendrag.",
            "maintenance_mobile/app/static/maintenance-mobile.css: styler varmepumpevalgene med samme chip-system som robotvaskere.",
            "build_log.py: registrerer build 1455.",
        ],
        "request": "Paa undersiden Varmepumpe skal man ha 3 valg som paa robotvaskere: 1.etg, 2.etg og VIP. Valgene i tillegg skal vaere Renset filter og Endret innstilling.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Varmepumper viser flervalg for 1.etg, 2.etg og VIP.",
            "Varmepumper viser tiltakene Renset filter og Endret innstilling.",
            "Renset filter er valgt som standard for nye varmepumpeposter.",
            "Lagring krever valgt varmepumpe og minst ett tiltak.",
            "Valgte varmepumper og tiltak lagres i target_name, tagger og automatisk sammendrag.",
        ],
    },
    {
        "version": "1",
        "build": "1454",
        "date": "07.07.2026",
        "headline": "Vedlikehold mobil samler toppfelt",
        "title": "Forside og undersider faar samme toppfelt med gul logostripe",
        "description": (
            "Build 1454 gjoer toppfeltet i vedlikeholdsappen mer konsekvent. Forsiden og undersidene bruker naa "
            "samme headerbakgrunn, samme gule stripe nederst og samme sentrerte tekstuttrykk. Undersidetitler "
            "sentreres mellom logo og spacer slik hovedtittelen er sentrert mellom logo og brukerknapp paa forsiden."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: oppdaterer asset-versjon.",
            "maintenance_mobile/app/static/maintenance-mobile.css: samler toppfeltbakgrunn, legger gul stripe og sentrerer undersidetitler.",
            "build_log.py: registrerer build 1454.",
        ],
        "request": "Legg en tynn gul stripe nederst paa toppfeltet, samme farge som i logoen. Sentrer teksten paa undersidene som paa forsiden og soerg for at alt er helt likt.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Forside og undersider bruker samme toppfeltbakgrunn.",
            "Begge toppfelt har en tynn gul stripe nederst.",
            "Undersidetitler er sentrert horisontalt som hovedtittelen.",
            "Asset-versjon er oppdatert for aa unngaa gammel mobilcache.",
        ],
    },
    {
        "version": "1",
        "build": "1453",
        "date": "07.07.2026",
        "headline": "Vedlikehold mobil strammer undersidetopp",
        "title": "Undersider faar eget toppfelt med riktig tekstplassering",
        "description": (
            "Build 1453 retter videre paa toppfeltet i vedlikeholdsappen. Undersidene hadde teknisk lik hoeyde, "
            "men tittelen laa for hoeyt og raden manglet tydelig visuell flate mot resten av siden. Undersidetoppen "
            "har naa egen lys headerflate, bunnlinje, svak skygge og bedre vertikal sentrering av tittel og tidspunkt."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: oppdaterer asset-versjon.",
            "maintenance_mobile/app/static/maintenance-mobile.css: gir undersidetopper egen headerflate, sticky plassering, bunnlinje og justert vertikal sentrering.",
            "build_log.py: registrerer build 1453.",
        ],
        "request": "Toppen paa undersidene er fortsatt feil; teksten staar for hoeyt og det er ingen fargeforskjell mellom toppfeltet og resten.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Undersidetoppen har naa synlig bakgrunnsfarge, bunnlinje og svak skygge.",
            "Tittel og tidspunkt sentreres bedre vertikalt mot logoen.",
            "Forside og undersider bruker samme horisontale marglogikk og cache-versjon.",
        ],
    },
    {
        "version": "1",
        "build": "1452",
        "date": "07.07.2026",
        "headline": "Robotvaskere far rengjort brett",
        "title": "Vedlikehold mobil utvider robotstandardoppgaver",
        "description": (
            "Build 1452 legger til Rengjort brett som eget standardvalg for Robotvaskere i mobilappen. "
            "Valget vises sammen med Rengjort, Skiftet mopper og Skiftet valse, og samme valgliste brukes "
            "naar egne robotposter aapnes for redigering."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: oppdaterer asset-versjon for mobilappen.",
            "maintenance_mobile/app/static/maintenance-mobile.js: legger Rengjort brett inn i standardoppgaver for robotvaskere og redigering av robotposter.",
            "build_log.py: registrerer build 1452.",
        ],
        "request": "Paa robotvaskerne mangler det et valg for Rengjort brett.",
        "work_duration": "ca. 5 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Robotvaskere har naa standardvalget Rengjort brett.",
            "Eksisterende robotposter som redigeres bruker samme standardoppgaveliste.",
            "Mobilappen peker paa ny asset-versjon slik at endringen ikke stoppes av cache.",
        ],
    },
    {
        "version": "1",
        "build": "1451",
        "date": "07.07.2026",
        "headline": "Vedlikehold mobil retter hopp i toppfelt",
        "title": "Forside og undersider får samme topplinjegeometri",
        "description": (
            "Build 1451 retter at logoen flyttet seg vertikalt mellom forsiden og undersidene i vedlikeholdsappen. "
            "Undersidemodus hadde ekstra topp-padding i app-shell, mens forsiden brukte app-topbar direkte. "
            "Undersidene bruker nå samme venstremarg, grid og høyde som forsiden, slik at logo og topplinje ikke hopper."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: oppdaterer asset-versjon.",
            "maintenance_mobile/app/static/maintenance-mobile.css: fjerner ekstra topp-padding på undersider og matcher topplinjehøyden mot forsiden.",
            "build_log.py: registrerer build 1451.",
        ],
        "request": "Toppen er fortsatt forskjellig på forside og underside, logoen hopper ned.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Undersider har ikke lenger ekstra topp-padding over toppfeltet.",
            "Undersidetoppene bruker samme horisontale margin som hovedtoppen.",
            "Undersidetoppens minstehøyde matcher hovedtoppen.",
            "Logoen skal ikke hoppe ned ved navigasjon fra forside til underside.",
        ],
    },
    {
        "version": "1",
        "build": "1450",
        "date": "07.07.2026",
        "headline": "Vedlikehold mobil far designopprydding",
        "title": "CSS, flater og kontroller strammes opp i vedlikeholdsappen",
        "description": (
            "Build 1450 er en samlet design- og CSS-opprydding i vedlikeholdsappen. Felles tokens for radius, "
            "flater og skygger er strammet opp, gamle regler for fjernede elementer er tatt bort, kort og knapper "
            "har fått roligere uttrykk, og valgchips/skjemafelt bruker en mer konsekvent farge- og størrelseslogikk. "
            "Inline tidspunkt i undersidetittelen er beholdt, men stylet mer som tekst og ikke som en egen farget knapp."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: oppdaterer asset-versjon og bruker HTML-entity for fallbacktekst på tidspunkt.",
            "maintenance_mobile/app/static/maintenance-mobile.css: rydder designvariabler, skygger, radius, kort, chips, skjema og toppfelt.",
            "maintenance_mobile/app/static/maintenance-mobile.js: fjerner gammel refresh-kobling til knapp som ikke lenger finnes.",
            "build_log.py: registrerer build 1450.",
        ],
        "request": "Ta en grundig gjennomgang av CSS og designet på denne appen. Det er en del avvik, stram opp.",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Felles radius- og skyggeverdier er innført for mer konsekvent uttrykk.",
            "Kort, oppgaveknapper og historikk har roligere skygge og mindre tunge rammer.",
            "Chips og aktive valg bruker samme grønne vedlikeholdsprofil.",
            "Skjemafelt, tidsfelt og toggles er justert til samme flate- og radiuslogikk.",
            "Gamle CSS-regler for fjernede elementer er fjernet.",
            "Gammel JS-lytter for fjernet refresh-knapp er tatt bort.",
        ],
    },
    {
        "version": "1",
        "build": "1449",
        "date": "07.07.2026",
        "headline": "Vedlikehold mobil finjusterer undersidetopper",
        "title": "Dato/tid flyttes inn i overskrift og undersider tones likere startsiden",
        "description": (
            "Build 1449 finjusterer undersidene i vedlikeholdsappen. Registreringssiden viser tidspunktet som "
            "klikkbar tekst etter komma i overskriften, i stedet for som en egen farget knapp. Undersidetitlene "
            "er venstrejustert, og bakgrunnsfargen rundt tidsfeltet er gjort mer nøytral slik at undersidene "
            "oppleves likere startsiden."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: flytter tidspunktknappen inn i registreringssidens overskrift og oppdaterer asset-versjon.",
            "maintenance_mobile/app/static/maintenance-mobile.css: venstrejusterer undersidetitler, gjør tidspunktet inline og nøytraliserer tidsfeltbakgrunn.",
            "build_log.py: registrerer build 1449.",
        ],
        "request": "Dato kan være etter komma i overskrift på undersidene, alt kan være venstrejustert, og bakgrunnsfargene bør gjøre undersidene likere hovedsiden.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Tidspunkt/dato vises etter komma i registreringssidens overskrift.",
            "Tidspunktet er fortsatt klikkbart og åpner samme tidsvelger.",
            "Undersidetitler er venstrejustert.",
            "Den fargede tidspunktknappen er fjernet.",
            "Tidsfeltets bakgrunn er gjort nøytral.",
        ],
    },
    {
        "version": "1",
        "build": "1448",
        "date": "07.07.2026",
        "headline": "Vedlikehold mobil far lik topp pa undersider",
        "title": "Registrering og profil bruker samme toppstruktur som startsiden",
        "description": (
            "Build 1448 gjor toppfeltet mer konsekvent i vedlikeholdsappen. Registreringssiden og brukersiden "
            "bruker na samme visuelle struktur som startsiden, med logo til venstre, sentrert tittel og funksjonsfelt "
            "til hoyre. Eksisterende funksjon er beholdt: logoen gar tilbake, og registreringssiden har fortsatt "
            "tidspunktknappen."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: merker undersidetopper som sub-topbar, legger spacer pa profilsiden og oppdaterer asset-versjon.",
            "maintenance_mobile/app/static/maintenance-mobile.css: fjerner kortutseende fra undersidetopper og matcher logo/tittel-strukturen fra startsiden.",
            "build_log.py: registrerer build 1448.",
        ],
        "request": "Toppen skal vaere lik ogsa pa undersidene, men med funksjonalitet som na.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Registreringssiden har samme toppstruktur som startsiden.",
            "Profilsiden har samme toppstruktur som startsiden.",
            "Logoen pa undersider beholder tilbakefunksjon.",
            "Tidspunktknappen pa registreringssiden er beholdt.",
            "Kortbakgrunn/ramme rundt undersidetoppen er fjernet.",
        ],
    },
    {
        "version": "1",
        "build": "1447",
        "date": "07.07.2026",
        "headline": "Vedlikehold mobil far roligere startflate",
        "title": "Topptekst sentreres og startoverskrift tas ut av kort",
        "description": (
            "Build 1447 rydder startsiden i vedlikeholdsappen. Toppbaren er gjort om til tre faste kolonner slik "
            "at teksten ligger sentrert mellom logo og brukerinitial, og teksten er flyttet litt ned for bedre "
            "visuell balanse. Startkortet er fjernet; startsiden viser na bare teksten Hva skal registreres?"
        ),
        "applications": [
            "maintenance_mobile/app/main.py: splitter toppbaren i logo, tittel og brukerknapp, fjerner startkortets ekstra tekst og oppdaterer asset-versjon.",
            "maintenance_mobile/app/static/maintenance-mobile.js: gjor userLine-oppdatering valgfri siden feltet er fjernet fra startsiden.",
            "maintenance_mobile/app/static/maintenance-mobile.css: sentrerer topptittel og styler startoverskriften uten kortbakgrunn.",
            "build_log.py: registrerer build 1447.",
        ],
        "request": "Teksten i toppen kan sentreres mellom logo og initial og flyttes litt ned. Boksen med Vedlikehold / Hva skal registreres skal fjernes, og det skal kun sta Hva skal registreres?",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Topplinjen bruker tre kolonner: logo, sentrert tittel og brukerinitial.",
            "Topptittelen er flyttet litt ned.",
            "Startkortet er fjernet fra startsiden.",
            "Startsiden viser bare Hva skal registreres? over oppgaveknappene.",
        ],
    },
    {
        "version": "1",
        "build": "1446",
        "date": "07.07.2026",
        "headline": "Vedlikehold mobil far egen brukerside",
        "title": "Brukersirkelen apner profilside med utlogging",
        "description": (
            "Build 1446 skiller brukerknappen og utloggingen i vedlikeholdsappen. Toppfeltet viser na bare en "
            "ren sirkel med brukerinitial, pa samme storrelse som logoen. Trykk pa sirkelen apner en egen "
            "brukerside med brukerinfo og logg-ut-knapp. Logoen pa brukersiden tar brukeren tilbake til startsiden."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: legger egen profilside og flytter logout-knappen dit.",
            "maintenance_mobile/app/static/maintenance-mobile.js: legger profilnavigasjon og brukerinfo fra bootstrap.",
            "maintenance_mobile/app/static/maintenance-mobile.css: styler ren brukersirkel og profilside.",
            "build_log.py: registrerer build 1446.",
        ],
        "request": "Brukerknappen skal bare vaere en sirkel med bokstav, like stor som logo og uten knappbakgrunn. Trykk skal apne en side med brukerinfo og logg-ut-knapp, og logoen skal ta tilbake.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Toppfeltet viser bare brukerinitial i en sirkel.",
            "Direkte logout fra toppfeltet er fjernet.",
            "Ny brukerside viser brukernavn, rolle og tilgang.",
            "Logg ut ligger som egen knapp pa brukersiden.",
            "Logoen pa brukersiden fungerer som tilbakeknapp.",
        ],
    },
    {
        "version": "1",
        "build": "1445",
        "date": "07.07.2026",
        "headline": "Vedlikehold mobil viser brukerknapp",
        "title": "Utloggingsknappen erstattes med innlogget bruker",
        "description": (
            "Build 1445 rydder toppfeltet i vedlikeholdsappen videre. Den gamle rene logout-knappen er erstattet "
            "med en kompakt brukerknapp som viser initial og brukernavn. Knappen beholder logout-funksjonen, men "
            "gjør det tydelig hvem som er innlogget."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: erstatter logout-ikonet med brukerknapp og oppdaterer asset-versjon.",
            "maintenance_mobile/app/static/maintenance-mobile.js: fyller brukerknappen med innlogget brukernavn og initial.",
            "maintenance_mobile/app/static/maintenance-mobile.css: styler brukerknappen kompakt i toppfeltet.",
            "build_log.py: registrerer build 1445.",
        ],
        "request": "Bruker kan være en knapp i stedet for logout-knappen.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Topplinjens høyre knapp viser innlogget bruker.",
            "Knappen viser initial og brukernavn.",
            "Logout-funksjonen er beholdt på samme knapp.",
            "Mobilasset-versjon er oppdatert for å bryte cache.",
        ],
    },
    {
        "version": "1",
        "build": "1444",
        "date": "07.07.2026",
        "headline": "Vedlikehold mobil far strammere toppfelt",
        "title": "Logo og appnavn justeres uten hoyere toppbar",
        "description": (
            "Build 1444 justerer toppfeltet i vedlikeholdsappen. Logoen er gjort litt storre, teksten er samlet "
            "pa en linje som Lilletorget, vedlikehold, og toppbaren beholder samme kompakte hoyde."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: samler appnavnet pa en linje og oppdaterer asset-versjon.",
            "maintenance_mobile/app/static/maintenance-mobile.css: oker logoen og sentrerer teksten uten a oke toppbarens hoyde.",
            "build_log.py: registrerer build 1444.",
        ],
        "request": "Gjor logoen i toppen litt storre uten a oke hoyden pa feltet. Lilletorget, vedlikehold skal sta pa en linje sentrert horisontalt i forhold til logo.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Logoen i mobilappens toppfelt er gjort storre.",
            "Teksten er samlet til Lilletorget, vedlikehold pa en linje.",
            "Toppfeltet er gjort mer kompakt for a unnga okning i hoyde.",
        ],
    },
    {
        "version": "1",
        "build": "1443",
        "date": "07.07.2026",
        "headline": "Robotvaskere far standardoppgaver",
        "title": "Vedlikehold mobil kan merke rengjort, mopper og valse",
        "description": (
            "Build 1443 gjor robotvaskerregistrering raskere i vedlikeholdsappen. Skjemaet viser na standardoppgaver "
            "over notatfeltet, med Rengjort valgt som standard. Brukeren kan velge flere oppgaver, og valgene lagres "
            "som tagger og tas med i automatisk sammendrag for nye robotposter. Notatfeltet er samtidig gjort lavere "
            "slik at skjermen bruker mindre plass."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: legger standardoppgavefelt i mobilskjemaet og oppdaterer asset-versjon.",
            "maintenance_mobile/app/static/maintenance-mobile.js: legger standardoppgaver, defaultvalg, validering, tagger og automatisk sammendrag.",
            "maintenance_mobile/app/static/maintenance-mobile.css: styler standardoppgaver og reduserer notatfeltets hoyde.",
            "build_log.py: registrerer build 1443.",
        ],
        "request": "Notatfeltet kan gjores litt lavere, og over det skal det ligge standardoppgaver man kan velge en eller flere av. Default skal Rengjort vaere markert. Valg: Rengjort, skiftet mopper, skiftet valse.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Robotvaskere viser standardoppgavene Rengjort, Skiftet mopper og Skiftet valse over notatfeltet.",
            "Rengjort er valgt som standard pa nye robotvaskerposter.",
            "Lagring krever minst en standardoppgave for robotvaskere.",
            "Valgte standardoppgaver lagres i tagger og automatisk sammendrag.",
            "Notatfeltet er gjort lavere for raskere mobilregistrering.",
        ],
    },
    {
        "version": "1",
        "build": "1442",
        "date": "07.07.2026",
        "headline": "Robotvaskere kan velges enkeltvis eller samlet",
        "title": "Vedlikehold mobil henter robotnavn fra Roborock og lagrer valgt robotgrunnlag",
        "description": (
            "Build 1442 utvider Robotvaskere i vedlikeholdsappen. Mobilappen henter robotnavn fra Fibaro10 sin "
            "renhold/Roborock-modul og viser dem som flervalg i registreringsskjemaet. Brukeren kan velge én, "
            "flere eller alle robotvaskere. Valget lagres i target_name, summary og tagger slik at historikken "
            "viser hvilken robot vedlikeholdet gjaldt."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: henter renhold-modul i bootstrap og eksponerer robotnavn som options. Legger robotfelt i mobilskjemaet.",
            "maintenance_mobile/app/static/maintenance-mobile.js: legger flervalg, Alle-knapp, validering og payload-mapping for robotvaskere.",
            "maintenance_mobile/app/static/maintenance-mobile.css: styler robotflervalget med samme mønster som romvalg.",
            "build_log.py: ny buildloggpost for robotvalg.",
        ],
        "request": "Det er 4 robotvaskere. Som med solsenger skal man kunne velge hvem vedlikeholdet gjelder, gjerne flere eller alle, med navn fra roboten selv.",
        "work_duration": "ca. 40 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Robotvaskere åpner et flervalg basert på Roborock-navn fra Fibaro10.",
            "Alle-knappen velger eller fjerner alle robotene.",
            "Lagring krever valgt robot når robotnavn finnes.",
            "Valgte robotnavn lagres i target_name og tagger; standardnotat oppdateres automatisk på nye poster.",
        ],
    },
    {
        "version": "1",
        "build": "1441",
        "date": "07.07.2026",
        "headline": "Vedlikehold mobil får fem enkle startvalg",
        "title": "Startsiden i vedlikeholdsappen viser lave enlinjeknapper",
        "description": (
            "Build 1441 forenkler startsiden i vedlikeholdsappen. Oppgavegridet er erstattet av fem lave "
            "knapper i én kolonne: Robotvaskere, Varmepumper, Solsenger, Kremautomat og Annet. Knappene viser "
            "bare én tekstlinje og åpner fortsatt registreringsskjemaet med riktige grunnverdier og tagger."
        ),
        "applications": [
            "maintenance_mobile/app/static/maintenance-mobile.js: erstatter aktiv oppgaveliste med fem hovedvalg og viser bare tittel på knappene.",
            "maintenance_mobile/app/static/maintenance-mobile.css: endrer startsiden fra 2-kolonne-kort til lav 1-kolonne-liste.",
            "maintenance_mobile/app/main.py: oppdaterer mobilasset-versjon.",
            "build_log.py: ny buildloggpost for startmenyen.",
        ],
        "request": "Knappene på første siden skal være lavere, én i bredden, begrenset til fem, og nederst skal det være Annet.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Startsiden viser Robotvaskere, Varmepumper, Solsenger, Kremautomat og Annet.",
            "Alle startknapper er én tekstlinje uten kode eller detaljtekst.",
            "Knappene ligger én per rad og er lavere enn de gamle kortene.",
            "Eksisterende registrerings- og redigeringsflyt er beholdt.",
        ],
    },
    {
        "version": "1",
        "build": "1440",
        "date": "07.07.2026",
        "headline": "Egne vedlikeholdsposter kan redigeres på mobil",
        "title": "Vedlikeholdsappen åpner egne registreringer for redigering",
        "description": (
            "Build 1440 gjør historikken i vedlikeholdsappen mer praktisk. Poster som er registrert av innlogget "
            "bruker kan trykkes på og åpnes i samme registreringsskjema for redigering. Lagre bruker PATCH mot "
            "eksisterende post i stedet for å opprette en ny. Mobilserveren sjekker også eierskap før endringen "
            "sendes videre til Fibaro10."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: legger PATCH-proxy for vedlikeholdsposter og sjekker at posten er brukerens egen.",
            "maintenance_mobile/app/static/maintenance-mobile.js: åpner egne historikkposter i redigeringsmodus og lagrer med PATCH.",
            "maintenance_mobile/app/static/maintenance-mobile.css: gjør egne historikkposter tydelige som trykkbare rader.",
            "build_log.py: ny buildloggpost for mobilredigering.",
        ],
        "request": "Det må være mulig å trykke på en allerede registrert oppgave, og hvis det er din egen skal den åpnes for redigering.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Egne historikkrader blir trykkbare i mobilappen.",
            "Skjemaet fylles med eksisterende tidspunkt, notat, rom, varighet og oppfølging.",
            "Lagreknappen bruker PATCH når en eksisterende post redigeres.",
            "Mobilserveren avviser forsøk på å redigere poster registrert av andre brukere.",
        ],
    },
    {
        "version": "1",
        "build": "1439",
        "date": "07.07.2026",
        "headline": "Renere registreringsheader mobil",
        "title": "Vedlikeholdsregistreringen viser bare oppgave, bruker og logo",
        "description": (
            "Build 1439 rydder toppen av registreringsskjermen i vedlikeholdsappen. Tilbakeknappen bruker "
            "sol/parkering-logoen uten tekst, og kategorioverskriften over oppgaven er fjernet slik at skjermen "
            "starter direkte med oppgavenavnet og hvem som registrerer."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: bytter tilbakepilen med Lilletorget sol/parkering-logo og fjerner kategorioverskrift.",
            "maintenance_mobile/app/static/maintenance-mobile.js: tolererer at taskCategory ikke finnes i registreringsheaderen.",
            "maintenance_mobile/app/static/maintenance-mobile.css: justerer logo-knappen og registreringsheaderen.",
            "build_log.py: ny buildloggpost for headeroppryddingen.",
        ],
        "request": "I toppen av vedlikeholdsregistreringen skal pila byttes med sol/parkering-logo uten tekst, og RENHOLD-overskriften skal bort.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Tilbakehandlingen er fortsatt tilgjengelig, men vises som sol/parkering-logo.",
            "Kategori/eyebrow over oppgaven er fjernet fra registreringsheaderen.",
            "Headeren viser oppgavenavn og hvem som registrerer.",
            "Mobilasset-versjon er oppdatert til 1439.",
        ],
    },
    {
        "version": "1",
        "build": "1438",
        "date": "07.07.2026",
        "headline": "Litt storre tekst i vedlikehold mobil",
        "title": "Registreringsskjermen i vedlikeholdsappen faar bedre lesbarhet",
        "description": (
            "Build 1438 oker fontstorrelse moderat paa registreringsskjermen i vedlikeholdsappen. "
            "Oppgavetittel, tidspunkt, romvalg, felttekst, tekstfelt og lagreknapp er gjort litt tydeligere "
            "uten aa endre hovedlayouten."
        ),
        "applications": [
            "maintenance_mobile/app/static/maintenance-mobile.css: justerer typografi paa registreringsskjermen.",
            "maintenance_mobile/app/main.py: oppdaterer mobilasset-versjon.",
            "build_log.py: ny buildloggpost for fontjusteringen.",
        ],
        "request": "Vurder om det er plass til aa oke fontstorrelsen noe paa registreringssiden.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Oppgavetittel og brukerlinje er litt storre.",
            "Tidspunktknappen er mer lesbar.",
            "Romknapper, labels og tekstfelt har litt storre tekst.",
            "Lagreknappen og oppfolgingslinjen matcher den nye skalaen.",
        ],
    },
    {
        "version": "1",
        "build": "1437",
        "date": "07.07.2026",
        "headline": "Renere vedlikeholdsregistrering",
        "title": "Vedlikeholdsappen fjerner unodige rammer og notatgjentakelse",
        "description": (
            "Build 1437 forenkler registreringsskjermen i vedlikeholdsappen. Den separate notatknappen er fjernet "
            "slik at oppgaven ikke gjentas som NOTAT + oppgavenavn, og selve skjemaet er gjort flatere med faerre "
            "rammer og mindre visuell stoy."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: viser notatfeltet direkte og oppdaterer mobilasset-versjon.",
            "maintenance_mobile/app/static/maintenance-mobile.js: holder notatfeltet synlig uten ekstra notatknapp.",
            "maintenance_mobile/app/static/maintenance-mobile.css: fjerner kortstil rundt skjemaet og rydder notatfeltet.",
            "build_log.py: ny buildloggpost for registreringsoppryddingen.",
        ],
        "request": "Registreringssiden har for mange rammer, og det er unodvendig aa gjenta NOTAT + oppgavenavn naar oppgaven allerede staar overst.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Notatfeltet vises direkte uten mellomliggende knapp.",
            "Oppgavenavnet gjentas ikke lenger i notatfeltets topp.",
            "Skjemaet har ikke lenger egen kortbakgrunn, border eller skygge.",
            "Bare faktiske kontroller som tekstfelt, romvalg og lagreknapp har tydelige rammer.",
        ],
    },
    {
        "version": "1",
        "build": "1436",
        "date": "07.07.2026",
        "headline": "Kompakt registrering i vedlikehold mobil",
        "title": "Registreringsskjermen i vedlikeholdsappen bruker mindre toppplass",
        "description": (
            "Build 1436 strammer inn registreringsskjermen i vedlikeholdsappen. Logo- og toppbanneret skjules "
            "naar man registrerer en oppgave, tilbakeknappen er redusert til en pil, og tidspunktfeltet ligger "
            "kompakt paa samme linje som oppgavetittelen."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: oppdaterer mobilasset-versjon og bytter tilbakeknappen til kompakt pil.",
            "maintenance_mobile/app/static/maintenance-mobile.js: setter entry-mode paa body naar registreringsskjermen vises.",
            "maintenance_mobile/app/static/maintenance-mobile.css: skjuler toppbanner paa registrering og komprimerer registreringsheaderen.",
            "build_log.py: ny buildloggpost for endringen.",
        ],
        "request": "Toppbanneret med logo trenger ikke vaere der paa registreringssiden, og registreringssiden skal bruke mindre plass paa overskrift, tidspunkt og tilbake.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Toppbanneret vises fortsatt paa startsiden, men skjules paa registreringsskjermen.",
            "Tilbakehandlingen er en kompakt pil med aria-label.",
            "Dato/tid beholdes som knapp, men tar mindre plass.",
            "Mobil-CSS legger ikke lenger tidspunktknappen ned paa egen rad.",
        ],
    },
    {
        "version": "1",
        "build": "1435",
        "date": "07.07.2026",
        "headline": "Raskere vedlikehold mobil",
        "title": "Vedlikeholdsappen paa mobil fokuserer riktig felt og viser relevant historikk",
        "description": (
            "Build 1435 gjor vedlikeholdsappen mer effektiv paa mobil. Naar en oppgave velges fra startsiden, "
            "settes fokus direkte til riktig felt: romvalg for sengoppgaver, oppfolging for avvik og notat for ovrige "
            "oppgaver. Historikken nederst filtreres etter valgt kategori slik at skjermen bare viser relevante poster."
        ),
        "applications": [
            "maintenance_mobile/app/static/maintenance-mobile.js: startfokus per oppgave, kategorifilter for historikk og oppdatert historikkflyt.",
            "maintenance_mobile/app/static/maintenance-mobile.css: tydelig fokusmarkering paa mobilknapper og romvalg.",
            "maintenance_mobile/app/main.py: cacheversjon for mobilassets, historikkoverskrift og storre historikkgrunnlag.",
            "build_log.py: ny buildloggpost for mobilappen.",
        ],
        "request": "Mobilgrensesnittet for vedlikehold maa vaere effektivt: markor til riktig felt og bare oppgaver fra valgt kategori nederst.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Oppgaveknapper sender brukeren rett til relevant felt etter valg.",
            "Seng- og romoppgaver fokuserer romvalgene.",
            "Avvik fokuserer oppfolgingsfeltet.",
            "Ovrige oppgaver aapner notatfeltet og markerer standardteksten for rask overskriving.",
            "Historikklisten viser bare poster som matcher valgt kategori eller oppgavens tagger.",
        ],
    },
    {
        "version": "1",
        "build": "1434",
        "date": "07.07.2026",
        "headline": "Grafitt morkt tema",
        "title": "Fibaro10 faar et roligere og mer profesjonelt morkt tema",
        "description": (
            "Build 1434 endrer det morke temaet fra blaa/svart og tung fargebruk til en mer noytral grafittpalett. "
            "Modulfargene brukes naa som markorer og aksenter i stedet for store fargede flater, slik at meny, toppfelt, "
            "kort, tabeller, diagrammer og portaler oppleves mer samlet og mindre slitende i bruk."
        ),
        "applications": [
            "desktop_v2/src/styles/dark-theme.css: ny grafittpalett, roligere meny, toppfelt, kort, tabeller, inputs og portalflater.",
            "desktop_v2/src/designTokens.ts: oppdaterte domenefarger og gridfarger for morkt tema.",
            "desktop_v2/src/chartTheme.ts: noytrale morke chartfarger for tooltip, akser og grid.",
            "build_log.py: ny buildloggpost for temaendringen.",
        ],
        "request": "Morkt tema er fortsatt ikke godt nok og maa forbedres grundig.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Store fargede aktive flater i toppmeny og venstremeny er erstattet med noytrale flater og tynne fargemarkeringer.",
            "Bakgrunnen er flyttet til en varmere grafittpalett med mindre blaa preg.",
            "Kort, tabeller, inputs, dropdowns, modaler og datepicker bruker samme morke flatesystem.",
            "Diagrammer har roligere grid, akser og tooltip som matcher resten av temaet.",
            "Status- og dashboardkort er dempet slik at domenefargene markerer innhold uten aa dominere skjermen.",
        ],
    },
    {
        "version": "1",
        "build": "1433",
        "date": "06.07.2026",
        "headline": "Polert morkt tema",
        "title": "Fibaro10 faar en grundig forbedret og mer balansert mork palett",
        "description": (
            "Build 1433 strammer opp det morke temaet med roligere domenefarger, mindre neonpreg og bredere dekning "
            "av spesialflater. Statuskort, oppgjor, tidslinjer, ventilasjon, ideer, energi, bildevisning, AntD-tags og "
            "diagramtema er tilpasset samme morke designsystem."
        ),
        "applications": [
            "desktop_v2/src/styles/dark-theme.css: ny balansert mork palett og flere modulspesifikke dark-overrides.",
            "desktop_v2/src/designTokens.ts: dynamiske domenefarger for morkt tema.",
            "desktop_v2/src/chartTheme.ts: morke chartfarger for tooltip, akser, grid og legend.",
            "desktop_v2/src/pages/ventilation/VentilationCharts.tsx: bruker felles charttema og mork off-markering.",
            "desktop_v2/src/pages/EnergySunbedsPage.tsx: bruker felles charttema og domenefarge for solsenggraf.",
            "build_log.py: ny buildloggpost for temaoppryddingen.",
        ],
        "request": "Gjor grundig forbedring av det morke temaet. Flere av fargene som er brukt er en utfordring.",
        "work_duration": "ca. 75 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Morkt tema bruker naa dempede, profesjonelle domenefarger i stedet for neonpreg.",
            "Aktive menyer og toppkontroller er tonet ned slik at de ikke blir hvite felter i mork flate.",
            "Status, oppgjor, tidslinjer, ventilasjon, ideer, energi og bildevisning har egne morke flater.",
            "Diagrammer bruker mork tooltip, akser, grid og legend der charttemaet benyttes.",
            "AntD-tags, alerts, checkbox, radio, switch, dropdowns og modaler er samordnet med mork palett.",
        ],
    },
    {
        "version": "1",
        "build": "1432",
        "date": "06.07.2026",
        "headline": "Morkt tema",
        "title": "Fibaro10 erstatter motlys med et reelt morkt tema",
        "description": (
            "Build 1432 endrer temabryteren fra Motlys til Morkt og gjor temaet gjennomfort morkt. "
            "Innholdsflate, kort, tabeller, skjema, menyer og portaler faar egne morke flater, tydeligere kontrast "
            "og beholdte domenefarger for omsetning, parkering, soling og energi."
        ),
        "applications": [
            "desktop_v2/src/components/AppShell.tsx: endrer tema-id til dark, migrerer gammelt sunlight-valg og viser Morkt i toppfeltet.",
            "desktop_v2/src/styles/dark-theme.css: nytt gjennomfort morkt tema for shell, kort, tabeller, skjema, dropdowns og diagramflater.",
            "desktop_v2/src/main.tsx: importerer dark-theme.css i stedet for tablet-contrast.css.",
            "build_log.py: ny buildloggpost for morkt tema.",
        ],
        "request": "Endre navnet til morkt og sorge for at det blir et bra morkt tema.",
        "work_duration": "ca. 40 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Temaknappen heter naa Morkt/Standard.",
            "Tidligere Motlys-valg paa enheten blir automatisk tolket som Morkt.",
            "Kort, tabeller, inputfelt, dropdowns og modalflater har morke kontrasttilpassede farger.",
            "Domenefargene er justert for mork bakgrunn slik at parkering, soling, energi og omsetning fortsatt er tydelige.",
        ],
    },
    {
        "version": "1",
        "build": "1431",
        "date": "06.07.2026",
        "headline": "Nytt motlystema",
        "title": "Fibaro10 faar et helt nytt motlystema med mork app-ramme og manuell temabryter",
        "description": (
            "Build 1431 erstatter den forsiktige tablet-kontrastjusteringen med et tydeligere motlystema. "
            "Temaet bruker mork topp- og sidemeny, mattere arbeidsbakgrunn, tydeligere kort og mer markante aktive farger. "
            "Det aktiveres automatisk paa iPad/tablet, men kan slas av og paa fra toppfeltet."
        ),
        "applications": [
            "desktop_v2/src/components/AppShell.tsx: legger til motlys/standard temabryter og lagrer valget lokalt.",
            "desktop_v2/src/styles/tablet-contrast.css: bygger nytt eksplisitt motlystema med mork app-ramme og roligere innholdsflate.",
            "build_log.py: ny buildloggpost for ny temaretning.",
        ],
        "request": "Forrige iPad-tema var litt bedre, men ikke bra. Tenk helt nytt.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Motlystema starter automatisk paa tablet-lignende skjermer.",
            "Toppfelt og venstremeny er gjort morkere for aa redusere stor lysflate.",
            "Innholdsflaten er matt blagraa med tydeligere kort, linjer og fargeankre.",
            "Temabryter i toppfeltet lar deg veksle mellom Standard og Motlys.",
        ],
    },
    {
        "version": "1",
        "build": "1430",
        "date": "06.07.2026",
        "headline": "Bedre iPad-kontrast",
        "title": "Fibaro10 faar egen tablet-kontrastprofil for bedre lesbarhet i motlys",
        "description": (
            "Build 1430 legger inn en egen CSS-profil for iPad/tablet og hoy-kontrastinnstillinger. Profilen demper "
            "de lyseste bakgrunnene, gjor tekst, linjer, kort, meny og toppfelt tydeligere, og bruker mer mettet "
            "farge paa aktive elementer."
        ),
        "applications": [
            "desktop_v2/src/styles/tablet-contrast.css: ny tablet-kontrastprofil med sterkere tekst, linjer, flater og menytilstand.",
            "desktop_v2/src/main.tsx: importerer kontrastprofilen sist slik at den overstyrer ordinart lyst tema.",
            "build_log.py: ny buildloggpost for temaendringen.",
        ],
        "request": "Tema paa Fibaro10 er for lyst og har for lite kontrast/farger paa iPad, spesielt i motlys.",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "iPad/tablet faar morkere sidebakgrunn og mindre blendende kortflater.",
            "Tekst, tabellhoder, kantlinjer og inputfelt faar mer kontrast.",
            "Venstremeny, toppmeny og aktiv modulmarkering faar tydeligere fargebruk.",
            "Desktop-temaet beholdes i hovedsak uendret.",
        ],
    },
    {
        "version": "1",
        "build": "1429",
        "date": "06.07.2026",
        "headline": "Kompakt oppgaveredigering",
        "title": "Vedlikehold/Besok faar ryddigere og mer kompakt oppgavedetalj",
        "description": (
            "Build 1429 strammer opp detaljvisningen for vedlikeholdsoppgaver. Metadatafeltene ligger naa i en "
            "kompakt grid, tekstfeltene bruker mindre hoyde og modaloppsettet er smalere og mer effektivt."
        ),
        "applications": [
            "desktop_v2/src/pages/module/MaintenanceVisitsPanel.tsx: komprimerer oppgaveformular og reduserer tekstfelthoyder.",
            "desktop_v2/src/styles/module-content.css: tettere modal, mindre marger og grid for metadatafeltene.",
            "build_log.py: ny buildloggpost for endringen.",
        ],
        "request": "Rydd og komprimer detaljvisningen av oppgave.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Oppgave-modal er redusert i bredde.",
            "Metadata vises i to kolonner der det passer.",
            "Notat og oppfolging bruker kortere standardhoyde.",
            "Marger og labelstorrelser er strammet opp.",
        ],
    },
    {
        "version": "1",
        "build": "1428",
        "date": "06.07.2026",
        "headline": "Besok som arbeidsflate",
        "title": "Vedlikehold/Besok faar egen oppgavevisning med klikkbare oppgaver og redigering",
        "description": (
            "Build 1428 bygger om Vedlikehold/Besok fra tabellorientert visning til en mer komplett arbeidsflate. "
            "Besok vises som en kompakt liste, valgt besok har tydeligere detaljer og oppgaver vises som egne klikkbare kort "
            "som kan aapnes og redigeres i en tilpasset modal."
        ),
        "applications": [
            "desktop_v2/src/pages/module/MaintenanceVisitsPanel.tsx: egen oppgaveflyt med kortliste og lokal redigeringsmodal.",
            "desktop_v2/src/pages/ModulePage.tsx: fjerner standard edit-prop fra spesialvisningen for Vedlikehold/Besok.",
            "desktop_v2/src/styles/module-content.css: ny styling for oppgavekort, oppgaveheader og modaloppsett.",
            "build_log.py: ny buildloggpost for endringen.",
        ],
        "request": "Gjor hele Besok-menyen bedre: liste, detaljer, oppgaver og mulighet for aa aapne/redigere oppgaver en og en.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Oppgaver vises som klikkbare arbeidskort i stedet for standard tabell.",
            "Klikk paa en oppgave aapner en egen todelt redigeringsmodal.",
            "Ny oppgave bruker samme modal og forhaandsutfylles med valgt besok.",
            "Besokslisten og valgt-besok-flaten er beholdt, men oppgaveflyten er ryddet opp.",
        ],
    },
    {
        "version": "1",
        "build": "1427",
        "date": "06.07.2026",
        "headline": "Polert vedlikeholdsvisning",
        "title": "Vedlikehold/Besok faar smalere besoksliste og ryddigere arbeidsflate",
        "description": (
            "Build 1427 strammer opp Vedlikehold/Besok visuelt. Besokslisten bruker omtrent en fjerdedel av bredden, "
            "valgt besok vises tydeligere, notatet ligger i egen skriveflate og oppgavene faar mer plass."
        ),
        "applications": [
            "desktop_v2/src/pages/module/MaintenanceVisitsPanel.tsx: rydder strukturen for valgt besok, notat og oppgaver.",
            "desktop_v2/src/styles/module-content.css: ny 1/4 + 3/4 layout, bedre listekort, aktivmarkering og kompakt notatflate.",
            "build_log.py: ny buildloggpost for vedlikeholdsoppryddingen.",
        ],
        "request": "Rydd opp og fikse grensesnittet slik at vedlikehold blir polert og bra, kanskje med 1/4 til besokslisten.",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Besokslisten er smalere og mer kompakt.",
            "Valgt besok har tydelig toppfelt og handlinger.",
            "Notatfeltet er flyttet til egen flate ved siden av nokkeldata.",
            "Oppgaver for valgt besok faar mer horisontal plass.",
        ],
    },
    {
        "version": "1",
        "build": "1426",
        "date": "06.07.2026",
        "headline": "Skrivbart besoksnotat",
        "title": "Vedlikehold/Besok kan skrive og lagre notat direkte paa valgt besok",
        "description": (
            "Build 1426 gjor besoksnotatet redigerbart direkte i master/detail-visningen paa Vedlikehold/Besok. "
            "Notatet lagres mot samme besoks-API som detaljsiden bruker, og moduldata oppdateres etter lagring."
        ),
        "applications": [
            "desktop_v2/src/pages/module/MaintenanceVisitsPanel.tsx: legger inn skrivbart notatfelt og lagreknapp for valgt besok.",
            "desktop_v2/src/styles/module-content.css: kompakt styling for notatfeltet i besoksdetaljene.",
            "build_log.py: ny buildloggpost for endringen.",
        ],
        "request": "Notat paa besok maa vaere mulig aa skrive.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Valgt besok viser et redigerbart notatfelt.",
            "Lagreknappen er deaktivert naar notatet ikke er endret.",
            "Etter lagring oppdateres baade Vedlikehold-modulen og eventuell besoksdetalj-cache.",
        ],
    },
    {
        "version": "1",
        "build": "1425",
        "date": "06.07.2026",
        "headline": "Besok med oppgaver i todelt visning",
        "title": "Vedlikehold/Besok viser besoksliste til venstre og oppgaver for valgt besok til hoyre",
        "description": (
            "Build 1425 gjor Vedlikehold/Besok til en master/detail-flate. Besokene ligger i en venstre kolonne "
            "paa omtrent en tredel av bredden, mens resten av flaten viser valgt besok og oppgavene som er koblet til det."
        ),
        "applications": [
            "desktop_v2/src/pages/module/MaintenanceVisitsPanel.tsx: ny todelt besoks- og oppgavevisning.",
            "desktop_v2/src/pages/ModulePage.tsx: Vedlikehold/Besok bruker spesialvisningen i stedet for standard tabellseksjoner.",
            "desktop_v2/src/styles/module-content.css: layout for 1/3 besoksliste og 2/3 oppgaveflate.",
        ],
        "request": "Besok skal ha en liste over besokene paa 1/3 av plassen, og resten skal vise oppgaver tilknyttet markert besok.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Valgt besok styrer oppgavetabellen til hoyre.",
            "Ny oppgave fra denne flaten forhaandsutfylles med valgt besok.",
            "Detaljknapp til eksisterende besoksside beholdes.",
        ],
    },
    {
        "version": "1",
        "build": "1424",
        "date": "06.07.2026",
        "headline": "Ryddigere vedlikeholdsmeny",
        "title": "Vedlikehold bruker toppmenyen som navigasjon og tabeller som seksjoner",
        "description": (
            "Build 1424 rydder overlappet i Vedlikehold mellom toppvelgeren og tab-fanen inne i tabellkortet. "
            "Vedlikehold beholder Oversikt/Besok i toppmenyen, mens tabellene vises som egne seksjoner under hverandre."
        ),
        "applications": [
            "desktop_v2/src/pages/ModulePage.tsx: Vedlikeholdstabeller rendres som stablede seksjoner i stedet for tab-faner.",
            "desktop_v2/src/styles/module-content.css: legger kompakt styling for søk og stablede tabellseksjoner.",
        ],
        "request": "Se paa overlapp i menyene paa Fibaro10 Vedlikehold, mellom horisontal toppmeny og undermeny.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Fjerner ekstra tab-nivaa paa Vedlikehold.",
            "Beholder toppmenyen som eneste navigasjon mellom Oversikt og Besok.",
            "Viser Vedlikeholdslogg, Siste Lilletorget-besok og Tagger som tydelige seksjoner.",
        ],
    },
    {
        "version": "1",
        "build": "1423",
        "date": "06.07.2026",
        "headline": "Klikkbare Lilletorget-besok",
        "title": "Vedlikeholdsbesok har egen detaljside med notat og oppgaver",
        "description": (
            "Build 1423 gjor siste Lilletorget-besok klikkbare fra Vedlikehold. Hvert besok har naa en egen "
            "detaljside med nokkeldata, notatfelt, radedata fra OwnTracks og redigerbare vedlikeholdsoppgaver."
        ),
        "applications": [
            "main.py: legger notatfelt paa site_visits, detalj-API for besok og lagring av besoksnotat.",
            "desktop_v2/src/pages/MaintenanceVisitDetailPage.tsx: ny detaljside for Lilletorget-besok.",
            "desktop_v2/src/pages/module/moduleTableUtils.tsx: tabellceller kan lenke via skjulte *_url-felter.",
            "desktop_v2/src/styles/records.css: kompakt layout for besoksdetaljer.",
        ],
        "request": "Siste besok Lilletorget bor vaere klikkbare og faa en underside som viser besoket med relevante data, notat og endring av oppgaver.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Starttidspunkt i besokstabeller lenker til egen detaljside.",
            "Besok har eget notatfelt som lagres i Fibaro10.",
            "Koblede vedlikeholdsoppgaver kan opprettes og redigeres fra besokssiden.",
            "Detaljsiden viser sentrale OwnTracks-felt og radedata for kontroll.",
        ],
    },
    {
        "version": "1",
        "build": "1422",
        "date": "05.07.2026",
        "headline": "Sun2 dagsfilflyt inn i QNAP-oppsett",
        "title": "Manglende Sun2 downloader/importer tas inn i standard compose og backup",
        "description": (
            "Build 1422 retter et funn fra systemgjennomgangen: Sun2 dagsfilnedlasting og romimport sto som "
            "aktive datakilder, men tjenestene var ikke med i hoved-QNAP-compose. De er naa lagt inn sammen med "
            "backup/restore-stotte for miljofiler og delt sun2_daily_data-katalog."
        ),
        "applications": [
            "docker-compose.qnap.yml: legger inn sun2_backfill_downloader og sun2_importer som faste tjenester.",
            ".env.qnap.example: dokumenterer SUN2_DAILY_DATA_DIR.",
            "scripts/qnap-backup.sh og scripts/qnap-full-restore-backup.sh: tar med Sun2 dagsfiler og .env-filer.",
        ],
        "request": "Gaa noye over og sjekk at alt fungerer og er logisk og godt designet.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Sun2 dagsfilnedlasting og romimport starter sammen med resten av Fibaro10-oppsettet.",
            "Datakildewarningene for Sun2 dagsfilflyt kan forsvinne etter neste vellykkede kjøring/import.",
            "Restore-backupen inneholder naa grunnlaget som trengs for aa sette opp flyten paa ny QNAP.",
        ],
    },
    {
        "version": "1",
        "build": "1421",
        "date": "05.07.2026",
        "headline": "OwnTracks-besok faar datakildestatus",
        "title": "Vedlikeholdsbesok synkes mer robust og vises som egen datakilde",
        "description": (
            "Build 1421 rydder i OwnTracks/Fibaro10-koblingen etter gjennomgang. Synkjobben rapporterer naa "
            "egen datakildestatus selv naar det ikke finnes Lilletorget-besok i perioden, og feil blir synlige "
            "i Admin/datakilder. Vedlikehold/Besok viser dermed bedre om grunnlaget faktisk er ferskt."
        ),
        "applications": [
            "main.py: OwnTracks-besokssynk logger suksess og feil til import_job_status.",
            "main.py: Vedlikehold/Besok henter synkstatus fra datakildestatus og finner koblede eldre besok.",
            "import_jobs.py: OwnTracks Lilletorget-besok er registrert som egen datakilde med forklaring.",
        ],
        "request": "Gaa noye over og sjekk at alt fungerer og er logisk og godt designet.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Datakildestatus viser naar Fibaro10 sist hentet OwnTracks-besok.",
            "Feil i synkjobben registreres som feilet datakilde i stedet for bare containerlogg.",
            "Koblede vedlikeholdslogger beholder korrekt besokslabel ogsaa naar besoket er eldre enn standardlisten.",
        ],
    },
    {
        "version": "1",
        "build": "1420",
        "date": "05.07.2026",
        "headline": "OwnTracks-besok kobles til vedlikehold",
        "title": "Fibaro10 synker Lilletorget-besok og kobler vedlikeholdsoppgaver automatisk",
        "description": (
            "Build 1420 gjor OwnTracks til kilde for opphold, mens Fibaro10 eier forretningshendelsen. "
            "Fibaro10 henter Lilletorget-besok fra OwnTracks API, lagrer dem i egen site_visits-tabell og "
            "kobler vedlikeholdslogg automatisk basert paa tidspunkt. Vedlikehold har naa en egen Besok-side."
        ),
        "applications": [
            "main.py: ny site_visits-modell, oppstartsindekser, OwnTracks-synkjobb og manuell synk-API.",
            "main.py: vedlikeholdslogg kobles automatisk til relevant Lilletorget-besok ved oppretting og redigering.",
            "main.py: Vedlikehold/Besok viser opphold, aktivt besok og koblede oppgaver.",
            "desktop_v2/src/moduleViews.ts: nytt Vedlikehold/Besok-menyvalg.",
            "desktop_v2/src/pages/module/moduleTableUtils.tsx: tabellnavn for besok og koblede oppgaver.",
            ".env.qnap.example og docs/owntracks-http.md: dokumenterer OwnTracks visits-API og Fibaro10-synk.",
        ],
        "request": "Gjor alt klart slik at Fibaro10 kan opprette hendelse for hvert besok paa Lilletorget og koble oppgavene som blir gjort der.",
        "work_duration": "ca. 90 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "OwnTracks skriver ikke direkte i Fibaro10-basen; Fibaro10 poller API og eier egne besoksrader.",
            "Vedlikeholdsposter faar site_visit_id naar tidspunktet matcher et Lilletorget-besok.",
            "Synkjobben gaar i bakgrunnen og kan trigges manuelt fra API.",
        ],
    },
    {
        "version": "1",
        "build": "1419",
        "date": "03.07.2026",
        "headline": "OwnTracks faar samme frontendrammeverk",
        "title": "Eget React/Vite/Ant Design-grensesnitt med venstremeny",
        "description": (
            "Build 1419 forbedrer OwnTracks-appen som selvstendig applikasjon. Den gamle innebygde HTML-siden "
            "erstattes i produksjon av et eget React/Vite/Ant Design-frontend med venstremeny, toppfelt, dashboard, "
            "kart, sonebesok, waypoints, meldinger, hendelser og buildlogg. FastAPI server fortsatt API-et og bruker "
            "gammel HTML som fallback dersom frontend_dist ikke er bygget."
        ),
        "applications": [
            "owntracks_service/frontend: nytt frontendprosjekt med React, TypeScript, Vite og Ant Design.",
            "owntracks_service/app/main.py: serverer bygget frontend og statiske assets.",
            "owntracks_service/Dockerfile: bygger frontend i Node-stage foer Python-imaget lages.",
            "scripts/check-local.ps1: inkluderer OwnTracks frontend typecheck/build i lokal kvalitetssjekk.",
            ".gitignore, .dockerignore og owntracks_service/.dockerignore: holder node_modules/dist ute av repo og Docker-kontekst.",
            "owntracks_service/app/build_log.py, docker-compose.qnap.yml og .env.qnap.example: OwnTracks build 5.",
        ],
        "request": "Kan du forbedre appen med venstremeny paa samme maate som Fibaro10, innfoere samme rammeverk.",
        "work_duration": "ca. 60 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "OwnTracks har samme type venstremeny og appskall som Fibaro10.",
            "Grensesnittet er delt i Dashboard, Kart, Sonebesok, Waypoints, Meldinger, Hendelser og Build.",
            "Produksjonsimaget bygger og serverer React-frontenden automatisk.",
        ],
    },
    {
        "version": "1",
        "build": "1418",
        "date": "03.07.2026",
        "headline": "OwnTracks beregnede sonebesok ryddes",
        "title": "Transition-meldinger lager ikke ekstra korte computed-position-besok",
        "description": (
            "Build 1418 retter neste OwnTracks-funn etter testtur. Waypoint-listen kunne se riktig ut, men "
            "transition enter/leave ble behandlet baade som eksplisitt hendelse og som vanlig posisjon i "
            "serverens radiusberegning. Dette kunne gi to og to sonebesok. Transition-meldinger holdes naa "
            "utenfor computed-position og faar ikke overskrive waypointets faste koordinater."
        ),
        "applications": [
            "owntracks_service/app/main.py: hopper over radiusberegning for transition og lar transition bare oppdatere status/hendelse.",
            "owntracks_service/app/build_log.py: registrerer OwnTracks build 4.",
            "docker-compose.qnap.yml og .env.qnap.example: oppdaterer OwnTracks build default til 4.",
            "tests/test_owntracks_service.py: legger regresjonstest for leave-transition uten ekstra beregnet besok.",
        ],
        "request": "Det ser jo riktig ut under waypoints, men vaare egne beregnede blir doble.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Transition enter/leave lager ikke lenger en ekstra computed-position-rad.",
            "Waypoint-koordinater beholdes fra Publish Waypoints og flyttes ikke av transition-posisjon.",
            "Ny test dekker at ett faktisk besok lukkes uten at et nytt aapnes fra samme leave-melding.",
        ],
    },
    {
        "version": "1",
        "build": "1417",
        "date": "03.07.2026",
        "headline": "OwnTracks sonebesok dupliseres ikke",
        "title": "Inregions og radiusberegning apner ikke samme sone to ganger",
        "description": (
            "Build 1417 retter en OwnTracks-feil der samme posisjonsmelding kunne gi to sonebesok med identisk "
            "starttid. Telefonen sender inregions samtidig som QNAP beregner radiusmatch selv. Begge signalene "
            "kunne treffe samme waypoint i samme database-session. Na caches apne sonebesok i sessionen slik at "
            "andre treff oppdaterer eksisterende rad."
        ),
        "applications": [
            "owntracks_service/app/main.py: cacher apne OwnTracksZoneVisit-rader per topic og waypoint i session.",
            "owntracks_service/app/build_log.py: registrerer OwnTracks build 3.",
            "docker-compose.qnap.yml og .env.qnap.example: oppdaterer OwnTracks build default til 3.",
            "tests/test_owntracks_service.py: legger regresjonstest for inregions + computed-position uten duplikat.",
        ],
        "request": "Hvorfor genererer den to poster med samme tidspunkt paa start?",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Samme posisjon kan ikke lenger apne samme waypoint to ganger.",
            "Rebuild av sonebesok rydder eksisterende duplikater etter deploy.",
            "OwnTracks buildnummer er oppdatert til 3.",
        ],
    },
    {
        "version": "1",
        "build": "1416",
        "date": "03.07.2026",
        "headline": "OwnTracks gammel adresse fjernes",
        "title": "OwnTracks publiserer kun paa eget domene og klargjoeres for tom database",
        "description": (
            "Build 1416 fullfoerer utskillingen av OwnTracks ved aa fjerne den gamle offentlige ruten via "
            "online.lilletorget.net/owntracks. Publisering skal naa skje via owntracks.lilletorget.net/pub. "
            "OwnTracks sin egen buildlogg oppdateres til build 2."
        ),
        "applications": [
            "Caddyfile: fjerner /owntracks-ruting fra online.lilletorget.net.",
            "owntracks_service/app/main.py: fjerner /owntracks/pub som publiseringsalias og legacy-informasjon fra status.",
            "owntracks_service/app/build_log.py: registrerer OwnTracks build 2.",
            "docker-compose.qnap.yml og .env.qnap.example: oppdaterer OwnTracks build default og fjerner legacy URL.",
            "docs/owntracks-http.md: fjerner overgangs-URL.",
            "tests/test_owntracks_service.py: tester ny /pub-rute og at legacy publish-ruten er borte.",
        ],
        "request": "Kan du tomme hele basen slik at jeg ser at det funker, fjern gammel adresse ogsaa.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Gammel online.lilletorget.net/owntracks-adresse er ikke lenger proxyet til OwnTracks.",
            "OwnTracks publisering skal bruke https://owntracks.lilletorget.net/pub?token=<token>.",
            "Database-toemming gjores paa QNAP etter deploy med backup foerst.",
        ],
    },
    {
        "version": "1",
        "build": "1415",
        "date": "03.07.2026",
        "headline": "OwnTracks skilles ut paa eget domene",
        "title": "OwnTracks faar owntracks.lilletorget.net, egen buildlogg og egen appflate",
        "description": (
            "Build 1415 skiller OwnTracks tydeligere ut fra Fibaro10 uten aa bytte database. Tjenesten faar eget "
            "Caddy-vhost-oppsett for owntracks.lilletorget.net, egen root-side, /pub-endepunkt, egen buildlogg og "
            "eksplisitt runtime-konfig. Gammel online.lilletorget.net/owntracks-rute beholdes som overgang."
        ),
        "applications": [
            "Caddyfile: legger til owntracks.lilletorget.net og blokkerer uautorisert eksponering av interne /api/owntracks-ruter.",
            "docker-compose.qnap.yml og .env.qnap.example: legger inn OwnTracks public URL, legacy URL og eget buildnummer.",
            "owntracks_service/app/main.py: legger root-admin, /pub-alias, public URL-info, buildstatus og buildlogg inn i tjenesten.",
            "owntracks_service/app/build_log.py: ny egen buildlogg for OwnTracks.",
            "docs/owntracks-http.md og system_inventory.py: oppdaterer arkitektur, adresser og driftsinformasjon.",
            "tests/test_owntracks_service.py: dekker ny root-side, /pub og egen buildlogg.",
        ],
        "request": "Kjor paa gjor alt unntatt database naa med en gang. Jeg legger inn domenepeker mot samme IP.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny anbefalt OwnTracks URL er https://owntracks.lilletorget.net/pub?token=<token>.",
            "Administrasjon ligger paa https://owntracks.lilletorget.net/ med tokenbeskyttelse.",
            "SQLite-datafilen beholdes uendret.",
        ],
    },
    {
        "version": "1",
        "build": "1414",
        "date": "03.07.2026",
        "headline": "OwnTracks waypoint-rebuild hindrer duplikate pending rader",
        "title": "Waypoint-rader caches under normalisering av historiske OwnTracks-meldinger",
        "description": (
            "Build 1414 retter enda en oppstartskant i OwnTracks normalisering. Flere historiske meldinger kan "
            "inneholde samme waypoint-navn på samme base-topic. Rebuild caches nå også waypoint-rader per "
            "topic/navn slik at samme rad oppdateres i stedet for å forsøkes opprettet flere ganger."
        ),
        "applications": [
            "owntracks_service/app/main.py: cacher OwnTracksWaypointState per topic og waypoint-navn under rebuild.",
            "build_log.py: dokumenterer stabiliseringsrettelsen.",
        ],
        "request": "OwnTracks-service restartet videre på unik constraint for waypoint-rader under historisk rebuild.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Hindrer duplikate pending OwnTracksWaypointState-rader i samme database-session.",
            "Beholder normalisert topic-modell og app-kompatibel HTTP-respons.",
        ],
    },
    {
        "version": "1",
        "build": "1413",
        "date": "03.07.2026",
        "headline": "OwnTracks oppstartsrebuild er stabilisert",
        "title": "Device-rader caches under rebuild slik at samme telefon ikke opprettes flere ganger",
        "description": (
            "Build 1413 retter en oppstartsfeil i OwnTracks-service fra build 1412. Når gamle topic-suffikser ble "
            "normalisert, kunne flere meldinger for samme telefon forsøke å opprette samme device-rad før commit. "
            "Rebuild bruker nå en session-cache og oppdaterer samme rad gjennom hele kjøringen."
        ),
        "applications": [
            "owntracks_service/app/main.py: cacher OwnTracksDevice per topic under rebuild og vanlig ingest.",
            "build_log.py: dokumenterer oppstartsrettelsen.",
        ],
        "request": "OwnTracks-service restartet etter opprydding av waypoint-topics og må stabiliseres.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Hindrer duplikate pending OwnTracksDevice-rader i samme database-session.",
            "Beholder topic-normalisering og waypoint-opprydding fra build 1412.",
        ],
    },
    {
        "version": "1",
        "build": "1412",
        "date": "03.07.2026",
        "headline": "OwnTracks waypoints samles på riktig enhet",
        "title": "Waypoint-, waypoints- og event-topic normaliseres til samme telefon",
        "description": (
            "Build 1412 rydder OwnTracks-datamodellen etter at Publish Waypoints begynte å komme inn. Android sender "
            "topic-varianter som /waypoint, /waypoints og /event. Disse normaliseres nå til samme enhet, slik at "
            "waypoint-listen speiler telefonens definerte waypoints uten duplikater fra transition-events."
        ),
        "applications": [
            "owntracks_service/app/main.py: normaliserer OwnTracks-topic og bygger avledede waypoint-tabeller på nytt ved behov.",
            "tests/test_owntracks_service.py: dekker topic-suffikser og transition uten definert waypoint.",
        ],
        "request": "Publish Waypoints kommer inn, men Waypoints skal kun vise de som ligger på telefonen og ikke avledede duplikater.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Lagrer OwnTracks-meldinger under base-topic for telefonen.",
            "Transition-events oppretter ikke lenger egne waypoint-rader når waypoint ikke allerede er definert.",
            "Ved oppstart normaliseres gamle suffix-topics og avledede tabeller bygges ryddig opp igjen.",
        ],
    },
    {
        "version": "1",
        "build": "1411",
        "date": "03.07.2026",
        "headline": "OwnTracks HTTP svarer med riktig JSON-format",
        "title": "Publish-endepunktet returnerer tom JSON-array slik OwnTracks forventer",
        "description": (
            "Build 1411 retter HTTP-responsen fra OwnTracks-mottaket. OwnTracks Android forventer at et vellykket "
            "HTTP-publish svarer med en JSON-array, normalt []. Endepunktet lagrer fortsatt meldingen internt, men "
            "returnerer ikke lenger et statusobjekt som appen tolker som feil JSON-format."
        ),
        "applications": [
            "owntracks_service/app/main.py: /owntracks/pub returnerer [] etter vellykket lagring.",
            "tests/test_owntracks_service.py: HTTP-publish-testene forventer OwnTracks-kompatibel respons.",
        ],
        "request": "OwnTracks viser statusfeil: java.io.IOExp: Failed to parse Json etter Publish Waypoints.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Rettet vellykket HTTP-respons fra JSON-objekt til tom JSON-array.",
            "Beholdt lagring og waypoint-normalisering uendret.",
            "Oppdatert testene slik at protokollformatet mot appen kontrolleres.",
        ],
    },
    {
        "version": "1",
        "build": "1410",
        "date": "03.07.2026",
        "headline": "OwnTracks tar imot Publish Waypoints mer robust",
        "title": "Waypoint-publisering fra Android kan komme som liste eller innpakket payload",
        "description": (
            "Build 1410 retter mottaket for Publish Waypoints i OwnTracks Android. Waypoints skal ikke utledes fra "
            "vanlige inregions i posisjonsmeldinger; de skal speiles fra faktiske waypoint-publiseringer. "
            "HTTP-mottaket godtar derfor waypoint-payloads som ren JSON-liste, som innpakket waypoints/data/wps "
            "eller som enkelt-waypoint uten eksplisitt _type."
        ),
        "applications": [
            "owntracks_service/app/main.py: normaliserer Publish Waypoints-format for HTTP-inntak.",
            "tests/test_owntracks_service.py: dekker ren waypoint-liste og innpakket waypoint-payload.",
        ],
        "request": "Waypoints kommer ikke inn selv om jeg legger inn nye i appen. Det finnes et valg som heter Publish Waypoints.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Waypoints-listen fylles bare fra faktiske waypoint-publiseringer.",
            "Ren JSON-liste fra Publish Waypoints behandles som _type=waypoints.",
            "Payload med waypoints, wps eller data behandles som _type=waypoints selv om _type mangler.",
            "Enkelt-waypoint med navn og koordinater behandles som _type=waypoint selv om _type mangler.",
        ],
    },
    {
        "version": "1",
        "build": "1409",
        "date": "03.07.2026",
        "headline": "OwnTracks godtar riktig URL-token selv med Basic Auth-felter",
        "title": "Retter HTTP-tokenprioritering for OwnTracks Android",
        "description": (
            "Build 1409 retter en feil der OwnTracks kunne sende riktig token i URL-en samtidig som appens "
            "Basic Auth-felt sendte et annet eller tomt passord. Serveren prioriterte tidligere Basic Auth over "
            "query-token og avviste derfor meldingen med 401. Na godtas meldingen hvis en av tokenkildene matcher."
        ),
        "applications": [
            "owntracks_service/app/main.py: samler tokenkandidater fra query, X-OwnTracks-Token, Bearer og Basic Auth.",
            "owntracks_service/Dockerfile: skrur av access-logg slik at query-token ikke havner i containerloggen.",
            "tests/test_owntracks_service.py: legger regresjonstest for riktig query-token kombinert med feil Basic Auth.",
        ],
        "request": "OwnTracks appen sender data hele tiden pa Move, men det kommer ikke inn noe.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "HTTP POST fra OwnTracks avvises ikke lenger hvis riktig token ligger i URL-en.",
            "Basic Auth kan fortsatt brukes alene nar passordet er riktig token.",
            "Token blir ikke lenger skrevet i uvicorn access-logg.",
        ],
    },
    {
        "version": "1",
        "build": "1408",
        "date": "03.07.2026",
        "headline": "OwnTracks far eget token-beskyttet webgrensesnitt",
        "title": "Standalone OwnTracks kan kontrolleres direkte uten Fibaro10",
        "description": (
            "Build 1408 legger inn en enkel administrasjonsside i owntracks_service. Siden viser status, enheter, "
            "siste posisjoner, waypoints, waypoint-hendelser og beregnede sonebesok. Eksterne visnings-API-er under "
            "/owntracks/api krever samme token som mobilpubliseringen, slik at posisjonsdata ikke ligger apent."
        ),
        "applications": [
            "owntracks_service/app/main.py: legger til token-beskyttet webgrensesnitt, kart, tabeller og eksterne API-aliaser.",
            "docs/owntracks-http.md: dokumenterer visningsside og tokenbruk.",
            "tests/test_owntracks_service.py: dekker at OwnTracks-service og administrasjonsside responderer riktig.",
        ],
        "request": "Lag et grensesnitt pa OwnTracks-serveren hvor jeg kan se det som kommer inn, men ikke la det ligge helt apent.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny side: https://online.lilletorget.net/owntracks.",
            "Siden viser siste posisjoner, enheter, waypoints, sonebesok og hendelser.",
            "Kartet viser spor, siste enhetsposisjon og waypoint-radius.",
            "Eksterne visningsendepunkter krever token eller Basic Auth.",
            "Lokal /health pa QNAP-porten er fortsatt tilgjengelig for intern helsesjekk.",
        ],
    },
    {
        "version": "1",
        "build": "1407",
        "date": "03.07.2026",
        "headline": "OwnTracks flyttes ut av Fibaro10 som ren HTTP-tjeneste",
        "title": "Egen applikasjonsserver for OwnTracks etableres uten MQTT-broker",
        "description": (
            "Build 1407 tar OwnTracks ut av Fibaro10 sin runtime og legger inn en separat FastAPI-tjeneste. "
            "Den nye tjenesten tar imot HTTP-publisering, lagrer data i egen SQLite-database "
            "og eksponerer egne API-endepunkter for en senere kontrollert integrasjon tilbake til Fibaro10."
        ),
        "applications": [
            "owntracks_service: ny FastAPI-app med HTTP-inntak, egen lagring, waypoint-tolkning og sonebesok.",
            "main.py: fjerner OwnTracks-modeller, worker, startup-opprydding, adminvisning og API-ruter fra Fibaro10.",
            "desktop_v2: fjerner OwnTracks adminside, route, API-typer og CSS fra Fibaro10-grensesnittet.",
            "docker-compose.qnap.yml og Caddyfile: legger til owntracks_service og ruter /owntracks dit.",
            "scripts/deploy-qnap.ps1: tar backup av owntracks_service/data, fjerner gammel broker-container og deployer ny tjeneste.",
        ],
        "request": "Fjern alt med OwnTracks i Fibaro10. Bygg forst serveren pa utsiden; nar den fungerer lager vi API som Fibaro10 kan hente fra.",
        "work_duration": "ca. 60 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Fibaro10 abonnerer ikke lenger pa OwnTracks MQTT.",
            "OwnTracks adminside og API-ruter er fjernet fra Fibaro10.",
            "Ny standalone tjeneste eier datainntak, lagring og beregning.",
            "Caddy sender /owntracks til standalone-tjenesten.",
            "Mosquitto-broker og MQTT-websocket-rute er fjernet fra deploy-oppsettet.",
        ],
    },
    {
        "version": "1",
        "build": "1406",
        "date": "03.07.2026",
        "headline": "OwnTracks fÃ¥r Fibaro10-beregnet sonebesÃ¸k",
        "title": "Presise posisjoner brukes til egne kom/gikk-besÃ¸k",
        "description": (
            "Build 1406 legger inn en separat OwnTracks-beregning hvor Fibaro10 bruker definerte waypoints og faktiske "
            "posisjonsmeldinger til Ã¥ lage egne sonebesÃ¸k. BesÃ¸kene lagres i egen tabell med start, slutt, varighet, "
            "avstand til senter, nÃ¸yaktighet og tillit. Kartet viser beregnede kom/gikk-punkter i tillegg til rÃ¥spor og "
            "OwnTracks sine egne waypoint-hendelser."
        ),
        "applications": [
            "main.py: legger til owntracks_zone_visits, materialisering fra posisjonsmeldinger, rebuild ved oppstart og API-data for kart.",
            "desktop_v2/src/api.ts: utvider OwnTracks kartkontrakten med beregnede sonebesÃ¸k.",
            "desktop_v2/src/pages/OwnTracksPage.tsx: tegner beregnede kom/gikk-punkter og besÃ¸kslinjer pÃ¥ kartet.",
            "desktop_v2/src/styles/owntracks.css: legger til forklaring for beregnet besÃ¸k.",
            "desktop_v2/src/pages/module/moduleTableUtils.tsx: legger til kolonnenavn for avstand, nÃ¸yaktighet og tillit.",
        ],
        "request": "Lag egen waypoint-side/logikk der Fibaro10 bruker presise OwnTracks-posisjoner og definerte lokasjoner til egne enter/leave-besÃ¸k.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Beregnet sonebesÃ¸k lagres separat fra rÃ¥ OwnTracks-hendelser.",
            "Nye OwnTracks-meldinger oppdaterer sonebesÃ¸k fortlÃ¸pende.",
            "Eksisterende historikk bygges opp igjen ved oppstart.",
            "Kartet viser kom/gikk-punkter med klokkeslett, avstand og tillit.",
        ],
    },
    {
        "version": "1",
        "build": "1405",
        "date": "03.07.2026",
        "headline": "OwnTracks rydder gamle dublette sonehendelser",
        "title": "Inn/ut-hendelser dedupliseres ved oppstart",
        "description": (
            "Build 1405 legger inn en egen opprydding for OwnTracks-hendelser som tidligere kunne bli liggende dobbelt "
            "når både transition-melding og syntetisk inregions-tolkning traff samme tidspunkt. Oppryddingen beholder den "
            "beste hendelsen, normalt ekte transition foran syntetisk event, og gjør Sonebesøk-listen ryddigere."
        ),
        "applications": [
            "main.py: legger til cleanup_owntracks_waypoint_event_duplicates og kjører den ved oppstart.",
            "build_log.py: registrerer build 1405.",
        ],
        "request": "Fullfør OwnTracks-oppryddingen slik at waypoint-loggingen blir forståelig og uten gamle dubletter.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Dublette enter/leave-hendelser innenfor samme korte tidsvindu fjernes.",
            "Ekte transition-events prioriteres foran syntetiske events når samme hendelse finnes flere ganger.",
            "Oppryddingen kjøres automatisk ved Fibaro10-oppstart.",
        ],
    },
    {
        "version": "1",
        "build": "1404",
        "date": "03.07.2026",
        "headline": "OwnTracks viser senterpunkt og sonebesøk tydeligere",
        "title": "Waypoint-sentre skilles fra telefonposisjon og besøk logges ryddigere",
        "description": (
            "Build 1404 gjør OwnTracks-feilsøkingen mer presis. Opprettede waypoint-sentre hentes fra rå "
            "waypoint-definisjoner og markeres separat i kartet, slik at det er lett å se om koordinatene eller radiusen "
            "er satt feil. Backend bevarer senterpunktet ved inn/ut-hendelser, reparerer tidligere overskrevne senterpunkt "
            "ved oppstart, de-dupliserer nye waypoint-hendelser og viser sonebesøk med inn, ut og varighet."
        ),
        "applications": [
            "main.py: bevarer og reparerer OwnTracks waypoint-sentre, legger til server-side geofence-toleranse og lager Sonebesøk-tabell.",
            "desktop_v2/src/pages/OwnTracksPage.tsx: viser opprettede senterpunkt og radius som egen oransje kartserie.",
            "desktop_v2/src/api.ts: utvider OwnTracks kartkontrakten med waypointDefinitions.",
            "desktop_v2/src/styles/owntracks.css: legger til kartforklaring for opprettet senterpunkt.",
            "desktop_v2/src/pages/module/moduleTableUtils.tsx: legger til norske kolonnenavn for sonebesøk.",
            "tests/test_owntracks_waypoints.py: dekker event-aliaser, varighet og paring av inn/ut-hendelser.",
            "build_log.py: registrerer build 1404.",
        ],
        "request": (
            "OwnTracks loggingen fanger ikke opp alle waypoints. Lag kartvisning der senterpunktet i hver opprettet "
            "posisjon markeres, og vurder om koordinater/radius kan være feil."
        ),
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Opprettede waypoint-sentre markeres separat i OwnTracks-kartet.",
            "Siste sone-status overskriver ikke lenger senterkoordinatene.",
            "Tidligere overskrevne senterpunkt repareres fra rå waypoint-definisjoner ved oppstart.",
            "Nye inn/ut-hendelser de-dupliseres slik at transition-meldinger ikke dobbelregistreres med syntetiske events.",
            "Sonebesøk vises som egen tabell med kom inn, dro ut, varighet og status.",
            "Server-side geofence-toleranse fanger opp stasjonære/WiFi-posisjoner der OwnTracks sender inregions tomt.",
        ],
    },
    {
        "version": "1",
        "build": "1403",
        "date": "03.07.2026",
        "headline": "Vedlikehold mobil blir raskere i bruk",
        "title": "Registrering krever færre trykk og mindre tasting",
        "description": (
            "Build 1403 optimaliserer mobilflaten for praktisk bruk på stedet. Oppgaver åpner ikke lenger tastaturet "
            "automatisk, notatfeltet er skjult til det trengs, og seng/rom kan velges med store hurtigknapper. "
            "Lagreknappen blir tydeligere og ligger lett tilgjengelig nederst mens man fyller ut."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: legger til hurtigvalg for rom/seng, sammenleggbar notatseksjon og melding etter lagring.",
            "maintenance_mobile/app/static/maintenance-mobile.js: styrer romknapper, notatvisning, lagretilstand og standardtekst for summary.",
            "maintenance_mobile/app/static/maintenance-mobile.css: gjør romvalg, notatknapp, lagremelding og sticky lagreknapp mobilvennlig.",
        ],
        "request": "Forbedre vedlikeholdsappen slik at den blir mest mulig effektiv og brukervennlig i bruk.",
        "work_duration": "ca. 40 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Tastaturet åpnes ikke automatisk når en oppgave velges.",
            "Notat ligger bak en knapp og bruker oppgavens standardtekst hvis feltet ikke fylles ut.",
            "Seng/rom velges med store hurtigknapper for oppgaver som krever rom.",
            "Lagreknappen deaktiveres til nødvendig seng/rom er valgt.",
            "Etter lagring returnerer appen til oppgavevalg og viser en kompakt lagret-melding.",
        ],
    },
    {
        "version": "1",
        "build": "1402",
        "date": "03.07.2026",
        "headline": "Vedlikehold mobil får enklere registrering",
        "title": "Utført av fjernes som felt og tidspunkt flyttes til toppknapp",
        "description": (
            "Build 1402 gjør registreringsskjermen i mobilappen mer effektiv. Utført av fylles nå automatisk fra innlogget "
            "Fibaro10-bruker og vises bare som liten metadata. Tidspunkt ligger som en knapp i toppen og åpner redigering "
            "bare når tidspunktet faktisk må korrigeres."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: flytter tidspunktkontroll til toppfeltet og gjør utført av til skjult automatisk verdi.",
            "maintenance_mobile/app/static/maintenance-mobile.js: oppdaterer tidspunktknapp, automatisk brukerlinje og payload for vedlikeholdslogg.",
            "maintenance_mobile/app/static/maintenance-mobile.css: strammer toppfelt og skjuler tidsfeltet til det trengs.",
        ],
        "request": (
            "Utført av er unødvendig som eget felt og kan ligge som liten tekst. Dato/tid bør flyttes inn på en knapp "
            "i øverste felt siden det sjelden må endres i appen."
        ),
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Registreringsskjemaet har ikke lenger synlig felt for utført av.",
            "Innlogget bruker sendes fortsatt med ved lagring og vises som liten tekst under oppgaven.",
            "Tidspunkt vises som kompakt knapp i toppen.",
            "Trykk på tidspunktknappen åpner datetime-feltet for korrigering.",
            "Asset-versjon er oppdatert slik at mobilnettlesere henter ny JS/CSS.",
        ],
    },
    {
        "version": "1",
        "build": "1401",
        "date": "03.07.2026",
        "headline": "Vedlikehold mobil får oppgaveknapper",
        "title": "Mobilflaten forenkles til 8 store vedlikeholdsvalg",
        "description": (
            "Build 1401 gjør vedlikeholdsappen enklere å bruke på mobil. Første skjerm er nå en 2x4-flate med store "
            "oppgaveknapper. Når en oppgave velges, åpnes et smalt registreringsskjema der riktig oppgavetype, objekt, "
            "status, prioritet og tagger settes automatisk."
        ),
        "applications": [
            "maintenance_mobile/app/main.py: bytter startsiden til oppgavevalg og egen registreringsskjerm.",
            "maintenance_mobile/app/static/maintenance-mobile.js: legger inn oppgavepresets, automatisk tagging og forenklet lagringspayload.",
            "maintenance_mobile/app/static/maintenance-mobile.css: bygger 2x4 mobilgrid med store knapper og strammere registreringsskjema.",
        ],
        "request": (
            "Forenkle vedlikeholdsappen. Første skjerm skal ha 8 store knapper, 4 rader og 2 i bredden, som går videre "
            "til mobilskjerm for utfylling. Start med Rens støvsugere, og automatisk tagg oppgaven med dato og type."
        ),
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Første skjerm viser åtte faste oppgavevalg, inkludert Rens støvsugere.",
            "Valgt oppgave fyller automatisk ut objekt, tiltak, prioritet, status og standardnotat.",
            "Seng/rom vises bare for oppgaver som trenger det.",
            "Lagring sender automatiske tagger for oppgave, kategori, mobilregistrering og dato.",
            "Etter lagring oppdateres historikken og brukeren sendes tilbake til oppgavevalgene.",
        ],
    },
    {
        "version": "1",
        "build": "1400",
        "date": "03.07.2026",
        "headline": "Egen mobilapp for vedlikehold",
        "title": "Vedlikehold får separat mobilflate på vedl.lilletorget.net",
        "description": (
            "Build 1400 legger til en egen mobiloptimalisert vedlikeholdsapp som bruker samme brukerbase som Fibaro10 "
            "og skriver nye vedlikeholdsposter til samme datagrunnlag. Appen er laget som en separat container og "
            "eksponeres via Caddy på vedl.lilletorget.net."
        ),
        "applications": [
            "maintenance_mobile: ny FastAPI/PWA-lignende mobilapp med innlogging, skjema, statuskort og siste vedlikeholdslogger.",
            "Fibaro10 API-integrasjon: mobilappen validerer brukere mot /api/auth/me og oppretter poster via /api/maintenance/logs.",
            "Docker/Caddy (docker-compose.qnap.yml, Caddyfile): ny maintenance_mobile-container og reverse proxy for vedl.lilletorget.net.",
            "Deploy og kvalitetssjekk (deploy-qnap.ps1, check-local.ps1): ny app bygges, startes og syntakssjekkes sammen med resten.",
            "Dokumentasjon (.env.qnap.example, maintenance_mobile/README.md): miljøvariabler og driftsformål dokumentert.",
        ],
        "request": (
            "Lag en helt egen vedlikeholdsapp for mobil, gjerne på vedl.lilletorget.net, med design hentet fra eksisterende mobilapp, "
            "samme brukerbase og logging til samme vedlikeholdsgrunnlag som Fibaro10."
        ),
        "work_duration": "ca. 1 t 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Alle innloggede Fibaro10-brukere kan registrere vedlikehold fra mobilflaten.",
            "Skjemaet har touch-vennlige valg for objekt, seng/rom, tiltak, prioritet, status og tagger.",
            "Siste vedlikeholdsposter vises direkte i mobilappen etter lagring.",
            "Appen lagrer ikke egne vedlikeholdsdata, men bruker Fibaro10 som autoritativ backend.",
            "Domeneoppsett er klart for vedl.lilletorget.net når DNS peker til samme server.",
        ],
    },
    {
        "version": "1",
        "build": "1399",
        "date": "03.07.2026",
        "headline": "Vedlikehold får objekt og bedre skjema",
        "title": "Vedlikeholdslogg kan knyttes til seng, rom og tiltak",
        "description": (
            "Build 1399 gjør Vedlikehold mer praktisk for fysisk drift av Sun2. Nye loggposter kan knyttes til objekt, "
            "seng/rom, tiltakstype og prioritet. Opprett/rediger-skjemaet er gjort bredere og delt i metadata til venstre "
            "og notat/oppfølging til høyre."
        ),
        "applications": [
            "Fibaro10 backend (main.py): utvider maintenance_log_entries med objekt, rom/seng, tiltakstype og prioritet.",
            "Fibaro10 backend (main.py): legger til valgsett og automatisk objektnavn for seng/rom basert på Sun2-romkartet.",
            "Desktop V2 skjema (api.ts, ModulePage.tsx, moduleTableUtils.tsx): legger til split-layout, feltseksjoner og textarea-rader i generisk modalskjema.",
            "Desktop V2 design (records.css): bredere og mer kompakt delt modal for vedlikeholdsregistrering.",
            "Buildlogg (build_log.py): registrerer build 1399.",
        ],
        "request": (
            "Gjør Vedlikehold mer gjennomarbeidet, blant annet med mulighet for å vedlikeholde en seng, "
            "og lag et bredere/lavere skjermbilde for ny post med metadata til venstre og skrivefelt til høyre."
        ),
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny post starter med objekt=Seng, tiltak=Kontroll og prioritet=Normal.",
            "Seng/rom kan velges fra Sun2-romlisten.",
            "Hvis objektnavn står tomt for seng/rom, settes et ryddig navn automatisk.",
            "Vedlikeholdstabellen viser objekt, objektnavn, tiltak, prioritet og status før notat.",
            "Vedlikeholdsmodalen er delt i Detaljer og Notat/oppfølging.",
        ],
    },
    {
        "version": "1",
        "build": "1398",
        "date": "03.07.2026",
        "headline": "Ideer flyttet til System",
        "title": "Utvikling-gruppen fjernes fra hovedmenyen",
        "description": (
            "Build 1398 forenkler venstremenyen ved aa fjerne overskriften Utvikling og flytte Ideer ned under System. "
            "Dette er kun en menystrukturendring; rutene og funksjonaliteten for Ideer er uendret."
        ),
        "applications": [
            "Desktop V2 navigasjon (appNavigation.tsx): fjerner Utvikling-gruppen og legger Ideer under System.",
            "Buildlogg (build_log.py): registrerer build 1398.",
        ],
        "request": "Fjern overskriften Utvikling i menyen og flytt Ideer ned under System.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Utvikling vises ikke lenger som egen menygruppe.",
            "System-gruppen viser naa Ideer, Mobil og Admin.",
        ],
    },
    {
        "version": "1",
        "build": "1397",
        "date": "03.07.2026",
        "headline": "Vedlikeholdslogg og ryddet meny",
        "title": "Bygg og drift får Vedlikehold, Renhold flyttes riktig og Ideer flyttes til Utvikling",
        "description": (
            "Build 1397 rydder venstremenyen slik at Bygg og drift samler fysisk drift av lokalet, mens Ideer ligger under Utvikling. "
            "Builden legger også til en ny Vedlikehold-side der arbeid på Sun2 kan logges med tidspunkt, utført av, tagger, status, varighet og oppfølging."
        ),
        "applications": [
            "Fibaro10 backend (main.py): ny maintenance_log_entries-tabell, modul-API for Vedlikehold og POST/PATCH-endepunkter for vedlikeholdslogg.",
            "Desktop V2 navigasjon (appNavigation.tsx, moduleViews.ts, AppRoutes.tsx): Renhold og Vedlikehold under Bygg og drift, Ideer under Utvikling og ny Vedlikehold-route.",
            "Desktop V2 modultabeller (api.ts, moduleTableUtils.tsx): generisk støtte for datetime-felt, tagg-input og standardverdier i opprettskjema.",
            "Design tokens og servermetadata (tokens.css, v2_navigation.py): egen vedlikeholdsfarge og serverlabel for Vedlikehold.",
            "Kvalitetssjekker (smoke-routes.mjs): Vedlikehold lagt inn i route-audit/smoke-grunnlaget.",
            "Buildlogg (build_log.py): registrerer build 1397.",
        ],
        "request": (
            "Flytt Renhold under Bygg og drift, flytt Ideer under Utvikling, og lag ny hovedmeny Vedlikehold "
            "for å registrere hva som gjøres hver gang jeg er tilstede på Sun2 med tagger og korrigerbart tidspunkt."
        ),
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Menygrupperingen er gjort eksplisitt i stedet for slice-basert, slik at nye hovedvalg ikke forskyver grupper.",
            "Ny Vedlikehold-side viser kort for i dag, måned, åpne oppfølgingspunkter og siste logg.",
            "Vedlikeholdsloggen kan opprettes og redigeres direkte i tabellen.",
            "Ny post får dagens dato og klokkeslett automatisk, men tidspunktet kan korrigeres før lagring.",
            "Tagger kan velges fra foreslåtte verdier eller skrives inn fritt.",
        ],
    },
    {
        "version": "1",
        "build": "1396",
        "date": "02.07.2026",
        "headline": "Sun2 stopper tom livefil",
        "title": "Sun2-scraper beskytter eksisterende dagsfil mot tom scrape",
        "description": (
            "Build 1396 hindrer at en aapen Sun2-dagsfil med eksisterende rader blir overskrevet av en scrape som plutselig "
            "finner 0 rader. Dette beskytter dagens grunnlag ved midlertidig feil i Sun2-listen eller tabellinnlesingen."
        ),
        "applications": [
            "Sun2 session scraper (sun2_session_scraper/app/main.py): sjekker eksisterende eksportfil og avviser tom scrape for aapen periode med tidligere rader.",
            "Buildlogg (build_log.py): registrerer build 1396.",
        ],
        "request": "Rett ustabil Sun2 live-sync etter at omsetning falt uten ny parkeringsimport.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Eksisterende dagsfil telles foer ny scrape skrives.",
            "Hvis ny scrape gir 0 rader mens eksisterende aapen dagsfil har rader, stoppes filskriving og posting.",
            "Dette kommer i tillegg til duplikatkontrollen fra build 1395 og backend-sperren fra build 1394.",
        ],
    },
    {
        "version": "1",
        "build": "1395",
        "date": "02.07.2026",
        "headline": "Sun2-scraper validerer foer post",
        "title": "Sun2 live-sync retryer og stopper dupliserte session-filer",
        "description": (
            "Build 1395 flytter Sun2-kontrollen ett steg tidligere i kjeden. Scraperen sjekker naa antall, dato og "
            "duplikate source_session_id foer den skriver dagsfilen og poster til Fibaro10. Ved midlertidig duplikat "
            "prover den paa nytt foer den gir opp."
        ),
        "applications": [
            "Sun2 session scraper (sun2_session_scraper/app/main.py): legger til valideringsretry og duplikatkontroll foer filskriving/post.",
            "Buildlogg (build_log.py): registrerer build 1395.",
        ],
        "request": "Finn aarsaken til at omsetning falt uten ny parkeringsimport og sorg for at det ikke skjer igjen.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Scraperen gjor inntil tre forsok dersom Sun2-listen gir duplikate source_session_id.",
            "En duplikatfil blir ikke skrevet til dagens eksportfil og blir ikke postet til Fibaro10.",
            "Backend-sperren fra build 1394 blir dermed siste forsvar, mens scraperen selv stopper feilgrunnlaget tidligere.",
            "Dagens Sun2-grunnlag ble reparert fra en korrekt backupfil med 48 unike soltimer.",
        ],
    },
    {
        "version": "1",
        "build": "1394",
        "date": "02.07.2026",
        "headline": "Idebank og Sun2-importvern",
        "title": "Ideer-meny og beskyttelse mot duplikate Sun2-sessioner",
        "description": (
            "Build 1394 legger til en egen Ideer-seksjon for forslag som kan vurderes foer de flyttes inn i fagomraadene. "
            "Builden stopper ogsaa Sun2 session-importer som inneholder duplikate source_session_id foer de kan erstatte korrekt dagsgrunnlag."
        ),
        "applications": [
            "Fibaro10 backend (main.py): avviser Sun2 session-import med duplikate source_session_id foer databasegrunnlaget erstattes.",
            "Desktop V2 Ideer (IdeasPage.tsx, ideas.css): ny hovedmeny med undersider for oversikt, kontroll, innsikt, automatisering og arbeidsflyt.",
            "Desktop V2 navigasjon/ruting (moduleViews.ts, appNavigation.tsx, AppRoutes.tsx): legger Ideer inn som eget hovedomraade.",
            "Server-ruting (main.py, v2_navigation.py): eksponerer Ideer-rutene i SPA og servermetadata.",
            "Kvalitetssjekker (smoke-routes.mjs, audit-bundle.mjs): legger Ideer inn i route smoke og justerer bundle-budsjett til faktisk app-storrelse.",
            "Buildlogg (build_log.py): registrerer build 1394.",
        ],
        "request": (
            "Lag en egen hovedmeny Ideer med undersider for forslag, og undersok hvorfor omsetning hittil i dag falt "
            "selv om det ikke var kjort ny parkeringsimport."
        ),
        "work_duration": "ca. 70 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ideer er lagt inn som ny hovedmeny med fem undersider og konkrete forslag til videre funksjonalitet.",
            "Sun2-importen validerer naa duplikate source_session_id foer den sletter/erstatter eksisterende rader fra samme kildefil.",
            "Feil Sun2-import blir logget som mislykket import med forklaring og uten aa endre soltimegrunnlaget.",
            "Fallet i omsetning ble sporet til Sun2 session-import, ikke EasyPark: parkeringssummen var uendret.",
            "Route smoke dekker Ideer-rutene slik at manglende SPA-ruting fanges foer deploy.",
        ],
    },
    {
        "version": "1",
        "build": "1393",
        "date": "02.07.2026",
        "headline": "EasyPark startes i bakgrunnen",
        "title": "Oppdater EasyPark blokkerer ikke grensesnittet",
        "description": (
            "Build 1393 endrer manuell EasyPark-oppdatering fra synkron import til bakgrunnsstart. "
            "Knappen starter naa downloader-jobben og slipper brukerflaten fri, mens faktisk parkeringsgrunnlag "
            "oppdateres naar EasyPark-downloaderen poster CSV-en tilbake til Fibaro10."
        ),
        "applications": [
            "EasyPark-downloader (easypark_downloader/app/main.py): legger til queue-sync-now og queue-sync-period som starter import i bakgrunnen.",
            "Fibaro10 backend (main.py): V2 og klassisk parkeringsoppdatering bruker ko-endepunkt med kort timeout.",
            "Mobil dashboard (online_dashboard/app/main.py): manuell parkeringsoppdatering bruker samme ko-endepunkt.",
            "QNAP deploy (scripts/deploy-qnap.ps1): bygger og restarter den separate EasyPark-downloaderen sammen med hoveddeploy.",
            "Live smoke (desktop_v2/scripts/smoke-live.mjs): sjekker faktisk HTTP-status i stedet for aa tolke datakildetekst som 404-side.",
            "Dokumentasjon (easypark_downloader/README.md): dokumenterer nye ko-endepunkter.",
            "Buildlogg (build_log.py): registrerer build 1393.",
        ],
        "request": "hvorfor stopper hele grensesnittet og venter til importen er ferdig naar man trykker paa Oppdater EasyPark paa Parkering oversikt. det trigger jo bare en annen tjeneste",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Manuell EasyPark-start svarer med en gang naar jobben er koet.",
            "Downloaderens status viser running/queued mens importen faktisk gaar.",
            "Planlagte importer hopper over ny start hvis manuell import allerede er aktiv.",
            "Parkeringscache ryddes fortsatt bare naar CSV-importen faktisk er mottatt av Fibaro10.",
        ],
    },
    {
        "version": "1",
        "build": "1392",
        "date": "02.07.2026",
        "headline": "Rydding omsetning parkering soling",
        "title": "Omsetning, parkering og soling er strukturert mer likt",
        "description": (
            "Build 1392 rydder i de tre mest brukte fagomraadene. Topp-tabeller er samlet i felles backend-hjelpere, "
            "parkering og soling viser samme fire toppperioder der det er relevant, og menyrekkefolgen er justert slik at oversikt, analyse, drift, oppgjor, prognose og grunnlagsdata ligger mer konsekvent."
        ),
        "applications": [
            "Fibaro10 backend (main.py): samler topp-tabeller for omsetning, parkering og soling i egne helper-funksjoner.",
            "Fibaro10 backend (main.py): utvider soling toppperioder til 20 rader og legger til Topp maaneder antall.",
            "Fibaro10 V2 Parkering oversikt: starter tabellfanene med toppperioder foer siste parkeringer.",
            "Desktop V2 meny (moduleViews.ts): sorterer omsetning, parkering og soling etter samme arbeidsflyt.",
            "Desktop V2 dashboard (OverviewPage.tsx): sorterer omsetningssnarveier likt som menyen.",
            "V2 navigasjonsmetadata (v2_navigation.py): speiler samme view-rekkefolge for titteloppslag.",
            "Buildlogg (build_log.py): registrerer build 1392.",
        ],
        "request": "grundig opprydding i applikasjonen baade omsetning, parkering og soling. rydd opp og strukturer til samme systemer og funksjoner men soerg for at alt blir med og funker",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Omsetning bruker felles topp-tabellbygger for oversikt.",
            "Parkering bruker felles topp-tabellbygger og viser toppperioder foer siste parkeringer.",
            "Soling viser naa topp dager/maaneder for baade omsetning og antall.",
            "Soling toppperioder er utvidet fra 10 til 20 rader.",
            "Menyene for omsetning, parkering og soling er sortert mer konsekvent uten at ruter er fjernet.",
            "Omsetning-dashboardets snarveier foelger samme rekkefolge som toppmenyen.",
        ],
    },
    {
        "version": "1",
        "build": "1391",
        "date": "02.07.2026",
        "headline": "Parkering topp antall",
        "title": "Parkering oversikt viser topp dager og måneder etter antall",
        "description": (
            "Build 1391 kompletterer toppoversikten for parkering med egne tabeller sortert på antall parkeringer. "
            "Dermed kan Parkering oversikt vise både beste perioder etter omsetning og høyeste volum."
        ),
        "applications": [
            "Fibaro10 backend (main.py): eksponerer top_days_by_count og top_months_by_count i V2 Parkering oversikt.",
            "Fibaro10 V2 Parkering oversikt: legger til Topp dager antall og Topp måneder antall.",
            "Buildlogg (build_log.py): registrerer build 1391.",
        ],
        "request": "du tok ikke med topp dager antall oensker ogsaa det og topp mnd antall",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Parkering/oversikt viser naa topp 20 dager sortert etter antall parkeringer.",
            "Parkering/oversikt viser naa topp 20 maaneder sortert etter antall parkeringer.",
            "Antall-tabellene viser ogsaa omsetning, biler og minutter som kontrollgrunnlag.",
        ],
    },
    {
        "version": "1",
        "build": "1390",
        "date": "02.07.2026",
        "headline": "Parkering topp omsetning",
        "title": "Parkering oversikt viser topp dager og måneder etter omsetning",
        "description": (
            "Build 1390 legger inn egne topp-tabeller for parkeringsomsetning på Parkering oversikt. "
            "Tabellene viser de 20 beste dagene og månedene sortert på beløp, med antall parkeringer, biler og minutter som kontrollgrunnlag."
        ),
        "applications": [
            "Fibaro10 backend (main.py): utvider parkeringssummeringene til 20 toppperioder.",
            "Fibaro10 backend (main.py): legger til API-rad for parkeringssummeringer.",
            "Fibaro10 V2 Parkering oversikt: viser Topp dager omsetning og Topp måneder omsetning.",
            "Desktop V2 tabeller: gir tydelige kolonnenavn for parkeringssummeringer.",
            "Buildlogg (build_log.py): registrerer build 1390.",
        ],
        "request": "vi har ikke topp dager og topp mnd paa parkering med hensyn til omsetning",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Parkering/oversikt har naa topp 20 dager rangert etter parkeringsomsetning.",
            "Parkering/oversikt har naa topp 20 maaneder rangert etter parkeringsomsetning.",
            "Tabellene viser omsetning, antall parkeringer, unike biler og minutter.",
        ],
    },
    {
        "version": "1",
        "build": "1389",
        "date": "02.07.2026",
        "headline": "Koble parkering ved soltreff",
        "title": "Koble skiller mellom total parkering og parkering knyttet til soltreff",
        "description": (
            "Build 1389 legger til belopet Parkert ved soltreff i Koble. Summen beregnes fra unike "
            "parkeringshendelser som faktisk har soltreff for bil/SUN2-paret, slik at den ikke blandes med "
            "bilens totale parkeringshistorikk."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger til matched_paid_total paa Koble-kandidater.",
            "Fibaro10 backend (main.py): beregner parkering ved soltreff per bil/SUN2-par og som deduplisert totalsum.",
            "Desktop V2 API-typer (api.ts): legger til matchedPaidTotal og qualifiedMatchedPaidTotal.",
            "Desktop V2 Koble (KobleReviewPanel.tsx): viser ved-soltreff-belop og totalbelop hver for seg.",
            "Desktop V2 tabeller/styling: legger til kolonnenavn og plass til tre oppsummeringskort.",
            "Buildlogg (build_log.py): registrerer build 1389.",
        ],
        "request": "du maa ogsaa gjoere det du foreslo for aa faa oversikt over parkering ved soltreff",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Koble > Biltreff viser Parkert ved soltreff som hovedbelop og Parkert totalt som undertekst.",
            "Koble > SUN2-kontroll viser begge belop i parkeringskolonnen.",
            "Koble-oversiktens kort skiller Parkert ved soltreff fra Parkert totalt.",
            "Eksisterende kandidater faar korrekt verdi direkte fra API-et uten aa vente paa bakgrunnsjobben.",
        ],
    },
    {
        "version": "1",
        "build": "1388",
        "date": "02.07.2026",
        "headline": "Dashboard dagsrangering",
        "title": "Omsetning hittil i dag viser dagens rangering mot historiske dager",
        "description": (
            "Build 1388 legger til en kompakt rangering foran hovedtallet paa omsetningskortet for i dag. "
            "Rangeringen beregnes mot historiske hele dagstotaler for samlet omsetning fra soling og parkering."
        ),
        "applications": [
            "Fibaro10 backend (main.py): beregner dagens omsetningsrangering fra kombinerte historiske dagssummer.",
            "Desktop V2 API-typer (api.ts): legger til valgfri rank-metadata paa statusperioder.",
            "Desktop V2 dashboard (OverviewPage.tsx): viser rangering foran dagens omsetningstall.",
            "Desktop V2 styling (status-periods.css): legger til kompakt rangeringsbadge i kortheader.",
            "Buildlogg (build_log.py): registrerer build 1388.",
        ],
        "request": "paa Dashboard omsetning, saa oensker jeg paa omsetning hitill i dag - foran det tallet et eget tall som viser hvilken rangering dagen har \"5 beste\" eller noe slikt",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Dagens omsetningskort viser for eksempel 5. beste foran hovedbelopet.",
            "Rangeringen oppdateres sammen med dashboardets vanlige datagrunnlag.",
            "Hovertekst forklarer at rangeringen er mot historiske hele dager.",
        ],
    },
    {
        "version": "1",
        "build": "1387",
        "date": "02.07.2026",
        "headline": "Koble krav presisert",
        "title": "SUN2-kontroll krever to ulike parkeringer med soltreff",
        "description": (
            "Build 1387 retter Koble-grunnlaget slik at kvalifiserte bil/SUN2-koblinger maa ha minst to ulike "
            "parkeringer med soltreff. Tidligere kunne en bil slippe inn hvis to soltimer var koblet til samme "
            "parkering, noe som gjorde at SUN2-kontroll kunne vise 1 av 2 parkeringer med soltreff."
        ),
        "applications": [
            "Fibaro10 backend (main.py): kvalifisert Koble-filter bruker parking_match_count >= 2.",
            "Fibaro10 backend (main.py): kort og tabelltitler beskriver 2+ parkeringer med soltreff.",
            "Desktop V2 (KobleReviewPanel.tsx): SUN2-kontroll og Biltreff forklarer at kravet er ulike parkeringer.",
            "Buildlogg (build_log.py): registrerer build 1387.",
        ],
        "request": "jeg forstaar ikke, naar jeg ser i sun2-kontorll tabellen saa er det su2 id er der som har 1 av 2 parkeringer med soltreff",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Rader med bare en parkering med soltreff blir ikke lenger med i kvalifisert SUN2-kontroll.",
            "Soltreff vises fortsatt som antall soltimer, men kvalifisering skjer paa ulike parkeringer.",
            "Tekster i Koble er justert for aa unngaa blanding av soltreff og parkeringstreff.",
        ],
    },
    {
        "version": "1",
        "build": "1386",
        "date": "02.07.2026",
        "headline": "Koble ryddigere meny",
        "title": "Koble deles i tydelige undersider for kontroll, kandidater og jobbstatus",
        "description": (
            "Build 1386 rydder Koble-modulen ved aa dele arbeidsflaten i egne undersider i den horisontale "
            "menyen: Oversikt, SUN2-kontroll, Biltreff, Kandidater, Treffgrunnlag og Jobb. Hver underside viser "
            "bare relevant innhold."
        ),
        "applications": [
            "Desktop V2 navigasjon (moduleViews.ts): legger til egne Koble-undersider.",
            "Fibaro10 backend navigation (v2_navigation.py): legger til titler for nye Koble-visninger.",
            "Desktop V2 (ModulePage.tsx): filtrerer Koble-kort, actions og tabeller etter aktiv underside.",
            "Desktop V2 (KobleReviewPanel.tsx): viser bare relevant Koble-seksjon per underside.",
            "Desktop V2 styling (koble.css): gir lange Koble-lister egen scrollflate.",
            "Fibaro10 backend (main.py): peker Koble-kort til riktige nye undersider.",
            "Buildlogg (build_log.py): registrerer build 1386.",
        ],
        "request": "naa kan du rydde opp og proeve aa gjoere alt rundt koble menyen mer oversiktlig. lag gjerne flere undersider med tilgang fra den horisontale menyen",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny horisontal Koble-meny med seks undersider.",
            "Oversikt viser kun statuskort og kort forklaring.",
            "SUN2-kontroll og Biltreff har egne kontrollflater.",
            "Treffgrunnlag og Jobb viser bare relevante generiske tabeller.",
            "Koble-actions vises bare paa Jobb-siden.",
        ],
    },
    {
        "version": "1",
        "build": "1385",
        "date": "02.07.2026",
        "headline": "Koble SUN2-tabell",
        "title": "Koble viser SUN2-orientert tabell over biler med gjentatte soltreff",
        "description": (
            "Build 1385 legger til en egen kontrolltabell som tar utgangspunkt i SUN2-ID. Tabellen viser alle "
            "bil/SUN2-kandidater med minst to soltreff, hvor mange soltreff paret har, hvor mange parkeringer "
            "som fikk soltime i tilknytning, total parkering på bilen og parkeringer uten soltreff."
        ),
        "applications": [
            "Fibaro10 backend (main.py): bygger qualifiedSun2Rows sortert og gruppert etter SUN2-ID.",
            "Desktop V2 API-typer (api.ts): legger til KobleQualifiedSun2Row.",
            "Desktop V2 (KobleReviewPanel.tsx): viser SUN2-basert kontrolltabell på Koble-siden.",
            "Desktop V2 styling (koble.css): legger til kompakt scrollbar tabell med SUN2-gruppeskiller.",
            "Buildlogg (build_log.py): registrerer build 1385.",
        ],
        "request": (
            "jeg ønsker at du skal vise en tabell med alle biler som er valgt ut som har mer enn 2 treff på en "
            "sun2 id. jeg vil at tabellen skal ta utgangspunt i sun2 id og vise hvilke bilnr som er assosiert "
            "med den 2 sun2 id min 2 ganger. men også hvor mange ganger og hvor mange av de parkeringene som "
            "har en sun2 time i tilknytning."
        ),
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny SUN2-basert kontrolltabell på Koble-siden.",
            "Tabellen viser soltreff, parkeringer med soltreff, total parkering og parkeringer uten soltreff.",
            "Samme SUN2-ID kan ha flere biler i tabellen.",
            "Generisk tabellgrunnlag får også tabellen SUN2 med biltreff.",
        ],
    },
    {
        "version": "1",
        "build": "1384",
        "date": "02.07.2026",
        "headline": "Koble parkeringssum",
        "title": "Koble viser hvor mye bilene med 2+ soltreff har parkert for",
        "description": (
            "Build 1384 legger til samlet parkeringsomsetning for de unike bilnummerne som har minst to soltreff "
            "mot samme SUN2-bruker innen koblingsvinduet. Summen dobbeltteller ikke biler med flere kandidatkoblinger."
        ),
        "applications": [
            "Fibaro10 backend (main.py): summerer paid_total per unikt bilnummer i kvalifisert Koble-grunnlag.",
            "Desktop V2 (KobleReviewPanel.tsx): viser totalen og parkeringssum per rad.",
            "Desktop V2 styling (koble.css): legger inn kompakt sumfelt og egen Parkert for-kolonne.",
            "Buildlogg (build_log.py): registrerer build 1384.",
        ],
        "request": "kan du lage en sum hvor mye disse bilene har parkert for",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Nytt kort i Koble: Parkert for.",
            "KobleReview-payloaden inkluderer qualifiedPaidTotal.",
            "Bilnummer med gjentatte treff viser samlet parkeringssum i toppfeltet.",
            "Listen viser Parkert for per bil/kandidat.",
        ],
    },
    {
        "version": "1",
        "build": "1383",
        "date": "02.07.2026",
        "headline": "Koble bilnr med gjentatte soltreff",
        "title": "Koble viser hvor mange bilnummer som har 2+ soltreff mot samme SUN2-bruker",
        "description": (
            "Build 1383 legger inn et tydelig tall og en sortert liste paa Koble-siden for bilnummer som har minst "
            "to soltimer fra samme SUN2-bruker innen koblingsvinduet etter parkering."
        ),
        "applications": [
            "Fibaro10 backend (main.py): teller unike bilnummer og kandidatpar med 2+ soltreff.",
            "Desktop V2 (KobleReviewPanel.tsx): viser egen liste sortert etter flest treff.",
            "Desktop V2 styling (koble.css): kompakt listevisning for bil/SUN2, treff og status.",
            "Buildlogg (build_log.py): registrerer build 1383.",
        ],
        "request": "paa koble siden saa vil jeg ha en oversikt over hvor mange bilnr som har to eller flere soltime av saamme bruker etter seg innenfor 3 min",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Koble faar kortet Bilnr 2+ soltreff.",
            "KobleReview-payloaden inkluderer qualifiedPlateCount, qualifiedPairCount og qualifiedRows.",
            "Visuell kontrollflate viser topp 12 sortert etter flest soltreff.",
            "Tabellen Bilnr med 2+ soltreff viser samme grunnlag i tabellform.",
        ],
    },
    {
        "version": "1",
        "build": "1382",
        "date": "02.07.2026",
        "headline": "Omsetning snitt pr uke",
        "title": "Omsetning oversikt viser gjennomsnittlig ukeomsetning hittil i aar",
        "description": (
            "Build 1382 legger inn et eget noekkeltall for snitt pr uke paa Omsetning oversikt. "
            "Tallet beregnes av samlet aarsomsetning delt paa antall paabegynte uker hittil i innevaerende aar."
        ),
        "applications": [
            "Fibaro10 backend (main.py): beregner snitt pr uke for samlet omsetning, soling og parkering.",
            "Desktop V2 styling (module-metrics.css): lar modulens noekkeltall fylle tilgjengelig bredde uten enslig kort paa ny rad.",
            "Buildlogg (build_log.py): registrerer build 1382.",
        ],
        "request": "paa omsetning oversikt saa skulle jeg gjerne hatt inn snitt pr uke",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Omsetning oversikt faar kortet Snitt pr uke.",
            "Detaljen viser fordeling mellom soling og parkering.",
            "Uketallet er basert paa antall paabegynte uker hittil i aar.",
            "Kortgriden justeres slik at sju noekkeltall kan ligge paa samme rad ved bred skjerm.",
        ],
    },
    {
        "version": "1",
        "build": "1381",
        "date": "02.07.2026",
        "headline": "Koble visuell kontroll",
        "title": "Koble-siden faar egen kontrollflate for a vurdere parkering mot SUN2",
        "description": (
            "Build 1381 videreutvikler Koble fra rene tabeller til en visuell kontrollko. Kandidater vises med "
            "sannsynlighet, bil/eier, SUN2-bruker, konkurranseindikatorer og konkrete parkering-soling-treff."
        ),
        "applications": [
            "Fibaro10 backend (main.py): sender strukturert kobleReview-payload med kandidater og detaljtreff.",
            "Desktop V2 (KobleReviewPanel.tsx): ny visuell kontrollflate med bekreft/avvis og kopiering av SUN2-ID.",
            "Desktop V2 styling (koble.css): kompakt review-design for scanning av score, identitet og tidslinjer.",
            "Buildlogg (build_log.py): registrerer build 1381.",
        ],
        "request": "proev aa videreutvikle dette konseptet slik at det er enkelt for meg aa gjoere en visuell kontroll",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Kandidater kan kontrolleres visuelt foer tabellgrunnlaget.",
            "Treff vises som parkeringstid, tidsavstand og soltime i samme rad.",
            "Konkurrerende kandidater markeres tydelig.",
            "Bekreft/avvis kan gjores direkte fra kontrollkortet.",
        ],
    },
    {
        "version": "1",
        "build": "1380",
        "date": "02.07.2026",
        "headline": "Koble refresh",
        "title": "Koble-siden kan lastes direkte og refreshes uten 404",
        "description": (
            "Build 1380 legger Koble inn i backendens SPA-fallback-ruter. Hard refresh paa /koble/oversikt "
            "returnerer naa desktop-appen i stedet for 404 fra FastAPI."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger til /koble og /koble/{path} som desktop-app-ruter.",
            "Live smoke-test (desktop_v2/scripts/smoke-live.mjs): feiler naa tydelig ved 404/Not Found.",
            "Buildlogg (build_log.py): registrerer build 1380.",
        ],
        "request": "om man trykker refresh naar man er inne paa koblingsiden saa blir det feil",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Direkte aapning og refresh av /koble/oversikt gaar til React-appen.",
            "Smoke-testen skal ikke lenger feilaktig godkjenne Not Found-sider.",
        ],
    },
    {
        "version": "1",
        "build": "1379",
        "date": "02.07.2026",
        "headline": "Koble rask sidevisning",
        "title": "Koble-siden leser ferdigberegnede kandidater uten full rescore ved åpning",
        "description": (
            "Build 1379 fjerner tung full-rescore fra selve Koble-sidevisningen. Siden leser nå lagrede kandidater, "
            "treffgrunnlag og jobbstatus, mens scoring oppdateres når sideappen rapporterer nye matcher."
        ),
        "applications": [
            "Fibaro10 backend (main.py): fjerner full refresh_parking_sun_link_candidate_pairs fra /api/modules/koble.",
            "Fibaro10 databaseindekser (main.py): legger indekser for kandidat-, treff- og sist behandlet-tabellene.",
            "Buildlogg (build_log.py): registrerer build 1379.",
        ],
        "request": "hvorfor går koble menyen så seint",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Koble-siden skal ikke lenger trigge dyr aggregering over hele historikken.",
            "Tabellene får indekser til sortering og paginering.",
            "Sideappen fortsetter å oppdatere kandidater løpende i bakgrunnen.",
        ],
    },
    {
        "version": "1",
        "build": "1378",
        "date": "02.07.2026",
        "headline": "Koble hele historikken",
        "title": "Koble kan kjøre mot alle biler og alle parkeringer uten tidsbegrenset bilutvalg",
        "description": (
            "Build 1378 endrer Koble-motorens bilutvalg slik at verdien 0 betyr hele historikken. "
            "Da sjekkes alle parkeringer vi har mot soltimer, ikke bare biler som har parkert de siste dagene."
        ),
        "applications": [
            "Koble-sideapp (parking_sun_linker): recent_days=0 betyr alle biler og alle parkeringer.",
            "Fibaro10 backend (main.py): tillater 0 som parameterverdi og bruker 0 som standard for nye state-rader.",
            "Desktop V2 tabeller: viser tydelig at bilutvalg 0 betyr alle.",
            "Buildlogg (build_log.py): registrerer build 1378.",
        ],
        "request": "tror ikke vi skal begrense til biler inneværende år, men sjekke parkeringer mot soling for alle parkeriger vi har på den enkelte bilen",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Bilutvalg kan nå settes til 0 for full historikk.",
            "Sideappen velger da alle ubehandlede parkeringer uavhengig av hvor nylig bilen har parkert.",
            "Live-jobben skal startes fra nyeste parkering med full historikk etter deploy.",
        ],
    },
    {
        "version": "1",
        "build": "1377",
        "date": "01.07.2026",
        "headline": "Koble smartere scoring",
        "title": "Koble-motoren scorer kandidater med forklaring, konkurranse og raskere batchkjøring",
        "description": (
            "Build 1377 videreutvikler koblingsmotoren mellom parkering og SUN2. Kandidater vurderes naa ut fra "
            "unike parkeringstreff, treffdager, tidsavstand og konkurrerende koblinger. Sideappen behandler flere "
            "parkeringer per runde for raskere ajourforing."
        ),
        "applications": [
            "Fibaro10 backend (main.py): utvider Koble-kandidatene med vurdering, parkeringstreff, treffdager og konkurransefelter.",
            "Fibaro10 backend (main.py): ny sannsynlighetsmodell som skiller svake observasjoner fra sterke kandidater.",
            "Koble-sideapp (parking_sun_linker): behandler parkeringer i batcher og rapporterer samlet resultat.",
            "Docker/QNAP (docker-compose.qnap.yml): legger til konfigurerbar KOBLE_BATCH_SIZE.",
            "Desktop V2 tabeller: legger lesbare kolonnenavn for de nye Koble-feltene.",
            "Buildlogg (build_log.py): registrerer build 1377.",
        ],
        "request": "prøv å videreutvikle denne koblingsmotoren på best mulig måte",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Kandidater viser naa en kort vurdering i tillegg til prosent.",
            "Sannsynlighet bruker unike parkeringer, ikke bare antall soltimer.",
            "Konkurrerende koblinger trekker ned sannsynligheten.",
            "Sterke kandidater betyr naa avventende kandidater med minst 70 % sannsynlighet.",
            "Sideappen behandler som standard 25 parkeringer per runde.",
        ],
    },
    {
        "version": "1",
        "build": "1376",
        "date": "01.07.2026",
        "headline": "Koble database-skjema",
        "title": "Koble reparerer delvise tabeller og viser kandidater til bekreftelse",
        "description": (
            "Build 1376 gjor oppstartsmigreringen for Koble robust dersom en tidligere deploy har opprettet "
            "tabellene delvis. Manglende kolonner og unike indekser legges inn ved oppstart, og sideappen kan "
            "rapportere prosesserte parkeringer og matcher uten aa vaere avhengig av gamle constraint-navn."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger inn manglende Koble-kolonner, unike indekser og standardverdier for jobbstatus.",
            "Fibaro10 worker-API (main.py): bruker index_elements for upsert av prosesserte parkeringer og matcher.",
            "Buildlogg (build_log.py): registrerer build 1376.",
        ],
        "request": "jeg maa kunne bekrefte om en kobling er rett - frem til da skal jeg ha en sannsynlighet paa koblingen",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Koble-sideappen stopper ikke lenger paa delvis opprettede tabeller.",
            "Kandidater kan ligge som Avventer med sannsynlighet til bruker bekrefter eller avviser dem.",
            "Bekreftelse/avvisning og start/stopp forblir styrt fra Fibaro10-grensesnittet.",
        ],
    },
    {
        "version": "1",
        "build": "1375",
        "date": "01.07.2026",
        "headline": "Koble worker-auth",
        "title": "Koble-sideappen slipper korrekt gjennom innloggingsmiddleware",
        "description": (
            "Build 1375 legger worker-rutene for Koble inn i intern app-autentisering i middleware. "
            "Sideappen kan dermed hente styringsparametere og rapportere status/resultater uten vanlig brukerinnlogging."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger /api/koble/worker/* inn i intern app-bypass med Koble-token.",
            "Buildlogg (build_log.py): registrerer build 1375.",
        ],
        "request": "jeg synes dette skal være en egen applikasjon som skal kjøre på siden, den skal hente styringsparameter fra fibaro10 siden og rapportere tilbake status og antall lest osv.",
        "work_duration": "ca. 5 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Koble-worker kan naa bruke worker-API uten 401 fra login-middleware.",
            "Vanlig brukerinnlogging er fortsatt krav for alle Koble-handlinger i grensesnittet.",
        ],
    },
    {
        "version": "1",
        "build": "1374",
        "date": "01.07.2026",
        "headline": "Koble worker-token",
        "title": "Koble-sideappen kan bruke eksisterende intern app-token",
        "description": (
            "Build 1374 justerer intern tokenkontroll for Koble-sideappen. Worker-API-et godtar naa baade "
            "egen KOBLE_WORKER_TOKEN og eksisterende CAR_INFO_APP_TOKEN, slik at QNAP-oppsettet fungerer uten "
            "manuell endring av sensitiv .env."
        ),
        "applications": [
            "Fibaro10 backend (main.py): worker-API for Koble godtar begge interne app-tokenene.",
            "Buildlogg (build_log.py): registrerer build 1374.",
        ],
        "request": "jeg må kunne bekrefte om en kobling er rett - frem til da skal jeg ha en sannsynlighet på koblingen",
        "work_duration": "ca. 5 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "parking_sun_linker kan autentisere mot Fibaro10 med tokenet som allerede finnes i QNAP-miljoet.",
            "Ingen endring i brukerrettigheter eller eksternt API.",
        ],
    },
    {
        "version": "1",
        "build": "1373",
        "date": "01.07.2026",
        "headline": "Koble som sideapp",
        "title": "Koble-jobben kjører som egen app med sannsynlighet og manuell bekreftelse",
        "description": (
            "Build 1373 flytter den kontinuerlige koblingsjobben ut av Fibaro10-prosessen og inn i egen "
            "sideapp. Fibaro10 styrer parametere, start/stopp, status og bekreftelse. Kandidater lagres "
            "med sannsynlighet frem til bruker bekrefter eller avviser koblingen."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger til persistente tabeller, worker-API, start/stopp/restart og bekreftelse av kandidater.",
            "Koble-side (main.py payload): viser jobbstatus, parametere, kandidater med sannsynlighet og treffgrunnlag fra lagrede data.",
            "parking_sun_linker: ny FastAPI-sideapp som leser parkeringer/soltimer og rapporterer funn tilbake til Fibaro10.",
            "Docker/deploy: legger parking_sun_linker inn i QNAP compose og deployflyt.",
            "Datakilder (import_jobs.py): registrerer Koble parkering/SUN2 som egen datakilde med forklaring.",
            "Desktop V2 tabeller: legger norske kolonnenavn for Koble-feltene.",
        ],
        "request": "jeg synes dette skal være en egen applikasjon som skal kjøre på siden, den skal hente styringsparameter fra fibaro10 siden og rapportere tilbake status og antall lest osv. den skal kunne stoppes og startes og alle mulige matcher skal vises løpende i grensesnittet på fibaro10. jeg må kunne bekrefte om en kobling er rett - frem til da skal jeg ha en sannsynlighet på koblingen",
        "work_duration": "ca. 70 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Koblingsjobben er ikke lenger en del av FastAPI-starten til Fibaro10.",
            "Sideappen prosesserer parkeringer fra nyeste og fortsetter til den er ajour.",
            "Parametere endres i Fibaro10 og starter jobben fra nyeste parkering.",
            "Alle kandidater vises med sannsynlighet, status og treffgrunnlag.",
            "Bekreftet kandidat skriver SUN2-ID tilbake på bilen; avvist kandidat blir liggende som avvist.",
        ],
    },
    {
        "version": "1",
        "build": "1371",
        "date": "01.07.2026",
        "headline": "Koble-regel siste 14 dager",
        "title": "Koble analyserer biler parkert siste 14 dager mot alle soltimer",
        "description": (
            "Build 1371 endrer Koble-siden slik at den foerst finner biler som har parkert siste 14 dager. "
            "For disse bilene sjekkes alle historiske parkeringer mot alle soltimer, og kandidat opprettes "
            "naar minst to distinkte soltimer paa samme SUN2-ID starter innen valgt minuttvindu etter "
            "parkering-start paa samme bil."
        ),
        "applications": [
            "Backend modul-API (main.py): endrer koblingssporringen fra lagret bil-SUN2-ID til kandidat-SUN2-ID fra soltimene.",
            "Backend modul-API (main.py): legger til filter for bilutvalg siste dager og teller biler som faktisk sjekkes.",
            "Koble-grensesnitt (main.py payload): fjerner kveldsfilter og viser at treffgrunnlaget teller distinkte soltimer.",
            "Buildlogg (build_log.py): registrerer build 1371.",
        ],
        "request": "jeg vil at loesningen skal gaa igjennom alle parkeringer de to siste uker og sjekke alle parkeringer for disse bilene mot alle soltimer. match er naar det er to soltimer paa samme sun2-id som starter innen 3 min etter en parkering paa samme bil.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Bilutvalget er naa biler med parkering siste 14 dager som standard.",
            "Alle parkeringer for disse bilene sjekkes mot alle soltimer.",
            "Kandidat-SUN2-ID hentes fra soltimehistorikken, ikke fra lagret sun2_id paa bilen.",
            "Minst to distinkte soltimer paa samme SUN2-ID maa starte innen valgt minuttvindu etter parkering.",
        ],
    },
    {
        "version": "1",
        "build": "1370",
        "date": "01.07.2026",
        "headline": "Koble parkering og soltime",
        "title": "Ny Koble-side finner sannsynlige koblinger mellom bil og Sun2-ID",
        "description": (
            "Build 1370 legger til hovedmenyen Koble med en foerste regel for aa finne sannsynlige "
            "koblinger mellom parkering og soltime. Siden lister biler der samme registreringsnummer "
            "og lagret SUN2-ID minst to ganger har soltime-start innen valgt minuttvindu etter "
            "parkering-start paa kvelden."
        ),
        "applications": [
            "Backend modul-API (main.py): legger til kandidatberegning for parkering/soltime og eksponerer kort, filtre og tabeller.",
            "Desktop V2 navigasjon (moduleViews.ts, appNavigation.tsx, AppRoutes.tsx): legger til hovedmenyen Koble.",
            "Desktop V2 tabeller (moduleTableUtils.tsx): legger til norske kolonnenavn for koblingsgrunnlag.",
            "Smoke/audit (smoke-routes.mjs, smoke-ui.mjs): legger Koble inn i route-testene.",
            "Buildlogg (build_log.py): registrerer build 1370.",
        ],
        "request": "jeg vil lage en egen side for aa koble parkering og soltime, om det min 2 ganger stemmer med at soltime starter maks 3 min etter en parkeiing paa kvelden samme bilnr og samme sun2 id saa er det sannsynlig at de hoerer sammenn da vil jeg at de skal listes ut paa en egen side.. lag en hovedmeny \"Koble\" saa skal vi etterhvert proeve aa finne smarte maater aa koble paa",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny hovedmeny Koble er tilgjengelig i venstremenyen.",
            "Siden viser sannsynlige koblinger per bil og SUN2-ID, med antall treff og foerste/siste treff.",
            "Siden viser konkrete trefflinjer med parkering-start, soltime-start, tidsdiff, rom, belop og kilde.",
            "Regelen kan justeres i grensesnittet med min. treff, maks minutter etter parkering og kveld-fra time.",
        ],
    },
    {
        "version": "1",
        "build": "1369",
        "date": "01.07.2026",
        "headline": "SUN2-ID paa enkelttimer",
        "title": "Soling enkelttimer viser og kopierer SUN2-ID",
        "description": (
            "Build 1369 gjor SUN2-ID/medlemsnummer lett tilgjengelig naar en enkelt soltime aapnes. "
            "Feltet ligger oeverst i detaljpanelet og har egen kopiknapp slik at nummeret kan limes inn "
            "paa kjoretoy eller andre registreringer."
        ),
        "applications": [
            "Desktop V2 soling enkelttimer (SunSessionsPanel.tsx): viser SUN2-ID som eget felt og legger til kopiknapp med fallback.",
            "Desktop V2 CSS (sun-sessions.css): fremhever SUN2-ID-feltet kompakt i detaljpanelet.",
            "Buildlogg (build_log.py): registrerer build 1369.",
        ],
        "request": "paa soling enkelttimer saa mangler vi sun2 id lett tilgjengelig naar vi aapner posten. den boer vaere lett aa finne og med en knapp for aa kopiere medlemsnummeret/sun2 id enkelt slik at vi kan lime den inn paa kjoretoy",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "SUN2-ID vises som eget felt oeverst naar en soltime aapnes.",
            "Kopier-knappen kopierer medlemsnummer/SUN2-ID til utklippstavlen.",
            "Kopiering har fallback for interne HTTP-flater der moderne Clipboard API kan vaere begrenset.",
        ],
    },
    {
        "version": "1",
        "build": "1368",
        "date": "01.07.2026",
        "headline": "Datakildeforklaringer",
        "title": "Datakildesider viser datagrunnlag, avhengigheter og kjoring",
        "description": (
            "Build 1368 utvider detaljsiden for datakilder med et forklaringsfelt som beskriver hvordan "
            "datagrunnlaget hentes, hvilke komponenter datakilden er avhengig av, og hvordan eller naar "
            "jobben forventes aa kjoere."
        ),
        "applications": [
            "Importjobb-definisjoner (import_jobs.py): legger til datagrunnlagstekst og avhengige komponenter per datakilde.",
            "Backend importstatus (main.py): eksponerer forklaring, avhengigheter, forventet intervall og beregnet kjoringsbeskrivelse.",
            "Desktop V2 datakilder (DataSourceDetailPage.tsx): viser nytt forklaringskort paa datakildedetaljen.",
            "Desktop V2 CSS (status.css): legger til kompakt layout for datakildeforklaringen.",
        ],
        "request": "jeg savner et tekst felt med forklaring paa hvordan dette datagrunnlaget hentes og hvilke komponenter det er avhengig av, naar det planlegges kjort alle tidspunkter eller hvor ofte liksom",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Alle definerte datakilder faar forklaring og komponentliste der metadata finnes.",
            "EasyPark viser faktisk fast importplan fra downloader-statusen, inkludert klokkeslettene.",
            "Andre datakilder viser forventet frekvens og varselgrense basert paa importjobb-definisjonen.",
        ],
    },
    {
        "version": "1",
        "build": "1367",
        "date": "01.07.2026",
        "headline": "Klikkbare datakilder",
        "title": "Admin datakilder har egen infoside per datakilde",
        "description": (
            "Build 1367 gjor datakildene klikkbare og legger til en egen detaljside for hver importjobb. "
            "Detaljsiden viser status, definisjon, siste tidspunkt, neste forventede kjoring og siste "
            "lagrede importkjoringer."
        ),
        "applications": [
            "Backend importstatus (main.py): legger til path paa datakilder og nytt detalj-API per job_name.",
            "Desktop V2 ruting (AppRoutes.tsx): legger til /admin/datakilder/:jobName.",
            "Desktop V2 datakilder (DataSourceDetailPage.tsx): ny infoside med statuskort, metadata og kjoringslogg.",
            "Admin drift (OperationsPage.tsx): datakildenavn lenker til samme infoside.",
            "Smoke-ruter: detaljsiden testes med EasyPark-importen.",
        ],
        "request": "alle datakilder under Admin/datakilder burde vaere klikkbare og ha en info side",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Alle datakilder i Admin/datakilder faar path og klikkbar tittel.",
            "Infosiden viser de siste 50 importkjoringene naar de finnes.",
            "Admin/drift lenker ogsaa til samme datakildeside for konsistent navigasjon.",
        ],
    },
    {
        "version": "1",
        "build": "1366",
        "date": "01.07.2026",
        "headline": "EasyPark importplan oppdatert",
        "title": "EasyPark-import kjoerer annenhver time gjennom dagen",
        "description": (
            "Build 1366 dokumenterer ny fast EasyPark-importplan. Runtime-konfigen paa QNAP er satt til "
            "08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00 og 23:00, slik at parkeringsgrunnlaget "
            "oppdateres oftere gjennom aapningstiden."
        ),
        "applications": [
            "EasyPark-downloader runtime: EASYPARK_RUN_TIMES er endret paa QNAP og containeren er restartet.",
            "EasyPark-downloader oppskrift (.env.example, README.md): dokumenterer ny standard importplan.",
            "Buildlogg (build_log.py): registrerer build 1366.",
        ],
        "request": "gjor det",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny plan er 08:00, 10:00, 12:00, 14:00, 16:00, 18:00, 20:00 og 23:00.",
            "Neste import i grensesnittet beregnes videre fra EasyPark-downloaderens faktiske /status-endepunkt.",
        ],
    },
    {
        "version": "1",
        "build": "1365",
        "date": "01.07.2026",
        "headline": "Neste import paa dashboard",
        "title": "Dashboardkort viser neste EasyPark-import ved parkeringsgrunnlaget",
        "description": (
            "Build 1365 viser neste planlagte EasyPark-import direkte i dashboardkortene der parkeringsdatatidspunktet "
            "allerede vises. Dette gjor at kortene viser baade hvor langt parkeringsgrunnlaget er oppdatert og naar "
            "neste import forventes aa kjoere."
        ),
        "applications": [
            "Desktop V2 dashboard (OverviewPage.tsx): henter nextExpectedAt fra EasyPark-datakilden og legger den bak parkeringsdatatidspunktet.",
            "Omsetningsdashboard: viser neste EasyPark-import paa datagrunnlagslinjen i hvert kort.",
            "Parkeringsdashboard: viser neste EasyPark-import paa per-linjen i hvert kort.",
            "Buildlogg (build_log.py): registrerer build 1365.",
        ],
        "request": "paa dashboard kortene saa kan ogsaa neste import tas med i parantes bak naar sist import for parkering gikk",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Neste import vises som kort tekst i parentes, for eksempel neste 01.07. 12:00.",
            "Solingkortene er ikke endret, siden neste import gjelder EasyPark/parkering.",
        ],
    },
    {
        "version": "1",
        "build": "1364",
        "date": "01.07.2026",
        "headline": "Nye kjoretoy utvidet",
        "title": "Nye kjoretoy-kortet viser maaned, forrige maaned og hittil i aar",
        "description": (
            "Build 1364 utvider toppkortet for nye kjoretoy paa Parkering > Oversikt. Hovedtallet viser fortsatt "
            "nye kjoretoy denne maaneden, mens detaljlinjen viser forrige maaned og hittil i aar basert paa samme "
            "first_seen-grunnlag."
        ),
        "applications": [
            "Backend moduldata (main.py): legger til periodegrenser for forrige maaned og innevaerende aar i modul-API-et.",
            "Parkering oversikt: Nye kjoretoy-kortet viser naa forrige maaned og hittil i aar i samme boks.",
            "Buildlogg (build_log.py): registrerer build 1364.",
        ],
        "request": "kan du ta med forste parkering forrige mnd samt saa langt dette aaret ogsaa i samme boks",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Denne maaneden er fortsatt hovedverdien i kortet.",
            "Detaljteksten viser forrige maaned og hittil i aar fra kjoretoy.first_seen.",
        ],
    },
    {
        "version": "1",
        "build": "1363",
        "date": "01.07.2026",
        "headline": "Nye kjoretoy paa parkering",
        "title": "Parkering oversikt viser nye kjoretoy denne maaneden",
        "description": (
            "Build 1363 legger til et nytt toppkort paa Parkering > Oversikt. Kortet viser hvor mange unike "
            "kjoretoy som har sin forste registrerte parkering i innevaerende maaned, basert paa kjoretoy.first_seen."
        ),
        "applications": [
            "Backend moduldata (main.py): beregner nye kjoretoy denne maaneden fra ParkingVehicle.first_seen.",
            "Desktop V2 parkering/oversikt: viser nytt kort i eksisterende toppgrid uten egen frontend-endring.",
            "Buildlogg (build_log.py): registrerer build 1363.",
        ],
        "request": "paa siden parkering/oversikt onsker jeg paa toppen sammen med de 5 andre boksene aa ha informasjon om hvor mange nye kjoretoy det er denne mnd.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Kortet heter Nye kjoretoy og lenker til kjoretoyoversikten.",
            "Tallet teller bare biler med first_seen fra maanedsstart til og med dagens importgrunnlag.",
        ],
    },
    {
        "version": "1",
        "build": "1362",
        "date": "01.07.2026",
        "headline": "Neste EasyPark-import synlig",
        "title": "PC og mobil viser faktisk neste planlagte EasyPark-import",
        "description": (
            "Build 1362 lar EasyPark-downloaderen eksponere tidspunktet for neste planlagte import fra samme "
            "schedulerlogikk som faktisk styrer jobben. Backend bruker dette tidspunktet i datakildestatus, "
            "PC-dashboardet viser neste import paa EasyPark-linjen, og mobilens parkering-side viser neste "
            "planlagte import sammen med sist oppdatert og manuell importstatus."
        ),
        "applications": [
            "EasyPark-downloader (easypark_downloader/app/main.py): eksponerer next_run_at i /health og /status.",
            "Backend datakilder (main.py): bruker faktisk next_run_at for EasyPark sin nextExpectedAt.",
            "Desktop V2 status (api.ts, OverviewPage.tsx): viser neste EasyPark-import i Status datakilder.",
            "Mobil dashboard (online_dashboard/app/main.py): viser neste planlagte EasyPark-import paa /parkering.",
            "Robusthet: statuskall mot EasyPark-downloaderen bruker kortere timeout i PC- og mobilbackend.",
        ],
        "request": "neste planlagte import burde vaere tydelig i grensesnittene baade paa mobil og pc",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Neste importtid beregnes ett sted i EasyPark-downloaderen og gjenbrukes av statusendepunktene.",
            "PC-grensesnittet viser neste planlagte EasyPark-import i datakildelisten.",
            "Mobilens parkering-side viser neste planlagte import i oppdatert-linjen og i manuell importstatus.",
        ],
    },
    {
        "version": "1",
        "build": "1361",
        "date": "30.06.2026",
        "headline": "Backend delt videre opp",
        "title": "Elvia-parser, SUN2-romlogikk og generisk verdi-parsing er flyttet ut av main.py",
        "description": (
            "Build 1361 fortsetter oppryddingen i backend-monolitten. Elvia-importens JSON-parser ligger nå i "
            "energy_helpers.py, SUN2-rommapping og mojibake-reparasjon ligger i sun2_helpers.py, og felles "
            "bool/int/float/timestamp-parsing ligger i value_parsing.py. API-oppførsel og databasekontrakter er "
            "uendret."
        ),
        "applications": [
            "Backend energi (energy_helpers.py): overtar parser for Elvia JSON-import og bruker felles verdi-parsing.",
            "Backend SUN2 (sun2_helpers.py): samler rom-id, rometiketter, gammel rom-10-spesialregel og mojibake-reparasjon.",
            "Backend verdi-parsing (value_parsing.py): samler bool/int/float/timestamp/areal/first-dict-hjelpere.",
            "Backend hovedapp (main.py): importerer de nye modulene og mister flere hundre linjer hjelpefunksjoner.",
            "Tester: legger til målrettede tester for Elvia-parser, SUN2-romlogikk og verdi-parsing.",
            "Lokal sjekk (scripts/check-local.ps1): kompilerer de nye modulene i standard pipeline.",
        ],
        "request": "fortsett med videre oppsplitting",
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "main.py er redusert med omtrent 300 linjer netto i denne runden.",
            "Elvia-importlogikken er testet med norsk desimalformat, delvis måned og meter-id fra filnavn.",
            "SUN2-rommappingen er testet for display-rom 10, gammel ukjent rom-10 og vanlige rom-id-formater.",
            "Felles verdi-parsing har egne tester for norske boolske verdier, tallformat, timestamp og Roborock-areal.",
        ],
    },
    {
        "version": "1",
        "build": "1360",
        "date": "30.06.2026",
        "headline": "CSS- og tidsmodul ryddet",
        "title": "Design-tokens, CSS-audit og felles datetime-hjelpere er strammet opp",
        "description": (
            "Build 1360 gjør en vedlikeholdsrunde med lav risiko. De mest repeterte nøytrale fargene og skyggene "
            "er flyttet til felles design-tokens, CSS-auditen skiller nå mellom token-definisjoner og reelle "
            "hardkodede verdier, og datetime-hjelpere som brukes bredt i backend er flyttet ut av main.py."
        ),
        "applications": [
            "Frontend design-system (desktop_v2/src/styles/tokens.css): legger til delte tokens for panelbakgrunn, linjer, tekst og svak skygge.",
            "Frontend CSS: bytter gjentatte hardkodede farger til tokens i status, energi, ventilasjon, parkering, soling og oppgjør.",
            "Frontend audit (desktop_v2/scripts/audit-css.mjs): teller token-farger separat og rapporterer topp hardkodede farger utenfor token-filen.",
            "Backend tidshåndtering (time_formatting.py, main.py): flytter felles datetime-hjelpere ut av main.py.",
            "Tester (tests/test_time_formatting.py): dekker lokal/UTC-konvertering og femminutters bucket.",
            "Shell (AppShell.tsx): retter tekstkoding på buildlogg-lenken.",
        ],
        "request": "kjør på gjør alt",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "CSS-auditen viser nå 41 token-farger og 121 hardkodede farger utenfor tokens, mot ca. 164 utenfor tokens før oppryddingen.",
            "possibleUnusedClasses er fortsatt 0 etter endringen.",
            "Frontend bundle er fortsatt innenfor grensen: 756,9 kB gzip mot 760 kB.",
            "main.py er litt mindre og bruker felles tidshjelpere fra time_formatting.py.",
        ],
    },
    {
        "version": "1",
        "build": "1359",
        "date": "30.06.2026",
        "headline": "Renere CSS-audit",
        "title": "CSS-auditen skiller Leaflet runtime-klasser fra reelt ubrukt CSS",
        "description": (
            "Build 1359 forbedrer kvalitetssignalet i frontend-auditen. Leaflet lager egne CSS-klasser i DOM "
            "runtime, og disse ble tidligere rapportert som mulig ubrukt CSS. Audit-scriptet behandler nå "
            "leaflet-prefixen som dynamisk på samme måte som Ant Design."
        ),
        "applications": [
            "Frontend audit (desktop_v2/scripts/audit-css.mjs): legger Leaflet-klasser inn som dynamiske runtime-klasser.",
            "Buildlogg (build_log.py): registrerer build 1359.",
        ],
        "request": "Kjør på gjør applikasjonen bedre og bedre. du har dagen på deg.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "CSS-auditens possibleUnusedClasses gikk fra 35 til 0.",
            "Kart-CSS for OwnTracks beholdes uendret.",
            "Videre CSS-opprydding får tydeligere signal, fordi tredjepartsklassene ikke lenger skaper falske funn.",
        ],
    },
    {
        "version": "1",
        "build": "1358",
        "date": "30.06.2026",
        "headline": "Renere QNAP-deploy",
        "title": "Deploy validerer Caddy i stedet for å reloade en nystartet proxy",
        "description": (
            "Build 1358 rydder opp i QNAP-deployen. Caddy kjører med admin-API avslått, og deployscriptet "
            "prøvde derfor å kjøre reload etter at proxyen allerede var startet på nytt. Scriptet validerer nå "
            "Caddyfile i containeren i stedet. Caddyfile er også formatert og ryddet for proxy-headere som Caddy "
            "setter selv."
        ),
        "applications": [
            "Deploy (scripts/deploy-qnap.ps1): bytter Caddy reload til Caddy validate etter proxy-restart.",
            "Proxy (Caddyfile): formaterer Caddyfile og fjerner unødvendige X-Forwarded-header overrides.",
            "Buildlogg (build_log.py): registrerer build 1358.",
        ],
        "request": "Kjør på gjør applikasjonen bedre og bedre. du har dagen på deg.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Deployloggen skal ikke lenger vise Caddy reload-feil på grunn av admin off.",
            "Caddyfile valideres eksplisitt etter restart.",
            "Proxyoppsettet beholder samme upstreams for online_dashboard, OwnTracks HTTP og OwnTracks MQTT/WebSocket.",
        ],
    },
    {
        "version": "1",
        "build": "1357",
        "date": "30.06.2026",
        "headline": "Mindre soling-monolitt",
        "title": "Død enkeltimer-kode er fjernet fra soling-modulen",
        "description": (
            "Build 1357 rydder bort en gammel duplisert kodegren for soling/enkeltimer i hovedmodulen. "
            "Aktiv enkeltimer-logikk ligger allerede i egen payload-funksjon, og ruten returnerer dit før "
            "den gamle grenen kunne nås. Dette gjør videre arbeid med soling tryggere og reduserer main.py."
        ),
        "applications": [
            "Backend (main.py): fjerner gammel unreachable enkeltimer-gren fra api_v2_soling_module.",
            "Backend struktur: beholder sun2_sessions_module_payload som eneste aktive modulbygger for soling/enkeltimer.",
            "Buildlogg (build_log.py): registrerer build 1357.",
        ],
        "request": "Kjør på gjør applikasjonen bedre og bedre. du har dagen på deg.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "115 døde linjer er fjernet fra main.py.",
            "Soling/enkeltimer har fortsatt samme aktive API-flate som build 1356.",
            "Senere endringer i enkeltimer trenger nå bare å gjøres i én funksjon.",
        ],
    },
    {
        "version": "1",
        "build": "1356",
        "date": "30.06.2026",
        "headline": "Server-side tabellpaging",
        "title": "Store modultabeller kan bla uten å hente alt på én gang",
        "description": (
            "Build 1356 gjør tunge tabellsider mer robuste ved at backend sender tabellmetadata og bare aktuell side "
            "av store lister. Frontend viser hvilket radintervall som er hentet og har Forrige/Neste-knapper direkte "
            "i tabellhodet. Dette reduserer lastetid og payload-risiko på sider som vokser med historikk."
        ),
        "applications": [
            "Backend (main.py): legger felles tabellmetadata og page/offset for soling/enkeltimer, soling/medlemmer og parkering/kjøretøy.",
            "API-kontrakter (api_types.py): utvider modul-tabeller med valgfri meta-informasjon.",
            "Desktop v2 API (api.ts): legger type for tabellmetadata.",
            "Desktop v2 modulsider (ModulePage.tsx, ModuleTablePane.tsx): viser radintervall og Forrige/Neste for server-side paging.",
            "Tester (tests/test_api_types.py): dekker at modul-tabeller kan ha metadata.",
            "Buildlogg (build_log.py): registrerer build 1356.",
        ],
        "request": "Kjør på gjør applikasjonen bedre og bedre. du har dagen på deg.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Soling/enkeltimer henter nå bare valgt side fra databasen, ikke første blokk uten sidekontroll.",
            "Soling/medlemmer og parkering/kjøretøy har samme server-side blaing.",
            "Tabellene viser nå tydelig radintervallet som er lastet, for eksempel 1-100 av 4823.",
            "Forrige/Neste-knapper ligger ved tabellen slik at brukeren slipper å skrive sidetall manuelt.",
            "Eksisterende Antall-filter beholdes for å styre hvor mange rader som lastes per side.",
        ],
    },
    {
        "version": "1",
        "build": "1355",
        "date": "30.06.2026",
        "headline": "Struktur- og ytelsesopprydding",
        "title": "Backend, CSS, systemkart og API-kontrakter er strammet opp",
        "description": (
            "Build 1355 starter den systematiske oppryddingen av Fibaro10 V2. Importjobb-definisjoner er flyttet "
            "ut av main.py, Admin har fått systemkart, CSS bruker flere felles design-tokens, tunge listevisninger "
            "er justert, Admin har fått samlet kontrollinngang og API-kontraktene for modulinnhold er tydeligere."
        ),
        "applications": [
            "Backend (main.py/import_jobs.py): flytter importjobb-metadata ut av monolitten og beholder samme API-bruk.",
            "Backend (system_inventory.py): legger felles systemoversikt som brukes av Admin/Systemkart.",
            "Backend/Admin: legger Kontroll som samlet inngang til parkering-, soling-, energi- og datakvalitetsavstemming.",
            "Backend ytelse: tynner energigrafdata til praktisk visningsoppløsning og reduserer standarduttrekk for tunge solinglister.",
            "Desktop v2 meny/ruting: legger Admin/Systemkart og retter fallback-lenke til reell dashboard-startside.",
            "Desktop v2 CSS: erstatter mange hardkodede farger med eksisterende design-tokens.",
            "API-kontrakter/tester: legger typer for modul-kort og tabeller, samt tester for importjobber og systemkart.",
            "Dokumentasjon: legger funksjonsstruktur for videre meny- og sideopprydding.",
        ],
        "request": "Kjør på med alle 7 trinnene, gjør det grundig.",
        "work_duration": "ca. 1 t 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Importjobb-definisjonene ligger nå i en egen modul i stedet for direkte i main.py.",
            "Admin-menyen har fått Systemkart med komponenter, runtime, helsesjekk og kritikalitet.",
            "Admin-menyen har fått Kontroll som samler eksisterende avstemminger uten å duplisere faglogikk.",
            "CSS-audit har færre hardkodede farger og mer konsekvent bruk av tokens.",
            "Energistatus sender færre grafpunkter til nettleseren uten å endre lagret 30-sekunders logging.",
            "Soling/enkeltimer og soling/medlemmer laster færre rader som standard, men beholder Antall-filter.",
            "Funksjonsstruktur er dokumentert for å redusere overlapp mellom sider videre.",
            "API-kontraktene dekker generiske modul-kort og tabeller.",
        ],
    },
    {
        "version": "1",
        "build": "1354",
        "date": "29.06.2026",
        "headline": "Stabile OwnTracks-punkter",
        "title": "OwnTracks-posisjoner blir liggende over kartflisene",
        "description": (
            "Build 1354 retter visningen av OwnTracks-kartet der posisjonspunktene kunne vises kort "
            "og deretter forsvinne når kartflisene var ferdig lastet. Leaflet-panene får nå eksplisitt "
            "lagrekkefølge slik at spor, punkter, markører og popup ligger over kartbakgrunnen."
        ),
        "applications": [
            "Desktop v2 CSS (owntracks.css): legger eksplisitt z-index for Leaflet tile-, overlay-, marker-, tooltip- og popup-pane.",
            "Buildlogg (build_log.py): registrerer build 1354.",
        ],
        "request": "Posisjonene vises et kort øyeblikk ved refresh og blir deretter borte.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Kartflisene ligger nå under posisjonspunktene.",
            "Spor og punkter skal ikke lenger forsvinne etter at kartet har lastet ferdig.",
            "Markører og popup har også eksplisitt lagrekkefølge.",
        ],
    },
    {
        "version": "1",
        "build": "1353",
        "date": "29.06.2026",
        "headline": "Alle OwnTracks-posisjoner",
        "title": "OwnTracks-kartet kan vise alle lagrede posisjonsmeldinger",
        "description": (
            "Build 1353 gjør Alle-valget i OwnTracks-kartet reelt ubegrenset. "
            "Når Alle er valgt hentes alle lagrede OwnTracks-meldinger som har koordinater, "
            "ikke bare et fast antall siste meldinger."
        ),
        "applications": [
            "Backend (main.py): lar /api/owntracks/map bruke limit=0 som ubegrenset posisjonsuttrekk.",
            "Desktop v2 (OwnTracksPage.tsx): lar Alle-valget hente alle lagrede posisjoner og viser dette tydelig i metateksten.",
            "Buildlogg (build_log.py): registrerer build 1353.",
        ],
        "request": "Gi mulighet til å vise alle OwnTracks-meldinger, altså alle rapporterte posisjoner.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Alle-valget på OwnTracks-kartet henter nå uten radbegrensning.",
            "Tidsfiltrene 1t, 6t, 24t og 7d beholder en praktisk grense for rask visning.",
            "Kartet teller og beskriver punktene som posisjoner, siden bare meldinger med koordinater kan vises på kart.",
        ],
    },
    {
        "version": "1",
        "build": "1352",
        "date": "29.06.2026",
        "headline": "OwnTracks kart",
        "title": "OwnTracks-meldinger vises på kart under Admin",
        "description": (
            "Build 1352 legger en dedikert kartside for OwnTracks under Admin. "
            "Siden viser siste posisjonsmeldinger som punkter og spor, siste posisjon per enhet "
            "og registrerte waypoints med radius der dette finnes."
        ),
        "applications": [
            "Backend (main.py): legger /api/owntracks/map med posisjoner, enheter og waypoints.",
            "Desktop v2 (OwnTracksPage.tsx): bygger kart med spor, siste posisjoner, waypoints, filter og eksisterende OwnTracks-tabeller.",
            "Desktop v2 CSS (owntracks.css): legger kartflate, markører, popup og nødvendig Leaflet-basestil.",
            "Desktop v2 ruting/API: kobler /admin/owntracks til dedikert side og legger typed fetch-funksjon.",
            "Frontend dependencies: legger til leaflet og @types/leaflet.",
            "Buildlogg (build_log.py): registrerer build 1352.",
        ],
        "request": "Vis alle siste OwnTracks-meldinger på et kart på enklest mulig måte.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "OwnTracks-siden under Admin har nå kart øverst.",
            "Kartet kan filtreres på 1 time, 6 timer, 24 timer, 7 dager eller alle lagrede punkter.",
            "Posisjonsmeldinger tegnes som punkter og spor per enhet.",
            "Siste kjente enhetsposisjon og waypoints vises direkte i kartet.",
            "Eksisterende OwnTracks-kort og tabeller beholdes under kartet.",
        ],
    },
    {
        "version": "1",
        "build": "1351",
        "date": "29.06.2026",
        "headline": "Ukegraf som dagsgraf",
        "title": "Ukegrafen i periodesammenligning bruker nå full uke som visningsakse",
        "description": (
            "Build 1351 gjør ukegrafen i omsetningens periodesammenligning likere dagsgrafen. "
            "Sammendragstallene sammenlignes fortsatt på riktig datatidspunkt, men selve grafen "
            "viser en full ukeakse og lar sammenligningsuken gå helt ut."
        ),
        "applications": [
            "Backend (main.py): bruker fast full uke som grafvindu for period=week i /api/status/comparison.",
            "Buildlogg (build_log.py): registrerer build 1351.",
        ],
        "request": "Ukegrafen er ikke lik dagsgrafen og bør endres.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ukegrafen får nå full uke som visningsakse.",
            "Inneværende uke stopper fortsatt ved siste datatidspunkt, slik dagsgrafen gjør for dagen i dag.",
            "Sammenligningsuken vises helt ut, slik gårsdagen vises helt ut i dagsgrafen.",
        ],
    },
    {
        "version": "1",
        "build": "1350",
        "date": "29.06.2026",
        "headline": "Presise omsetningsklikk",
        "title": "Klikk på omsetningskort åpner grafen med bare valgt sammenligning aktiv",
        "description": (
            "Build 1350 gjør lenkene fra omsetningskortene mer presise. Når man klikker på for eksempel "
            "Mot i går samme tidspunkt, åpnes periodesammenligningen med bare dagens periode og gårsdagen "
            "som aktive dataserier. Ekstra referanselinjer blir ikke sendt med for disse kortklikkene."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): legger references=none på lenker fra omsetningskortene.",
            "Desktop v2 (StatusComparisonPage.tsx, api.ts, queryKeys.ts): sender og cacher referansevalget som del av grafspørringen.",
            "Backend (main.py): støtter references=none på /api/status/comparison.",
            "Buildlogg (build_log.py): registrerer build 1350.",
        ],
        "request": "Når man klikker på sammenligningsfeltene på omsetningskortene, skal grafen bare ha valgt sammenligning og aktuell periode aktiv.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Omsetningskortene åpner nå sammenligningsgrafen uten ekstra referanseserier.",
            "Direkte bruk av sammenligningssiden kan fortsatt bruke standard referanser.",
            "Navigering frem og tilbake i grafen beholder samme rene sammenligningsmodus.",
        ],
    },
    {
        "version": "1",
        "build": "1349",
        "date": "29.06.2026",
        "headline": "Ryddigere CSS-eierskap",
        "title": "Dashboardkortene har tydeligere CSS-eierskap og færre skjulte overstyringer",
        "description": (
            "Build 1349 rydder i CSS-eierskapet mellom status-overview.css og status-periods.css. "
            "De generiske dashboardreglene er avgrenset slik at de ikke overstyrer periodekortene for "
            "omsetning, parkering og soling, og gjentatte farge- og borderverdier er samlet i lokale "
            "variabler på periodekortene."
        ),
        "applications": [
            "Desktop v2 CSS (status-periods.css): samler periodekortets tone-, border- og bakgrunnsverdier i lokale CSS-variabler.",
            "Desktop v2 CSS (status-overview.css): avgrenser generiske status-period-card-regler slik at de ikke overstyrer revenue-period-card.",
            "Buildlogg (build_log.py): registrerer build 1349.",
        ],
        "request": "Gjennomgå CSS, stram opp, rydd opp og effektiviser uten å endre funksjon.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Skjult cascade-konflikt mellom status-overview.css og status-periods.css er ryddet bort.",
            "Gjentatte farge- og borderuttrykk i periodekortene er samlet i lokale CSS-variabler.",
            "Topplinjen på periodekortene styres nå fra periodkortets egen CSS.",
            "Dashboardenes visuelle uttrykk er beholdt, men CSS-strukturen er tydeligere.",
        ],
    },
    {
        "version": "1",
        "build": "1348",
        "date": "29.06.2026",
        "headline": "Tonet referansefelt",
        "title": "Nederste felt på dashboardkortene skiller seg tydeligere ut",
        "description": (
            "Build 1348 gir nederste referansefelt på dashboardets periodekort en svak domene-tonet bakgrunn "
            "og en smal venstremarkering. Feltet bruker samme tone som siden, slik at omsetning, parkering og "
            "soling fortsatt er konsekvente uten at referansefeltet blir visuelt tungt."
        ),
        "applications": [
            "Desktop v2 CSS (status-periods.css): legger svak tonet bakgrunn, tydeligere border og venstremarkering på referansefeltet.",
            "Buildlogg (build_log.py): registrerer build 1348.",
        ],
        "request": "Gjør nederste felt på kortene mer adskilt med bakgrunnsfarge.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Referansefeltet nederst får en svak farget bakgrunn basert på kortets domene.",
            "En diskret farget venstremarkering gir tydeligere separasjon.",
            "Kortets størrelse og innhold er ellers uendret.",
        ],
    },
    {
        "version": "1",
        "build": "1347",
        "date": "29.06.2026",
        "headline": "Finjusterer korttetthet",
        "title": "Dashboardkortene er senket ytterligere mot samme mellomromsrytme",
        "description": (
            "Build 1347 finjusterer minimumshøyden på periodekortene etter live-måling av avstanden før nederste "
            "referansefelt. Omsetningskortene og antallskortene blir litt lavere, slik at nederste felt ligger "
            "nærmere samme visuelle rytme som sammenligningsboksene øverst."
        ),
        "applications": [
            "Desktop v2 CSS (status-periods.css): justerer min-height fra 312/264 til 300/254.",
            "Buildlogg (build_log.py): registrerer build 1347.",
        ],
        "request": "Gjør kortene lavere og la nederste felt få tilsvarende mellomrom som de øverste boksene.",
        "work_duration": "ca. 5 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Omsetningskortene er senket ytterligere.",
            "Parkering- og solingkortene er senket ytterligere.",
            "Avstanden før nederste referansefelt er redusert for å matche resten av kortets rytme bedre.",
        ],
    },
    {
        "version": "1",
        "build": "1346",
        "date": "29.06.2026",
        "headline": "Lavere dashboardkort",
        "title": "Periodekortene er strammet inn i høyde og referansefelt",
        "description": (
            "Build 1346 reduserer minimumshøyden på dashboardets periodekort og strammer inn luft, padding "
            "og ikonstørrelse i nederste referansefelt. Parkering- og solingkortene får lavere minimumshøyde "
            "fordi de har én datalinje, mens omsetningskortene beholder samme struktur med to linjer."
        ),
        "applications": [
            "Desktop v2 CSS (status-periods.css): reduserer min-height, card-body-gap, referansepadding og referanseikon.",
            "Buildlogg (build_log.py): registrerer build 1346.",
        ],
        "request": "Gjør alle kortene litt lavere, og gjør mellomrommet i nederste boks tilsvarende de øverste boksene med utgangspunkt i omsetningskortene.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Omsetningskortene har lavere minimumshøyde og mindre ubrukt luft før referansefeltet.",
            "Parkering- og solingkortene bruker samme kompakte rytme, men med lavere høyde tilpasset én datalinje.",
            "Nederste referansefelt har strammere padding og mindre ikon slik at det visuelt matcher toppboksene bedre.",
        ],
    },
    {
        "version": "1",
        "build": "1345",
        "date": "29.06.2026",
        "headline": "Strammere referansefelt",
        "title": "Referansefeltet nederst på dashboardkortene viser bare tallene",
        "description": (
            "Build 1345 fjerner overskriftene Hele referansedagen, Hele referanseuken, Hele referansemåneden "
            "og Hele referanseåret fra nederste referansefelt på dashboardkortene. Selve referansetallene og "
            "lenkene er uendret, men kortene blir lavere og mer konsekvente."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): fjerner referanseoverskriften fra omsetning-, parkering- og solingkort.",
            "Desktop v2 CSS (status-periods.css): fjerner ubrukt tittelstyling og toppmargin i referansefeltet.",
            "Buildlogg (build_log.py): registrerer build 1345.",
        ],
        "request": "Overskriften på den nederste boksen, for eksempel Hele referanseuken, kan fjernes på alle kortene.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Nederste referansefelt viser nå direkte referanselinjene uten egen overskrift.",
            "Endringen gjelder alle periodkort på omsetning, parkering og soling.",
            "Ubrukt CSS for den fjernede overskriften er ryddet bort.",
        ],
    },
    {
        "version": "1",
        "build": "1344",
        "date": "29.06.2026",
        "headline": "Likere dashboardkort",
        "title": "Parkering og soling bruker samme kortstruktur som omsetning",
        "description": (
            "Build 1344 fjerner Største driver-etikettene fra omsetningskortene og legger parkering-/solingkortene "
            "over på samme interne struktur som omsetningskortene. Antallskortene bruker nå samme topp, sammenligningsfelt, "
            "tabellseksjon og referansefelt nederst, men med én linje og antall som hovedverdi."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): fjerner største-driver-logikken og bygger parkering-/solingkort med samme tabellstruktur som omsetning.",
            "Desktop v2 CSS (status-periods.css): fjerner activity-spesiallayout og badge-styling slik at kortene deler samme grunnstil.",
            "Buildlogg (build_log.py): registrerer build 1344.",
        ],
        "request": "Ta bort etiketter med Største driver, og sørg for at parkering- og solingkortene er eksakt like som omsetning selv om de ikke har alle feltene.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Alle synlige Største driver-etiketter er fjernet.",
            "Omsetningskortene beholder samme tall og sammenligninger uten ekstra badge-støy.",
            "Parkering- og solingkortene bruker samme tabellseksjon som omsetningskortene.",
            "Den gamle tre-boks-layouten for antallskort er fjernet.",
            "Activity-spesifikk CSS er ryddet bort der felles kortstil nå dekker behovet.",
        ],
    },
    {
        "version": "1",
        "build": "1343",
        "date": "29.06.2026",
        "headline": "Fjerner Drivere-overskrift",
        "title": "Omsetningskortene starter driverdelen rett på tabellen",
        "description": (
            "Build 1343 fjerner den ekstra Drivere-overskriften inne i omsetningskortene. "
            "Tabellhodet forklarer allerede innholdet, så kortene blir lavere og roligere uten å miste informasjon."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): fjerner Drivere-tittelen fra RevenuePeriodCard.",
            "Desktop v2 CSS (status-periods.css): fjerner ubrukt styling for revenue-drivers-title.",
            "Buildlogg (build_log.py): registrerer build 1343.",
        ],
        "request": "Overskriften Drivere på omsetningskortene kan fjernes.",
        "work_duration": "ca. 5 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Drivere-overskriften er fjernet fra alle omsetningskort.",
            "Driver-tabellen og alle tall/sammenligninger er uendret.",
            "Ubrukt CSS for den fjernede overskriften er ryddet bort.",
        ],
    },
    {
        "version": "1",
        "build": "1342",
        "date": "29.06.2026",
        "headline": "Fjerner dashboardtoppfelt",
        "title": "Omsetning-, parkering- og solingdashboard starter rett på periodekortene",
        "description": (
            "Build 1342 fjerner seksjonsfeltet som lå over de fire periodekortene på dashboardene. "
            "Kortene inneholder allerede datatidspunkt og periodekontekst, så dashboardet får nå mindre repetisjon og mer plass til selve tallene."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): gjør StatusSection-headeren valgfri og skjuler den på omsetning-, parkering- og solingdashboardene.",
            "Desktop v2 CSS (status-overview.css): legger til enkel no-header-variant for dashboardseksjoner.",
            "Buildlogg (build_log.py): registrerer build 1342.",
        ],
        "request": "Feltet over alle omsetningskortene er overflødig fordi tidspunkt repeteres i hvert kort.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Omsetningsdashboardet starter nå rett på de fire periodekortene.",
            "Parkering- og solingdashboardene følger samme mønster for konsistens.",
            "Driftdashboardet beholder egne seksjonsoverskrifter der de fortsatt grupperer ulikt innhold.",
        ],
    },
    {
        "version": "1",
        "build": "1341",
        "date": "29.06.2026",
        "headline": "Rydder periodekort",
        "title": "Datagrunnlagstripen er fjernet og årsreferanser vises på egne linjer",
        "description": (
            "Build 1341 fjerner det overflødige datagrunnlagsfeltet over periodekortene på dashboardene. "
            "Tidspunktet står allerede inne i hvert kort, så visningen blir roligere uten å miste informasjon. "
            "Referansefeltet nederst på omsetningskortene er samtidig strammet opp slik at hvert referanseår vises på egen linje."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): fjerner felles datagrunnlagstrip over omsetning-, parkering- og solingkort.",
            "Desktop v2 CSS (status-periods.css): viser referanser nederst i omsetningskortene som separate, ryddige linjer og fjerner ubrukt basis-styling.",
            "Buildlogg (build_log.py): registrerer build 1341.",
        ],
        "request": "Årskortet for omsetning må bruke to linjer på referanseårene, og feltet over alle kortene er overflødig fordi tidspunkt repeteres i hvert kort.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Felles datagrunnlagsfelt over periodekortene er fjernet.",
            "Omsetningskortenes referansefelt nederst viser nå én referanse per linje.",
            "Årskortet får samme referansestruktur som dag-, uke- og månedskortene.",
            "Ubrukt CSS for datagrunnlagstripen er fjernet.",
        ],
    },
    {
        "version": "1",
        "build": "1340",
        "date": "29.06.2026",
        "headline": "Fjerner redundant sumlinje",
        "title": "Omsetningskortene viser ikke lenger Sum hittil inne i driver-tabellen",
        "description": (
            "Build 1340 fjerner den overflodige Sum hittil-raden i driver-tabellen på omsetningskortene. "
            "Totalen står allerede tydelig som hovedtall øverst i hvert periodekort, så driver-tabellen viser nå kun "
            "fordelingen mellom soling og parkering."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): fjerner Sum hittil-raden fra RevenuePeriodCard.",
            "Desktop v2 CSS (status-periods.css): fjerner ubrukt styling for revenue-driver-total og rydder siste driverlinje.",
            "Buildlogg (build_log.py): registrerer build 1340.",
        ],
        "request": "Sum hittil-linja på omsetningskortene er overflødig fordi summen allerede står øverst.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Omsetningskortenes driver-tabell viser nå bare Soling og Parkering.",
            "Den redundante Sum hittil-raden er fjernet fra markup og CSS.",
            "Siste driverlinje avsluttes rent uten ekstra bunnstrek.",
        ],
    },
    {
        "version": "1",
        "build": "1339",
        "date": "29.06.2026",
        "headline": "Helhetlig dashboarddesign",
        "title": "Dashboardflatene får roligere rammer, tydeligere hierarki og mer kontrollert fargebruk",
        "description": (
            "Build 1339 gjør en samlet designopprydding av dashboardene for omsetning, parkering, soling og drift. "
            "Rammer og skygger er dempet, domenefarger brukes mer som aksenter enn som full ramme rundt alle elementer, "
            "og periodekort, datagrunnlag, støttebokser og arbeidsflater er justert til samme visuelle system."
        ),
        "applications": [
            "Desktop v2 CSS (status-overview.css): strammer opp dashboardseksjoner, arbeidsflatekort, infofelt og dashboard-spesifikke kortoverstyringer.",
            "Desktop v2 CSS (status-periods.css): demper periodekort, sammenligningsbokser, støttefelt og intern korttypografi.",
            "Buildlogg (build_log.py): registrerer build 1339.",
        ],
        "request": "Kjør seriøs designgjennomgang av dashboard og gjør det enda proffere og mer helhetlig.",
        "work_duration": "ca. 40 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Dashboardseksjonene er gjort roligere med mindre konkurrerende rammer og mykere flater.",
            "Periodekortene bruker nå domenefarge som aksentlinje i stedet for kraftig ramme rundt alt.",
            "Sammenligningsbokser, driver-tabeller og referansefelt er dempet for bedre lesbarhet.",
            "Arbeidsflatekort og infofelt er justert til samme visuelle rytme som periodekortene.",
            "CSS-overstyringer er lagt i riktig importrekkefølge slik at dashboardstilen blir stabil.",
        ],
    },
    {
        "version": "1",
        "build": "1338",
        "date": "29.06.2026",
        "headline": "Strammere dashboardkort",
        "title": "Dashboardkortene får roligere typografi og mindre dominerende hovedtall",
        "description": (
            "Build 1338 justerer typografien i periodekortene på dashboardene. De største tallene, titlene, "
            "sammenligningsfeltene og støtteverdiene er redusert noe i størrelse og fontvekt, slik at kortene "
            "leses mer som et operativt styringspanel og mindre som store plakater."
        ),
        "applications": [
            "Desktop v2 CSS (status-periods.css): reduserer fontstørrelser, fontvekter, padding og ikonstørrelser i periodekortene.",
            "Buildlogg (build_log.py): registrerer build 1338.",
        ],
        "request": "Reduser litt størrelse på fonter på kortene, spesielt de største bokstavene og tallene, og vurder bold/strammere design.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Hovedtall i omsetning-, parkering- og solingkort er gjort mindre og lettere.",
            "Korttitler og datagrunnlagstekst bruker lavere fontvekt.",
            "Sammenligningsfelter, støttefelter og referansebokser er strammet inn.",
            "Responsive fontstørrelser er justert slik at kortene holder samme rolige skala på smalere skjermer.",
        ],
    },
    {
        "version": "1",
        "build": "1337",
        "date": "28.06.2026",
        "headline": "Antallsdashboard for parkering og soling",
        "title": "Dashboard > Parkering og Dashboard > Soling får periodkort med antall som hovedfokus",
        "description": (
            "Build 1337 bygger om parkering- og soling-dashboardene slik at de følger samme 2x2-periodestruktur som "
            "omsetningsdashboardet, men med antall som hovedtall. Kortene viser i dag, uke, måned og år, sammenligner "
            "mot relevante referanseperioder og bruker beløp/snitt som støtteinfo i stedet for hovedfokus."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): legger til felles antallskort for parkering og soling basert på statusPeriods-data.",
            "Desktop v2 CSS (status-periods.css): legger til visuell stil for antallsdashboardene med domain-farger for parkering og soling.",
            "Buildlogg (build_log.py): registrerer build 1337.",
        ],
        "request": "Lag tilsvarende dashboard for parkering og soling, men fokusert på antall.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Parkering-dashboardet viser nå fire like antallskort for i dag, uke, måned og år.",
            "Soling-dashboardet viser nå fire like antallskort for i dag, uke, måned og år.",
            "Kortene sammenligner antall mot forrige periode og relevant fjorårs-/uke-referanse der data finnes.",
            "Beløp og snitt vises som støtteinfo, ikke som hovedtall.",
            "Sammenligningskortene åpner eksisterende periodesammenligning i antallsmodus.",
        ],
    },
    {
        "version": "1",
        "build": "1336",
        "date": "28.06.2026",
        "headline": "Felles design- og CSS-opprydding",
        "title": "Desktop v2 får strammere grunnstil for kort, tabeller, kontroller og statusflater",
        "description": (
            "Build 1336 rydder i de sentrale CSS-lagene som styrer hele desktop-appen. Felles designtokens er utvidet, "
            "Ant Design-kort, tabeller og kontroller bruker nå mer konsistente regler, og status-/omsetningskortene er "
            "justert mot samme visuelle språk. Målet er mindre lokal CSS-støy og et roligere, mer systematisk uttrykk på tvers av sidene."
        ),
        "applications": [
            "Desktop v2 CSS (tokens.css): utvider felles designtokens for paneler, kontroller, overflater og tekstnivåer.",
            "Desktop v2 CSS (layout.css): normaliserer kort, tabeller, skjemaelementer, segmenterte valg og global tabelltetthet.",
            "Desktop v2 CSS (module-content.css): fjerner dupliserte summary-card-regler og samler felles kortstil.",
            "Desktop v2 CSS (app-shell.css, module-metrics.css, module-charts.css, status-*.css): flytter sentrale farger og kanter over på felles tokens.",
            "Buildlogg (build_log.py): registrerer build 1336.",
        ],
        "request": "Gjør en grundig gjennomgang av design og CSS slik at hele appen blir mer ryddig, pen og systematisk.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Hardkodede CSS-farger er redusert fra 458 til 346 i audit.",
            "Felles tabeller er gjort mer kompakte og konsekvente.",
            "Summary-kort har én samlet definisjon i stedet for konkurrerende overstyringer.",
            "Status-, omsetnings-, meny- og nøkkelkort bruker mer av samme designsystem.",
            "Ingen funksjonelle sider eller API-er er endret.",
        ],
    },
    {
        "version": "1",
        "build": "1335",
        "date": "28.06.2026",
        "headline": "Omsetning sammenlignes mot samme periode i fjor",
        "title": "Dashboard > Omsetning bruker samme uke og måned i fjor som sekundær referanse",
        "description": (
            "Build 1335 bytter ut sekundærsammenligningene for uke og måned fra to uker/to måneder tilbake til "
            "samme ISO-uke og samme kalendermåned året før. Årskortet viser konkrete dynamiske årstall, slik at "
            "kortet nå viser mot fjoråret og året før med faktiske årstall i stedet for generiske tekster."
        ),
        "applications": [
            "Backend (main.py): beregner samme ISO-uke i fjor og samme måned i fjor med samme relative datatidspunkt.",
            "Desktop v2 (OverviewPage.tsx): viser dynamiske etiketter som Mot samme uke 2025, Mot samme måned 2025, Mot 2025 og Mot 2024.",
            "Buildlogg (build_log.py): registrerer build 1335.",
        ],
        "request": (
            "Bytt ut 'mot to uker siden' med samme uke 2025, 'mot to måneder siden' med samme måned 2025, "
            "og endre årskortet til Mot 2025 og Mot 2024. Alle årstall skal være dynamiske."
        ),
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Uke-kortet sammenligner nå sekundært mot samme ISO-uke året før.",
            "Måned-kortet sammenligner nå sekundært mot samme kalendermåned året før.",
            "År-kortet viser konkrete sammenligningsår dynamisk.",
            "Omsetning/periodesammenligning-ruten støtter de nye sammenligningsnøklene.",
        ],
    },
    {
        "version": "1",
        "build": "1334",
        "date": "28.06.2026",
        "headline": "Omsetningskort gjort strammere",
        "title": "Dashboard > Omsetning får lavere kort og logo-inspirerte sol- og parkeringsikoner",
        "description": (
            "Build 1334 strammer inn de fire omsetningskortene slik at de tar mindre høyde uten å endre "
            "informasjonsstrukturen. Driverlinjene bruker nå solsymbolet fra logo-uttrykket for soling og en "
            "tilsvarende P for parkering, slik at ikonbruken blir mer konsekvent med resten av løsningen."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): bytter soling og parkering til egne logo-inspirerte inline-ikoner i driverlinjene.",
            "Desktop v2 CSS (status-periods.css): reduserer padding, fontstørrelser og ikonstørrelser i omsetningskortene.",
            "Buildlogg (build_log.py): registrerer build 1334.",
        ],
        "request": (
            "Prøv å redusere litt på størrelse og skift ut symbolet på sol til solsymbolet vårt. "
            "Bruk gjerne P-en på parkering også."
        ),
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Omsetningskortene er gjort lavere og mer kompakte i 2x2-gridet.",
            "Soling bruker et eget solikon basert på logoens formspråk.",
            "Parkering bruker en tilsvarende P i samme ikonstil.",
            "Avstand, tabelltekst, sammenligningsfelt og referansefot er justert ned for bedre skjermutnyttelse.",
        ],
    },
    {
        "version": "1",
        "build": "1333",
        "date": "28.06.2026",
        "headline": "Omsetningskort som kompakte driverkort",
        "title": "Dashboard > Omsetning får tydeligere 2x2-kort med tabellstyrte drivere",
        "description": (
            "Build 1333 viderefører fire like omsetningskort i 2x2-grid, men organiserer hvert kort mer som et "
            "kompakt kontrollkort. Hovedomsetningen er størst, sammenligningene ligger øverst, soling og parkering "
            "står i en fast driver-tabell, og hele referanseperioden ligger som sekundær kontroll nederst."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): bygger om omsetningskortene til felles driverstruktur med ikon, differanse og referansefot.",
            "Desktop v2 CSS (status-periods.css): lager ny kompakt kortlayout inspirert av ønsket eksempel, men beholdt som fire like kort.",
            "Buildlogg (build_log.py): registrerer build 1333.",
        ],
        "request": (
            "Hva med noe slikt, men underteksten på når data er oppdatert må være som det er på build 1332. "
            "Kortene skal fortsatt være like, i grid med 2 i bredden og 2 i høyden, og omsetning skal være det "
            "viktigste tallet."
        ),
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Alle fire kort bruker samme visuelle struktur og samme informasjonsrekkefølge.",
            "Hovedomsetning er løftet visuelt øverst til høyre i hvert kort.",
            "Sammenligningene vises som tydelige avvikskort med retning.",
            "Soling og parkering vises i en fast tabell med dagens/periodebeløp og avvik mot referanser.",
            "Underteksten for datatidspunkt er beholdt i samme form som build 1332.",
        ],
    },
    {
        "version": "1",
        "build": "1332",
        "date": "28.06.2026",
        "headline": "Omsetningskort samlet i lik struktur",
        "title": "Dashboard > Omsetning bruker fire like kort i 2x2-grid",
        "description": (
            "Build 1332 rydder omsetningsdashboardet tilbake til fire like oversiktskort. Alle periodene bruker "
            "samme struktur: total omsetning øverst, sammenligning mot relevante referanser, kort forklaring av "
            "største avvik, fordeling mellom soling og parkering, og en diskret kontroll mot hele referanseperioden."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): fjerner spesialkortet for dagsomsetning og samler dag, uke, måned og år i samme kortkomponent.",
            "Desktop v2 CSS (status-periods.css): erstatter tabell-/dagskort-CSS med kompakte felles kortregler for 2x2-grid.",
            "Buildlogg (build_log.py): registrerer build 1332.",
        ],
        "request": (
            "Jeg synes ikke dette ble bra, alle kortene skal jo være like også. jeg tneker at en grid med 2 i "
            "bredden og 2 i høyden er noe vi skal etterstrebe. KAn du gjøre en veldig nøye vurdering av disse "
            "dataene og hva som er viktig i et slikt oversiktskort. det er som før sagt omsetning som er det aller "
            "viktigste og det må være lett å få oversikt. Gjør det nøye ryddig og bra nå så får jeg se. RYDD OPP"
        ),
        "work_duration": "ca. 40 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Alle fire omsetningsperioder bruker nå samme kortlayout.",
            "Kortene prioriterer total omsetning og avvik mot relevante referanser.",
            "Soling og parkering vises som forklarende linjer med beløp, antall, snitt og avvik.",
            "Hele referanseperioden er flyttet til en diskret fot i hvert kort.",
            "Gammel spesial-CSS og tabellvisning for dagskortet er fjernet.",
        ],
    },
    {
        "version": "1",
        "build": "1331",
        "date": "28.06.2026",
        "headline": "Dagsomsetning som KPI-kort",
        "title": "Dashboard > Omsetning fremhever omsetning hittil i dag med tydelige sammenligninger",
        "description": (
            "Build 1331 gjør dagskortet på omsetningsdashboardet mer KPI-drevet. Hovedtallet for omsetning hittil "
            "i dag løftes frem, sammenligning mot i går samme tidspunkt og samme ukedag forrige uke vises rett under, "
            "og omsetning per linje samles i en tydelig tabell. Hele referansedagen er flyttet ned som sekundær "
            "kontekst."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): legger til egen KPI-komponent for dagsomsetning uten å endre datakilder.",
            "Desktop v2 CSS (status-periods.css): legger til fullbredde dagskort, KPI-strip, innsiktslinje og responsiv tabell.",
            "Buildlogg (build_log.py): registrerer build 1331.",
        ],
        "request": (
            "Du jobber i eksisterende repo. Finn komponenten som rendrer kortet for “Omsetning hittil i dag” / "
            "dagsomsetning, og endre layouten slik at kortet blir lettere å forstå. Kortet skal vise dagens "
            "omsetning, sammenligning mot i går samme tidspunkt og samme ukedag forrige uke, største avvik, "
            "omsetning per linje og sekundær visning av hele referansedagen."
        ),
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Dagskortet bruker tittel 'Omsetning hittil i dag' og stor KPI-verdi.",
            "Sammenligning mot i går samme tidspunkt og samme ukedag forrige uke vises rett under hovedtallet.",
            "Automatisk innsiktslinje viser største bidragsyter til avviket mot i går.",
            "Hovedtabellen bruker kolonnene I dag hittil, I går samme tidspunkt og Samme ukedag forrige uke.",
            "Hele referansedagen er gjort sekundær med kompakte totalsummer og gjenstår/over-beregning.",
        ],
    },
    {
        "version": "1",
        "build": "1330",
        "date": "28.06.2026",
        "headline": "Dashboardtabeller samlet",
        "title": "Dashboard > Omsetning viser hittil-sammenligninger i samme tabell som nåtallene",
        "description": (
            "Build 1330 legger referansetallene for tilsvarende tidspunkt inn i samme tabell som dagens/periodens "
            "nåtall. Hele referanseperioder ligger i en egen kompakt tabell under, med beregning av hvor mye som "
            "mangler eller hvor mye perioden ligger over for soling, parkering og sum."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): erstatter sammenligningskort med felles hittil-tabell og egen fullperiode-tabell.",
            "Desktop v2 CSS (status-periods.css): justerer tabellbredder, beløpsceller og kompakt differansevisning.",
            "Buildlogg (build_log.py): registrerer build 1330.",
        ],
        "request": (
            "hva om vi putter tallet så langt i går og så langt smame dag forrige uke i samme tabell som i dag. "
            "også tar vi hele dag i går og hele samme dag forrige uke i en tabell under med utregning av hvor mye "
            "vi mangler på begge. både parkering og sol."
        ),
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Hittil-tall for referansene vises som egne kolonner i utregningstabellen.",
            "Full dag/uke/måned/år vises i en egen tabell under med mangler/over-beregning.",
            "Soling, parkering og sum får samme struktur i begge tabeller.",
            "Gamle mini-kort for sammenligning er fjernet fra dashboardet.",
        ],
    },
    {
        "version": "1",
        "build": "1329",
        "date": "28.06.2026",
        "headline": "Sammenligninger komprimert",
        "title": "Dashboard > Omsetning bruker brede mini-kort for sammenligningene",
        "description": (
            "Build 1329 reduserer høyden på omsetningskortene ved å gjøre sammenligningene om til kompakte "
            "mini-kort i bredderetningen. Referanser som i går og samme dag forrige uke vises nå mer likt "
            "hovedutregningen: tittel, sum, avvik og egne linjer for soling og parkering."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): erstatter tunge sammenligningstabeller med kompakte sammenligningskort.",
            "Desktop v2 CSS (status-periods.css): legger sammenligningene i et to-kolonne grid og rydder bort gamle referansetabellregler.",
            "Buildlogg (build_log.py): registrerer build 1329.",
        ],
        "request": (
            "fortsatt for mange linjer, kan ikke sammenligningene i går og samme dag forrige uke settes opp mer "
            "på samme måte som I dag.. vær kreativ. vi har jo bredde men vi kan ikke bruke så mye høyde"
        ),
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Sammenligninger vises som mini-kort ved siden av hverandre når det er plass.",
            "Hvert mini-kort viser referansesum og avvik mot valgt periode i toppen.",
            "Soling og parkering vises som to kompakte linjer med antall, snitt, beløp og avvik.",
            "Fullperiodetall beholdes som en liten sekundærlinje nederst i mini-kortet.",
        ],
    },
    {
        "version": "1",
        "build": "1328",
        "date": "28.06.2026",
        "headline": "Omsetningskort forenklet",
        "title": "Dashboard > Omsetning samler datagrunnlag over kortene og flytter antall inn i ledetekstene",
        "description": (
            "Build 1328 forenkler periodekortene på omsetningsdashboardet etter visuell gjennomgang. "
            "Oppdateringstidspunkt for soling og parkering vises nå i ett felles datagrunnlagfelt over de fire "
            "kortene. Egen nøkkeltallblokk og antallkolonne er fjernet; antall og snitt står i stedet som "
            "sekundær tekst i ledeteksten for soling og parkering."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): flytter datagrunnlag til ett felles felt og forenkler utregningstabellen.",
            "Desktop v2 CSS (status-periods.css): rydder bort ubrukt nøkkeltall-/datagrunnlagstabell og legger til kompakt datagrunnlagstripe.",
            "Buildlogg (build_log.py): registrerer build 1328.",
        ],
        "request": (
            "Dette ble jo mye rot, nøkkeltall må vi finne en smartere måte å vise. å ha egne linjer for når det er "
            "oppdatert synes jeg også blir overkill. la det stå i parantes bak \"I dag\" osv. I å med at antall kun er "
            "en opplysning og ikke noe som ksal regnes noe med så kan vi ant skrive det i ledeteksten eks: Soling "
            "(1177 stk, 189 kr snitt). trenger ikke å ha det i en egen kollonne liksom. eller at tidspunkt for "
            "oppdatert parkering og soling står i et eget felt felles for alt over de 4 boksene"
        ),
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Felles datagrunnlagfelt over de fire omsetningskortene viser soling og parkering sitt oppdateringstidspunkt.",
            "Fjernet egen datagrunnlagstabell fra hvert kort.",
            "Fjernet egen nøkkeltallblokk fra hvert kort.",
            "Fjernet antallkolonnen og viser antall/snitt i ledeteksten for soling og parkering.",
        ],
    },
    {
        "version": "1",
        "build": "1327",
        "date": "28.06.2026",
        "headline": "Omsetningskort ryddet i egne linjer",
        "title": "Dashboard > Omsetning viser datagrunnlag, utregning og sammenligning med tydelige linjer",
        "description": (
            "Build 1327 rydder periodekortene på omsetningsdashboardet videre. Kortene har egne blokker for "
            "datagrunnlag, utregning, nøkkeltall og sammenligning, og soling/parkering vises som egne linjer "
            "i stedet for sammenslåtte tekstlinjer. Sammenligninger er lagt i egne referanseblokker slik at "
            "tidspunkt for soling, parkering og hele perioden ikke klemmes inn i en smal tabellkolonne."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): deler datatidspunkt, nøkkeltall og sammenligninger i egne soling-/parkeringlinjer.",
            "Desktop v2 CSS (status-periods.css): bygger ny tabell-layout for utregning, nøkkeltall og referanseblokker.",
            "Buildlogg (build_log.py): registrerer build 1327.",
        ],
        "request": "du kan gjøre det enda mer ryddig. hva om vi på hvert sted bruker egne linjer for soling og parkering ikke sånn samlet med / i mellom. tydelige ledetekster er dag viktig. og logisk oppsett med utregning. vurder og lag en god løsning",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Datagrunnlag viser soling og parkering på hver sin rad.",
            "Utregning viser soling, parkering og sum i logisk rekkefølge.",
            "Nøkkeltall viser snitt og andel på separate rader for soling og parkering.",
            "Sammenligninger er delt i egne blokker med referansetidspunkt og underrader for sum, soling og parkering.",
        ],
    },
    {
        "version": "1",
        "build": "1326",
        "date": "28.06.2026",
        "headline": "Dashboardbanner fjernet",
        "title": "Dashboard starter direkte på innholdet",
        "description": (
            "Build 1326 fjerner det store toppfeltet med teksten Dashboard og aktivt område fra "
            "dashboardflatene. Sidene starter nå direkte på innholdsseksjonen, slik at skjermplassen "
            "brukes på tall og tabeller."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): fjerner DashboardHeader fra dashboardflatene.",
            "Desktop v2 CSS (status-overview.css): fjerner ubrukt banner-CSS for dashboard-view-head.",
            "Buildlogg (build_log.py): registrerer build 1326.",
        ],
        "request": "det store feltet \"DASHBOARD Omseting\" helt øverst er helt unødvendig. fjern det!",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Fjernet toppbanneret fra Dashboard > Omsetning og de andre dashboardflatene.",
            "Beholdt eksisterende innholdsseksjoner, periodekort og topplinje-navigasjon uendret.",
            "Ryddet bort tilhørende CSS slik at det ikke ligger ubrukt bannerkode igjen.",
        ],
    },
    {
        "version": "1",
        "build": "1325",
        "date": "28.06.2026",
        "headline": "Omsetningsdashboard med fire periodebokser",
        "title": "Dashboard > Omsetning viser dag, uke, m\u00e5ned og \u00e5r som store tabellkort",
        "description": (
            "Build 1325 fjerner Fordeling-flisene fra omsetningsdashboardet og erstatter de tre gamle "
            "periodekortene med fire store bokser i to kolonner. Hver boks viser sum, soling, parkering "
            "og sammenligninger i tabeller med h\u00f8yrejusterte tall."
        ),
        "applications": [
            "Fibaro10 backend (main.py): /api/overview sender n\u00e5 ogs\u00e5 \u00e5rsperiode med i fjor og to \u00e5r siden som referanser.",
            "Desktop v2 (OverviewPage.tsx): omsetningsdashboardet bruker fire periodekort og fjerner Fordeling-seksjonen.",
            "Desktop v2 CSS (status-periods.css/status-refinements.css/status-overview.css): periodekortene er lagt om til tabellbasert 2x2-layout.",
            "Tester (test_api_contracts.py): dekker at \u00e5rstotalene i /api/overview faktisk er definert.",
            "Buildlogg (build_log.py): registrerer build 1325.",
        ],
        "request": "hva om vi dropper alle de flisene under fordeling ogs\u00e5, lager 4 store bokser to i bredden p\u00e5 en vanlig skjermbredde. i dag, denne uke, denne mnd, dette \u00e5r. med tilsvarende sammenligninger for alt. husk \u00e5 sette ting inn i tabeller slik at det blir riktig justert sm\u00e5 og store tall osv.",
        "work_duration": "ca. 40 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "La til \u00e5r som fjerde periode i omsetningsdashboardet.",
            "Fjernet Fordeling-seksjonen under omsetningsperiodene.",
            "Byttet periodeinnhold fra fliser til tabeller med justerte tallkolonner.",
            "Beholder snitt og prosentvis fordeling inne i hvert periodekort.",
            "Definerer \u00e5rstotalene eksplisitt i backend slik at dashboardet fungerer mot ekte live-data.",
            "\u00c5rskortets sammenligningslenker peker til \u00e5rssammenligningen for \u00e5 unng\u00e5 tung hendelsestidslinje for hele \u00e5r.",
        ],
    },
    {
        "version": "1",
        "build": "1324",
        "date": "28.06.2026",
        "headline": "Dashboard visuelt ryddet",
        "title": "Dashboardet har faatt mer luft, tydeligere seksjoner og roligere fargebruk",
        "description": (
            "Build 1324 gjoer et samlet designgrep paa dashboardflatene. "
            "Toppfelt, seksjoner, periodekort, noekkeltall og snarveier har faatt mer luft, "
            "mykere flater og konsekvente domenefarger uten endringer i datagrunnlag eller logikk."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): dashboardets vertikale avstand er oekt noe.",
            "Desktop v2 CSS (status-overview.css): toppfelt, seksjonshoder og dashboardflater er modernisert.",
            "Desktop v2 CSS (status-refinements.css): periodekort og statusflater har faatt tydeligere rytme og markeringer.",
            "Desktop v2 CSS (status-widgets.css): noekkeltallskort har faatt mer luft og konsekvent tonefarge.",
            "Buildlogg (build_log.py): registrerer build 1324.",
        ],
        "request": "gjoer et designgrep paa dashboard, trenger litt mer luft, kanksje litt mer farger eller markeringer. kort sagt gjoer det ryddig, pent, oversiktelig og moderne",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Dashboard-headeren er gjort roligere med domenefarge, oppdatert-tidspunkt som pill og bedre typografisk hierarki.",
            "Dashboard-seksjoner har faatt mer luft, egen flate og tydelig seksjonsmarkering.",
            "Omsetningskortene har faatt bedre avstand, tydeligere toppmarkering og mer lesbar intern struktur.",
            "Noekkeltallskort og snarveier bruker samme domenefarger og mykere hover-effekt.",
        ],
    },
    {
        "version": "1",
        "build": "1323",
        "date": "28.06.2026",
        "headline": "Omsetningsdashboard ryddet",
        "title": "Omsetningsdashboardet viser bare perioder og fordeling",
        "description": (
            "Build 1323 fjerner de nederste blokkene for siste soling/parkering og snarveier fra Dashboard > Omsetning. "
            "Siden blir dermed mer fokusert pa omsetningstallene og sammenligningene."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): omsetningsdashboardet stopper etter fordeling.",
            "Buildlogg (build_log.py): registrerer build 1323.",
        ],
        "request": "du klarer a gjore den enda bedre, de to nederste blokkene \"siste soing og parkering\" og \"Snarveier\" trenger vi ikke her",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Fjernet blokken Siste soling og parkering fra omsetningsdashboardet.",
            "Fjernet blokken Snarveier fra omsetningsdashboardet.",
            "Parkering, soling og drift beholder sine egne arbeidsflateblokker.",
        ],
    },
    {
        "version": "1",
        "build": "1322",
        "date": "28.06.2026",
        "headline": "Omsetningsdashboard forenklet",
        "title": "Sammenligningskortene er gjort enklere og mer lesbare",
        "description": (
            "Build 1322 forenkler Dashboard > Omsetning etter at fullreferansene ble lagt inn. "
            "Sammenligningene vises na som rene linjer med referanse, samme tidspunkt, full periode og mangler/over, "
            "mens ekstra malepunkter er samlet i korte tekstlinjer."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): sammenligningsradene er skrevet om til enklere linjevisning.",
            "Desktop v2 CSS (status-periods.css/status-refinements.css): gamle bokser er fjernet og erstattet med kompakt tabellpreg.",
            "Buildlogg (build_log.py): registrerer build 1322.",
        ],
        "request": "kan du gjore det enklere a forsta, enda enklere utforming og mer oversiktelig - fol deg fri",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Referansene heter kortere, for eksempel I gar og Forrige uke.",
            "Samme tidspunkt og full referanse vises som to enkle linjer.",
            "Mangler/over vises direkte pa full referanselinje.",
            "Snitt og fordeling er samlet i to kompakte tekstlinjer.",
            "Ubrukt CSS fra forrige kortdesign er fjernet.",
        ],
    },
    {
        "version": "1",
        "build": "1321",
        "date": "28.06.2026",
        "headline": "Omsetningsdashboard fullreferanser",
        "title": "Dashboard viser samme tidspunkt, full referanse og mangler til referansetotal",
        "description": (
            "Build 1321 gjor Dashboard > Omsetning tydeligere i periodekortene. "
            "Sammenligningene viser na bade totalen ved samme datatidspunkt og full total for referanseperioden, "
            "slik at det kommer klart frem hvor mye dagens, ukens eller manedens omsetning mangler for a matche referansen."
        ),
        "applications": [
            "Fibaro10 backend (main.py): /api/overview sender full referansetotal for hver sammenligning.",
            "Desktop v2 (OverviewPage.tsx): periodekortene viser samme tidspunkt, full referanse og mangler/over.",
            "Desktop v2 CSS (status-periods.css/status-refinements.css): ny kompakt layout for sammenligningsrader.",
            "Desktop v2 API-typer (api.ts): statusPeriod-typene er utvidet med fullreferanser.",
            "Buildlogg (build_log.py): registrerer build 1321.",
        ],
        "request": "jeg savner a se totalen for i gar, samme dag, forrige uke osv.. gjerne med hvor mye man mangler og tydelig tidspunkt for sammenligningstidspunktet. kan du oppgradere dashboard og gjore det enda mer oversiktelig",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "I dag viser na samme tidspunkt i gar og hele i gar.",
            "I dag viser ogsa samme dag forrige uke med full dag som referanse.",
            "Uke og maned viser full referanseperiode for forrige periode og ekstra sammenligning.",
            "Kortene markerer tydelig om man mangler til full referansetotal eller ligger over.",
            "Sammenligningstidspunkt for soling og parkering vises eksplisitt i hver rad.",
        ],
    },
    {
        "version": "1",
        "build": "1320",
        "date": "28.06.2026",
        "headline": "Omsetningsdashboard målepunkter",
        "title": "Omsetningskortene viser snitt, fordeling og volumendring",
        "description": (
            "Build 1320 gjør de tre periodekortene på Dashboard > Omsetning mer analytiske. "
            "Kortene viser fortsatt total, soling, parkering og sammenligninger, men har nå også "
            "snitt per soling, snitt per parkering, inntektsfordeling og volumendring mot hovedsammenligningen."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): periodekortene beregner snitt, fordeling og volumendring fra eksisterende statusPeriods-data.",
            "Desktop v2 CSS (status-periods.css/status-refinements.css): kompakt visning for nye målepunkter i periodekortene.",
            "Buildlogg (build_log.py): registrerer build 1320.",
        ],
        "request": "nå kan vi gjøre de 3 øverste på dashboard/omsetning litt mer utfyllende. ønsker at du skal finne nyttige parametre å måle mot",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "I dag, Uke og Måned viser snittomsetning per soling.",
            "I dag, Uke og Måned viser snittomsetning per parkering.",
            "Kortene viser inntektsfordeling mellom soling og parkering.",
            "Kortene viser volumendring for soling og parkering mot hovedsammenligningen.",
        ],
    },
    {
        "version": "1",
        "build": "1319",
        "date": "28.06.2026",
        "headline": "Fire dashboardflater",
        "title": "Dashboard er delt i omsetning, parkering, soling og drift",
        "description": (
            "Build 1319 deler Fibaro10 sitt Dashboard i fire tydelige arbeidsflater. "
            "Omsetning viser periodene med datatidspunkt og sammenligninger, Parkering og Soling viser "
            "egne nøkkeltall og snarveier, mens Drift samler åpning, datakilder, lys, ventilasjon, energi, temperatur og vær."
        ),
        "applications": [
            "Desktop v2 (OverviewPage.tsx): ny Dashboard-rendering med fire visninger.",
            "Desktop v2 (moduleViews.ts/AppRoutes.tsx): Dashboard-menyen har Omsetning, Parkering, Soling og Drift.",
            "Desktop v2 (status-overview.css): styling for dashboard-header og snarveikort.",
            "Desktop v2 smoke (smoke-routes.mjs/smoke-ui.mjs): tester de fire nye Dashboard-rutene.",
            "Fibaro10 backend (main.py): root og driftkort peker til nye Dashboard-ruter.",
            "Dokumentasjon (docs/desktop-v2.md): startside og Dashboard-ruter er oppdatert.",
            "Buildlogg (build_log.py): registrerer build 1319.",
        ],
        "request": "under dashboard så tenker jeg vi kan dele i 4 dashboard. omsetning, parkering, soling og drift",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Dashboard har fire sidestilte toppvalg i stedet for én samlet oversikt.",
            "Omsetningsdashboardet beholder sammenligningskortene for dag, uke og måned.",
            "Parkering og Soling har egne nøkkeltall, siste hendelse og relevante snarveier.",
            "Driftdashboardet samler datakilder, lys, ventilasjon og teknisk status.",
        ],
    },
    {
        "version": "1",
        "build": "1318",
        "date": "28.06.2026",
        "headline": "Mobil parkering ryddet",
        "title": "Mobil parkering viser dagens biler med kjoretoyinfo",
        "description": (
            "Build 1318 rydder mobilundersiden for parkering. Listen over siste importforsok er tatt bort, "
            "mens siste importtidspunkt og eventuell feil fortsatt vises kompakt over innholdet. "
            "Dagens parkeringer listes med regnr og samme kjoretoyfelt som hovedappen bruker."
        ),
        "applications": [
            "Online dashboard (online_dashboard/app/main.py): /parkering henter dagens parkeringer med kjoretoydata fra kjoretoy og kjoretoy_nokkeldata.",
            "Online dashboard (online_dashboard/app/main.py): importhistorikk-listen er fjernet fra mobilvisningen.",
            "Online dashboard CSS (static/online-dashboard.css): ny kompakt listevisning for dagens biler.",
            "Buildlogg (build_log.py): registrerer build 1318.",
        ],
        "request": "i mobil appen så har vi mulighet til å velge parkeringer, på undersiden der så er det nå brukt masse plass på å liste opp siste importer. dette trenger vi ikke, holder med sist import øverst slik som nå og evt feilet om den feiler. så vil jeg liste ut bilene som har parkert inkl merke/type/årsmodell alstså det feltet vi kaller \"Kjøretøy\" under parkering\\kjøretøy i hoved appen",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Mobil parkering bruker ikke lenger plass paa flere tidligere importforsok.",
            "Siste importstatus beholdes i toppstatusen, med egen melding hvis siste forsok feilet.",
            "Dagens parkeringer viser regnr, status, kjoretoy, varighet og belop for brukere med tilgang.",
        ],
    },
    {
        "version": "1",
        "build": "1317",
        "date": "28.06.2026",
        "headline": "OwnTracks waypoints",
        "title": "OwnTracks-waypoints lagres i egne tabeller for rask oversikt",
        "description": (
            "Build 1317 beholder full historikk av alle OwnTracks-lokasjoner i owntracks_locations, "
            "men materialiserer waypoints/soner i egne tabeller. Siste kjente sonestatus lagres i "
            "owntracks_waypoints, og inn/ut-hendelser, waypoint-definisjoner og syntetiske endringer "
            "lagres i owntracks_waypoint_events."
        ),
        "applications": [
            "Fibaro10 backend (main.py): nye OwnTracksWaypointState og OwnTracksWaypointEvent-tabeller.",
            "OwnTracks-lagring (main.py): location-meldinger med inregions oppdaterer sonestatus.",
            "OwnTracks-lagring (main.py): transition- og waypoint-meldinger lagres som egne hendelser.",
            "Fibaro10 admin/API (main.py): /admin/owntracks viser waypoints og hendelser, /api/owntracks/waypoints er lagt til.",
            "Drift/observability (observability.py): nye tabeller er med i storage-listen.",
            "Dokumentasjon (docs/owntracks-mqtt.md): beskriver waypoint-lagring og endepunkt.",
            "Buildlogg (build_log.py): registrerer build 1317.",
        ],
        "request": "jeg vil gjerne lagre alle lokasjonsdata for senere bruk, men akkurat Waypoint vil jeg gjerne ha litt lettere tilgjengelig så en egen tabell er sikkert fint",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Alle OwnTracks-lokasjoner lagres fortsatt komplett i historikktabellen.",
            "Waypoints/soner kan leses direkte fra egne tabeller uten aa parse raadata.",
            "Fibaro10 lager syntetiske enter/leave-hendelser naar inregions endrer seg.",
            "Eksisterende OwnTracks-historikk backfilles forsiktig hvis waypoint-tabellene er tomme.",
        ],
    },
    {
        "version": "1",
        "build": "1316",
        "date": "28.06.2026",
        "headline": "OwnTracks med Fibaro10-brukere",
        "title": "OwnTracks kan bruke vanlige Fibaro10-brukere via HTTP-endepunkt",
        "description": (
            "Build 1316 legger til en anbefalt OwnTracks-inngang paa "
            "https://online.lilletorget.net/owntracks/pub. Endepunktet bruker Fibaro10 sin eksisterende "
            "autentisering med HTTP Basic, slik at vanlige Fibaro10-brukere og passord kan brukes direkte "
            "i OwnTracks. MQTT-brokeren beholdes for intern bruk og MQTT-klienter."
        ),
        "applications": [
            "Fibaro10 backend (main.py): Basic auth-stotte i innloggingslaget og nytt /owntracks/pub-endepunkt.",
            "OwnTracks-lagring (main.py): HTTP-publisering lagres i samme owntracks_devices/owntracks_locations-tabeller.",
            "Caddy (Caddyfile): ruter /owntracks/* paa online.lilletorget.net til Fibaro10.",
            "Dokumentasjon (docs/owntracks-mqtt.md): anbefaler HTTP-modus med Fibaro10-bruker.",
            "Buildlogg (build_log.py): registrerer build 1316.",
        ],
        "request": "kan du ikke gjøre slik at brukerne i fibaro10 kan benyttes",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "OwnTracks kan settes til HTTP-modus og bruke samme brukernavn/passord som Fibaro10.",
            "Endepunktet returnerer OwnTracks-kompatibel tom JSON-liste etter mottak.",
            "Meldinger fra HTTP og MQTT havner i samme OwnTracks-oversikt i Admin.",
            "Eksisterende MQTT-oppsett beholdes som alternativ.",
        ],
    },
    {
        "version": "1",
        "build": "1315",
        "date": "28.06.2026",
        "headline": "OwnTracks via lilletorget.net",
        "title": "OwnTracks MQTT kan brukes uten VPN via eksisterende online-domene",
        "description": (
            "Build 1315 eksponerer OwnTracks-brokeren via MQTT over WebSocket paa "
            "https://online.lilletorget.net/mqtt. Caddy tar TLS paa eksisterende offentlig "
            "HTTPS-endepunkt og sender bare /mqtt videre til Mosquitto sin interne WebSocket-listener. "
            "Fibaro10 fortsetter samtidig aa abonnere internt paa vanlig MQTT-port."
        ),
        "applications": [
            "Mosquitto (mqtt/mosquitto.conf): legger til intern WebSocket-listener paa port 9001.",
            "Mosquitto entrypoint (mqtt/entrypoint.sh): gir intern Fibaro10-bruker lesetilgang til $SYS for healthcheck.",
            "Caddy (Caddyfile): ruter /mqtt paa online.lilletorget.net til owntracks_mqtt.",
            "Docker/QNAP (docker-compose.qnap.yml): proxyen avhenger ogsaa av owntracks_mqtt.",
            "Deploy (scripts/deploy-qnap.ps1): restart/reload av broker og Caddy naar konfig endres.",
            "Dokumentasjon (docs/owntracks-mqtt.md): beskriver ekstern OwnTracks-konfig uten VPN.",
            "Buildlogg (build_log.py): registrerer build 1315.",
        ],
        "request": "jeg oensker at den skal eksponeres gjennom lilletorget.net serveren som allerede er tilgjengelig uten aa gaa via vpn",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Offentlig OwnTracks-tilgang gaar over eksisterende HTTPS-port 443.",
            "Ingen vanlig MQTT-port eksponeres direkte mot internett.",
            "Eksisterende MQTT-brukere og ACL brukes videre.",
            "Deploy aktiverer Caddy/Mosquitto-konfig uten manuell restart.",
            "Intern Fibaro10-integrasjon er uendret og bruker broker-navnet owntracks_mqtt.",
        ],
    },
    {
        "version": "1",
        "build": "1314",
        "date": "28.06.2026",
        "headline": "OwnTracks MQTT for Fibaro10",
        "title": "Fibaro10 har faatt intern MQTT-broker og OwnTracks-mottak",
        "description": (
            "Build 1314 setter opp Eclipse Mosquitto som egen QNAP-container for OwnTracks, med anonym tilgang "
            "deaktivert, passordfil og ACL generert fra QNAP .env. Fibaro10 abonnerer paa owntracks/# via en intern "
            "MQTT-bruker, lagrer siste status per enhet og historikk over mottatte meldinger, og viser dette under "
            "Admin > OwnTracks. Datakilden OwnTracks MQTT er ogsaa lagt inn i eksisterende importstatus."
        ),
        "applications": [
            "Docker/QNAP (docker-compose.qnap.yml): ny owntracks_mqtt Mosquitto-service paa intern port 1883.",
            "Deploy (scripts/deploy-qnap.ps1): bevarer mqtt/data og starter owntracks_mqtt ved deploy.",
            "Fibaro10 backend (main.py): OwnTracks-tabeller, MQTT-konsument, datakilde og JSON-endepunkt.",
            "Fibaro10 desktop V2: nytt Admin > OwnTracks menyvalg, smoke-route og tabell-labels.",
            "Konfigurasjon/dokumentasjon (.env.qnap.example, docs/owntracks-mqtt.md, mqtt/mosquitto.conf, mqtt/entrypoint.sh): oppskrift og broker-konfig.",
        ],
        "request": "sett opp en MQTT server for owntracks appen slik at jeg kan benytte dette i Fibaro10",
        "work_duration": "ca. 60 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny Mosquitto-broker bundet til 192.168.20.218:1883.",
            "Separate MQTT-brukere for OwnTracks-publisering og intern Fibaro10-abonnering.",
            "OwnTracks-meldinger lagres i owntracks_devices og owntracks_locations.",
            "Ny kontrollside /admin/owntracks og JSON-endepunkt /api/owntracks/devices.",
            "OwnTracks MQTT vises som egen datakilde i datakildelisten.",
        ],
    },
    {
        "version": "1",
        "build": "1313",
        "date": "28.06.2026",
        "headline": "Elvia-kontroll for energi",
        "title": "Energi har faatt en egen V2-side som sammenligner Elvia mot HC3 time for time",
        "description": (
            "Build 1313 legger til Energi > Elvia-kontroll i desktop V2. Siden materialiserer den gamle "
            "Energi status-logikken som en tydelig kontrollflate: HC3/Fibaro10 sitt realtime-baserte "
            "inntaksforbruk summeres per time, forskyves en time bakover fordi deltaene er endestemplet, "
            "og sammenlignes mot importerte Elvia-timesverdier. Visningen gir sumkort, timegraf, "
            "akkumulert graf og tabell med avvik per time."
        ),
        "applications": [
            "Fibaro10 backend (main.py): ny helper og modulrespons for Energi > Elvia-kontroll.",
            "Fibaro10 desktop V2 (moduleViews.ts og v2_navigation.py): nytt menyvalg under Energi.",
            "Fibaro10 desktop V2 (moduleTableUtils.tsx og domainModel.ts): labels og kortnavigasjon for kontrollfeltene.",
            "Buildlogg (build_log.py): registrerer build 1313.",
        ],
        "request": "lag en ny side under energi paa v2 hvor du matrialiserer disse tankene",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny side /energi/elvia-kontroll med dagsvelger.",
            "Sammenligner HC3 realtime-basert kWh mot Elvia per time og for hele valgt dag.",
            "Viser baade timegraf og akkumulert graf for aa se hvor avviket oppstaar.",
            "Tabellen viser HC3 kWh, Elvia kWh, avvik, prosentavvik, sampledekning og Elvia-status per time.",
        ],
    },
    {
        "version": "1",
        "build": "1312",
        "date": "28.06.2026",
        "headline": "V1 frakoblet datakilder",
        "title": "Fibaro10 V1 er gjort om til en isolert funksjonsreferanse uten live datakilder",
        "description": (
            "Build 1312 kobler V1-porten fra produksjonsdatabasen og eksterne datakilder. I stedet "
            "serveres en egen referanseapp paa port 8111 som viser V1-menyen, gamle ruter og hva slags "
            "funksjonalitet sidene hadde. Dette fjerner risikoen for at gammel V1-kode henger seg paa "
            "tunge lesesider, samtidig som den fortsatt kan brukes som sammenligningsgrunnlag."
        ),
        "applications": [
            "Fibaro10 V1-referanse (v1_reference): ny isolert app uten database eller eksterne kilder.",
            "QNAP V1-compose (docker-compose.v1-reference.yml): kjører fibaro10_v1 paa port 8111 som referanse.",
            "V1 deploy (deploy-qnap-v1-history.ps1): bygger og starter frakoblet referanseapp.",
            "Lokal kvalitetssjekk (check-local.ps1): inkluderer syntakskontroll av V1-referanseappen.",
            "Dokumentasjon (docs/utviklingsoppsett.md): beskriver nytt V1-oppsett.",
            "Buildlogg (build_log.py): registrerer build 1312.",
        ],
        "request": "du kan egentlig koble den ifra datakilder men jeg vil ha mulighet til aa se hva slags funksjonalitet den hadde",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Port 8111 viser historisk V1-funksjonalitet uten aa lese eller skrive produksjonsdata.",
            "V1 referansen viser meny, ruter, formaal, funksjoner og hvilke kilder sidene opprinnelig brukte.",
            "Gammel V1-container erstattes av en trygg referansecontainer med samme navn og port.",
        ],
    },
    {
        "version": "1",
        "build": "1311",
        "date": "28.06.2026",
        "headline": "Robust smoke-provisionering",
        "title": "Provision-scriptet sender Python-koden robust over SSH uten quoting-problemer",
        "description": (
            "Build 1311 gjoer provision-live-smoke-user.ps1 mer robust mot QNAP/SSH-quoting ved aa "
            "sende databaseoppdateringen som base64-kodet Python-payload. Dermed kan fibaro-smoke "
            "opprettes eller roteres uten at remote shell fjerner anfoerselstegn i Python-koden."
        ),
        "applications": [
            "Fibaro10 driftsscript (provision-live-smoke-user.ps1): base64-kodet Python-payload over SSH.",
            "Buildlogg (build_log.py): registrerer build 1311.",
        ],
        "request": "gjor det",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Provisionering av fibaro-smoke er robust mot remote shell-quoting.",
            "Ingen endring i produksjonsdata utover at scriptet kan opprette/rotere smoke-brukeren.",
        ],
    },
    {
        "version": "1",
        "build": "1310",
        "date": "28.06.2026",
        "headline": "Smoke-provisionering rettet",
        "title": "Provision-scriptet for innlogget live-smoke fungerer ogsaa i Windows PowerShell",
        "description": (
            "Build 1310 retter passordgenereringen i provision-live-smoke-user.ps1 slik at scriptet "
            "bruker RandomNumberGenerator.Create().GetBytes(...), som fungerer i Windows PowerShell "
            "paa denne maskinen. Dette gjoer at fibaro-smoke-brukeren kan opprettes eller roteres "
            "fra utviklingsmaskinen uten manuell databaseendring."
        ),
        "applications": [
            "Fibaro10 driftsscript (provision-live-smoke-user.ps1): kompatibel kryptografisk passordgenerering.",
            "Buildlogg (build_log.py): registrerer build 1310.",
        ],
        "request": "gjor det",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Innlogget live-smoke kan provisioneres fra Windows PowerShell.",
            "Ingen endring i produksjonsdata eller applikasjonslogikk.",
        ],
    },
    {
        "version": "1",
        "build": "1309",
        "date": "28.06.2026",
        "headline": "Innlogget live-smoke",
        "title": "Deploy har faatt innlogget live-smoke og Python-avhengigheter er laast",
        "description": (
            "Build 1309 gjoer videre kvalitetsoppsett for produksjon. Python runtime-avhengigheter "
            "er laast med eksakte top-level-versjoner, live-smoke kan lese en lokal .env.live-smoke, "
            "deploy kjorer live-smoke etter vanlig health/smoke, og det finnes et eget script for aa "
            "opprette eller rotere en dedikert fibaro-smoke-bruker paa QNAP."
        ),
        "applications": [
            "Fibaro10 kravfiler: top-level Python-avhengigheter er pinna med eksakte versjoner.",
            "Fibaro10 desktop V2 (smoke-live.mjs): leser .env.live-smoke og kan kjore innloggede ruter.",
            "Fibaro10 deploy (deploy-qnap.ps1): kjorer live-smoke etter vanlig smoke-check.",
            "Fibaro10 driftsscript (provision-live-smoke-user.ps1): lager/roterer fibaro-smoke-brukeren og lokal env-fil.",
            "Dokumentasjon (docs/utviklingsoppsett.md): beskriver innlogget live-smoke.",
            "Buildlogg (build_log.py): registrerer build 1309.",
        ],
        "request": "gjor det",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "QNAP-deploy kan naa verifisere innloggede desktop-ruter naar lokal smoke-env finnes.",
            "Smoke-brukeren er viewer og skal bare brukes til lesende rutesjekk.",
            "Python-pakker endrer seg ikke lenger uventet fra deploy til deploy.",
        ],
    },
    {
        "version": "1",
        "build": "1308",
        "date": "28.06.2026",
        "headline": "Elvia-tekster rettet",
        "title": "Energi/Elvia har faatt ryddet siste synlige mojibake-tekster i backend",
        "description": (
            "Build 1308 retter fire feilkodede norske tekster i backend for Elvia-visningen: "
            "tom importstatus, aarsoppsummering, topp maaneder og valideringsmelding ved opplasting."
        ),
        "applications": [
            "Fibaro10 backend (main.py): rettet synlige Elvia-tekster med feil tegnsett.",
            "Buildlogg (build_log.py): registrerer build 1308.",
        ],
        "request": "fortsett aa forbedre",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Energi/Elvia viser riktige norske tegn for aar, maaned, for og ennaa.",
            "Ingen endring i beregninger, database eller API-struktur.",
        ],
    },
    {
        "version": "1",
        "build": "1307",
        "date": "28.06.2026",
        "headline": "Mer robust Docker-build",
        "title": "Docker-builden har faatt npm-retry for aa ta bedre hoyde for nettbrudd paa QNAP",
        "description": (
            "Build 1307 gjoer deployen mer robust etter at QNAP-builden feilet i npm ci med ECONNRESET. "
            "Frontend-builderen setter naa eksplisitte npm fetch-retries og lengre retry-timeouts for aa "
            "redusere risikoen for at korte nettbrudd stopper deploy."
        ),
        "applications": [
            "Fibaro10 Dockerfile: npm ci kjorer med fetch-retries og lengre retry-timeouts.",
            "Buildlogg (build_log.py): registrerer build 1307.",
        ],
        "request": "fortsett aa forbedre",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "QNAP-deploy er mindre saarbar for midlertidige npm-nettverksbrudd.",
            "Ingen funksjonell endring i app eller API.",
        ],
    },
    {
        "version": "1",
        "build": "1306",
        "date": "28.06.2026",
        "headline": "Ruteaudit og tekstfiks",
        "title": "Desktop V2 har faatt automatisk kontroll av meny-/smoke-dekning og ryddet synlige tekstfeil",
        "description": (
            "Build 1306 legger inn en egen ruteaudit som sammenligner menystrukturen i MODULE_VIEWS "
            "med rutene som dekkes av Playwright smoke-testen. Standard lokal sjekk stopper naa hvis "
            "et nytt menyvalg ikke er med i smoke-dekningen. Samtidig er synlige feil med norske tegn "
            "i tabellsok og tom-tabelltekst rettet."
        ),
        "applications": [
            "Fibaro10 desktop V2 (audit-routes.mjs): ny automatisk kontroll av menyvalg mot smoke-ruter.",
            "Fibaro10 desktop V2 (package.json): ny npm-kommando audit:routes.",
            "Fibaro10 sjekk (check-local.ps1): route audit kjorer som fast del av lokal kvalitetssjekk.",
            "Fibaro10 desktop V2 (ModuleTablePane.tsx): rettet synlige norske tegn i tabellsok og tom-tabelltekst.",
            "Buildlogg (build_log.py): registrerer build 1306.",
        ],
        "request": "fortsett aa forbedre",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Nye eller endrede menyvalg maa naa ogsaa dekkes av smoke-ruter.",
            "Menystrukturen kontrolleres automatisk mot smoke-testens ruteliste.",
            "Tabellsok og tom-tabelltekst viser riktige norske tegn.",
        ],
    },
    {
        "version": "1",
        "build": "1305",
        "date": "28.06.2026",
        "headline": "Bred smoke-test og driftstatus",
        "title": "Fibaro10 har faatt bredere rutesjekk, bedre health-details og mer operasjonell Drift-side",
        "description": (
            "Build 1305 gjoer kvalitetskontrollen mer systematisk. Smoke-testen har en felles ruteliste "
            "som dekker hovedsidene og undersidene i desktop-appen, lokal smoke har mockdata for spesialsider, "
            "og live-smoke bruker samme rutegrunnlag naar innloggingsmiljoe er satt. Drift-siden leser naa "
            "health-details og viser datakilder/jobber med status, kilde, sist OK, neste forventet og melding."
        ),
        "applications": [
            "Fibaro10 backend (health): health-details bruker samme importstatuslogikk som dashboard/datkilder.",
            "Fibaro10 backend (observability.py/api_types.py): health har summary for datakilder.",
            "Fibaro10 desktop V2 (smoke-routes.mjs): felles rutegrunnlag for lokal og live smoke.",
            "Fibaro10 desktop V2 (smoke-ui.mjs): lokal Playwright-smoke dekker alle sentrale desktop-ruter.",
            "Fibaro10 desktop V2 (smoke-live.mjs): live-smoke bruker samme rutegrunnlag og kan overstyres med env.",
            "Fibaro10 desktop V2 (OperationsPage.tsx): Drift viser operasjonell jobb-/datakildetabell.",
            "Fibaro10 backup (qnap-backup.sh/verify-qnap-backup.ps1): restore-test kan hoppe over Axis snapshot-arkiv.",
            "Dokumentasjon (docs/utviklingsoppsett.md): backup/restore-test er oppdatert.",
        ],
        "request": "kjor paa med alt du foreslo her",
        "work_duration": "ca. 1 t 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Lokal UI-smoke sjekker 55 ruter og feiler paa manglende API-mock eller HTTP 4xx/5xx.",
            "Health har summering av OK/treg/feil/ukjent datakilder.",
            "Admin > Drift gir bedre oversikt over importjobber og datakilder.",
            "Backup-verifikasjon kan testes raskt uten aa pakke hele bildearkivet.",
        ],
    },
    {
        "version": "1",
        "build": "1304",
        "date": "28.06.2026",
        "headline": "Bundle-audit lagt til",
        "title": "Desktop V2 har faatt automatisk kontroll av frontend-bundle-storrelse",
        "description": (
            "Build 1304 legger til en bundle-audit etter frontend-build. Den rapporterer storste "
            "JS/CSS-assets, total gzip-storrelse og stopper sjekken dersom bundles vokser over "
            "definerte grenser. Dette gir fast ytelseskontroll for de tunge sidene uten aa endre UI."
        ),
        "applications": [
            "Fibaro10 desktop V2 (audit-bundle.mjs): ny bundle-audit for dist/assets.",
            "Fibaro10 desktop V2 (package.json): ny npm-kommando audit:bundle.",
            "Fibaro10 sjekk (check-local.ps1): kjorer bundle-audit som del av standard lokal sjekk.",
            "Buildlogg (build_log.py): registrerer build 1304.",
        ],
        "request": "kjor paa med alt dette",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Tunge chunks som antd-core og charts blir synlige i hver sjekk.",
            "Total gzip-budget hindrer at frontend vokser ubemerket.",
            "Grensene kan overstyres via FIBARO10_BUNDLE_* miljo variabler ved behov.",
        ],
    },
    {
        "version": "1",
        "build": "1303",
        "date": "28.06.2026",
        "headline": "Modul-CSS delt opp",
        "title": "Desktop V2 har splittet generisk modul-CSS i metrics, diagram og filter",
        "description": (
            "Build 1303 rydder videre i frontend-rammeverket. module-content.css er redusert "
            "ved aa flytte kort/metrics, chart-toolbar og filterlayout til egne CSS-filer. "
            "Noen hardkodede modul-farger er samtidig byttet til eksisterende design tokens."
        ),
        "applications": [
            "Fibaro10 desktop V2 (module-content.css): redusert til generisk modulinnhold og felles kort.",
            "Fibaro10 desktop V2 (module-metrics.css): ny CSS-fil for metrics og kompakte kort.",
            "Fibaro10 desktop V2 (module-charts.css): ny CSS-fil for diagramkort og diagramkontroller.",
            "Fibaro10 desktop V2 (module-filters.css): ny CSS-fil for filterkort og responsive filtergrid.",
            "Fibaro10 desktop V2 (main.tsx): importerer de nye modul-CSS-filene.",
            "Buildlogg (build_log.py): registrerer build 1303.",
        ],
        "request": "kjor paa med alt dette",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Storre generisk CSS er delt etter ansvar.",
            "Metrics og chart-kontroller bruker flere felles tokens for farge/linjer.",
            "Ingen React-komponenter eller API-kontrakter er endret.",
        ],
    },
    {
        "version": "1",
        "build": "1302",
        "date": "28.06.2026",
        "headline": "UniFi Protect skilt ut",
        "title": "Fibaro10 har flyttet UniFi Protect-lenker ut av main.py og isolert testen",
        "description": (
            "Build 1302 fortsetter backend-oppryddingen med lav risiko. Generering av UniFi "
            "Protect-timelapse-lenker for parkering ligger naa i egen modul. Den tilhorende testen "
            "importerer modulen direkte, slik at den ikke lenger trenger aa starte hele main.py."
        ),
        "applications": [
            "Fibaro10 backend (unifi_protect.py): ny modul for UniFi Protect-konfigurasjon og timelapse-URL.",
            "Fibaro10 backend (main.py): bruker UniFi Protect-modulen i parkeringsrad-API.",
            "Fibaro10 tester (test_unifi_protect_links.py): tester modulen direkte uten databaseoppsett.",
            "Buildlogg (build_log.py): registrerer build 1302.",
        ],
        "request": "kjor paa med alt dette",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "main.py har mindre hardkodet ekstern-lenkeoppsett.",
            "UniFi-lenketesten er raskere og mer isolert.",
            "Eksisterende API-felt for unifi_start_url og unifi_end_url er uendret.",
        ],
    },
    {
        "version": "1",
        "build": "1301",
        "date": "28.06.2026",
        "headline": "Ventilasjons-CSS delt opp",
        "title": "Desktop V2 har splittet ventilasjons-CSS i grunnlayout, diagram og innstillinger",
        "description": (
            "Build 1301 rydder videre i frontend-CSS. Den tidligere store ventilation.css er delt "
            "i egne filer for dagslogg/Yr-diagram og innstillingsflater. Importrekkefolgen er "
            "bevart slik at eksisterende uttrykk og komponentoppforsel ikke endres."
        ),
        "applications": [
            "Fibaro10 desktop V2 (ventilation.css): redusert til grunnlayout, statuskort og visuelle refinements.",
            "Fibaro10 desktop V2 (ventilation-charts.css): ny CSS-fil for dagslogg, viftebaner og hendelsesliste.",
            "Fibaro10 desktop V2 (ventilation-settings.css): ny CSS-fil for ventilasjonsinnstillinger.",
            "Fibaro10 desktop V2 (main.tsx): importerer de nye CSS-filene.",
            "Buildlogg (build_log.py): registrerer build 1301.",
        ],
        "request": "fortsett med det",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Stor ventilasjons-CSS er mindre og lettere aa vedlikeholde.",
            "Diagram- og innstillingsstil kan endres separat fremover.",
            "Ingen React-komponenter eller API-kontrakter er endret.",
        ],
    },
    {
        "version": "1",
        "build": "1300",
        "date": "28.06.2026",
        "headline": "Live smoke mot QNAP",
        "title": "Desktop V2 har faatt en separat live-smoke for QNAP-installasjonen",
        "description": (
            "Build 1300 legger til en manuell Playwright-basert live-smoke. Den sjekker alltid "
            "QNAP sin /health, og kan i tillegg gaa gjennom viktige innloggede sider naar "
            "FIBARO10_LIVE_USERNAME og FIBARO10_LIVE_PASSWORD er satt. Standard lokal sjekk og deploy "
            "er ikke gjort avhengig av innloggingsdata."
        ),
        "applications": [
            "Fibaro10 desktop V2 (smoke-live.mjs): ny live-smoke mot aktiv QNAP-installasjon.",
            "Fibaro10 desktop V2 (package.json): ny npm-kommando smoke:live.",
            "Buildlogg (build_log.py): registrerer build 1300.",
        ],
        "request": "fortsett med det",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "QNAP health kan sjekkes direkte fra frontend-toolchainen.",
            "Innlogget smoke kan aktiveres uten aa hardkode brukernavn eller passord.",
            "Automatisk deploy forblir stabil selv om live-miljoet mangler testcredentials.",
        ],
    },
    {
        "version": "1",
        "build": "1299",
        "date": "28.06.2026",
        "headline": "Kjoretoyhelpers skilt ut",
        "title": "Fibaro10 har flyttet nummerplate-, SVV- og utenlandsoppslag-hjelpere ut av main.py",
        "description": (
            "Build 1299 fortsetter backend-oppryddingen. Logikk for normalisering av registreringsnummer, "
            "svenske/danske skilt, SVV-data og visning av kjoretoyinfo er flyttet til en egen helpermodul. "
            "Ruter, databasekall og API-kontrakter er beholdt i main.py."
        ),
        "applications": [
            "Fibaro10 backend (main.py): redusert ved aa importere kjoretoyhelpers fra egen modul.",
            "Fibaro10 backend (parking_vehicle_helpers.py): ny modul for skilt, SVV-felter, car-info og parkeringsrad-context.",
            "Buildlogg (build_log.py): registrerer build 1299.",
        ],
        "request": "fortsett med det",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "main.py har mindre blanding av parkeringsruting og generell kjoretoylogikk.",
            "Nordiske kjoretoyoppslag og SVV-visningsfelter ligger samlet ett sted.",
            "Endringen er strukturell og skal ikke endre dataflyt eller brukergrensesnitt.",
        ],
    },
    {
        "version": "1",
        "build": "1298",
        "date": "28.06.2026",
        "headline": "Status-CSS delt opp",
        "title": "Desktop V2 har splittet den storste status-CSS-filen i mindre ansvarsomraader",
        "description": (
            "Build 1298 gjennomforer siste planlagte CSS-opprydding. status-widgets.css er delt "
            "slik at periodekort og status-refinements ligger i egne filer. Importrekkefolgen er "
            "bevart for aa unngaa visuelle regresjoner."
        ),
        "applications": [
            "Fibaro10 desktop V2 (status-widgets.css): redusert til grunnleggende status/widgets.",
            "Fibaro10 desktop V2 (status-periods.css): ny CSS-fil for periodekort og sammenligninger.",
            "Fibaro10 desktop V2 (status-refinements.css): ny CSS-fil for siste visuelle status-justeringer.",
            "Fibaro10 desktop V2 (main.tsx): importerer de nye CSS-filene i kontrollert rekkefolge.",
            "Buildlogg (build_log.py): registrerer build 1298.",
        ],
        "request": "Gjor alt dette trinn for trinn slik at det blir klart.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Den storste status-CSS-flaten er lettere aa vedlikeholde.",
            "CSS parse/audit og UI smoke validerer splitten i standard sjekk.",
            "Ingen komponentlogikk eller API er endret i dette bygget.",
        ],
    },
    {
        "version": "1",
        "build": "1297",
        "date": "28.06.2026",
        "headline": "UI smoke utvidet",
        "title": "Desktop V2 tester flere hovedsider automatisk ved lokal sjekk og deploy",
        "description": (
            "Build 1297 utvider Playwright smoke-testen. Den sjekker naa status, omsetning, "
            "parkering, soling, energi, ventilasjon, lys, renhold, admin og buildlogg med mocket "
            "API-data. Dette fanger flere brutte ruter og renderfeil for hver build."
        ),
        "applications": [
            "Fibaro10 desktop V2 (smoke-ui.mjs): utvidet mocket API og rutesjekk.",
            "Fibaro10 sjekk/deploy: eksisterende check-local og deploy kjører den utvidede smoke-testen.",
            "Buildlogg (build_log.py): registrerer build 1297.",
        ],
        "request": "Gjor alt dette trinn for trinn slik at det blir klart.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Flere hovedmenyvalg blir automatisk validert.",
            "Smoke-testen bruker fortsatt lokal dist og mocket API, saa den er rask og stabil.",
            "Meny/brand, buildlogg og generiske modulflater har bedre regresjonsdekning.",
        ],
    },
    {
        "version": "1",
        "build": "1296",
        "date": "28.06.2026",
        "headline": "Backendhjelpere skilt ut",
        "title": "Fibaro10 har flyttet energi- og PDF-hjelpere ut av main.py",
        "description": (
            "Build 1296 starter backend-oppryddingen med lav risiko. Rene form-, filter- og "
            "PDF-tabellhjelpere er flyttet til egne moduler, mens eksisterende energi-ruter og "
            "API-kontrakter ligger uendret."
        ),
        "applications": [
            "Fibaro10 backend (main.py): redusert ved aa flytte ut energi- og PDF-hjelpere.",
            "Fibaro10 backend (energy_helpers.py): ny modul for energi-formverdier, solsengfilter og URL-hjelper.",
            "Fibaro10 backend (pdf_exports.py): ny modul for generering av enkle tabell-PDF-er.",
            "Buildlogg (build_log.py): registrerer build 1296.",
        ],
        "request": "Gjor alt dette trinn for trinn slik at det blir klart.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "main.py har mindre blanding av ruting og generelle hjelpefunksjoner.",
            "Energiens kurs- og last-PDF-er bruker samme logikk via ny PDF-modul.",
            "Endringen er bevisst avgrenset til lavrisiko kode uten databaseeierskap.",
        ],
    },
    {
        "version": "1",
        "build": "1295",
        "date": "28.06.2026",
        "headline": "VentilationPage fullfort som container",
        "title": "Desktop V2 har flyttet filter, innstillinger og tabellomraade ut av VentilationPage",
        "description": (
            "Build 1295 fullforer splitten av VentilationPage. FilterBar, SettingsView og TableArea "
            "ligger naa i VentilationPanels.tsx. VentilationPage er redusert til en liten container "
            "som velger snapshot, dagslogg, Yr, innstillinger, hendelser og tabeller."
        ),
        "applications": [
            "Fibaro10 desktop V2 (VentilationPage.tsx): redusert til overordnet container.",
            "Fibaro10 desktop V2 (VentilationPanels.tsx): ny komponentfil for filter, settings og tabeller.",
            "Buildlogg (build_log.py): registrerer build 1295.",
        ],
        "request": "Gjor alt dette trinn for trinn slik at det blir klart.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "VentilationPage har tydelig ansvar og mindre risiko ved videre endringer.",
            "Innstillinger og tabellomraade kan videreutvikles separat.",
            "Ventilasjonssplitten er fullfort uten funksjonsendring.",
        ],
    },
    {
        "version": "1",
        "build": "1294",
        "date": "28.06.2026",
        "headline": "Ventilasjonsdiagram skilt ut",
        "title": "Desktop V2 har flyttet dagslogg- og Yr-diagrammene til egen charts-fil",
        "description": (
            "Build 1294 flytter DayChart og WeatherChart ut av VentilationPage og inn i "
            "VentilationCharts.tsx. ECharts-oppsett, dagvelger, fokusvalg og viftebaner er dermed "
            "samlet separat fra hovedsidens ruting og visningsvalg."
        ),
        "applications": [
            "Fibaro10 desktop V2 (VentilationPage.tsx): bruker DayChart og WeatherChart fra egen fil.",
            "Fibaro10 desktop V2 (VentilationCharts.tsx): ny komponentfil for ventilasjonsdiagrammer.",
            "Buildlogg (build_log.py): registrerer build 1294.",
        ],
        "request": "Gjor alt dette trinn for trinn slik at det blir klart.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Diagramoppsett og viftebaner er isolert fra VentilationPage.",
            "VentilationPage er redusert til overordnet ventilasjonsvisning.",
            "Dagslogg og Yr-logg bruker samme data og samme visuelle oppsett som for.",
        ],
    },
    {
        "version": "1",
        "build": "1293",
        "date": "28.06.2026",
        "headline": "Ventilasjon snapshot skilt ut",
        "title": "Desktop V2 har flyttet ventilasjonens status- og snapshotkort til egen komponentfil",
        "description": (
            "Build 1293 flytter Snapshot og CompactSnapshot ut av VentilationPage. Siste sample, "
            "temperatur-/fuktkort, vaerlinje og viftestatuspiller ligger naa i VentilationSnapshot.tsx."
        ),
        "applications": [
            "Fibaro10 desktop V2 (VentilationPage.tsx): bruker Snapshot og CompactSnapshot fra egen fil.",
            "Fibaro10 desktop V2 (VentilationSnapshot.tsx): ny komponentfil for statuskortene.",
            "Buildlogg (build_log.py): registrerer build 1293.",
        ],
        "request": "Gjor alt dette trinn for trinn slik at det blir klart.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ventilasjonsstatusen er isolert fra dagsloggdiagram og settings.",
            "Hovedsiden har mindre JSX og tydeligere ansvar.",
            "Ingen dataflyt eller visning er endret funksjonelt.",
        ],
    },
    {
        "version": "1",
        "build": "1292",
        "date": "28.06.2026",
        "headline": "Ventilasjonshjelpere skilt ut",
        "title": "Desktop V2 har flyttet formattering, viftelogikk og ventilasjonstabeller ut av VentilationPage",
        "description": (
            "Build 1292 starter splitten av VentilationPage. Formattere, tids-/minutthjelpere, "
            "viftestatussegmenter, tooltip-formattering og den generiske ventilasjonstabellen ligger "
            "naa i ventilationHelpers.tsx."
        ),
        "applications": [
            "Fibaro10 desktop V2 (VentilationPage.tsx): bruker ventilasjonshjelpere fra egen fil.",
            "Fibaro10 desktop V2 (ventilationHelpers.tsx): ny fil for formattering, viftelogikk og tabell.",
            "Buildlogg (build_log.py): registrerer build 1292.",
        ],
        "request": "Gjor alt dette trinn for trinn slik at det blir klart.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "VentilationPage er redusert og har mindre teknisk hjelpekode lokalt.",
            "Dagslogg og tabeller bruker samme eksisterende logikk via import.",
            "Dette legger grunnlag for videre komponentdeling av snapshot, diagram og settings.",
        ],
    },
    {
        "version": "1",
        "build": "1291",
        "date": "28.06.2026",
        "headline": "ModulePage gjort til modulcontainer",
        "title": "Desktop V2 har flyttet dagvelger og tabellpanelet ut av ModulePage",
        "description": (
            "Build 1291 fullforer ModulePage-splitten ved aa flytte dagvelgeren til "
            "ModuleDayNavigationBar.tsx og tabellvisningen til ModuleTablePane.tsx. ModulePage "
            "styrer naa primart ruting, lasting, filter, actions og valg av modulvisning."
        ),
        "applications": [
            "Fibaro10 desktop V2 (ModulePage.tsx): redusert til overordnet modulcontainer.",
            "Fibaro10 desktop V2 (ModuleDayNavigationBar.tsx): ny komponent for dagvelger.",
            "Fibaro10 desktop V2 (ModuleTablePane.tsx): ny komponent for generiske modultabeller.",
            "Buildlogg (build_log.py): registrerer build 1291.",
        ],
        "request": "Gjor alt dette trinn for trinn slik at det blir klart.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "ModulePage har tydeligere ansvar og mindre lokal UI-kode.",
            "Dagvelger og tabellpanelet kan videreutvikles separat.",
            "Dette avslutter ModulePage-delen av oppryddingen.",
        ],
    },
    {
        "version": "1",
        "build": "1290",
        "date": "27.06.2026",
        "headline": "Soltimepanel skilt ut",
        "title": "Desktop V2 har flyttet soltime- og bildearkivpanelet ut av ModulePage",
        "description": (
            "Build 1290 flytter soling/enkeltimer-komponenten, inline bildebytte og bildearkiv-modal "
            "til SunSessionsPanel.tsx. ModulePage beholder ruting, filter og overordnet modulvisning, "
            "mens solbildelogikken er isolert i en egen komponent."
        ),
        "applications": [
            "Fibaro10 desktop V2 (ModulePage.tsx): bruker SunSessionsPanel for soling/enkeltimer.",
            "Fibaro10 desktop V2 (SunSessionsPanel.tsx): ny komponent for soltimer og Axis-bildearkiv.",
            "Buildlogg (build_log.py): registrerer build 1290.",
        ],
        "request": "Gjor alt dette trinn for trinn slik at det blir klart.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Bildearkivlogikken er samlet i en egen komponent.",
            "ModulePage er redusert til en mer overordnet modulcontainer.",
            "Videre opprydding kan gjores med mindre risiko for soltimebildene.",
        ],
    },
    {
        "version": "1",
        "build": "1289",
        "date": "27.06.2026",
        "headline": "ModulePage-tabeller skilt ut",
        "title": "Desktop V2 har flyttet generiske modultabeller til en egen helperfil",
        "description": (
            "Build 1289 reduserer ModulePage ved aa flytte generiske tabellkolonner, sortering, "
            "sok, radnokler, visningsformatering og redigeringsfelt til moduleTableUtils.tsx. "
            "Dette endrer ikke funksjonalitet, men gjor modulsiden mindre og tryggere aa dele videre."
        ),
        "applications": [
            "Fibaro10 desktop V2 (ModulePage.tsx): bruker felles tabellhjelpere fra moduleTableUtils.",
            "Fibaro10 desktop V2 (moduleTableUtils.tsx): ny fil for tabell-, filter- og edit-hjelpere.",
            "Buildlogg (build_log.py): registrerer build 1289.",
        ],
        "request": "Gjor alt dette trinn for trinn slik at det blir klart.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "ModulePage er redusert med generisk tabellkode flyttet ut.",
            "Tabellvisning og redigeringsfelt har samme API som for.",
            "Refaktoren gir bedre grunnlag for videre splitting av solbilder og dagvelger.",
        ],
    },
    {
        "version": "1",
        "build": "1288",
        "date": "27.06.2026",
        "headline": "CSS-kvalitetsgate lagt til",
        "title": "Desktop V2 parser og auditerer CSS som del av lokal sjekk",
        "description": (
            "Build 1288 styrker kvalitetssjekken for frontend. Alle CSS-filer parses med PostCSS "
            "som en hard gate, og eksisterende CSS-audit kjores som rapport i check-local.ps1. "
            "Dette skal stoppe feil som kappede selectors eller ugyldige stilark for deploy."
        ),
        "applications": [
            "Fibaro10 desktop V2 (parse-css.mjs): ny parser alle CSS-filer enkeltvis.",
            "Fibaro10 desktop V2 (package.json): legger til npm-scriptet parse:css.",
            "Deploy/test (check-local.ps1): kjorer parse:css og audit:css i standard sjekk.",
            "Buildlogg (build_log.py): registrerer build 1288.",
        ],
        "request": "Gjor alt dette trinn for trinn slik at det blir klart.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "CSS-parse blir en hard kvalitetsgate for deploy.",
            "CSS-audit blir del av normal lokal rapportering.",
            "Videre CSS- og komponentrydding kan gjores med lavere risiko.",
        ],
    },
    {
        "version": "1",
        "build": "1287",
        "date": "27.06.2026",
        "headline": "Status-CSS cascade rettet",
        "title": "Desktop V2 har rettet splitten mellom status-overview.css og status-widgets.css",
        "description": (
            "Build 1287 retter status-CSS-splitten slik at ingen selector blir kappet mellom to filer. "
            "Oversiktssidens spesifikke kommando- og mediaregler ligger i status-overview.css, mens "
            "status-widgets.css starter med globale basisregler for dashboard-widgetene."
        ),
        "applications": [
            "Fibaro10 desktop V2 (status-overview.css): komplett oversiktsside-CSS uten kappede selectors.",
            "Fibaro10 desktop V2 (status-widgets.css): ren basisfil for status-widgeter.",
            "Buildlogg (build_log.py): registrerer build 1287.",
        ],
        "request": "Kjor videre trinn for trinn og gjor oppryddingen ferdig.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Kappede status-summary selectors er samlet tilbake i riktig fil.",
            "Importrekkefolgen kan brukes uten implicit CSS-sammensying.",
            "Videre CSS-splitt kan gjores fra en ryddig baseline.",
        ],
    },
    {
        "version": "1",
        "build": "1286",
        "date": "27.06.2026",
        "headline": "Status-widget-CSS skilt ut",
        "title": "Desktop V2 har flyttet statusdashboardets basisregler til status-widgets.css",
        "description": (
            "Build 1286 retter og rydder cascade for statusdashboardet. Basisregler for statussummary, "
            "kommando-striper, periodekort, stottekort, hendelser og datakilder er flyttet til "
            "status-widgets.css. status-overview.css ligger etterpaa og inneholder bare oversiktssidens "
            "egne layoutoverstyringer."
        ),
        "applications": [
            "Fibaro10 desktop V2 (status-widgets.css): ny fil for dashboardets status-widgeter.",
            "Fibaro10 desktop V2 (status-overview.css): redusert til oversiktssidens spesifikke layout.",
            "Fibaro10 desktop V2 (main.tsx): importerer status-widgets.css for status-overview.css.",
            "Buildlogg (build_log.py): registrerer build 1286.",
        ],
        "request": "Kjor videre trinn for trinn og gjor oppryddingen ferdig.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Cascade for statusdashboardet er gjort mer robust.",
            "status-overview.css er tilbake til kun side-spesifikk layout.",
            "Basisreglene kan vedlikeholdes separat fra oversiktssidens overstyringer.",
        ],
    },
    {
        "version": "1",
        "build": "1285",
        "date": "27.06.2026",
        "headline": "Oppgjorsdetalj-CSS skilt ut",
        "title": "Desktop V2 har flyttet originalskjema og leste verdier til settlement-detail.css",
        "description": (
            "Build 1285 rydder videre i oppgjorsstilene. PDF/originalvisning, leste verdier, "
            "sumkontroll, filfakta og detaljsidens rapporthode er flyttet fra records-settlements.css "
            "til settlement-detail.css. records-settlements.css beholder liste- og felles kontrollregler."
        ),
        "applications": [
            "Fibaro10 desktop V2 (settlement-detail.css): ny fil for oppgjorets detalj- og originalvisning.",
            "Fibaro10 desktop V2 (records-settlements.css): redusert til oppgjorslister og felles kontroller.",
            "Fibaro10 desktop V2 (main.tsx): importerer settlement-detail.css etter records-settlements.css.",
            "Buildlogg (build_log.py): registrerer build 1285.",
        ],
        "request": "Kjor videre trinn for trinn og gjor oppryddingen ferdig.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Detaljsidens PDF/originalskjema ligger i eget stilark.",
            "Oppgjorsliste-CSS er mer konsentrert om lister og kontrollfelter.",
            "Felles topptekstregler er splittet mellom liste- og detaljvisning.",
        ],
    },
    {
        "version": "1",
        "build": "1284",
        "date": "27.06.2026",
        "headline": "Soloppgjor-CSS skilt ut",
        "title": "Desktop V2 har flyttet soling-oppgjor til sun-settlements.css",
        "description": (
            "Build 1284 rydder i oppgjorsstilene. Rene soling-regler for oppgjorslisten, "
            "forenklet kreditnota/bilag, periodefelt, payout og soling-spesifikk tabellayout "
            "er flyttet ut av records-settlements.css og inn i sun-settlements.css. Felles "
            "oppgjorsdetaljer og kontrollkomponenter ligger fortsatt samlet."
        ),
        "applications": [
            "Fibaro10 desktop V2 (sun-settlements.css): ny fil for soling-oppgjor og forenklet bilag.",
            "Fibaro10 desktop V2 (records-settlements.css): beholder felles oppgjorsvisning og parkering-liste.",
            "Fibaro10 desktop V2 (main.tsx): importerer sun-settlements.css etter records-settlements.css.",
            "Buildlogg (build_log.py): registrerer build 1284.",
        ],
        "request": "Kjor videre trinn for trinn og gjor oppryddingen ferdig.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Soling-oppgjorets bilagslayout er isolert fra felles oppgjors-CSS.",
            "records-settlements.css er mindre og har tydeligere felles ansvar.",
            "Importrekkefolgen bevarer tidligere cascade for soling-oppgjor.",
        ],
    },
    {
        "version": "1",
        "build": "1283",
        "date": "27.06.2026",
        "headline": "Statusdashboard-CSS samlet",
        "title": "Desktop V2 har flyttet statusdashboard-regler til status-overview.css",
        "description": (
            "Build 1283 rydder videre i status-stilene. Dashboard-spesifikke regler for "
            "statussummary, lys/ventilasjon-striper, periodekort, stottekort, hendelser og "
            "datakilder er flyttet til status-overview.css. status.css inneholder naa bare "
            "status/omsetning-toolbar og omsetning-sidens summary-kort."
        ),
        "applications": [
            "Fibaro10 desktop V2 (status-overview.css): overtar dashboard-spesifikke statusregler.",
            "Fibaro10 desktop V2 (status.css): redusert til status/omsetning-toolbar og omsetning-summary.",
            "Buildlogg (build_log.py): registrerer build 1283.",
        ],
        "request": "Kjor videre trinn for trinn og gjor oppryddingen ferdig.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "status.css er redusert kraftig og har tydeligere ansvar.",
            "Dashboardets statuskomponenter ligger naa samlet med resten av oversiktssiden.",
            "Importrekkefolgen er uendret, slik at visuell prioritet fortsatt er den samme.",
        ],
    },
    {
        "version": "1",
        "build": "1282",
        "date": "27.06.2026",
        "headline": "AppShell-CSS skilt ut",
        "title": "Desktop V2 har flyttet venstremeny og toppbar til app-shell.css",
        "description": (
            "Build 1282 rydder i layout.css. Stiler for applikasjonsskall, venstremeny, logo/"
            "wordmark, menyvalg, buildnummer, toppbar og brukerprofil er flyttet til app-shell.css. "
            "layout.css beholder basisregler, globale Ant Design-justeringer og generelle sidekomponenter."
        ),
        "applications": [
            "Fibaro10 desktop V2 (app-shell.css): ny fil for AppShell, hovedmeny og toppbar.",
            "Fibaro10 desktop V2 (layout.css): beholder grunnlayout, PageHeader, PeriodNavigator, tabeller og tabs.",
            "Fibaro10 desktop V2 (main.tsx): importerer app-shell.css etter layout.css.",
            "Buildlogg (build_log.py): registrerer build 1282.",
        ],
        "request": "Kjør videre trinn for trinn og gjør oppryddingen ferdig.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "layout.css er redusert betydelig og er mer generell.",
            "Venstremeny og toppbar er samlet i eget stilark.",
            "AppShell kan videreutvikles uten å blande seg med tabell- og sidekomponentstiler.",
        ],
    },
    {
        "version": "1",
        "build": "1281",
        "date": "27.06.2026",
        "headline": "Tidslinje-CSS delt",
        "title": "Desktop V2 har delt soling- og parkeringstidslinjer i egne stilark",
        "description": (
            "Build 1281 fjerner den gamle samlefilen timelines.css. Soling/dagslinje er flyttet "
            "til sun-timeline.css, mens parkering/belegg er flyttet til parking-timeline.css. "
            "Små refinement-regler er lagt i samme domene som resten av tidslinjen."
        ),
        "applications": [
            "Fibaro10 desktop V2 (sun-timeline.css): egen fil for soling/dagslinje.",
            "Fibaro10 desktop V2 (parking-timeline.css): egen fil for parkering/belegg.",
            "Fibaro10 desktop V2 (main.tsx): erstatter timelines.css-importen med de to nye stilarkene.",
            "Buildlogg (build_log.py): registrerer build 1281.",
        ],
        "request": "Kjør videre trinn for trinn og gjør oppryddingen ferdig.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Tidslinjestiler er nå delt etter funksjonsområde.",
            "Samlefila timelines.css er fjernet.",
            "Soling og parkering kan justeres videre hver for seg uten å påvirke den andre tidslinjen.",
        ],
    },
    {
        "version": "1",
        "build": "1280",
        "date": "27.06.2026",
        "headline": "Solsengenergi-CSS flyttet",
        "title": "Desktop V2 har flyttet energisiden for solsenger til energy.css",
        "description": (
            "Build 1280 flytter stilene for energi/solsenger ut av module-content.css og inn "
            "i energy.css. Generelle filter- og modulregler ligger fortsatt i module-content.css, "
            "mens energidomenet nå eier både Elvia- og solsengenergi-visningene."
        ),
        "applications": [
            "Fibaro10 desktop V2 (energy.css): overtar energy-sunbeds- og sunbed-regler.",
            "Fibaro10 desktop V2 (module-content.css): beholder felles modulfilter og modul-layout.",
            "Buildlogg (build_log.py): registrerer build 1280.",
        ],
        "request": "Fortsett med CSS-opprydding og flytt domenespesifikke regler ut av felles stilark.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "module-content.css er redusert videre og inneholder mindre energispesifikk kode.",
            "energy.css samler nå både Elvia og beregning av solsengforbruk.",
            "Media-regelen for solsengenergi ble flyttet sammen med resten av domenestilene.",
        ],
    },
    {
        "version": "1",
        "build": "1279",
        "date": "27.06.2026",
        "headline": "Dashboard-CSS skilt ut",
        "title": "Desktop V2 har flyttet statusdashboard-stiler ut av status.css",
        "description": (
            "Build 1279 rydder i den største gjenværende CSS-filen. Dashboard-spesifikke regler "
            "for status/oversikt, kommando-kort, seksjonshoder og info-grid er flyttet til "
            "status-overview.css, mens status.css beholder felles statuskomponenter."
        ),
        "applications": [
            "Fibaro10 desktop V2 (status-overview.css): ny fil for dashboard/status oversikt.",
            "Fibaro10 desktop V2 (status.css): beholder felles statuskort, striper, perioder og kildelister.",
            "Fibaro10 desktop V2 (main.tsx): importerer status-overview.css etter status.css.",
            "Buildlogg (build_log.py): registrerer build 1279.",
        ],
        "request": "Fortsett med CSS-opprydding og splitt de største stilarkene mer systematisk.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "status.css er redusert med dashboard-spesifikke regler.",
            "OverviewPage sine egne layoutregler ligger nå samlet i status-overview.css.",
            "Importrekkefølgen gjør at dashboard-overstyringer fortsatt kommer etter felles statusstiler.",
        ],
    },
    {
        "version": "1",
        "build": "1278",
        "date": "27.06.2026",
        "headline": "Soltime-CSS skilt ut",
        "title": "Desktop V2 har flyttet soltime- og bildearkivstiler ut av module-content.css",
        "description": (
            "Build 1278 rydder videre i frontend-stilene. Regler for soltime-listen, inline "
            "bildevelger og bildearkivmodal er flyttet fra module-content.css til sun-sessions.css. "
            "Generelle modulmetrikker og diagram-/filterregler blir igjen i module-content.css."
        ),
        "applications": [
            "Fibaro10 desktop V2 (sun-sessions.css): ny fil for soltimekort og bildearkiv.",
            "Fibaro10 desktop V2 (module-content.css): beholder generelle modul-, tabell-, filter- og diagramstiler.",
            "Fibaro10 desktop V2 (main.tsx): importerer sun-sessions.css etter module-content.css.",
            "Buildlogg (build_log.py): registrerer build 1278.",
        ],
        "request": "Fortsett med CSS-opprydding og splitt de største stilarkene mer systematisk.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "module-content.css er redusert med rundt 4,9 KB.",
            "Soltime- og bildearkivregler har fått eget domene-stilark.",
            "Generelle module-metric-regler er bevisst beholdt i module-content.css fordi de brukes på tvers av modulsider.",
        ],
    },
    {
        "version": "1",
        "build": "1277",
        "date": "27.06.2026",
        "headline": "Oppgjørs-CSS skilt ut",
        "title": "Desktop V2 har flyttet oppgjørsflater ut av records.css",
        "description": (
            "Build 1277 fortsetter CSS-splittingen. Alle settlement- og sun-settlement-regler "
            "er flyttet fra records.css til records-settlements.css, mens tabell-, kjøretøy- "
            "og tomtilstandsstiler blir igjen i records.css."
        ),
        "applications": [
            "Fibaro10 desktop V2 (records-settlements.css): ny fil for oppgjør og bilagsflater.",
            "Fibaro10 desktop V2 (records.css): beholder kjøretøy, tabell, skjema og tomtilstander.",
            "Fibaro10 desktop V2 (main.tsx): importerer records-settlements.css etter records.css.",
            "Buildlogg (build_log.py): registrerer build 1277.",
        ],
        "request": "Fortsett med CSS-opprydding og splitt de største stilarkene mer systematisk.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "records.css er redusert til under 4 KB.",
            "Oppgjør for parkering og soling har fått eget stilark.",
            "Responsive oppgjørsoverstyringer ligger fortsatt samlet i responsive.css og lastes sist.",
        ],
    },
    {
        "version": "1",
        "build": "1276",
        "date": "27.06.2026",
        "headline": "Sammenlignings-CSS skilt ut",
        "title": "Desktop V2 har flyttet status-sammenligning ut av status.css",
        "description": (
            "Build 1276 starter CSS-splittingen av de største stilarkene. Regler for "
            "periodesammenligning og årssammenligning er flyttet fra status.css til "
            "status-comparison.css, mens importrekkefølgen er beholdt slik at visningen får "
            "samme cascade som før."
        ),
        "applications": [
            "Fibaro10 desktop V2 (status-comparison.css): ny fil for sammenligningssidene.",
            "Fibaro10 desktop V2 (status.css): fjerner status-comparison-regler fra hovedfilen.",
            "Fibaro10 desktop V2 (main.tsx): importerer status-comparison.css etter status.css.",
            "Buildlogg (build_log.py): registrerer build 1276.",
        ],
        "request": "Fortsett med CSS-opprydding og splitt de største stilarkene mer systematisk.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "status.css er redusert med rundt 4,6 KB.",
            "Sammenligningssidene har fått eget stilark.",
            "Blandede refinement-selectorer er splittet slik at statusdashboard og sammenligning ikke er koblet i samme CSS-regel.",
        ],
    },
    {
        "version": "1",
        "build": "1275",
        "date": "27.06.2026",
        "headline": "Årssammenligning deler felles hjelpefunksjoner",
        "title": "Desktop V2 har samlet årvalg, differanseformat og månedsetiketter",
        "description": (
            "Build 1275 rydder videre i årssammenligningssidene. Felles logikk for aktivt årvalg "
            "fra URL, standard sammenligningsår, månedsetiketter på aksen, datoformat og positive/"
            "negative differanser er flyttet til yearComparison."
        ),
        "applications": [
            "Fibaro10 desktop V2 (yearComparison.ts): ny felles modul for årssammenligningshjelpere.",
            "Fibaro10 desktop V2 (RevenueYearComparisonPage.tsx): bruker felles årvalg og formattering.",
            "Fibaro10 desktop V2 (SunYearComparisonPage.tsx): bruker felles årvalg og formattering.",
            "Fibaro10 desktop V2 (ParkingYearComparisonPage.tsx): bruker felles årvalg og formattering.",
            "Buildlogg (build_log.py): registrerer build 1275.",
        ],
        "request": "Fortsett på gjøremålslisten og gjennomfør foreslått teknisk opprydding.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Årssammenligningssidene deler nå felles helper for aktivt årvalg.",
            "Dato-, differanse- og månedsetikett-format er samlet.",
            "Soling og parkering beholder lokal logikk for beløp/antall der den faktisk avviker.",
        ],
    },
    {
        "version": "1",
        "build": "1274",
        "date": "27.06.2026",
        "headline": "Felles diagramtema i V2",
        "title": "Desktop V2 har samlet standard ECharts-stiler i chartTheme",
        "description": (
            "Build 1274 rydder i diagramkoden. Tooltip, legend, akselinjer, gridlinjer og tittelstil "
            "er samlet i chartTheme og brukt på moduldiagram, månedsoversikt, periodesammenligning "
            "og årssammenligningene for omsetning, soling og parkering."
        ),
        "applications": [
            "Fibaro10 desktop V2 (chartTheme.ts): ny felles modul for standard diagramutseende.",
            "Fibaro10 desktop V2 (ModuleChartPanel.tsx): bruker felles tooltip, legend og aksestiler.",
            "Fibaro10 desktop V2 (RevenueMonthPage.tsx): bruker felles diagramtema i månedsoversikten.",
            "Fibaro10 desktop V2 (StatusComparisonPage.tsx): bruker felles diagramtema i periodesammenligning.",
            "Fibaro10 desktop V2 (Revenue/Sun/ParkingYearComparisonPage.tsx): bruker felles diagramtema i årssammenligningene.",
            "Buildlogg (build_log.py): registrerer build 1274.",
        ],
        "request": "Fortsett på gjøremålslisten og gjennomfør foreslått teknisk opprydding.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Repeterte ECharts-stiler er samlet i chartTheme.",
            "Diagramsidene har mindre lokal stilkode og mer lik visuell oppførsel.",
            "Ingen API-er eller datalogikk er endret.",
        ],
    },
    {
        "version": "1",
        "build": "1273",
        "date": "27.06.2026",
        "headline": "Frontend-modulnavn samlet bedre",
        "title": "Desktop V2 gjenbruker felles modulmodell i hovedmenyen",
        "description": (
            "Build 1273 fortsetter oppryddingen i V2-frontend. Hovedmenyen henter nå modulnavn "
            "og menyfarger fra moduleViews i stedet for å hardkode alt direkte i appNavigation. "
            "Ikoner og gruppering ligger fortsatt i appNavigation, der de hører hjemme som UI-struktur."
        ),
        "applications": [
            "Fibaro10 desktop V2 (moduleViews.ts): legger til felles navigasjonsnavn og modul-fargeoppslag.",
            "Fibaro10 desktop V2 (appNavigation.tsx): bruker felles modulmodell for label og farge.",
            "Buildlogg (build_log.py): registrerer build 1273.",
        ],
        "request": "Fortsett på gjøremålslisten og gjennomfør foreslått teknisk opprydding.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Hovedmenytekstene gjenbruker samme modulnavn som resten av frontend.",
            "Menyfarger er samlet som moduloppslag i moduleViews.",
            "appNavigation er smalere og eier bare ikonrekkefølge og gruppering.",
        ],
    },
    {
        "version": "1",
        "build": "1272",
        "date": "27.06.2026",
        "headline": "V2-navnetekster flyttet ut av main.py",
        "title": "Backend har skilt V2-navnegrunnlag fra hovedlogikken",
        "description": (
            "Build 1272 fortsetter teknisk opprydding ved å flytte V2-modulnavn, sidenavn og "
            "tittelbygging ut av main.py og inn i en egen v2_navigation-modul. Dette gjør "
            "hovedfila mindre, reduserer duplisering og gjør videre meny-/tekstendringer tryggere."
        ),
        "applications": [
            "Fibaro10 backend (v2_navigation.py): ny modul for V2-modulnavn, sidenavn og tittelbygging.",
            "Fibaro10 backend (main.py): importerer felles tittelbygger i stedet for å eie V2-navneordbok.",
            "Buildlogg (build_log.py): registrerer build 1272.",
        ],
        "request": "Fortsett på gjøremålslisten og gjennomfør foreslått teknisk opprydding.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "V2-navnegrunnlaget ligger nå samlet i v2_navigation.py.",
            "main.py er redusert og slipper egen meny-/sidetittelordbok.",
            "Ingen ruter, API-kontrakter eller synlig menyoppførsel er endret.",
        ],
    },
    {
        "version": "1",
        "build": "1271",
        "date": "27.06.2026",
        "headline": "Menytekster og betegnelser er ryddet",
        "title": "Desktop V2 har mer konsistente norske menyvalg, sidetitler og oppgjørstekster",
        "description": (
            "Build 1271 rydder synlige betegnelser i V2-grensesnittet. Årssammenligning, "
            "periodesammenligning, Temperatur og fukt, Yr-logg, Lux-logg, Forbruk per seng "
            "og Buildlogg brukes nå konsekvent i meny og sidetitler. I tillegg er noen "
            "oppgjørs- og tabelltekster rettskrevet."
        ),
        "applications": [
            "Fibaro10 desktop V2 (moduleViews.ts): strammer inn menyetiketter og undermenyvalg.",
            "Fibaro10 backend (main.py): legger inn felles V2-navneordbok og bruker den i moduloverskrifter.",
            "Fibaro10 desktop V2 (sammenligningssider): retter årssammenligning/periodesammenligning og tidsaksetekst.",
            "Fibaro10 desktop V2 (ModulePage.tsx): retter enkelte tabellkolonnenavn.",
            "Buildlogg (build_log.py): registrerer build 1271.",
        ],
        "request": "Gå gjennom alle betegnelser og menyvalgtekster, sjekk konsistens og rettskriving, og vurder navneendringer.",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Årssammenligning og periodesammenligning er tydeligere adskilt.",
            "Temp/fukt, Yr logg, Lux logging, Forbruk/seng og Build er erstattet med mer konsistente navn.",
            "Backendtitler bruker samme navnegrunnlag som menyen.",
            "Flere synlige oppgjørstekster er rettskrevet.",
        ],
    },
    {
        "version": "1",
        "build": "1270",
        "date": "27.06.2026",
        "headline": "Dashboard inn i venstremenyen",
        "title": "Desktop V2 har fjernet Hjem fra toppbar og lagt Dashboard øverst i hovedmenyen",
        "description": (
            "Build 1270 rydder videre i appnavigasjonen. Hjem-knappen i toppbaren er fjernet, og Dashboard "
            "er lagt inn som første faste valg i venstremenyen. Dashboard peker til statusoversikten og bruker "
            "statusfargen, slik at startsiden er tilgjengelig som en normal del av hovedmenyen."
        ),
        "applications": [
            "Fibaro10 desktop V2 (appNavigation.tsx): legger Dashboard/status inn som første hovedmenypunkt.",
            "Fibaro10 desktop V2 (AppShell.tsx): fjerner Hjem-lenken fra toppbaren og håndterer gruppe uten overskrift.",
            "Fibaro10 desktop V2 (layout.css): fjerner CSS for den gamle Hjem-knappen.",
            "Buildlogg (build_log.py): registrerer build 1270.",
        ],
        "request": "Fjern Hjem-knapp i menyen og legg Dashboard øverst i venstremeny.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Dashboard ligger nå øverst i venstremenyen.",
            "Toppbaren har ikke lenger egen Hjem-knapp.",
            "Gammel CSS for header-home-link er fjernet.",
        ],
    },
    {
        "version": "1",
        "build": "1269",
        "date": "27.06.2026",
        "headline": "Roligere Lilletorget-logo i sidebaren",
        "title": "Desktop V2 har faatt et enklere og mer seriost logofelt",
        "description": (
            "Build 1269 rydder logo-/brandfeltet i venstremenyen. Kortutforming, driftssystem-brikke og "
            "undertekst er fjernet, slik at det kun staar Lilletorget-logo/wordmark direkte paa bakgrunnen "
            "med en diskret skillelinje under. Maalet er et roligere og mer kvalitetsorientert uttrykk."
        ),
        "applications": [
            "Fibaro10 desktop V2 (AppShell.tsx): fjerner undertekst og driftssystem-brikke fra BrandHome.",
            "Fibaro10 desktop V2 (layout.css): erstatter kortpreget logoomraade med flat merkevareflate.",
            "Buildlogg (build_log.py): registrerer build 1269.",
        ],
        "request": "Ta en ny runde paa logo feltet. Kun logoen og teksten Lilletorget, ikke som knapp, seriost kvalitetsuttrykk.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Logoomraadet viser kun Lilletorget-wordmark.",
            "Kortbakgrunn, ramme, skygge, fargelinje og brikke er fjernet.",
            "Flaten har kun diskret avstand og skillelinje mot hovedmenyen.",
        ],
    },
    {
        "version": "1",
        "build": "1268",
        "date": "26.06.2026",
        "headline": "Hovedmeny-modell skilt ut",
        "title": "Desktop V2 har flyttet menystruktur og farger til egen appNavigation",
        "description": (
            "Build 1268 rydder videre i frontendfundamentet. Hovedmenyens moduler, ikoner, grupper og aktive "
            "menyoppslag er flyttet ut av AppShell og inn i appNavigation.tsx. AppShell eier dermed layouten, "
            "mens menystrukturen kan endres separat."
        ),
        "applications": [
            "Fibaro10 desktop V2 (appNavigation.tsx): ny fil for hovedmenyens moduler, grupper, ikoner og farger.",
            "Fibaro10 desktop V2 (components/AppShell.tsx): bruker appNavigation i stedet for lokal menydefinisjon.",
            "Buildlogg (build_log.py): registrerer build 1268.",
        ],
        "request": "Fortsett med alle de tingene du foreslo at du ville gjore slik at alt er klart.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Menystruktur ligger naa i appNavigation.tsx.",
            "AppShell er redusert til layout, toppbar og brukerprofil.",
            "Videre menyendringer kan gjores uten aa endre appskall-komponenten.",
        ],
    },
    {
        "version": "1",
        "build": "1267",
        "date": "26.06.2026",
        "headline": "Ubrukt status-CSS fjernet",
        "title": "Desktop V2 har fjernet ubrukt CSS fra omsetning/sammenligning",
        "description": (
            "Build 1267 rydder opp etter CSS-audit. Den eneste konkrete ubrukt-klassen auditverktøyet fant, "
            "status-comparison-current-period, er fjernet fra status.css. Dette er en liten kontrollert "
            "opprydding uten funksjonell endring."
        ),
        "applications": [
            "Fibaro10 desktop V2 (status.css): fjerner ubrukt status-comparison-current-period.",
            "Buildlogg (build_log.py): registrerer build 1267.",
        ],
        "request": "Fortsett med alle de tingene du foreslo at du ville gjore slik at alt er klart.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "CSS-audit er brukt til aa finne konkret ubrukt kode.",
            "Ubrukt status-comparison-current-period er fjernet.",
            "Ingen UI-logikk eller ruter er endret.",
        ],
    },
    {
        "version": "1",
        "build": "1266",
        "date": "26.06.2026",
        "headline": "Ruter samlet i egen AppRoutes",
        "title": "Desktop V2 har skilt appskall og ruter i to tydelige filer",
        "description": (
            "Build 1266 fullfoerer neste steg i appskall-oppryddingen. Alle lazy page-importer, legacy-redirects "
            "og Route-definisjoner er flyttet fra App.tsx til AppRoutes.tsx. App.tsx holder naa bare styr paa aktiv "
            "modul/view og monterer AppShell + AppRoutes."
        ),
        "applications": [
            "Fibaro10 desktop V2 (AppRoutes.tsx): ny rutekomponent med eksisterende ruter og redirects.",
            "Fibaro10 desktop V2 (App.tsx): redusert til aktiv modul/view og montering av AppShell og AppRoutes.",
            "Buildlogg (build_log.py): registrerer build 1266.",
        ],
        "request": "Fortsett med alle de tingene du foreslo at du ville gjore slik at alt er klart.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Rutekonfigurasjonen ligger naa i AppRoutes.",
            "Legacy-redirects er samlet med rutene de gjelder.",
            "App.tsx er mindre og tryggere aa endre videre.",
        ],
    },
    {
        "version": "1",
        "build": "1265",
        "date": "26.06.2026",
        "headline": "Appskall flyttet ut av App.tsx",
        "title": "Desktop V2 har faatt et eget AppShell for meny, toppbar og brukerprofil",
        "description": (
            "Build 1265 fortsetter frontend-oppryddingen ved aa flytte venstremeny, toppbar, brandfelt, "
            "brukerprofil og innholdskonteiner ut av App.tsx og inn i en egen AppShell-komponent. App.tsx "
            "blir dermed mer rendyrket som rutefil, mens appskallet kan forbedres videre uten aa rote i "
            "routing og spesialsider."
        ),
        "applications": [
            "Fibaro10 desktop V2 (components/AppShell.tsx): ny komponent for sidebaren, toppbaren, brandfelt og brukerprofil.",
            "Fibaro10 desktop V2 (App.tsx): redusert til modulvalg, active view og ruter.",
            "Buildlogg (build_log.py): registrerer build 1265.",
        ],
        "request": "Fortsett med alle de tingene du foreslo at du ville gjore slik at alt er klart.",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Appskall og navigasjon ligger naa samlet i AppShell.",
            "App.tsx blander ikke lenger brukerprofil, menytilstand og routing i samme komponent.",
            "Dette gjoer neste opprydding i ruter eller menystruktur mindre risikabel.",
        ],
    },
    {
        "version": "1",
        "build": "1264",
        "date": "26.06.2026",
        "headline": "Stabil og gruppert hovedmeny",
        "title": "Desktop V2 har faatt egen sidenavigasjon med faste fagfarger",
        "description": (
            "Build 1264 erstatter Ant Design Menu i venstremenyen med en egen, enklere sidenavigasjon. "
            "Menyen er delt i Oekonomi, Bygg og drift og System, og fargene settes direkte per menypunkt "
            "i komponenten. Det fjerner skjore nth-child-regler i CSS og gjoer videre designarbeid mer "
            "forutsigbart."
        ),
        "applications": [
            "Fibaro10 desktop V2 (App.tsx): bytter Ant Design Menu til egen SideNavigation med grupper.",
            "Fibaro10 desktop V2 (layout.css): rydder bort nth-child-regler og legger stabile fargevariabler per menypunkt.",
            "Buildlogg (build_log.py): registrerer build 1264.",
        ],
        "request": "Fortsett med de endringene du ville gjore.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Venstremenyen er delt i Oekonomi, Bygg og drift og System.",
            "Farge settes direkte per menypunkt i komponenten i stedet for via CSS-posisjon.",
            "Menyikonene har fargede brikker og aktivtilstand med samme fagfarge.",
        ],
    },
    {
        "version": "1",
        "build": "1263",
        "date": "26.06.2026",
        "headline": "Mer farge og tydeligere Lilletorget-brand",
        "title": "Desktop V2 har faatt mer karakter i logo, hovedmeny og toppbar",
        "description": (
            "Build 1263 viderefoerer appskall-oppryddingen etter at forrige versjon ble for flat. Brandfeltet bruker "
            "naa Lilletorget-wordmark, en tydelig driftssystem-brikke og varm/gullpreget bakgrunn. Hovedmenyen har "
            "faste farger per fagomraade, og toppbaren har en diskret fargelinje koblet til aktivt omraade."
        ),
        "applications": [
            "Fibaro10 desktop V2 (App.tsx): bruker full Lilletorget-wordmark i BrandHome og legger klasse per hovedmenypunkt.",
            "Fibaro10 desktop V2 (layout.css): legger mer farge i brandkort, domenefargede menyikoner, aktivfelt og toppbar.",
            "Buildlogg (build_log.py): registrerer build 1263.",
        ],
        "request": "Jeg synes ikke det ble bra. Vil ha det bedre og med litt mer farger.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Brandfeltet viser naa Lilletorget-wordmark i stedet for kun mark + tekst.",
            "Hvert hovedmenypunkt har egen domenefarge for ikon og hover/aktiv bakgrunn.",
            "Toppbaren har en tynn fargelinje og mer aktiv farge i hjem-/menyknapper.",
            "Visuell Playwright-preview er kontrollert etter endringen.",
        ],
    },
    {
        "version": "1",
        "build": "1262",
        "date": "26.06.2026",
        "headline": "Ny appprofil og lysere navigasjon",
        "title": "Desktop V2 har faatt mer moderne Lilletorget-profil i appskallet",
        "description": (
            "Build 1262 rydder hjemknapp, logo/navn, venstremeny og toppmeny. Den moerke sidebaren er erstattet "
            "av en lysere Lilletorget-inspirert navigasjon med eksisterende logoasset, tydeligere aktivmarkering "
            "og en egen hjemknapp i toppbaren. Toppfanene er gjort roligere og mer systematiske uten aa endre ruter "
            "eller menyinnhold."
        ),
        "applications": [
            "Fibaro10 desktop V2 (App.tsx): legger inn gjenbrukbar BrandHome og egen Hjem-knapp i toppbaren.",
            "Fibaro10 desktop V2 (layout.css): moderniserer sidebar, logo-/brandfelt, hovedmeny, buildlenke og toppfaner.",
            "Fibaro10 desktop V2 (designTokens.ts): oppdaterer Ant Design Layout-token fra moerk til lys sidebar.",
            "Buildlogg (build_log.py): registrerer build 1262.",
        ],
        "request": "Se paa hjemknappen, navn/logo, toppmeny og venstremeny og gjoer appen penere og mer moderne med inspirasjon fra mobilappen.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Sidebar bruker naa lys bakgrunn, Lilletorget-mark og tydeligere aktiv hovedmeny.",
            "Appnavnet er endret fra Fibaro10-brand til Lilletorget med undertekst for solsenter og parkering.",
            "Headeren har en separat Hjem-knapp ved siden av menyknappen.",
            "Toppfanene har mindre tung graaflate og mer presis aktivfarge per fagomraade.",
            "Endringen er visuelt verifisert med lokal Playwright-preview.",
        ],
    },
    {
        "version": "1",
        "build": "1261",
        "date": "26.06.2026",
        "headline": "Felles tabellsoek i modulvisningene",
        "title": "Desktop V2 har faatt en felles komponent for tabellsoek",
        "description": (
            "Build 1261 fortsetter frontend-oppryddingen med en liten, kontrollert komponentuttrekking. "
            "Soltimepanelet og de generiske modultabellene bruker naa samme TableSearch-komponent, slik at "
            "soek, enter-knapp, tomt felt og ryddelogikk oppfoerer seg likt."
        ),
        "applications": [
            "Fibaro10 desktop V2 (TableSearch.tsx): legger inn felles soekekomponent for tabellflater.",
            "Fibaro10 desktop V2 (ModulePage.tsx): erstatter lokale Input.Search-blokker i soltimer og modultabeller.",
            "Buildlogg (build_log.py): registrerer build 1261.",
        ],
        "request": "Kjoer neste ting du ville gjoere.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Tabellsoek i modulflater har naa ett felles implementasjonspunkt.",
            "Soltimer og generiske modultabeller beholder samme funksjon, men med mindre duplisert frontend-kode.",
            "Dette gjoer neste opprydding i ModulePage tryggere fordi soekelogikken allerede er isolert.",
        ],
    },
    {
        "version": "1",
        "build": "1260",
        "date": "26.06.2026",
        "headline": "Felles periodekontroller og tabellkort",
        "title": "Desktop V2 har faatt standardkomponenter for periodevalg og tabellflater",
        "description": (
            "Build 1260 fortsetter frontend-oppryddingen med felles PeriodNavigator og DataTableCard. Dags-, maaneds- "
            "og aarsnavigasjon bruker naa samme komponent paa tvers av omsetning, soling, parkering, moduldiagrammer "
            "og ventilasjon. Buildloggen og maanedsoversikten bruker felles tabellkort."
        ),
        "applications": [
            "Fibaro10 desktop V2 (PeriodNavigator.tsx/layout.css): legger inn felles komponent og stil for forrige/neste/dato-kontroller.",
            "Fibaro10 desktop V2 (DataTableCard.tsx): legger inn felles wrapper for standard tabellkort.",
            "Fibaro10 desktop V2 (RevenueMonthPage, StatusComparisonPage og aarssammenligninger): flytter periodevalg til felles komponent.",
            "Fibaro10 desktop V2 (ModulePage, ModuleChartPanel, ParkingTimelinePanel, SunTimelinePanel, VentilationPage): standardiserer dagsnavigasjon.",
            "Fibaro10 desktop V2 (BuildLogPage): bruker felles tabellkort.",
            "Buildlogg (build_log.py): registrerer build 1260.",
        ],
        "request": "Da kan du fortsette med neste.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Forrige/neste/dato-kontroller har samme struktur og CSS paa tvers av sidene.",
            "Maanedsoversikt og buildlogg bruker felles DataTableCard.",
            "Flere lokale ikon- og knappemønstre er fjernet fra sidene.",
            "Dette gir mindre spesialkode og et bedre grunnlag for videre feature-opprydding.",
        ],
    },
    {
        "version": "1",
        "build": "1259",
        "date": "26.06.2026",
        "headline": "Frontend datalag og felles sideheader",
        "title": "Desktop V2 har faatt TanStack Query, tydelige query-noekler og felles toppkomponent",
        "description": (
            "Build 1259 starter den strukturelle frontend-oppryddingen uten rammeverksbytte. API-data gaar naa via "
            "TanStack Query med felles QueryClient, navngitte query-noekler og cache-invalidation etter handlinger. "
            "Drift og mobil bruker en ny felles PageHeader-komponent, og gamle lokale reload-tellere er fjernet fra "
            "modul-, oppgjoer- og kjoeretoeysidene."
        ),
        "applications": [
            "Fibaro10 desktop V2 (package.json): legger til @tanstack/react-query.",
            "Fibaro10 desktop V2 (queryClient.ts/queryKeys.ts/hooks.ts): etablerer felles query-cache, query-noekler og API-hook.",
            "Fibaro10 desktop V2 (App.tsx/main.tsx): kobler appen til QueryClientProvider og henter innlogget bruker via query-cache.",
            "Fibaro10 desktop V2 (ModulePage og oppgjoer/kjoeretoey-sider): bytter reloadToken/refreshKey til presis query-invalidation.",
            "Fibaro10 desktop V2 (PageHeader.tsx/layout.css): legger inn felles toppkomponent for mer konsekvent sidestil.",
            "Buildlogg (build_log.py): registrerer build 1259.",
        ],
        "request": "Kan du sette igang med det du sier du faktisk ville gjort.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Innfører TanStack Query som standard datalag for frontend.",
            "Status, drift, buildlogg, mobil, omsetning, aarssammenligninger, modulvisninger, oppgjoer og kjoeretoeydetaljer har navngitte query-noekler.",
            "Mutasjoner og importer oppdaterer naa relevante datasett med invalidateQueries i stedet for lokale reload-tellere.",
            "Drift og mobil bruker felles PageHeader, og gammel mobil/status-header-CSS er ryddet bort.",
        ],
    },
    {
        "version": "1",
        "build": "1258",
        "date": "26.06.2026",
        "headline": "Mer systematisk CSS-opprydding",
        "title": "Desktopdesignet har faatt mindre overlapp og ryddigere fellesregler",
        "description": (
            "Build 1258 fortsetter designoppryddingen ved aa samle aktive CSS-regler i hoveddefinisjonene og fjerne "
            "gamle overstyringslag i modul-, status-, record-, energi- og ventilasjonsstilene. Resultatet er mindre "
            "CSS, mer forutsigbar arv og et roligere, mer systematisk visuelt uttrykk."
        ),
        "applications": [
            "Fibaro10 desktop V2 (module-content.css): samler metrik-kort, diagramkort og felles modulflater.",
            "Fibaro10 desktop V2 (status.css): fjerner gamle overstyringer for statuskort, sammenligning og dashboardflater.",
            "Fibaro10 desktop V2 (records.css): samler tabell-, fanetall- og kjoeretoeykortregler.",
            "Fibaro10 desktop V2 (energy.css): samler Elvia-kortregler og reduserer dupliserte verdier.",
            "Fibaro10 desktop V2 (ventilation.css): samler ventilasjonskort, viftefelt og dagslogg-markeringer.",
            "Buildlogg (build_log.py): registrerer build 1258.",
        ],
        "request": "Ta en designopprydding og gjoer alt penere og mer systematisk.",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Fjernet flere gamle CSS-overstyringsblokker.",
            "Reduserte CSS-stoerrelsen i frontend-builden.",
            "Metrikkort, tabeller, energi- og ventilasjonsflater har mer konsistent grunnstil.",
            "Dashboard/status bruker mindre spesiallogikk i CSS og blir enklere aa videreutvikle.",
        ],
    },
    {
        "version": "1",
        "build": "1257",
        "date": "26.06.2026",
        "headline": "Ryddigere desktopdesign",
        "title": "Desktopgrensesnittet har faatt strammere kort, tabeller, statusfelt og felles designregler",
        "description": (
            "Build 1257 rydder visuelt i V2-grensesnittet med mer systematiske tokens, tettere Ant Design-tema, "
            "roligere kortflater, mer kompakte tabeller og en ryddigere statusoversikt. Endringen er avgrenset til "
            "frontend-design og endrer ikke datalogikk."
        ),
        "applications": [
            "Fibaro10 desktop V2 (designTokens.ts): justerer felles Ant Design-tema for tettere kontrollhøyder, kort og tabeller.",
            "Fibaro10 desktop V2 (tokens.css/layout.css): legger felles overflate-, spacing- og tabellregler for hele appen.",
            "Fibaro10 desktop V2 (status.css): rydder status/dashboard med roligere lys- og ventilasjonsrader og mer kompakte kort.",
            "Fibaro10 desktop V2 (module-content.css, records.css, energy.css, ventilation.css): standardiserer kort, nøkkeltall og tabellflater.",
            "Buildlogg (build_log.py): registrerer build 1257.",
        ],
        "request": "Ta en designopprydding og gjoer alt penere og mer systematisk.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Mindre og mer konsekvente kort med roligere skygger.",
            "Mer systematisk typografi og tettere Ant Design-kontroller.",
            "Statusoversikten har slankere lys- og ventilasjonsrader.",
            "Tabeller har mer lik header, radavstand og hover-effekt.",
            "Energi- og ventilasjonskort er strammet inn visuelt.",
        ],
    },
    {
        "version": "1",
        "build": "1256",
        "date": "26.06.2026",
        "headline": "Paa gaaende viser oppdateringsalder",
        "title": "Parkering oversikt viser hvor lenge siden paa gaaende-data ble oppdatert",
        "description": (
            "Build 1256 endrer kortet Paa gaaende paa Parkering > Oversikt slik at detaljteksten viser hvor lenge "
            "det er siden siste vellykkede EasyPark-import, i stedet for en fast Akkurat naa-tekst."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger til en egen teksthelper for importstatus som aldri viser Akkurat naa paa dette kortet.",
            "Fibaro10 backend (main.py): kobler Paa gaaende-kortet til EasyPark-importens faktiske oppdateringsalder.",
            "Buildlogg (build_log.py): registrerer build 1256.",
        ],
        "request": "Paa kortet paa gaaende boer det ikke staa akkurat naa, men hvor lenge det er siden sist oppdatert.",
        "work_duration": "ca. 8 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Paa gaaende-kortet viser naa for eksempel Oppdatert 11 min siden.",
            "Ved helt fersk import vises Oppdatert under 1 min siden.",
            "Manglende importstatus vises som Ingen importstatus.",
        ],
    },
    {
        "version": "1",
        "build": "1255",
        "date": "26.06.2026",
        "headline": "Riktig tid paa parkering oppdatert",
        "title": "Sist oppdatert paa Parkering oversikt viser lokal importtid uten ekstra tidssonepaaslag",
        "description": (
            "Build 1255 retter tidsvisningen i kortet Sist oppdatert paa Parkering > Oversikt. EasyPark-importstatus "
            "lagres som lokal Oslo-tid uten timezone, og skal derfor formateres som kildetidspunkt uten UTC-konvertering."
        ),
        "applications": [
            "Fibaro10 backend (main.py): bruker format_source_datetime for EasyPark-importens lokale tidspunkt.",
            "Tester (tests/test_time_formatting.py): dekker at lokal-naiv tid 15:52 vises som 15:52.",
            "Buildlogg (build_log.py): registrerer build 1255.",
        ],
        "request": "Sist oppdatert viser 17:52, men riktig tidspunkt er 15:52.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Fjerner utilsiktet +2 timer i sist oppdatert-kortet.",
            "EasyPark-importtid vises naa som lokal kildetid.",
            "Regresjonstest lagt til for lokal-naiv tidsformattering.",
        ],
    },
    {
        "version": "1",
        "build": "1254",
        "date": "26.06.2026",
        "headline": "Tydelig sist oppdatert paa parkering",
        "title": "Parkering oversikt viser siste EasyPark-oppdatering som eget nokkelkort",
        "description": (
            "Build 1254 gjor sist oppdatert-tidspunkt tydelig paa Parkering > Oversikt. Siden viser naa siste "
            "vellykkede EasyPark-import som et eget nokkelkort forst i kortrekken, med lenke til datakilder."
        ),
        "applications": [
            "Fibaro10 backend (main.py): henter ImportJobStatus for easypark_parking_import paa parkeringsoversikten.",
            "Fibaro10 backend (main.py): legger Sist oppdatert som forste kort paa Parkering > Oversikt.",
            "Buildlogg (build_log.py): registrerer build 1254.",
        ],
        "request": "Sist oppdatert tidspunkt maa komme tydelig frem paa siden.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Parkering > Oversikt viser Sist oppdatert som tydelig forste kort.",
            "Tidspunktet bruker siste vellykkede EasyPark-import.",
            "Kortet peker til Admin > Datakilder for mer detaljer.",
        ],
    },
    {
        "version": "1",
        "build": "1253",
        "date": "26.06.2026",
        "headline": "Bilinfo i siste parkeringer",
        "title": "Parkering oversikt viser merke, type og farge i siste parkeringer",
        "description": (
            "Build 1253 rydder videre i tabellen Siste parkeringer paa Parkering > Oversikt. Omraadekolonnen "
            "fjernes, og bilen faar egne kolonner for bilmerke, type og farge rett etter registreringsnummer. "
            "Feltene hentes fra SVV-nokkeldata der de finnes, med fallback til utenlandsk kjoeretoeyoppslag."
        ),
        "applications": [
            "Fibaro10 backend (main.py): kobler kjoeretoeydetaljer inn i siste parkeringer og fyller merke/type/farge.",
            "Fibaro10 frontend (ModulePage.tsx): legger tabelloverskrifter for Bilmerke, Type og Farge.",
            "Tester (tests/test_parking_row_api.py): dekker SVV-detaljer og utenlandsk fallback i parkeringsrader.",
            "Buildlogg (build_log.py): registrerer build 1253.",
        ],
        "request": "Paa Siste parkeringer under Parkering > Oversikt: fjern Omraade og legg inn bilmerke, type og farge etter reg.nr.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Omraade er fjernet fra Siste parkeringer.",
            "Bilmerke, Type og Farge vises etter Reg.nr.",
            "Svenske/danske oppslag kan fylle feltene naar SVV-detaljer mangler.",
        ],
    },
    {
        "version": "1",
        "build": "1252",
        "date": "26.06.2026",
        "headline": "Siste parkeringer med eier og kamera",
        "title": "Parkering oversikt faar bedre siste parkeringer-tabell",
        "description": (
            "Build 1252 rydder tabellen Siste parkeringer paa Parkering > Oversikt. Status flyttes forst, "
            "eier-sjekk byttes ut med faktisk eiernavn paa bilen, og start/slutt-tidspunkt faar UniFi-lenker "
            "som aapner 15 sekunder foer hendelsen."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger vehicle_owner i parkeringsradene og endrer kolonneoppsett paa oversikten.",
            "Fibaro10 backend (main.py): bruker 15 sekunder foer for UniFi-lenker paa Parkering > Oversikt.",
            "Fibaro10 frontend (ModulePage.tsx): legger tabelloverskrift for Eier.",
            "Tester (tests/test_unifi_protect_links.py): dekker 15-sekunders UniFi-vindu.",
            "Buildlogg (build_log.py): registrerer build 1252.",
        ],
        "request": "Paa Parkering > Oversikt: i Siste parkeringer skal Eier-sjekk byttes med eier paa bilen, Status skal forst, og start/slutt skal ha kamera-lenker 15 sekunder foer tidspunktet.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Status er forste kolonne i Siste parkeringer.",
            "Eier viser navn fra kjoeretoeyregisteret i stedet for eier-sjekk.",
            "Start og slutt viser videoikon med 15 sekunder foer hendelsen.",
        ],
    },
    {
        "version": "1",
        "build": "1251",
        "date": "26.06.2026",
        "headline": "Omsetningsoversikt uten oppgjorstabell",
        "title": "Omsetning oversikt viser kun relevante topplister og omsetningsgraf",
        "description": (
            "Build 1251 fjerner oppgjorstabellen fra Omsetning > Oversikt og lar ukesgrafen der vise bare "
            "omsetning. Antall-valget fjernes fra grafen fordi antall ikke er relevant for denne oversikten."
        ),
        "applications": [
            "Fibaro10 backend (main.py): fjerner oppgjorstabell og oppgjorsoppslag fra omsetningsoversikten.",
            "Fibaro10 backend (main.py): sender kun omsetningsmetric for ukesgrafen.",
            "Fibaro10 frontend (ModuleChartPanel.tsx): skjuler metric-velger naar grafen bare har ett valg.",
            "Buildlogg (build_log.py): registrerer build 1251.",
        ],
        "request": "Paa Omsetning > Oversikt: ta bort tabellen Oppgjor, og fjern valg mellom omsetning og antall i grafen fordi kun omsetning er relevant.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Oppgjorstabellen vises ikke lenger paa Omsetning > Oversikt.",
            "Oversikten gjor ikke lenger oppgjorsavstemming i bakgrunnen.",
            "Ukesgrafen viser bare omsetning og har ikke antall-bryter.",
        ],
    },
    {
        "version": "1",
        "build": "1250",
        "date": "26.06.2026",
        "headline": "Ryddigere omsetningsoversikt",
        "title": "Omsetning oversikt faar kompakte topplister med riktig kolonnerekkefolge",
        "description": (
            "Build 1250 rydder tabellene paa Omsetning > Oversikt. Oppgjorsfeltet har kortere tittel, "
            "topplistene viser de 20 beste dagene og maanedene, og kolonene prioriterer sum kroner, parkering "
            "og soling uten unodvendig totalt antall."
        ),
        "applications": [
            "Fibaro10 backend (main.py): utvider topplister til 20 og endrer kolonneoppsett for omsetningsoversikt.",
            "Fibaro10 frontend (ModulePage.tsx): justerer tabelloverskrifter for sum og antall.",
            "Buildlogg (build_log.py): registrerer build 1250.",
        ],
        "request": "Paa Omsetning > Oversikt: fjern 'Oppgjor mot Fibaro10', fjern 'Antall totalt' fra toppdager og toppmaaneder, sett rekkefolgen til Sum kr, Sum parkering, Antall parkering, Sum sol og Antall sol, og vis 20 beste maaneder og dager.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Oppgjorstabellen har naa kort tittel.",
            "Topp dager og topp maaneder viser 20 rader.",
            "Topplistene viser Sum kr forst og dropper Antall totalt.",
        ],
    },
    {
        "version": "1",
        "build": "1249",
        "date": "26.06.2026",
        "headline": "Mobilrammer uten topp",
        "title": "Mobilpreview starter direkte paa innholdet",
        "description": (
            "Build 1249 rydder mobilveggen ved aa skjule mobilappens logo-/topplinje og detaljhero inne i "
            "previewrammene. Mobilappen ute paa nett er uendret; dette gjelder bare intern desktop-preview."
        ),
        "applications": [
            "Fibaro10 backend (main.py): justerer preview-CSS som injiseres i mobilrammene.",
            "Buildlogg (build_log.py): registrerer build 1249.",
        ],
        "request": "Ta bort logoen og alt over i mobilpreviewen fordi det ikke gir verdi.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Logo-/topplinjen i mobilrammene skjules.",
            "Detaljheroen inne i mobilskjermene skjules.",
            "Rammene starter tettere paa faktisk innhold.",
        ],
    },
    {
        "version": "1",
        "build": "1248",
        "date": "26.06.2026",
        "headline": "Mobilveggen i desktop",
        "title": "Ny hovedmeny Mobil viser live skjermbilder fra mobilappen",
        "description": (
            "Build 1248 legger inn hovedmenyen Mobil i desktop-appen. Siden viser alle sentrale mobilskjermer som "
            "kompakte live-forhåndsvisninger i et rutenett, bygget med samme HTML/CSS og renderfunksjoner som "
            "online_dashboard. Dermed følger visningen endringer i mobilappen uten å kopiere kortlogikken inn i desktop."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger skjermregister og interne preview-endepunkter for mobilrutene.",
            "Fibaro10 frontend (MobileOverviewPage.tsx): ny ruteside med live iframe-rutenett og auto-refresh.",
            "Fibaro10 frontend (App.tsx/moduleViews.ts): legger Mobil inn som eget hovedmenypunkt.",
            "Fibaro10 frontend CSS (mobile-preview.css/tokens.css): kompakt telefonrutenett og egen mobilfarge.",
            "Buildlogg (build_log.py): registrerer build 1248.",
        ],
        "request": "Legg alle skjermbildene fra mobilappen under egen hovedmeny Mobil i et smart rutesystem, og hold dem oppdatert mot mobilappen.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Ny hovedmeny Mobil med ruten Mobil > Oversikt.",
            "Forside, soling, parkering, omsetning, ukediagram, energi, temperatur, lys og ventilasjon vises som live mobilrammer.",
            "Previewene bruker mobilappens eksisterende renderkode og oppdateres automatisk.",
        ],
    },
    {
        "version": "1",
        "build": "1247",
        "date": "23.06.2026",
        "headline": "UniFi-video paa parkeringslisten",
        "title": "Parkering > Parkeringer faar Protect-lenker paa start og slutt",
        "description": (
            "Build 1247 legger UniFi Protect-videoikon inn paa Parkering > Parkeringer. Denne listen bruker et kortere "
            "oppslagspunkt med ett minutt foer start eller slutt, mens bilsiden fortsatt bruker to minutter foer."
        ),
        "applications": [
            "Fibaro10 backend (main.py): gjoer Protect-forhaandssekunder konfigurerbart per API-rad.",
            "Fibaro10 backend (main.py): bruker 60 sekunder foer paa Parkering > Parkeringer.",
            "Fibaro10 frontend (ModulePage.tsx): viser videoknapp ved start/slutt i generiske modultabeller.",
            "Tester (tests/test_unifi_protect_links.py): dekker baade 2 min og 1 min foer.",
            "Buildlogg (build_log.py): registrerer build 1247.",
        ],
        "request": "Legg UniFi-lenker inn paa Parkering > Parkeringer, men med 1 minutt foer.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Parkering > Parkeringer viser videoikon ved Start og Slutt.",
            "Lenkene paa denne siden aapner ett minutt foer hendelsen og fem minutter etter.",
            "Eksisterende bilside beholder to minutter foer hendelsen.",
        ],
    },
    {
        "version": "1",
        "build": "1246",
        "date": "23.06.2026",
        "headline": "UniFi-lenker starter tidligere",
        "title": "Protect-lenker paa parkering hopper til starten av videovinduet",
        "description": (
            "Build 1246 retter UniFi Protect-lenkene paa parkeringer slik at klikket aapner to minutter foer "
            "start- eller sluttidspunktet. Selve videovinduet er fortsatt fra to minutter foer til fem minutter etter "
            "hendelsen."
        ),
        "applications": [
            "Fibaro10 backend (main.py): setter Protect time-parameteren til vindustart i stedet for hendelsestidspunkt.",
            "Tester (tests/test_unifi_protect_links.py): verifiserer at time og start peker paa to minutter foer.",
            "Buildlogg (build_log.py): registrerer build 1246.",
        ],
        "request": "UniFi-lenken aapnet ikke 2 min foer, men omtrent etter hendelsen.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Start- og sluttikonene aapner naa ved begynnelsen av videovinduet.",
            "URL-ene beholder samme kamera og samme 7-minutters visningsvindu.",
            "Regresjonstest dekker start, end og time-parametere.",
        ],
    },
    {
        "version": "1",
        "build": "1245",
        "date": "23.06.2026",
        "headline": "UniFi-video paa bilparkeringer",
        "title": "Parkering per kjoeretoey faar direkte Protect-lenker paa start og slutt",
        "description": (
            "Build 1245 legger direkte UniFi Protect-lenker paa start- og sluttidspunkt for alle parkeringer paa "
            "kjoeretoeysiden. Hver lenke aapner kameraet fra to minutter foer hendelsen til fem minutter etter, med "
            "avspilling satt til selve start- eller sluttidspunktet."
        ),
        "applications": [
            "Fibaro10 backend (main.py): bygger UniFi Protect timelapse-lenker for parkeringsstart og parkeringsslutt.",
            "Fibaro10 frontend (ParkingVehicleDetailPage.tsx): viser videoknapp ved Start og Slutt i parkeringstabellen.",
            "Tester (tests/test_unifi_protect_links.py): verifiserer tidsvinduet i Protect-lenken.",
            "Buildlogg (build_log.py): registrerer build 1245.",
        ],
        "request": "Legg UniFi Protect-lenke paa parkeringer for enkeltbil, fra 2 min foer til 5 min etter start og slutt.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Starttidspunkt har videoknapp som aapner Protect paa riktig kamera.",
            "Sluttidspunkt har tilsvarende videoknapp naar sluttid finnes.",
            "Kamera og console er konfigurerbare via env, med default fra oppgitt UniFi-lenke.",
        ],
    },
    {
        "version": "1",
        "build": "1244",
        "date": "23.06.2026",
        "headline": "Solsengforbruk cachet kort",
        "title": "Energi > Forbruk per seng gjenbruker tung analyse i tre minutter",
        "description": (
            "Build 1244 legger kort cache på den tunge leseanalysen for estimert solsengforbruk. Siden bygger samme "
            "beregning som før, men gjentatte åpninger av samme periode slipper å lese og analysere alle energisamples "
            "og soltimer på nytt."
        ),
        "applications": [
            "Fibaro10 backend (main.py): tre minutters cache for load_sunbed_power_analysis.",
            "Buildlogg (build_log.py): registrerer build 1244.",
        ],
        "request": "Soerg for at alt er perfekt. Reduser gjenværende trege sider etter bred modulsmoke.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Energi > Forbruk per seng returnerer cachet analyse for samme datoperiode.",
            "Cache gjelder bare visningspayload og endrer ikke logging, import eller beregning.",
            "Gjentatte sidevisninger blir vesentlig raskere.",
        ],
    },
    {
        "version": "1",
        "build": "1243",
        "date": "23.06.2026",
        "headline": "Prognosehistorikk forberedes én gang",
        "title": "Kald prognoseberegning bruker ferdigindeksert historikk",
        "description": (
            "Build 1243 fortsetter ytelsesarbeidet fra build 1242. Historiske prognoseverdier for soling og parkering "
            "normaliseres nå til en lett intern struktur før dagmodellene kjøres. Dermed slipper hver prognosedag aa "
            "slaa opp de samme dato-, helligdag- og omsetningsverdiene gjentatte ganger."
        ),
        "applications": [
            "Fibaro10 backend (main.py): ferdigindeksert historikk for solprognose.",
            "Fibaro10 backend (main.py): ferdigindeksert historikk for parkeringsprognose.",
            "Fibaro10 backend (main.py): felles konstante sesongvekter i prognoseberegning.",
            "Buildlogg (build_log.py): registrerer build 1243.",
        ],
        "request": "Soerg for at alt er perfekt. Fortsett aa forbedre hastighet og struktur uten aa endre prognoselogikk.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Historikkverdier pakkes én gang foer prognosedagene regnes ut.",
            "Dagmodellene unngaar gjentatte dict-oppslag og datooperasjoner i innerloekken.",
            "Samme vekter, tempo og sammenligningsgrunnlag beholdes.",
        ],
    },
    {
        "version": "1",
        "build": "1242",
        "date": "23.06.2026",
        "headline": "Prognoser beregnes raskere",
        "title": "Parkering og soling faar lettere prognosemodell og mindre dobbelarbeid",
        "description": (
            "Build 1242 optimaliserer de siste tydelige treghetene fra bred modulsmoke. Prognoseberegningen bruker "
            "samme vektlogikk som foer, men summerer alle noekkeltall i én passering per historisk dag og gjenbruker "
            "modellverdier for samme prognosedag. Lagrede prognoser beregner ogsaa faktisk resultat bare én gang per "
            "unik periode i stedet for aa gjoere samme databasekall flere ganger."
        ),
        "applications": [
            "Fibaro10 backend (main.py): raskere dagmodell for soling og parkering.",
            "Fibaro10 backend (main.py): intern prognosecache per dag i samme API-kall.",
            "Fibaro10 backend (main.py): dedupliserer faktisk resultat i lagrede prognosetabeller.",
            "Buildlogg (build_log.py): registrerer build 1242.",
        ],
        "request": "Soerg for at alt er perfekt. Gaa igjennom hele appen, sjekk funksjonalitet, logiske brister, fiks hastighet.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoering",
        "changes": [
            "Kald prognoseberegning bruker mindre CPU uten endret beregningsgrunnlag.",
            "Parkering og soling gjenbruker modell for samme dato innen ett prognosekall.",
            "Lagrede prognoser slipper gjentatte identiske actual-spoerringer.",
            "Endringen er verifisert med enhetstester foer deploy.",
        ],
    },
    {
        "version": "1",
        "build": "1241",
        "date": "22.06.2026",
        "headline": "Energiregistre slipper dagsgraf-payload",
        "title": "Energi > Kurser, Laster og Verktøy får egne lette API-stier",
        "description": (
            "Build 1241 rydder videre etter bred modulsmoke. Energisidene for kurser, laster og verktøy brukte ikke "
            "døgnchartet, men fikk likevel med full dagsgraf og energisample-tabell i API-responsen. Disse sidene "
            "returnerer nå bare registerdata og relevante kort."
        ),
        "applications": [
            "Fibaro10 backend (main.py): tidlige retur-stier for Energi > Kurser, Laster og Verktøy.",
            "Buildlogg (build_log.py): registrerer build 1241.",
        ],
        "request": "Gå igjennom hele appen, sjekk funksjonalitet, logiske brister, fiks hastighet og sørg for at alt er perfekt.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Energi > Kurser returnerer ikke lenger energidøgnchart.",
            "Energi > Laster returnerer ikke lenger energidøgnchart.",
            "Energi > Verktøy returnerer ikke lenger energidøgnchart.",
            "Registersidene beholder kort, filtre og redigerbare tabeller.",
        ],
    },
    {
        "version": "1",
        "build": "1240",
        "date": "22.06.2026",
        "headline": "Yr-logg får smal API-payload",
        "title": "Ventilasjon > Yr logg sender ikke lenger rå Yr-json i tabellrader",
        "description": (
            "Build 1240 følger opp audit av tunge API-kall. Yr-tabellen viste bare et lite sett kolonner, men "
            "backend sendte hele Yr-raden inkludert rå JSON for hver rad. Responsen er nå begrenset til de synlige "
            "kolonnene i tabellen."
        ),
        "applications": [
            "Fibaro10 backend (main.py): ny YR_LOG_TABLE_COLUMNS og smalere tabellpayload for Ventilasjon > Yr logg.",
            "Buildlogg (build_log.py): registrerer build 1240.",
        ],
        "request": "Gå igjennom hele appen, sjekk funksjonalitet, logiske brister, fiks hastighet og sørg for at alt er perfekt.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Yr-tabellen returnerer bare synlige kolonner.",
            "Skjulte felt som raw og extra sendes ikke lenger til V2 for denne tabellen.",
            "Payloaden for Ventilasjon > Yr logg blir vesentlig mindre uten funksjonelt tap.",
        ],
    },
    {
        "version": "1",
        "build": "1239",
        "date": "22.06.2026",
        "headline": "Audit fikser tunge API-kall",
        "title": "Energi og ventilasjon laster bare data som sidene faktisk bruker",
        "description": (
            "Build 1239 retter en konkret ytelsesfeil i beregningen av solsengforbruk og rydder datalasting i "
            "ventilasjonsmodulen. Energi > Forbruk per seng unngår nå tunge standardsvar fra energimodulen, og "
            "ventilasjonsundersider henter ikke lenger Yr, temperatur, hendelser og dagsgrafgrunnlag samtidig."
        ),
        "applications": [
            "Fibaro10 backend (main.py): binærsøk for nærmeste ventilasjonssample i solsengforbruksberegningen.",
            "Fibaro10 backend (main.py): tidlig, spesialisert payload for Energi > Forbruk per seng.",
            "Fibaro10 backend (main.py): selektiv datalasting for Ventilasjon > Dagslogg, Temp logg, Yr logg og Hendelser.",
            "Buildlogg (build_log.py): registrerer build 1239.",
        ],
        "request": "Gå igjennom hele appen, sjekk funksjonalitet, logiske brister, fiks hastighet og sørg for at alt er perfekt.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Solsengforbruksanalyse matcher takvifte-status med tidsindeks i stedet for lineært søk per energisample.",
            "Energi > Forbruk per seng returnerer bare kort, filter og energySunbeds-data.",
            "Ventilasjon > Yr logg slipper full dagslogg-payload.",
            "Ventilasjon > Temp logg og Hendelser henter bare relevant tabellgrunnlag.",
            "Automatiserte tester, frontend-build, UI-smoke og CSS-audit er kjørt før deploy.",
        ],
    },
    {
        "version": "1",
        "build": "1238",
        "date": "22.06.2026",
        "headline": "Omsetning får samlet oppgjørsavstemming",
        "title": "Omsetning > Oversikt viser Fibaro10 mot parkerings- og solingsoppgjør",
        "description": (
            "Build 1238 legger en samlet avstemmingstabell på Omsetning > Oversikt. Tabellen viser måned for måned "
            "Fibaro10-tall for parkering og soling ved siden av importerte oppgjørstall, med avvik og status."
        ),
        "applications": [
            "Fibaro10 backend (main.py): ny samlet avstemmingsrad per oppgjørsperiode.",
            "Desktop V2 tabeller (src/pages/ModulePage.tsx): lesbare kolonnenavn og statusmerking for kontrollkolonner.",
        ],
        "request": "På omsetning ønskes en forståelig tabell med parkering, oppgjør parkering, sol og oppgjør sol.",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Omsetning > Oversikt får tabellen Oppgjør mot Fibaro10.",
            "Parkering vises som Fibaro10 eks. mva mot oppgjør parkering eks. mva.",
            "Soling vises som Fibaro10 eks. mva mot oppgjør soling eks. mva.",
            "Avvik og status beregnes separat for parkering, soling og totalsum.",
        ],
    },
    {
        "version": "1",
        "build": "1237",
        "date": "22.06.2026",
        "headline": "Inline bildeviser blar videre i arkivet",
        "title": "Soling > Enkelttimer kan bla forbi lagrede fem bilder uten å bytte flate",
        "description": (
            "Build 1237 gjør bildeviseren på soltimen mer direkte: forrige/neste går videre inn i Axis-arkivet når "
            "brukeren blar ut av de fem lagrede bildene. Når et arkivbilde settes som hovedbilde, lagres en ny "
            "fem-bilders pakke rundt valgt bilde automatisk."
        ),
        "applications": [
            "Desktop V2 enkelttimer (src/pages/ModulePage.tsx): inline-viseren kan bla fra lagrede bilder og videre i arkivet.",
            "Desktop V2 API-typer (src/api.ts): lagring av valgt snapshot returnerer bildearkiv-payload.",
            "Desktop V2 styling (src/styles/module-content.css): faste knappebredder og loadingindikator i samme bildeflate.",
        ],
        "request": "Bla automatisk videre i bildearkivet når man blar ut fra de fem lagrede bildene, og lagre ny fem-bilders pakke når man trykker sett som hovedbilde.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Forrige/neste i soltimen går videre til eldre/nyere Axis-bilder når lagret pakke passeres.",
            "Samme bildepanel brukes for både lagrede bilder og arkivbilder.",
            "Sett som hovedbilde lagrer ny pakke på fem bilder rundt valgt snapshot.",
            "Knapper holder fast bredde og flytter seg ikke under blaing eller lagring.",
        ],
    },
    {
        "version": "1",
        "build": "1236",
        "date": "22.06.2026",
        "headline": "Bildearkiv lagrer fem bilder uten hopp",
        "title": "Soling > Enkelttimer lagrer valgt bildepakke fra arkivet",
        "description": (
            "Build 1236 endrer manuell lagring i bildearkivet slik at valgt arkivbilde blir midtpunktet i en ny "
            "fem-bilders pakke. Modalflaten beholdes åpen, og knappene har stabil plassering under blaing og lagring."
        ),
        "applications": [
            "Fibaro10 backend (main.py): lagrer to bilder før, valgt hovedbilde og to bilder etter ved manuell arkivlagring.",
            "Desktop V2 enkelttimer (src/pages/ModulePage.tsx): fast lagreknapp og ingen modal-lukking ved lagring.",
            "Desktop V2 styling (src/styles/module-content.css): faste knappebredder i bildearkivet.",
            "Tester (tests/test_sun2_axis_snapshots.py): dekker fem-bilders serie rundt valgt arkivbilde.",
        ],
        "request": "Ikke skift grensesnittflate ved eldre bilder; lagre fem aktuelle bilder, og ikke la knapper bytte plass eller hoppe ut ved lagring.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Valgt arkivbilde lagres som hovedbilde.",
            "To arkivbilder før og to etter lagres sammen med hovedbildet.",
            "Eksisterende bildepakke på posten erstattes samlet.",
            "Modalen blir stående åpen etter lagring.",
            "Footer-knapper har stabil tekst og bredde.",
        ],
    },
    {
        "version": "1",
        "build": "1235",
        "date": "22.06.2026",
        "headline": "Enkelttimer får hurtigsti",
        "title": "Soling > Enkelttimer slipper tunge oversiktsberegninger",
        "description": (
            "Build 1235 gjør Soling > Enkelttimer til en egen hurtigsti i API-et. Siden bygger nå bare filter, "
            "enkelttime-tabell og bildemetadata, i stedet for å regne ut oversikt, statistikk, senger og medlemmer først."
        ),
        "applications": [
            "Fibaro10 backend (main.py): ny sun2_sessions_module_payload og tidlig retur for view=enkeltimer.",
            "Buildlogg (build_log.py): registrerer build 1235.",
        ],
        "request": "Gjør hele bildeopplegget og soling/enkelttimer raskere og mer funksjonelt.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Enkelttimer henter ikke lenger unødvendige oversiktsgrafer før listen vises.",
            "Filter, treffkort og bildemetadata bygges direkte for enkelttimevisningen.",
        ],
    },
    {
        "version": "1",
        "build": "1234",
        "date": "22.06.2026",
        "headline": "Raskere bildearkiv for soltimer",
        "title": "Soling > Enkelttimer og bildearkiv optimaliseres",
        "description": (
            "Build 1234 optimaliserer bildeopplegget for soltimer. Axis-arkivet indekseres per dag med cache i stedet "
            "for å skanne hele snapshot-arkivet ved hvert bildearkivkall, og enkelttime-listen henter bare bildemetadata."
        ),
        "applications": [
            "Fibaro10 backend (main.py): dagbasert Axis-cache, avgrenset arkivsøk og lettere bilde-metadata-spørringer.",
            "Desktop V2 enkelttimer (src/pages/ModulePage.tsx): detaljrader rendres først når de åpnes.",
            "Desktop V2 styling (src/styles/module-content.css): bedre loading-overlegg i bildearkivet.",
            "Desktop V2 API-typer (src/api.ts): legger til arkivdag i bildearkivresponsen.",
            "Tester (tests/test_sun2_axis_snapshots.py): dekker tidsavgrenset Axis-kandidatsøk.",
        ],
        "request": "Soling/enkelttimer, bildearkiv og hele bildeopplegget er veldig tregt og lite funksjonelt.",
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Bildearkivet skanner ikke lenger alle Axis-bilder ved hvert kall.",
            "Periodisk bildekobling bruker bare relevant tidsrom i stedet for hele arkivet.",
            "Enkelttime-listen unngår å hente JPEG-bytes for alle viste rader.",
            "Skjulte enkelttime-detaljer bygges ikke før raden åpnes.",
            "Bildearkivet beholder gjeldende bilde synlig mens neste/forrige bilde lastes.",
        ],
    },
    {
        "version": "1",
        "build": "1233",
        "date": "19.06.2026",
        "headline": "Produktsalg per dag viser hele måneden",
        "title": "Soling > Produkter fyller daggrafen med alle dager i måneden",
        "description": (
            "Build 1233 endrer daggrafen for produktsalg slik at den viser hele måneden, ikke bare dager med salg "
            "eller siste 120 dager. Uten datofilter brukes inneværende måned. Ved datofilter brukes måneden til valgt dato."
        ),
        "applications": [
            "Fibaro10 backend (main.py): bygger dagserie med en rad per kalenderdag i valgt måned.",
            "Buildlogg (build_log.py): registrerer build 1233.",
        ],
        "request": "Produktsalg pr dag så bør vi jo vise alle dager inneværende mnd?",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Produktsalg per dag viser alle dager i måneden.",
            "Dager uten salg vises som 0.",
            "Fremtidige dager i inneværende måned vises uten verdi, slik at aksen likevel er komplett.",
            "Graftekst er oppdatert fra siste 120 dager til valgt måned.",
        ],
    },
    {
        "version": "1",
        "build": "1232",
        "date": "19.06.2026",
        "headline": "Produktsiden valideres mot PostgreSQL",
        "title": "Soling > Produkter retter gruppering av topp produkter",
        "description": (
            "Build 1232 retter en PostgreSQL-spesifikk grupperingsfeil i topp-produkter-tabellen på Soling > Produkter. "
            "Feilen ble fanget ved intern container-test mot QNAP-databasen etter deploy av build 1231."
        ),
        "applications": [
            "Fibaro10 backend (main.py): bruker samme SQL-uttrykk i SELECT og GROUP BY for produktnavn/kategori.",
            "Buildlogg (build_log.py): registrerer build 1232.",
        ],
        "request": "Rett valideringsfeilen på den nye produktsiden under Soling.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Retter PostgreSQL GROUP BY for Topp produkter.",
            "Validerer produktsalg-payload direkte inne i QNAP-containeren.",
        ],
    },
    {
        "version": "1",
        "build": "1231",
        "date": "19.06.2026",
        "headline": "Produktsalg inn under Soling",
        "title": "Soling > Produkter viser Sun2 produktsalg og kontrollgrunnlag",
        "description": (
            "Build 1231 legger produktsalg inn som egen underside under Soling. Siden viser daglige produktlinjer, "
            "månedsgrunnlag, topp produkter og kort for i dag, måned og år. Månedsgrunnlaget bruker månedsimport "
            "der den finnes og daglige linjer som fallback, slik at kontrollgrunnlaget ikke dobbelttelles."
        ),
        "applications": [
            "Fibaro10 backend (main.py): ny Soling > Produkter payload med kort, grafer, filtre og tabeller for sun2_product_sales.",
            "Desktop V2 meny (src/moduleViews.ts): legger Produkter inn under Soling.",
            "Desktop V2 tabeller (src/pages/ModulePage.tsx): legger lesbare norske labels for produktsalgskolonner.",
            "Desktop V2 hurtiglenker (src/domainModel.ts): peker produktrelaterte solingkort til den nye siden.",
            "Buildlogg (build_log.py): registrerer build 1231.",
        ],
        "request": "Jeg vil ha inn produkter under soling.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Nytt menyvalg Soling > Produkter.",
            "Kort for produktsalg i dag, måned og år.",
            "Graf for daglig produktsalg siste 120 dager.",
            "Graf og tabell for månedsgrunnlag.",
            "Filtre for søk, dato, kategori, betaling, grunnlag og antall rader.",
            "Daglige linjer er standard for å unngå dobbelttelling mot månedsimport.",
        ],
    },
    {
        "version": "1",
        "build": "1230",
        "date": "19.06.2026",
        "headline": "Omsetning faar akkumulert aarsammenligning",
        "title": "Omsetning > Akkumulert aar viser aarsvis omsetning uten antallvalg",
        "description": (
            "Build 1230 legger en dedikert aarsammenligning under Omsetning. Siden viser akkumulert "
            "omsetning aar mot aar, bruker samlet daglig omsetning fra soling og parkering, og holder "
            "seg til omsetning uten antall-toggle."
        ),
        "applications": [
            "Fibaro10 backend (main.py): nytt API for omsetning aarsammenligning basert paa samlet daglig omsetning.",
            "Desktop V2 API-typer (src/api.ts): legger til fetcher og typealiaser for omsetning aarsammenligning.",
            "Desktop V2 side (src/pages/RevenueYearComparisonPage.tsx): ny akkumulert omsetningsgraf med aarvelger.",
            "Desktop V2 ruting og hurtiglenker (src/App.tsx, src/domainModel.ts): kobler Omsetning > Akkumulert aar til den nye siden.",
            "Buildlogg (build_log.py): registrerer build 1230.",
        ],
        "request": "Lag aarsammenligning paa omsetning paa samme maate som soling og parkering, men kun med omsetning og ikke antall.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny backendrespons for samlet omsetning per aar.",
            "Standard aktiv graf er valgt aar og forrige aar.",
            "Alle tilgjengelige aar kan slaas paa manuelt.",
            "Siden viser bare kronebelop og har ikke antall-valg.",
            "Eksisterende menyvalg Omsetning > Akkumulert aar bruker den nye siden.",
        ],
    },
    {
        "version": "1",
        "build": "1229",
        "date": "19.06.2026",
        "headline": "Aarsgrafer kan vise alle aar",
        "title": "Soling og parkering aarsammenligning kan sammenligne alle tilgjengelige aar",
        "description": (
            "Build 1229 utvider Soling > Sammenligning og Parkering > Sammenligning med valg for hvilke aar som "
            "skal vises i grafen. Standardvisningen er fortsatt siste/valgt aar og forrige aar, mens alle andre "
            "tilgjengelige aar kan slaas paa manuelt eller aktiveres med Alle aar-knappen."
        ),
        "applications": [
            "Fibaro10 backend (main.py): aarsammenlignings-API-ene returnerer alle tilgjengelige aar og komplette aarsserier.",
            "Desktop V2 API-typer (src/api.ts): utvider aarsammenligningsresponsen med availableYears og series.",
            "Desktop V2 soling (src/pages/SunYearComparisonPage.tsx): legger til aarvelger og fler-serie graf.",
            "Desktop V2 parkering (src/pages/ParkingYearComparisonPage.tsx): legger til aarvelger og fler-serie graf.",
            "Desktop V2 CSS (src/styles/status.css): styler aarvelgeren i grafkortet.",
            "Buildlogg (build_log.py): registrerer build 1229.",
        ],
        "request": "Paa baade soling og parkering skal det vaere mulig aa sammenligne alle aar, men bare siste aar og fjoraar skal vaere aktive naar siden aapnes.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Alle tilgjengelige aar leveres til frontend for soling og parkering.",
            "Standard aktivt utvalg er valgt aar og forrige aar.",
            "Brukeren kan slaa paa enkelt-aar med avkryssing.",
            "Alle aar-knapp aktiverer alle tilgjengelige aar.",
            "Standard-knapp tilbakestiller til valgt aar og forrige aar.",
        ],
    },
    {
        "version": "1",
        "build": "1228",
        "date": "19.06.2026",
        "headline": "Parkering faar akkumulert aarsammenligning",
        "title": "Ny Parkering > Sammenligning viser akkumulert utvikling aar mot aar",
        "description": (
            "Build 1228 legger til samme type aarsvis sammenligning for parkering som allerede finnes for soling. "
            "Siden bruker dagssammendrag fra parkering, viser akkumulert parkeringsbelop eller antall parkeringer "
            "gjennom valgt aar, og sammenligner mot forrige aar. For innevaerende aar sammenlignes hovedtallene mot "
            "forrige aar til samme dagnummer, mens grafen viser hele forrige aar som kontekst."
        ),
        "applications": [
            "Fibaro10 backend (main.py): nytt API for parkering aarsammenligning basert paa parkeringsdager.",
            "Desktop V2 API-typer (src/api.ts): legger til fetcher og typealiaser for parkering aarsammenligning.",
            "Desktop V2 side (src/pages/ParkingYearComparisonPage.tsx): ny akkumulert graf med aar-navigasjon og belop/antall-valg.",
            "Desktop V2 ruting og meny (src/App.tsx, src/moduleViews.ts): legger siden under Parkering > Sammenligning.",
            "Desktop V2 hurtigsoek (src/domainModel.ts): peker parkering/sammenligning til ny side.",
            "Buildlogg (build_log.py): registrerer build 1228.",
        ],
        "request": "Gjor det samme for parkering som for soling: akkumulert aarsgraf med sammenligning aar mot aar.",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny underside Parkering > Sammenligning.",
            "Valgt aar kan blas ett aar frem og tilbake.",
            "Grafen kan skifte mellom parkeringsbelop og antall parkeringer.",
            "Kortene viser valgt aar, forrige aar til samme dagnummer og forrige aar totalt.",
            "Sammenligningen bruker dagssammendrag for rask respons.",
        ],
    },
    {
        "version": "1",
        "build": "1227",
        "date": "18.06.2026",
        "headline": "Soling faar akkumulert aarsammenligning",
        "title": "Ny Soling > Sammenligning viser akkumulert utvikling aar mot aar",
        "description": (
            "Build 1227 legger til en egen sammenligningsside under Soling. Siden bruker dagssammendrag for aa "
            "vise akkumulert solomsetning eller antall solinger gjennom valgt aar, sammenlignet med forrige aar. "
            "For innevaerende aar sammenlignes hovedtallene mot forrige aar til samme dagnummer, mens grafen viser "
            "hele forrige aar som kontekst."
        ),
        "applications": [
            "Fibaro10 backend (main.py): nytt API for soling aarsammenligning basert paa dagssammendrag.",
            "Desktop V2 API-typer (src/api.ts): legger til respons-typer og fetcher for soling aarsammenligning.",
            "Desktop V2 side (src/pages/SunYearComparisonPage.tsx): ny akkumulert graf med aar-navigasjon og omsetning/antall-valg.",
            "Desktop V2 ruting og meny (src/App.tsx, src/moduleViews.ts): legger siden under Soling > Sammenligning.",
            "Desktop V2 hurtigsoek (src/domainModel.ts): peker soling/sammenligning til ny side.",
            "Buildlogg (build_log.py): registrerer build 1227.",
        ],
        "request": "Lag samme type akkumulert sammenligningsgraf under Soling som Omsetning > Sammenligning, men med sammenligning av aar i stedet for maaned.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny underside Soling > Sammenligning.",
            "Valgt aar kan blas ett aar frem og tilbake.",
            "Grafen kan skifte mellom omsetning og antall solinger.",
            "Kortene viser valgt aar, forrige aar til samme dagnummer og forrige aar totalt.",
            "Sammenligningen bruker dagssammendrag for rask respons.",
        ],
    },
    {
        "version": "1",
        "build": "1226",
        "date": "16.06.2026",
        "headline": "I dag viser sol og parkering separat",
        "title": "Omsetning oversikt viser separat soling og parkering paa I dag-kortet",
        "description": (
            "Build 1226 retter I dag-kortet paa Omsetning > Oversikt slik at detaljlinjen viser soling og "
            "parkering som separate belop. Kortet viser fortsatt totalomsetningen som hovedtall, men underteksten "
            "folger naa samme fordeling som uke-, maaned- og aarskortene."
        ),
        "applications": [
            "Fibaro10 backend (main.py): endrer detaljlinjen paa I dag-kortet for omsetning.",
            "Buildlogg (build_log.py): registrerer build 1226.",
        ],
        "request": "Paa I dag-kortet i Omsetning > Oversikt skal tall for parkering og soling vises separat.",
        "work_duration": "ca. 5 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "I dag-kortet viser total omsetning som hovedtall.",
            "Detaljlinjen viser naa Sol X kr og parkering Y kr separat.",
        ],
    },
    {
        "version": "1",
        "build": "1225",
        "date": "16.06.2026",
        "headline": "Omsetning oversikt viser relevante aarstall",
        "title": "Omsetning oversikt erstatter historiske totalfliser med innevaerende aar",
        "description": (
            "Build 1225 rydder toppflisene paa Omsetning > Oversikt. All-time totalene er fjernet fordi "
            "datagrunnlaget ikke er komplett like langt tilbake for soling og parkering. Siden viser naa foerst "
            "i dag, uke og maaned, og deretter innevaerende aar samlet med fordeling paa soling og parkering."
        ),
        "applications": [
            "Fibaro10 backend (main.py): bygger aarsgrunnlag for samlet omsetning fra soling og parkering.",
            "Fibaro10 backend (main.py): erstatter all-time kort med I aar, Soling i aar og Parkering i aar.",
            "Buildlogg (build_log.py): registrerer build 1225.",
        ],
        "request": "Paa Omsetning > Oversikt skal Sum omsetning, Soling totalt og Parkering totalt fjernes. Vis i stedet dette aar, soling i aar og parkering i aar, plassert etter I dag, Uke og Maaned.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Historiske totalfliser er fjernet fra Omsetning > Oversikt.",
            "Nye aarsfliser bruker bare innevaerende aar.",
            "Aarskortet viser fordeling mellom soling og parkering.",
            "Kortenes rekkefolge prioriterer dag, uke og maaned foer aarstall.",
        ],
    },
    {
        "version": "1",
        "build": "1224",
        "date": "16.06.2026",
        "headline": "Riktig dagsnitt for paagaaende maaned",
        "title": "Omsetning maanedsoversikt beregner snitt per dag bare til og med aktuell dag",
        "description": (
            "Build 1224 retter dagsnittet paa Omsetning > Maanedsoversikt. For innevaerende maaned deles "
            "maanedssummen bare paa dager til og med i dag, mens avsluttede maaneder fortsatt bruker alle "
            "dagene i maaneden. Backend sender naa ferdig beregnet snitt og daggrunnlag til frontend."
        ),
        "applications": [
            "Fibaro10 backend (main.py): beregner average_per_day og average_day_count i felles maanedscontext.",
            "Fibaro10 klassisk statusrute (main.py): bruker samme felles maanedscontext for aa unngaa duplisert logikk.",
            "Desktop V2 omsetning (src/pages/RevenueMonthPage.tsx): viser backend-beregnet snitt og antall dager i grunnlaget.",
            "API-typer (src/api.ts): utvider maanedssammendrag med averagePerDay og averageDayCount.",
            "Buildlogg (build_log.py): registrerer build 1224.",
        ],
        "request": "Paa Omsetning/Maanedsoversikt er Snitt per dag feil naar maaneden ikke er ferdig; snittet maa bare regnes til og med aktuell dag.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Innevaerende maaned bruker antall dager til og med i dag som divisor.",
            "Historiske maaneder bruker hele maaneden som divisor.",
            "Frontend viser antall dager som snittet bygger paa.",
            "Klassisk statusrute bruker samme maanedsgrunnlag som ny frontend.",
        ],
    },
    {
        "version": "1",
        "build": "1223",
        "date": "16.06.2026",
        "headline": "Parkeringer viser valgt dag og bilhistorikk",
        "title": "Parkeringer-listen starter paa dagens dato og viser tidligere bruk per bil",
        "description": (
            "Build 1223 rydder Parkering > Parkeringer. Siden bruker naa en kompakt dagvelger med forrige dag, "
            "i dag, neste dag og datofelt. De fire toppflisene er fjernet, og tabellen starter med status. "
            "Omraadefeltet fra EasyPark-listen er tatt bort, mens tidligere parkeringer og tidligere betalt belop "
            "per bil vises direkte i tabellen."
        ),
        "applications": [
            "Fibaro10 backend (main.py): bruker day-parameter for parkeringer, beregner tidligere parkeringer/belop per bil og rydder tabellkolonner.",
            "Desktop V2 modulside (src/pages/ModulePage.tsx): legger inn kompakt dagvelger og kolonnenavn for bilhistorikk.",
            "Desktop V2 modul-CSS (src/styles/module-content.css): styler dagvelgeren.",
            "API-typer (src/api.ts): utvider modulrespons med dayNavigation.",
            "Buildlogg (build_log.py): registrerer build 1223.",
        ],
        "request": "Paa parkering/parkeringer: fjern flisene, start paa dagens dato med forrige/neste dag-knapper, flytt status forst i tabellen, fjern Lilletorget-omraadefelt og vis hvor mange parkeringer/belop bilen har hatt for.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Parkeringer-siden starter paa dagens dato naar day ikke er satt.",
            "Dato styres med forrige dag, i dag, neste dag og datofelt.",
            "De fire toppflisene paa Parkeringer er fjernet.",
            "Status er forste tabellkolonne.",
            "Omraadekolonnen fra parkeringslisten er fjernet.",
            "Tabellen viser tidligere parkeringer og tidligere betalt belop per bil.",
        ],
    },
    {
        "version": "1",
        "build": "1222",
        "date": "16.06.2026",
        "headline": "Hovedmenyen kan skjules",
        "title": "Desktopgrensesnittet har faatt enkel skjul/vis-knapp for hovedmenyen",
        "description": (
            "Build 1222 legger til en liten knapp i toppbaren som skjuler eller viser hovedmenyen. Valget lagres "
            "lokalt i nettleseren, slik at arbeidsflaten kan holdes bredere uten aa endre menystruktur, ruting eller "
            "innhold paa sidene."
        ),
        "applications": [
            "Desktop V2 appskall (src/App.tsx): legger til skjul/vis-tilstand for hovedmenyen og lagrer valget lokalt.",
            "Desktop V2 layout-CSS (src/styles/layout.css): styler den nye menyknappen og skjult sidemeny.",
            "Buildlogg (build_log.py): registrerer build 1222.",
        ],
        "request": "Gjor saa hovedmenyen kan forsvinne om man vil og hentes tilbake paa en enkel maate, uten aa rote til noe.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny ikonknapp i toppbaren skjuler og viser hovedmenyen.",
            "Menyen kollapser helt bort naar den skjules.",
            "Valget lagres i localStorage per nettleser.",
            "Menyinnhold, ruter og eksisterende navigasjon er uendret.",
        ],
    },
    {
        "version": "1",
        "build": "1221",
        "date": "16.06.2026",
        "headline": "Sammenligningsgraf starter paa omsetning",
        "title": "Omsetning/sammenligning har renere grafheader og omsetning som standard",
        "description": (
            "Build 1221 fjerner den ekstra forklaringslegend-raden over grafen paa Omsetning > Sammenligning. "
            "Valget for grafmodus ligger naa alene helt til hoyre, og siden starter paa omsetning som standard. "
            "Antall kan fortsatt velges manuelt."
        ),
        "applications": [
            "Desktop V2 omsetningssammenligning (src/pages/StatusComparisonPage.tsx): endrer standard metric til omsetning og fjerner ekstra legend i grafheader.",
            "Desktop V2 status-CSS (src/styles/status.css): fjerner ubrukte legend-regler.",
            "Buildlogg (build_log.py): registrerer build 1221.",
        ],
        "request": "Paa Omsetning/Sammenligning skal 'valgt periode, sammenligning, samme dag forrige uke' bort fra grafens topplinje, knappene helt til hoyre, og default skal vaere omsetning.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Grafen starter paa omsetning naar URL-en ikke angir metric.",
            "Segmentert valg viser Omsetning og Antall.",
            "Den ekstra legend-raden i grafheaderen er fjernet.",
            "Ubrukte CSS-regler for den gamle legend-raden er fjernet.",
        ],
    },
    {
        "version": "1",
        "build": "1220",
        "date": "16.06.2026",
        "headline": "Sammenligning viser samme dag forrige uke",
        "title": "Omsetning/sammenligning erstatter differansekortet med ukereferanse",
        "description": (
            "Build 1220 rydder toppkortene paa Omsetning > Sammenligning. Det separate differansekortet er "
            "erstattet av et kort for samme dag forrige uke naar den referansen finnes. Differanser mot valgt "
            "periode vises direkte inne i sammenligningskortene for total, soling og parkering."
        ),
        "applications": [
            "Desktop V2 omsetningssammenligning (src/pages/StatusComparisonPage.tsx): bygger dynamisk kortrekke med valgt periode, aktiv sammenligning og samme dag forrige uke.",
            "Desktop V2 status-CSS (src/styles/status.css): legger til kompakt visning av differanser inne i sammenligningskortene.",
            "Buildlogg (build_log.py): registrerer build 1220.",
        ],
        "request": "Paa omsetning/sammenligning skal differansekortet endres til Samme dag forrige uke, med differanser inne paa de to sammenligningskortene.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Differanse vises ikke lenger som eget tredje kort.",
            "Samme dag forrige uke vises som eget kort naar API-et leverer referansen.",
            "Sammenligningskortene viser totaldifferanse mot valgt periode.",
            "Soling og parkering viser egne differanser i kr og antall.",
        ],
    },
    {
        "version": "1",
        "build": "1219",
        "date": "16.06.2026",
        "headline": "Dashboardtoppen er strammet opp",
        "title": "Status, lys og ventilasjon har faatt en roligere og mer presis toppseksjon",
        "description": (
            "Build 1219 rydder den oeverste delen av dashboardet. Den store datakilde-pillen er gjort om til "
            "kompakt metadata, mens lys og ventilasjon vises som faste statusrader med jevn kolonnebruk. "
            "Endringen er kun visuell og endrer ikke datagrunnlaget."
        ),
        "applications": [
            "Desktop V2 statusdashboard (src/pages/OverviewPage.tsx): legger til egen toppstruktur for statusstripene.",
            "Desktop V2 status-CSS (src/styles/status.css): strammer inn dashboard-toppen, metadatavisning og lys/ventilasjon-rader.",
            "Buildlogg (build_log.py): registrerer build 1219.",
        ],
        "request": "Rydd opp i dashboardtoppen. Skjermbildet viser at dette ikke er ryddig.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Datakildestatus og sist oppdatert er gjort om fra tung pillestil til kompakt toppmetadata.",
            "Lys og ventilasjon bruker faste rader med navn til venstre og status til hoyre.",
            "Spacing, tag-storrelser og borderbruk i toppkortet er redusert.",
            "Responsiv fallback samler toppseksjonen i en kolonne paa smalere skjermer.",
        ],
    },
    {
        "version": "1",
        "build": "1218",
        "date": "16.06.2026",
        "headline": "Dashboardet er ryddet visuelt",
        "title": "Statusoversikten har tydeligere seksjoner og roligere layout",
        "description": (
            "Build 1218 rydder dashboard/statusoversikten uten aa endre datagrunnlaget. Drift naa, omsetning, "
            "nokkeltall og oppfolging er delt i tydeligere soner. Lys og ventilasjon er samlet i ett kompakt "
            "driftskort, mens siste hendelser og datakilder ligger i en ren bunnseksjon."
        ),
        "applications": [
            "Desktop V2 statusdashboard (src/pages/OverviewPage.tsx): deler siden i statuskort, omsetningsseksjon, nokkeltall og oppfolging.",
            "Desktop V2 status-CSS (src/styles/status.css): legger til dashboard-spesifikke layoutregler for seksjoner, driftskort og bunnrutenett.",
            "Buildlogg (build_log.py): registrerer build 1218.",
        ],
        "request": "Rydd dashboard siden, den er litt rotete.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Status, siste oppdatering og datakildestatus er samlet i ett toppkort.",
            "Lys og ventilasjon vises side om side inne i samme driftsflate.",
            "Omsetningskortene har egen seksjonsoverskrift.",
            "Nokkeltall for energi, temperatur og vaer har egen seksjon.",
            "Siste hendelser og datakilder er samlet i et roligere tospaltet bunnfelt.",
        ],
    },
    {
        "version": "1",
        "build": "1217",
        "date": "16.06.2026",
        "headline": "Dagsgrafen starter klokken 06",
        "title": "Omsetning/sammenligning viser dagutvikling fra 06:00 til 00:00",
        "description": (
            "Build 1217 strammer inn dagvis omsetningssammenligning. Grafvinduet starter naa klokken 06:00 og "
            "slutter ved midnatt, slik at visningen bruker plassen paa den delen av dognet som faktisk er relevant "
            "for drift. Summeringskort og differansetall bruker fortsatt hele korrekt dataperiode."
        ),
        "applications": [
            "Backend status comparison API (main.py): dagvis grafvindu settes til 06:00-00:00.",
            "Backend status timeline lanes (main.py): soling og parkering i grafen klippes mot det nye grafvinduet.",
            "Buildlogg (build_log.py): registrerer build 1217.",
        ],
        "request": "Begrens grafen/visningen paa Omsetning > Sammenligning til aa starte kl 06 og slutte kl 00.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Dagvis grafakse gaar fra 06:00 til 00:00.",
            "Historiske sammenligningskurver fyller hele 06:00-00:00-vinduet.",
            "Dagens kurve stopper fortsatt ved siste tilgjengelige datatidspunkt.",
            "Toppkortene og kontrolltallene er uendret.",
        ],
    },
    {
        "version": "1",
        "build": "1216",
        "date": "16.06.2026",
        "headline": "Sammenligning viser hele dagen",
        "title": "Omsetning/sammenligning bruker full dagsakse i dagvis graf",
        "description": (
            "Build 1216 endrer grafgrunnlaget for Omsetning > Sammenligning. Dagvis sammenligning viser naa "
            "hele dognaksen selv om dagen ikke er ferdig. Summeringskortene bruker fortsatt korrekt datatidspunkt "
            "for soling og parkering, mens historiske kurver kan vise resten av dagen slik at utviklingen blir "
            "lettere aa lese."
        ),
        "applications": [
            "Backend status comparison API (main.py): skiller mellom summeringsperiode og grafperiode for dagvis sammenligning.",
            "Backend status timeline lanes (main.py): sender endLeft slik at frontend vet hvor langt hver kurve faktisk har datagrunnlag.",
            "Desktop V2 API-kontrakt (src/api.ts): utvider StatusComparisonLane med endLeft.",
            "Desktop V2 sammenligningsgraf (src/pages/StatusComparisonPage.tsx): stopper dagens kurve ved faktisk datadekning og lar historiske dagkurver fylle hele dagen.",
            "Buildlogg (build_log.py): registrerer build 1216.",
        ],
        "request": "Omsetning/sammenligning skal vise hele dagen selv om dagen ikke er over, slik at utviklingen videre kan sees.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Dagvis sammenligning har naa 24-timers akse.",
            "Historiske sammenligningskurver viser hele dagen.",
            "Dagens kurve stopper ved siste tilgjengelige datatidspunkt i stedet for aa flate ut til midnatt.",
            "Toppkortene og differansetallene er ikke endret og bruker fortsatt riktig datatidspunkt for sammenligning.",
        ],
    },
    {
        "version": "1",
        "build": "1215",
        "date": "16.06.2026",
        "headline": "CSS-eierskap er strammet inn",
        "title": "Visuelle overstyringer er flyttet fra patch-lag til riktige domene-filer",
        "description": (
            "Build 1215 rydder videre i frontend-CSS. visual-refresh.css er fjernet som eget sent overstyringslag. "
            "Globale Ant Design-kontroller ligger naa i layout.css, mens status, modulinnhold, tidslinjer, ventilasjon, "
            "energi og registertabeller eier sine egne visuelle justeringer. CSS-auditen rapporterer naa ogsaa hvor "
            "mange klasser som fortsatt er spredt over flere stilark."
        ),
        "applications": [
            "Desktop V2 layout (src/styles/layout.css): overtar global styling for Ant Design-knapper, input, select og datepicker.",
            "Desktop V2 modulinnhold (src/styles/module-content.css): overtar felles metrikkort, summary-kort og chart-toolbar-styling.",
            "Desktop V2 status (src/styles/status.css): overtar statusperioder, statusfliser, datakilder og sammenligningskort.",
            "Desktop V2 tidslinjer (src/styles/timelines.css): overtar sol- og parkeringslinjenes visuelle finpuss.",
            "Desktop V2 ventilasjon (src/styles/ventilation.css): overtar kompakt status, viftefelt og ventilasjonskort.",
            "Desktop V2 energi (src/styles/energy.css): overtar Elvia-kort, uploadflate og energitabeller.",
            "Desktop V2 register/tabeller (src/styles/records.css): overtar kjoretoyfelt, tabellflater og tom-/lastetilstander.",
            "Desktop V2 appstart (main.tsx): fjerner import av visual-refresh.css og laster modulinnhold for domene-stilene.",
            "Desktop V2 verktøy (scripts/audit-css.mjs): legger til crossFileClassSelectors for aa finne klasser som fortsatt krysser filgrenser.",
            "Buildlogg (build_log.py): registrerer build 1215.",
        ],
        "request": "Gjor videre endringer som du mener er best. Alt skal vaere saa strukturert og effektivt som mulig.",
        "work_duration": "ca. 40 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "visual-refresh.css er fjernet.",
            "CSS-regler ligger naa naermere domenet eller felleskomponenten som faktisk bruker dem.",
            "CSS-audit viser fortsatt 0 mulige ubrukte klasser.",
            "Ny audit-verdi viser 42 klasser som krysser CSS-filgrenser. De fleste er bevisste globale tone-/statusklasser eller responsive regler.",
            "Produksjons-CSS gzip er litt mindre enn forrige build selv om kildekoden er mer eksplisitt.",
        ],
    },
    {
        "version": "1",
        "build": "1214",
        "date": "16.06.2026",
        "headline": "CSS er delt etter funksjonsomraade",
        "title": "Den gamle samlefila er erstattet med domenevise stilark",
        "description": (
            "Build 1214 strukturerer frontend-CSS videre. Den store styles.css-fila er delt i tydelige filer for "
            "status, modulinnhold, tidslinjer, ventilasjon, energi, register/oppgjor og responsive regler. "
            "Appstarten importerer filene i en eksplisitt rekkefolge, og CSS-auditen leser naa alle stilarkene i "
            "styles-mappen."
        ),
        "applications": [
            "Desktop V2 CSS (src/styles/status.css): statusoversikt, perioder og sammenligningssider.",
            "Desktop V2 CSS (src/styles/module-content.css): felles modulinnhold, metrikkort, tabellflater, bildelister og modulfilter.",
            "Desktop V2 CSS (src/styles/timelines.css): dagslinjer for soling og parkering.",
            "Desktop V2 CSS (src/styles/ventilation.css): ventilasjonsoversikt, dagslogg og innstillinger.",
            "Desktop V2 CSS (src/styles/energy.css): Elvia og energirelaterte visninger.",
            "Desktop V2 CSS (src/styles/records.css): redigering, kjoretoy, oppgjor og generiske tabelltilstander.",
            "Desktop V2 CSS (src/styles/responsive.css): felles responsive regler.",
            "Desktop V2 appstart (main.tsx): importerer de nye domenevise stilarkene eksplisitt.",
            "Desktop V2 verktøy (scripts/audit-css.mjs): auditerer alle CSS-filer i styles-mappen.",
            "Buildlogg (build_log.py): registrerer build 1214.",
        ],
        "request": "Gjor de grepene du mener er riktig, men spor prinsipielle veivalg for videre utvikling.",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "styles.css er fjernet som samlefil.",
            "CSS-audit viser fortsatt 0 mulige ubrukte CSS-klasser.",
            "Produksjons-CSS er uendret i storrelse, men kildekoden er vesentlig enklere aa navigere.",
            "Neste prinsipielle valg er om vi skal fortsette med globale domene-stilark eller gaa til komponentnaer styling/CSS Modules.",
        ],
    },
    {
        "version": "1",
        "build": "1213",
        "date": "16.06.2026",
        "headline": "CSS-strukturen er kontrollert og ryddet",
        "title": "Frontend-stilark har eksplisitt lastrekkefolge og audit for videre opprydding",
        "description": (
            "Build 1213 rydder frontendrammeverket rundt CSS. Globale CSS-avhengigheter lastes eksplisitt fra appstart "
            "i stedet for skjulte @import i hovedstilarket. En ny audit-kommando rapporterer CSS-storrelse, dupliserte "
            "selektorer, hardkodede farger og mulige ubrukte klasser. Gamle oppgjorsregler som ikke lenger brukes av "
            "React-komponentene er fjernet."
        ),
        "applications": [
            "Desktop V2 appstart (main.tsx): laster tokens.css, layout.css, build.css, styles.css og visual-refresh.css eksplisitt.",
            "Desktop V2 CSS (styles.css): fjerner ubrukte gamle settlement-regler og tilhorende responsive rester.",
            "Desktop V2 verktøy (scripts/audit-css.mjs): legger CSS-audit for klassebruk, duplisering, filstorrelse og hardkodede farger.",
            "Desktop V2 package.json: legger npm-scriptet audit:css.",
            "Buildlogg (build_log.py): registrerer build 1213.",
        ],
        "request": "Ta en grundig gjennomgang av CSS og frontend rammeverket.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "styles.css er redusert fra 4378 til 3648 linjer.",
            "Statisk audit viser 0 mulige ubrukte CSS-klasser etter oppryddingen.",
            "CSS-importrekkefolgen er tydelig og lettere aa vedlikeholde.",
            "Auditrapporten peker videre paa at visual-refresh.css fortsatt overstyrer en del baseklasser som bor konsolideres gradvis.",
        ],
    },
    {
        "version": "1",
        "build": "1212",
        "date": "15.06.2026",
        "headline": "Deploy lar QNAP-eksempelfil vaere urort",
        "title": "Miljoeksempel paa QNAP blir ikke restaurert som runtime-hemmelighet",
        "description": (
            "Build 1212 retter en deploy-hygiene-feil der .env.qnap.example ble fanget av .env.*-backupen "
            "og lagt tilbake etter git reset paa QNAP. Eksempelfilen er en tracked dokumentasjonsfil og skal "
            "ikke behandles som lokal runtime-konfigurasjon."
        ),
        "applications": [
            "Deploy-script (scripts/deploy-qnap.ps1): hopper over .env.qnap.example ved backup og restore av lokale miljoefiler.",
            "Buildlogg (build_log.py): registrerer build 1212.",
        ],
        "request": "Kjor tester og finn feil og rett dem.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "QNAP-worktree blir ikke skitten av deploy fordi tracked .env.qnap.example ikke lenger restaureres fra lokal backup.",
            "Deploy beholder fortsatt faktiske runtime-miljoefiler som .env og app-spesifikke .env-varianter.",
        ],
    },
    {
        "version": "1",
        "build": "1211",
        "date": "15.06.2026",
        "headline": "Docker-deploy sender ikke runtime-bilder",
        "title": "Build-context kuttes ved aa ignorere snapshots og runtime-data",
        "description": (
            "Build 1211 rydder Docker build-context. Deploy av Fibaro10 sendte tidligere store runtime-mapper, "
            "blant annet Axis-snapshots, inn i Docker-builden. Dette gjorde bygg og idriftsetting unodvendig tregt. "
            ".dockerignore er utvidet slik at snapshots, data-mapper, outputs, lokale Vite-artefakter og .env-varianter "
            "ikke blir med i image-context."
        ),
        "applications": [
            "Docker-oppsett (.dockerignore): ignorerer axis_camera_snapshots/snapshots, axis data, car_info data, outputs og .env-varianter.",
            "Buildlogg (build_log.py): registrerer build 1211.",
        ],
        "request": "Ta en skikkelig kontroll og opprydding i hele appen med hensyn paa hastighet, CSS osv.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Docker build-context slipper aa pakke Axis snapshot-arkivet paa rundt 8,9 GB.",
            "Deploy blir raskere og mindre sårbar for store runtime-data.",
            "Miljofiler og lokale runtime-data holdes tydeligere utenfor image-build.",
        ],
    },
    {
        "version": "1",
        "build": "1210",
        "date": "15.06.2026",
        "headline": "Frontend lastes raskere og CSS er ryddet",
        "title": "Diagramkode splittes ut og ECharts bygges med bare nodvendige moduler",
        "description": (
            "Build 1210 rydder frontend-ytelse og styling. Standard modulsider laster ikke lenger "
            "ventilasjon, Elvia, solsengforbruk eller diagramkomponenten for de faktisk trengs. "
            "ECharts er lagt bak en felles core-wrapper som bare registrerer linje- og stolpediagrammer "
            "med nodvendige komponenter. Metrikkort-CSS er samlet slik at samme tetthetsregler ikke ligger "
            "duplisert flere steder."
        ),
        "applications": [
            "Desktop V2 (ModulePage.tsx): lazy-loader ventilasjon, Elvia, solsengforbruk og moduldiagrammer.",
            "Desktop V2 (ModulePage.tsx): memoizer tabellkolonner, filtrerte rader og tabellradnokler.",
            "Desktop V2 (AppChart.tsx): innforer felles ECharts core-wrapper med bare bar/line, grid, tooltip, legend, dataZoom og markLine.",
            "Desktop V2 (diagram-sider): bytter alle ReactECharts-standardimporter til AppChart.",
            "Desktop V2 (ModuleMetric.tsx/ModuleChartPanel.tsx): splitter metrikkort og diagram i separate moduler.",
            "Desktop V2 CSS (visual-refresh.css): konsoliderer metrikkort-tetthet og fjerner dupliserte sluttregler.",
            "Buildlogg (build_log.py): registrerer build 1210.",
        ],
        "request": "Ta en skikkelig kontroll og opprydding i hele appen med hensyn paa hastighet, CSS osv.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "ModulePage-chunken ble redusert fra ca. 70,6 KB til ca. 37,6 KB for produksjonsbuild.",
            "ECharts-chunken ble redusert fra ca. 1,05 MB til ca. 582 KB for produksjonsbuild.",
            "Charts gzip-storrelse ble redusert fra ca. 350 KB til ca. 195 KB.",
            "Metrikkort-styling ligger naa ett sted i visual-refresh-laget i stedet for som dupliserte sluttregler.",
        ],
    },
    {
        "version": "1",
        "build": "1209",
        "date": "15.06.2026",
        "headline": "Nordiske fallback-kilder er hendelsesstyrte",
        "title": "Tjekbil og Biluppgifter blir ikke gamle naar koen er tom",
        "description": (
            "Build 1209 retter statuslogikken for Biluppgifter Sverige og Tjekbil Danmark. Disse kildene kjoerer "
            "bare naar SVV ikke finner et svensk eller dansk kandidatnummer, og skal derfor ikke markeres som "
            "gammel bare fordi det ikke finnes nye kandidater."
        ),
        "applications": [
            "Fibaro10 backend (main.py): setter Biluppgifter og Tjekbil som hendelsesstyrte datakilder uten fast forventet intervall.",
            "Fibaro10 backend (main.py): nuller neste forventet i importstatus naar en datakilde ikke har fast intervall.",
            "Buildlogg (build_log.py): registrerer build 1209.",
        ],
        "request": "Hva med Tjekbil Danmark?",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Tjekbil Danmark viser OK naar siste kjente oppslag er behandlet uten systemfeil, selv om det er lenge siden.",
            "Biluppgifter Sverige bruker samme hendelsesstyrte statusmodell.",
            "Neste forventet tidspunkt vises ikke for disse fallback-kildene.",
        ],
    },
    {
        "version": "1",
        "build": "1208",
        "date": "15.06.2026",
        "headline": "Datakilder får faste referansenummer",
        "title": "Datakildelister viser Nr for enklere feilsøking",
        "description": (
            "Build 1208 gir alle definerte datakilder et fast nummer basert paa definisjonsrekkefolgen. "
            "Nummeret vises i V2 statusoversikt, admin/datakilder-tabeller og klassisk datakildeside, slik at "
            "det er enklere aa henvise presist til for eksempel Tjekbil Danmark."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger source_no paa importstatus-rader og API-responsen for statusoversikten.",
            "Desktop V2 (OverviewPage.tsx, api.ts, ModulePage.tsx): viser nummerbrikke og tabellkolonnen Nr.",
            "Desktop V2 CSS (styles.css): styler datakildenummer kompakt.",
            "Klassisk datakildeside (templates/import_status.html): viser nummer paa kort og i historikktabellen.",
            "Buildlogg (build_log.py): registrerer build 1208.",
        ],
        "request": "Hva med Tjekbil Danmark, og kan alle datakilder faa nummer saa de er lettere aa henvise til?",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Tjekbil Danmark kan identifiseres med fast datakildenummer i listene.",
            "Admin > Datakilder viser Nr som forste kolonne.",
            "Statusforsiden viser samme nummer som en liten brikke foran datakildenavnet.",
        ],
    },
    {
        "version": "1",
        "build": "1207",
        "date": "15.06.2026",
        "headline": "Nordiske biloppslag finner skilt med spesialtegn",
        "title": "Svenske og danske fallback-oppslag bruker samme kompakte nokkel",
        "description": (
            "Build 1207 retter en feil der EasyPark-skilt med ikke-ASCII-bokstaver eller andre "
            "ikke-ASCII-tegn kunne ligge i kjoretoy-tabellen med original tekst, mens SVV og nordisk oppslag brukte "
            "kompakt registreringsnummer. Resultatet var at car_info_lookup fant eller forsokte aa hente data, men "
            "Fibaro10 svarte 404 ved lagring."
        ),
        "applications": [
            "Fibaro10 backend (main.py): finner kjoretoy paa eksakt plate eller kompakt plate ved SVV-lagring og nordisk postback.",
            "Fibaro10 backend (main.py): bruker kompakt plateuttrykk i svenske/danske kandidatfilter, slik at backloggen ser samme skilt som Python-oppslaget.",
            "Tester (test_car_info_lookup.py): dekker konkret svensk skilt med spesialtegn fra EasyPark-data.",
            "Buildlogg (build_log.py): registrerer build 1207.",
        ],
        "request": "Hvorfor fungerer ikke innlesingen av svenske og danske biler?",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Direkte nordisk oppslag feiler ikke lenger med 404 naar EasyPark-raden har spesialtegn i registreringsnummeret.",
            "SVV-status lagres paa riktig kjoretoyrad selv om oppslagsnokkelen er kompakt.",
            "Backloggen for Biluppgifter og Tjekbil bruker samme normalisering som runtime-oppslaget.",
        ],
    },
    {
        "version": "1",
        "build": "1206",
        "date": "15.06.2026",
        "headline": "Oppgjør sorteres med siste måned øverst",
        "title": "Årsvalg viser nyeste bilag først",
        "description": (
            "Build 1206 retter sorteringen av oppgjørslistene. API-et sorterer nå på oppgjørsperiode, "
            "og soloppgjørssiden tolker også norske månedsnavn robust hvis periodefeltene mangler."
        ),
        "applications": [
            "Fibaro10 backend (main.py): sorterer sol- og parkeringsoppgjør etter periodestart synkende og sender periodestart/periodeslutt i tabellkontrakten.",
            "Desktop V2 (SunSettlementsPage.tsx): gjør årvalg og månedsrekkefølge robust mot norske månedsnavn.",
            "Buildlogg (build_log.py): registrerer build 1206.",
        ],
        "request": "Sorter oppgjør slik at siste måned ligger øverst når siden åpnes og når man velger år.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Soloppgjør innen valgt år vises nyeste måned først.",
            "Backend-listene for soling og parkering sorteres etter periode, ikke importtidspunkt.",
            "Kortet Siste import bruker fortsatt faktisk siste importtidspunkt.",
        ],
    },
    {
        "version": "1",
        "build": "1205",
        "date": "15.06.2026",
        "headline": "Oppgjørsdetalj viser bare navn og beløp",
        "title": "Verdilinjene forenkles helt",
        "description": (
            "Build 1205 forenkler verdilisten ved originalskjemaet ytterligere. Hver linje viser bare "
            "feltteksten og beløpet, uten statusprikker, beregnet-linjer eller avvikstekst."
        ),
        "applications": [
            "Desktop V2 (SettlementDetailPage.tsx): fjerner ekstra kontrolltekst fra verdiradene på oppgjørsdetaljen.",
            "Desktop V2 (styles.css): rydder bort styling for statusprikker og kontroll-underlinjer.",
            "Buildlogg (build_log.py): registrerer build 1205.",
        ],
        "request": "Forenkle undersiden ved original-PDF-en ytterligere; det holder med teksten, for eksempel Solomsetning for perioden, og tallet.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Hver avlest verdi vises som én rad med etikett og beløp.",
            "Beregnet/system/avvik-linjer er fjernet fra detaljvisningen.",
            "Statusprikker og radbaserte confidence-tags er fjernet fra verdilisten.",
        ],
    },
    {
        "version": "1",
        "build": "1204",
        "date": "15.06.2026",
        "headline": "Oppgjørsdetalj fjerner støy rundt originalskjema",
        "title": "Renere PDF-side uten dobbelt filnavn",
        "description": (
            "Build 1204 fullfører oppryddingen av detaljsiden ved originalskjemaet. Filnavn og filtype vises "
            "ikke flere steder samtidig, og PDF-panelet har bare en kort tittel før dokumentet."
        ),
        "applications": [
            "Desktop V2 (SettlementDetailPage.tsx): fjerner duplisert filnavn fra topp og PDF-toolbar.",
            "Desktop V2 (styles.css): forenkler PDF-toolbar etter at ekstra metadata er fjernet.",
            "Buildlogg (build_log.py): registrerer build 1204.",
        ],
        "request": "Gjør undersiden ved original-PDF-en ryddigere; den bruker fortsatt for mye plass og virker rotete.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Toppen viser bare oppgjørstype, periode og handlinger.",
            "PDF-panelet viser bare tittelen Originalskjema.",
            "Filnavn, parser, metode og sidetall ligger samlet i den kompakte venstrekolonnen.",
        ],
    },
    {
        "version": "1",
        "build": "1203",
        "date": "15.06.2026",
        "headline": "Oppgjørsdetalj får renere dokumentvisning",
        "title": "Original-PDF får hovedplassen",
        "description": (
            "Build 1203 rydder detaljsiden for oppgjør videre. De leste verdiene er flyttet til en smal "
            "inspektørkolonne uten store kort, tomme kontrollinjer fjernes, og originalskjemaet vises som "
            "en roligere dokumentflate med diskret filinformasjon."
        ),
        "applications": [
            "Desktop V2 (SettlementDetailPage.tsx): erstatter Ant Design-kortene med en egen dokumentlayout for originalskjema og leste verdier.",
            "Desktop V2 (styles.css): fjerner gamle kortregler, strammer inspektørkolonnen og lar PDF-flaten bruke mer høyde og bredde.",
            "Buildlogg (build_log.py): registrerer build 1203.",
        ],
        "request": "Rydd opp i undersiden ved original-PDF-en; verdiene som er lest ut bruker fortsatt for mye plass og siden oppleves uryddig.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Leste beløp og sumkontroll vises som kompakte linjer i en smal inspektørkolonne.",
            "Kontrollinfo vises bare når det faktisk finnes et beregnet sammenligningsgrunnlag.",
            "Filnavn, parser, metode og sidetall er flyttet til små tekstlinjer nederst i kolonnen.",
            "Originalskjemaet har bare en diskret toolbar og mer sammenhengende PDF-flate.",
        ],
    },
    {
        "version": "1",
        "build": "1202",
        "date": "15.06.2026",
        "headline": "Oppgjørsdetalj viser leste verdier som kompakt liste",
        "title": "Originalskjema får mindre verdipanel",
        "description": (
            "Build 1202 gjør detaljsiden for oppgjør mer plassgjerrig. De maskinleste beløpene vises som "
            "kompakte linjer i stedet for store bokser, slik at originalskjemaet får mer effektiv plass. "
            "Historiske Sun2 produktsalg for mai-desember 2025 er også hentet inn via scraperen."
        ),
        "applications": [
            "Desktop V2 (SettlementDetailPage.tsx): endrer leste skjemafelter fra store bokser til kompakte linjer.",
            "Desktop V2 (styles.css): smalner verdipanelet og reduserer padding, fontstørrelse og radavstand.",
            "Drift/data: importerte Sun2 produktsalg for mai, juni, juli, august, september, oktober, november og desember 2025.",
            "Buildlogg (build_log.py): registrerer build 1202.",
        ],
        "request": "Forklar hvorfor produkt 2025 manglet, les inn tallene hvis de finnes, og gjør tallene på originalskjema-siden mye mindre eller som liste.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Maskinleste beløp på oppgjørsdetaljen vises nå som kompakte listeverdier.",
            "Verdipanelet er smalere, og originalskjemaet får mer plass.",
            "Produktsalg for alle importerte 2025-oppgjør er hentet fra Sun2 og postet til Fibaro10.",
            "Produktkontrollen for mai-desember 2025 er verifisert OK med 0 i avvik.",
        ],
    },
    {
        "version": "1",
        "build": "1201",
        "date": "15.06.2026",
        "headline": "Soloppgjør bruker Sun2-dagsstatistikk når finansgrunnlag mangler",
        "title": "2025-oppgjør får riktig intern solkontroll",
        "description": (
            "Build 1201 strammer soloppgjørsraden videre og retter kontrollgrunnlaget for eldre perioder. "
            "Når Sun2 finansoppgjør ikke finnes, brukes eksisterende Sun2 dagsstatistikk eller rå enkelttimer "
            "som intern solomsetning i stedet for å vise manglende grunnlag."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger fallback fra Sun2 finansoppgjør til Sun2 dagsstatistikk og rå enkelttimer for solomsetning.",
            "Desktop V2 (SunSettlementsPage.tsx): deler soloppgjørsraden i periode, kontroll og bilag.",
            "Desktop V2 (styles.css): flytter kontrollboksene tett inntil bilaget og reduserer radhøyden.",
            "Tester (test_settlement_parser.py): dekker fallback til Sun2 dagsstatistikk når finansoppgjør mangler.",
            "Buildlogg (build_log.py): registrerer build 1201.",
        ],
        "request": "Flytt Sol/Produkt/Utbetalt-boksene tett inntil oppgjørsskjemaet, la måned og år stå alene, og rett at 2025-bilag feilaktig viser mangler Sun2-grunnlag.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Perioden står alene i venstre kolonne.",
            "Kontrollboksene ligger rett ved oppgjørsskjemaet.",
            "Oppgjørsraden er lavere.",
            "Eldre soloppgjør bruker Sun2 dagsstatistikk som kontrollgrunnlag når finansoppgjør mangler.",
            "Kilden som brukes for solkontroll sendes med i API-et.",
        ],
    },
    {
        "version": "1",
        "build": "1200",
        "date": "15.06.2026",
        "headline": "Soloppgjør får lavere og renere bilagsrad",
        "title": "Filnavn og tolkningsscore flyttes ned i bilaget",
        "description": (
            "Build 1200 strammer soloppgjørslisten visuelt. Kontrollkolonnen viser bare perioden over "
            "kontrollboksene, filnavn og tolkningsscore ligger nederst i bilagsflaten, oppgjørsskjemaet er "
            "smalere og beløpene i kontroll- og utbetalingsboksene er høyrejustert."
        ),
        "applications": [
            "Desktop V2 (SunSettlementsPage.tsx): flytter filnavn og tolkningsscore fra kontrollkolonnen til bunnen av bilagsflaten.",
            "Desktop V2 (styles.css): reduserer radhøyde, smalner bilaget og høyrejusterer beløp i kontroll- og utbetalingsbokser.",
            "Buildlogg (build_log.py): registrerer build 1200.",
        ],
        "request": "Flytt filnavn og 100 % tolket nederst under oppgjørsskjemaet, la bare januar 2026 stå over kontrollboksene, gjør bilaget smalere og høyrejuster tallene.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Venstrekolonnen viser nå bare periode over Sol, Produkt og Utbetalt.",
            "Filnavn og tolkningsscore ligger i en diskret footer på bilaget.",
            "Oppgjørsskjemaet er smalere og raden lavere.",
            "Beløp i kontrollboksene og utbetaltboksen er høyrejustert.",
        ],
    },
    {
        "version": "1",
        "build": "1199",
        "date": "15.06.2026",
        "headline": "Soloppgjør samles per år med bilag og kontroll side om side",
        "title": "Oppgjørslisten får årsvelger og tydeligere bilagslayout",
        "description": (
            "Build 1199 flytter sol- og produktkontrollene til venstre for oppgjørsskjemaet, legger utbetalt "
            "under kontrollene og gjeninnfører alle bilag for valgt år på samme side. Nyeste bilag vises øverst, "
            "og toppen er forenklet til en årsvelger."
        ),
        "applications": [
            "Desktop V2 (SunSettlementsPage.tsx): bytter månedsfilter til årsvelger og sorterer oppgjør nyest først.",
            "Desktop V2 (SunSettlementsPage.tsx): bygger om hver oppgjørsrad med kontrollkolonne til venstre og bilag til høyre.",
            "Desktop V2 (styles.css): justerer grid, bilagsbredde, kontrollkolonne og responsiv oppførsel for soloppgjør.",
            "Buildlogg (build_log.py): registrerer build 1199.",
        ],
        "request": "Legg kontrollboksene til venstre for skjemaet, utbetalt nederst under kontrollene, bilaget til høyre, og vis alle bilag for ett år med bare årsvelger øverst.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppgjørslisten viser valgt år i stedet for valgt måned.",
            "Nyeste bilag i året ligger øverst.",
            "Sol- og produktkontroll ligger samlet til venstre.",
            "Utbetalt ligger som egen oppsummering nederst i kontrollkolonnen.",
            "Bilaget ligger smalere og roligere til høyre.",
        ],
    },
    {
        "version": "1",
        "build": "1198",
        "date": "15.06.2026",
        "headline": "Soloppgjør viser ett månedsbilag om gangen",
        "title": "Oppgjørlisten får månedsblaing og roligere bilag",
        "description": (
            "Build 1198 retter norske tegn i soloppgjørlisten, viser bare valgt måned om gangen og gir "
            "oppgjørbilaget mer plass. Bilaget er satt opp med alle linjer under hverandre, nøytrale farger "
            "og lettere typografi, mens kontrollfeltene ligger stablet til høyre."
        ),
        "applications": [
            "Desktop V2 (SunSettlementsPage.tsx): legger periodevalg, forrige/neste måned og viser bare oppgjør for valgt måned.",
            "Desktop V2 (SunSettlementsPage.tsx): retter UTF-8/norske tegn i synlige tekster på soloppgjørssiden.",
            "Desktop V2 (styles.css): gjør bilaget vertikalt, demper farger og fontvekter, og stabler Sol/Produkt-kontrollene.",
            "Buildlogg (build_log.py): registrerer build 1198.",
        ],
        "request": "Rett norske ø-tegn, gi bilaget plass med alle linjer under hverandre, dropp sterke fonter/farger, stable kontrollfeltene og legg inn månedsblaing.",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Kun valgt oppgjørsmåned vises i listen.",
            "Forrige/Neste måned-knapper er lagt inn over listen.",
            "Bilaget har en linje per felt og nøytral beløpsvisning.",
            "Sol- og Produktkontroll ligger over hverandre til høyre.",
        ],
    },
    {
        "version": "1",
        "build": "1197",
        "date": "15.06.2026",
        "headline": "Soloppgjorlisten faar forenklet bilagsvisning",
        "title": "Oppgjorsregnestykket ligner mer paa originalskjemaet",
        "description": (
            "Build 1197 formaterer soloppgjorlisten som et lite bilag. Inntekter, fratrekk og summer vises "
            "som tekstlinjer med hoyrestilte belop og skillelinjer, i stedet for en lopende formeltekst."
        ),
        "applications": [
            "Desktop V2 (SunSettlementsPage.tsx): bytter formeltekst til en forenklet bilagsstruktur med linjer for inntekter, kostnader og summer.",
            "Desktop V2 (styles.css): legger bilagspreg med topptekst, hoyrestilte belop, summeringslinje og tydelig sluttsum.",
            "Buildlogg (build_log.py): registrerer build 1197.",
        ],
        "request": "Formatter oppgjorregnestykket bedre, slik at det ligner et bilag eller en forenklet utgave av originalen.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Oppgjorstallene vises som en mini-tabell med tekst og belop.",
            "Inntekter, fratrekk og totalsummer skilles visuelt.",
            "Sluttsummen Til utbetaling har egen markeringslinje.",
        ],
    },
    {
        "version": "1",
        "build": "1196",
        "date": "15.06.2026",
        "headline": "Soloppgjor viser regnestykket som ren formellinje",
        "title": "Oppgjorregnestykket er ryddet uten sma bokser",
        "description": (
            "Build 1196 forenkler regnskapslinjen i soloppgjorlisten. Tallene vises som ett lopende "
            "regnestykke med pluss, minus og er-lik, i stedet for mange separate feltbokser."
        ),
        "applications": [
            "Desktop V2 (SunSettlementsPage.tsx): bytter skjematallene fra enkeltbokser til en formellinje med operatorer.",
            "Desktop V2 (styles.css): fjerner boksdesign for hvert skjematall og bruker lett inline typografi.",
            "Buildlogg (build_log.py): registrerer build 1196.",
        ],
        "request": "Sett opp oppgjorstallene som et regnestykke uten masse bokser.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Regnestykket vises som Sol + Produkt - kostnader = Sum eks. mva + Mva = Utbetalt.",
            "Kostnader vises med minus og absolutte belop for bedre lesbarhet.",
            "Sol- og Produktkontrollene til hoyre beholdes uendret.",
        ],
    },
    {
        "version": "1",
        "build": "1195",
        "date": "15.06.2026",
        "headline": "Soloppgjor viser hele skjema-regnestykket i listen",
        "title": "Oppgjorlisten har venstre sammendrag og hoyre kontrollfelt",
        "description": (
            "Build 1195 flytter Sol- og Produktkontroll helt til hoyre i soloppgjorlisten. Venstre side "
            "viser periode, tolking, utbetalt belop og hele regnestykket fra oppgjor skjemaet med inntekter, "
            "kostnader, sum eks. mva, mva og utbetaling."
        ),
        "applications": [
            "Fibaro10 backend (main.py): sender med markedsforing SMS og e-post i soloppgjorlisten slik at skjema-regnestykket er komplett.",
            "Desktop V2 (SunSettlementsPage.tsx): bygger ny radstruktur med oppgjorssammendrag til venstre og Sol/Produkt-kontroll til hoyre.",
            "Desktop V2 (styles.css): legger kompakt formelstripe og hoyrestilt kontrollsone for soloppgjor.",
            "Buildlogg (build_log.py): registrerer build 1195.",
        ],
        "request": "Flytt Sol og Produkt til hoyre. Vis sum utbetalt sammen med dato og tolket, og ta med kostnader og inntekter fra hele oppgjor regnestykket.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Soloppgjorraden viser Sol, Produkt, Transaksjon, Service, SMS, E-post, Sum eks. mva, Mva og Utbetalt.",
            "Tolking og utbetalt belop ligger sammen med periode og importinformasjon.",
            "Sol- og Produktkontroll ligger samlet helt til hoyre.",
        ],
    },
    {
        "version": "1",
        "build": "1194",
        "date": "15.06.2026",
        "headline": "Oppgjorstabeller bruker mindre plass",
        "title": "Soloppgjorlisten er gjort mer kompakt",
        "description": (
            "Build 1194 strammer opp listevisningen for oppgjor slik at radene bruker vesentlig mindre "
            "plass. Soloppgjor viser fortsatt skjema, system og avvik, men samler tallene i kompakte "
            "kontrollfelt for Sol og Produkt."
        ),
        "applications": [
            "Desktop V2 (SunSettlementsPage.tsx): samler skjema, system og avvik i to kontrollfelt i stedet for flere brede tabellfelt.",
            "Desktop V2 (styles.css): reduserer kolonnebredder, padding, ikonstorrelser, radhoyde og typografi for oppgjorstabellene.",
            "Buildlogg (build_log.py): registrerer build 1194.",
        ],
        "request": "Feltene i tabellen er altfor store. Bruk vesentlig mindre plass.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Oppgjorradene er lavere og tettere.",
            "Sol og Produkt har hver sine kompakte kontrollbokser med Skjema, System og Avvik.",
            "Kolonneetiketter og belopsfelt er kortet ned for bedre oversikt.",
        ],
    },
    {
        "version": "1",
        "build": "1193",
        "date": "15.06.2026",
        "headline": "Soloppgjor viser bare system, skjema og avvik",
        "title": "Ekstra forklaringsfelt er fjernet fra oppgjorskontrollen",
        "description": (
            "Build 1193 rydder soloppgjorvisningen slik at kontrollen kun viser tallene som faktisk skal "
            "avstemmes: intern maanedsomsetning, oppgjor skjema og avvik. Ekstra forklaringsfelt er fjernet "
            "fra API-oppsummeringen og brukerflaten."
        ),
        "applications": [
            "Fibaro10 backend (main.py): fjerner ekstra forklaringsfelt fra soloppgjor-API og bruker kun systemomsetning som kontrollgrunnlag.",
            "Tester (test_settlement_parser.py): fjerner forventninger om ekstra forklaringsfelt i oppgjorstestene.",
            "Buildlogg (build_log.py): rydder synlige beskrivelser i siste oppgjorbuilds.",
        ],
        "request": "Ta bort ekstra forklaringsfeltet, det var ikke del av ønsket kontrollmodell.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Oppgjorlisten og detaljgrunnlaget viser ikke lenger eget forklaringsfelt.",
            "Soling og produktsalg kontrolleres fortsatt som system minus oppgjor skjema.",
            "Synlige buildtekster er ryddet slik at de beskriver system/skjema/avvik-modellen.",
        ],
    },
    {
        "version": "1",
        "build": "1192",
        "date": "15.06.2026",
        "headline": "Soloppgjor kontrolleres mot intern maanedsomsetning",
        "title": "Oppgjor skjema sammenlignes med brutto soling og produktsalg",
        "description": (
            "Build 1192 retter kontrollmodellen for solingsoppgjor. Oppgjorstallene sammenlignes naa mot "
            "intern maanedsomsetning i systemet for baade soling og produktsalg, i stedet for mot nettofelt "
            "som allerede var justert og derfor kunne gi null avvik."
        ),
        "applications": [
            "Fibaro10 backend (main.py): bruker Sun2 brutto maanedsomsetning som kontrollgrunnlag for soling og produktsalg.",
            "Desktop V2 (SunSettlementsPage.tsx): viser System og Avvik i solkontroll.",
            "Tester (test_settlement_parser.py): oppdaterer parserkontroll slik at avvik beregnes som system minus skjema.",
            "Buildlogg (build_log.py): registrerer build 1192.",
        ],
        "request": "Kontroller oppgjoret mot maanedsomsetningen i systemet, ikke mot et regnestykke som gir null avvik.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Soling: Sun2 medlemssolinger + uregistrerte solinger brukes som intern maanedsomsetning.",
            "Produktsalg: Sun2 brutto produktsalg brukes som intern maanedsomsetning.",
            "Avvik vises som system minus oppgjor skjema.",
            "Oppgjorlisten viser bare systemtall, skjema og avvik.",
        ],
    },
    {
        "version": "1",
        "build": "1191",
        "date": "15.06.2026",
        "headline": "Omsetning faar egen akkumulert aarsside",
        "title": "Akkumulert aar viser lopende omsetning og antall per uke",
        "description": (
            "Build 1191 legger en egen side under Omsetning for akkumulert aarsutvikling. Diagrammet bruker "
            "samme ukesgrunnlag som Omsetning oversikt, men summerer lopende fra uke 1 slik at utviklingen "
            "kan sammenlignes direkte mellom aar."
        ),
        "applications": [
            "Fibaro10 backend (main.py): bygger akkumulert aarsdiagram og aarskort fra samlet soling og parkering.",
            "Desktop V2 (moduleViews.ts): legger Akkumulert aar som eget menyvalg under Omsetning.",
            "Buildlogg (build_log.py): registrerer build 1191.",
        ],
        "request": "Lag et diagram for akkumulert aaret, samme som oversikt men bare akkumulert, paa en egen side.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny side: /omsetning/akkumulert.",
            "Diagrammet viser akkumulert sum per uke med omsetning som standard.",
            "Brukeren kan bytte mellom omsetning og antall.",
            "Innevaerende aar og fjoraret er synlige som standard, andre aar kan slaas paa i legenda.",
        ],
    },
    {
        "version": "1",
        "build": "1190",
        "date": "15.06.2026",
        "headline": "Soling oppgjor viser maanedsomsetning og avvik",
        "title": "Sun2 brutto og oppgjor skjema skilles tydelig",
        "description": (
            "Build 1190 rydder kontrollen av solingsoppgjor. Maanedsomsetning hentes fra "
            "Sun2 finanshistorikk og vises som kontrollgrunnlag mot kreditnotaens solomsetning, "
            "mens ra enkelttimer kontrolleres separat mot Sun2."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger brutto maanedsomsetning og ra-timekontroll som separate kontroller.",
            "Desktop V2 (SunSettlementsPage.tsx): viser systemgrunnlag og avvik i soloppgjorlisten.",
            "Tester (test_settlement_parser.py): laaser at avvik beregnes fra Sun2 brutto minus skjemaets solomsetning.",
            "Buildlogg (build_log.py): registrerer build 1190.",
        ],
        "request": "Mai skal vise avvik paa soling, og vi maa se maanedsomsetningen.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Soloppgjor viser naa Sun2 brutto maanedsomsetning.",
            "Avvik mellom system og oppgjor blir synlig.",
            "Nettoavvik mot skjemaet beholdes separat og skal fortsatt kunne vaere 0 naar kreditnotaen stemmer.",
            "Ra enkelttimer kontrolleres mot Sun2 brutto, ikke mot netto oppgjor.",
        ],
    },
    {
        "version": "1",
        "build": "1189",
        "date": "15.06.2026",
        "headline": "Soling oppgjor kontrolleres mot Sun2 finanshistorikk",
        "title": "Solomsetning avstemmes med finanshistorikk og uregistrerte solinger",
        "description": (
            "Build 1189 kompletterer solingsoppgjor med kontroll av selve solomsetningen, ikke bare produktsalg. "
            "Sun2 scraperen henter finanshistorikk per maaned, parser medlemssolinger, uregistrerte solinger og "
            "kontrollgrunnlag, og Fibaro10 bruker dette mot Altera-kreditnotaen."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger sun2_finance_settlements, ingest-endepunkt, period-summary og solomsetningskontroll.",
            "Sun2 scraper (sun2_session_scraper/app/main.py): legger finansoppgjor-scraper, maanedlig jobb og manuelle endepunkter.",
            "Desktop V2 (SunSettlementsPage.tsx): viser Solkontroll ved siden av Produktkontroll i oppgjorlisten.",
            "Desktop V2 (SettlementDetailPage.tsx): viser kildekontroll og avvik ogsaa paa belopsradene.",
            "Database/health/tester: legger migrasjon, observability-tabell og parsertest for solomsetningskontroll.",
        ],
        "request": "Du mangler jo kontroll av soling ogsaa, ikke bare produkt.",
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Solomsetning kontrolleres mot Sun2 finanshistorikk.",
            "Oppgjorlisten har egne kontrollfelt for soling og produktsalg.",
            "Detaljsiden viser forventet Sun2-belop og avvik paa belopsfeltene.",
            "Ny manuell endpoint: /sync-finance-settlement-month.",
        ],
    },
    {
        "version": "1",
        "build": "1188",
        "date": "15.06.2026",
        "headline": "Soling oppgjor bruker ekte penger i produktkontroll",
        "title": "Sun2 produktsalg avstemmes mot Altera",
        "description": (
            "Build 1188 retter avstemmingen av produktsalg i solingsoppgjor. Sun2 sin produkttabell viser "
            "total inntjening, mens Altera-kreditnotaen bruker et avstemmingsgrunnlag. Scraperen "
            "lagrer naa periodesammendraget fra Sun2, og oppgjorskontrollen bruker dette naar det finnes."
        ),
        "applications": [
            "Sun2 scraper (sun2_session_scraper/app/main.py): leser #finance-now og lagrer periodesammendrag for produktsalg.",
            "Fibaro10 backend (main.py): legger period_summary inn i produktdata og bruker ekte penger som kontrollgrunnlag.",
            "Buildlogg (build_log.py): registrerer build 1188.",
        ],
        "request": "Jeg kan ikke se at soling oppgjoret funker som det skal.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Februar-avviket forklares av forskjell mellom Sun2-sammendrag og kreditnota.",
            "Produktkontroll bruker naa ekte penger / 1,25 mot kreditnotaens eks. mva-felt.",
            "Detaljteksten viser Sun2-grunnlag naar Sun2 oppgir dette.",
        ],
    },
    {
        "version": "1",
        "build": "1187",
        "date": "15.06.2026",
        "headline": "Sun2 produktsalg vises komplett i driftssjekk",
        "title": "Health og datakilder kjenner produktsalgstabellen",
        "description": (
            "Build 1187 kompletterer driftssynligheten for Sun2 produktsalg. Health-listen inkluderer "
            "sun2_product_sales-tabellen, og Datakilder kan bygge fallback-status fra siste importerte "
            "produktfil dersom statusraden mangler."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger fallback-status for daglig og maanedlig Sun2 produktsalg.",
            "Observability (observability.py): legger sun2_product_sales i health storage-listen.",
            "Buildlogg (build_log.py): registrerer build 1187.",
        ],
        "request": "Fullfoer daglig og maanedlig produktsalg slik at dagsfordeling brukes og maanedskjoringen brukes til kontroll.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Health viser naa sun2_product_sales som del av lagringsoversikten.",
            "Datakilder kan vise siste produktfil og antall linjer fra tabellen ved behov.",
        ],
    },
    {
        "version": "1",
        "build": "1186",
        "date": "15.06.2026",
        "headline": "Sun2 produktsalg filtreres riktig per dag",
        "title": "Dagsimport av produktsalg bruker riktig Sun2-datovelger",
        "description": (
            "Build 1186 fikser datofilteret for Sun2 produktsalg. Produktsalg-siden bruker egen datovelger "
            "`product-dates`, mens den opprinnelige importen bare aapnet datovelgeren for medlemsrapporten. "
            "Daglig produktsalg kan dermed lagres som faktisk dagsgrunnlag, mens maanedsimporten fortsatt "
            "brukes til kontroll og avstemming mot solingsoppgjor."
        ),
        "applications": [
            "Sun2 scraper (sun2_session_scraper/app/main.py): datovelger-helperen aapner naa baade member-dates og product-dates.",
            "Buildlogg (build_log.py): registrerer build 1186.",
        ],
        "request": "Kanskje vi ogsaa maa lage en pr dag slik at vi faar salget oppdelt pr dag og kun bruker mnd-kjoringen for kontroll og avstemming.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Produktsalg for enkelt dag filtreres via Sun2 sin #product-dates-kontroll.",
            "Maanedsjobben beholdes som separat kontrollgrunnlag.",
            "Manuell test mot 14.06.2026 viste dagslinje paa 89 kr i stedet for standard maanedsperiode.",
        ],
    },
    {
        "version": "1",
        "build": "1185",
        "date": "15.06.2026",
        "headline": "Sun2 produktsalg importeres for oppgjorskontroll",
        "title": "Daglig og maanedlig produktsalg fra Sun2",
        "description": (
            "Build 1185 legger produktsalg fra Sun2 inn som egen idempotent datakilde. Daglig jobb henter "
            "gaarsdagen for dagsfordeling, mens maanedlig jobb henter hele forrige maaned som avstemming mot "
            "solingsoppgjor. Oppgjorlisten viser naa Sun2-grunnlag og avvik for produktsalg."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger modellen sun2_product_sales, ingest-endepunkt og oppgjorskontroll mot produktsalg.",
            "Sun2 scraper (sun2_session_scraper/app/main.py): legger daglig og maanedlig produktsalgjobb med manuelle endepunkter.",
            "Desktop V2 (SunSettlementsPage.tsx): viser produktkontroll med Sun2-belop og avvik i oppgjorlisten.",
            "Database (migrations): legger idempotent sun2_product_sales-tabell og indekser.",
            "Dokumentasjon/tester: oppdaterer Sun2 scraper-oppsett og parserkontrolltest.",
        ],
        "request": "Lag jobber for aa hente produktsalg en gang pr mnd for hele forrige maaned, og ogsaa pr dag for dagsfordeling. Maanedskjoring brukes til kontroll av oppgjor soling.",
        "work_duration": "ca. 1 t",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Daglig produktsalgimport henter gaarsdagen og lagrer salg med stat_date.",
            "Maanedlig produktsalgimport henter hele forrige maaned uten aa dobbelttelle eksisterende daglige salg.",
            "Solingsoppgjor kontrollerer Produktsalg for perioden mot Sun2-belop eks. mva.",
            "Datakilder faar egne statusrader for daglig produktsalg og maanedskontroll.",
        ],
    },
    {
        "version": "1",
        "build": "1184",
        "date": "15.06.2026",
        "headline": "Datakildestatus for Biluppgifter strammet inn",
        "title": "Interne oppslagsfeil markerer ikke ekstern bilkilde som nede",
        "description": (
            "Build 1184 hindrer at interne feil mellom Fibaro10 og car_info_lookup blir logget som feil paa "
            "Biluppgifter eller Tjekbil. De eksterne datakildene oppdateres naa av postback med faktisk "
            "leverandorsvar. Hvis en lokal bilrad mangler, eller oppslagsappen midlertidig ikke svarer, skal "
            "ikke det maskeres som at Biluppgifter.se eller Tjekbil.dk er nede."
        ),
        "applications": [
            "Fibaro10 backend (main.py): direkteutloeser etter SVV returnerer interne feil uten aa skrive ekstern datakildestatus.",
            "Fibaro10 backend (main.py): manuell car-info-sync skriver ikke lenger feil paa begge eksterne leverandorer ved intern oppslagsapp-feil.",
            "Buildlogg (build_log.py): registrerer build 1184.",
        ],
        "request": "Biluppgifter Sverige feiler naa.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ekstern kilde-status oppdateres bare naar leverandorsvaret postes tilbake til kjoretoyet.",
            "Interne 404/connection-feil i oppslagsflyten gjor ikke Biluppgifter-raden rod.",
        ],
    },
    {
        "version": "1",
        "build": "1183",
        "date": "15.06.2026",
        "headline": "Biluppgifter direkteoppslag fikset",
        "title": "Fibaro10 bruker riktig intern URL til car_info_lookup",
        "description": (
            "Build 1183 retter direkteutloeste svenske/danske kjoretoyoppslag etter SVV. Fibaro10 brukte "
            "fallback-URL til 127.0.0.1:8126 hvis miljovariabelen manglet, men car_info_lookup kjoerer i egen "
            "container. Docker Compose setter naa eksplisitt CAR_INFO_LOOKUP_URL=http://car_info_lookup:8126 "
            "paa Fibaro10-containeren."
        ),
        "applications": [
            "Docker/QNAP (docker-compose.qnap.yml): setter CAR_INFO_LOOKUP_URL direkte for Fibaro10.",
            "Buildlogg (build_log.py): registrerer build 1183.",
        ],
        "request": "Biluppgifter Sverige feiler naa.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Direkte biloppslag etter SVV bruker car_info_lookup-containeren i stedet for localhost.",
            "Feilen Connection refused fra 127.0.0.1:8126 elimineres.",
        ],
    },
    {
        "version": "1",
        "build": "1182",
        "date": "15.06.2026",
        "headline": "Separate nordiske kjoretoykilder",
        "title": "Biluppgifter og Tjekbil vises som egne datakilder",
        "description": (
            "Build 1182 splitter den tidligere samlede statusen for nordiske kjoretoyoppslag. Svenske "
            "oppslag logges naa som Biluppgifter Sverige, mens danske oppslag logges som Tjekbil Danmark. "
            "404 fra en kilde behandles som et gyldig kilde-svar, mens rate-limit og serverfeil fortsatt gir "
            "datakildevarsel."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger egne importstatus-nokler for Biluppgifter.se og Tjekbil.dk.",
            "Fibaro10 backend (main.py): mapper postback fra car_info_lookup til riktig datakilde basert paa landkode eller skilttype.",
            "Fibaro10 backend (main.py): legger fallback fra eksisterende kjoretoydata slik at nye statusrader faar historisk grunnlag.",
            "Buildlogg (build_log.py): registrerer build 1182.",
        ],
        "request": "Hvorfor ligger datakildene for Sverige og Danmark under Nordiske kjoretoyoppslag, det er to forskjellige datakilder.",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Admin > Datakilder viser Biluppgifter Sverige og Tjekbil Danmark separat.",
            "Nye svenske og danske oppslag oppdaterer hver sin statusrad.",
            "Ikke-funnet-svar fra kilden regnes ikke som teknisk datakildefeil.",
        ],
    },
    {
        "version": "1",
        "build": "1181",
        "date": "15.06.2026",
        "headline": "Mangler omraade-visning",
        "title": "Flisen for manglende omraade viser egen kjoretoy-liste",
        "description": (
            "Build 1181 kobler flisene for manglende omraade til en filtrert V2-visning. Naar brukeren "
            "klikker paa Mangler omraade eller Ikke funnet omraade, aapnes Parkering > Oppslag med bare "
            "kjoretoy uten omraade, egne kontrollkort og direkte lenker til kjoretoydetaljene."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger filter=mangler-omrade paa relevante fliser og returnerer en filtrert oppslagstabell.",
            "Buildlogg (build_log.py): registrerer build 1181.",
        ],
        "request": "Jeg vil ogsaa ha en visning som viser de uten omraade naar jeg klikker paa den flisa.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Mangler omraade-flisen peker til /parkering/oppslag?filter=mangler-omrade.",
            "Oppslagssiden viser bare kjoretoy uten omraade naar filteret er satt.",
            "Listen viser opptil 1000 rader og har lenke til hvert kjoretoy.",
        ],
    },
    {
        "version": "1",
        "build": "1180",
        "date": "15.06.2026",
        "headline": "Aggressiv nordisk backlog",
        "title": "Danske og svenske kjoretoyoppslag kjoeres raskt i blandet ko",
        "description": (
            "Build 1180 endrer nordisk backlog fra svensk-forst til en eksplisitt landsekvens `DK,S`. "
            "Dette gjoer at danske Tjekbil-oppslag starter umiddelbart i stedet for aa vente til svensk backlog "
            "er ferdig. Svenske Biluppgifter-oppslag kjoeres med 2 sekunders pause, danske Tjekbil-oppslag uten "
            "ekstra pause. 429/Cloudflare stopper fortsatt jobben og setter global backoff."
        ),
        "applications": [
            "Fibaro10 backend (main.py): kandidatlisten kan filtreres med country=DK/S og bruker ikke lenger svensk-forst-sortering.",
            "Nordisk biloppslag (car_info_lookup/app/main.py): veksler backlog etter landsekvens og senker svenske/danske pauser.",
            "Konfigurasjon (.env.qnap.example, docker-compose.qnap.yml): setter DK,S, svensk 2 sekunder og dansk 0 sekunder.",
            "Dokumentasjon (docs/car-info-oppslag.md, car_info_lookup/README.md): beskriver aggressiv blandet backlog.",
            "Buildlogg (build_log.py): registrerer build 1180.",
        ],
        "request": "Kan vi ikke bare kjorer de danske umiddelbart? API bor vel funke raskt, og svensk kan kanskje kjoeres med 2 sekunder mellom hver.",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Backlog starter med dansk kandidat og veksler deretter dansk/svensk.",
            "Svensk Biluppgifter-delay er satt til 2 sekunder.",
            "Dansk Tjekbil-delay er satt til 0 sekunder.",
            "Kandidat-API-et kan filtrere paa country=DK eller country=S.",
        ],
    },
    {
        "version": "1",
        "build": "1179",
        "date": "15.06.2026",
        "headline": "Raskere svensk backlog",
        "title": "Biluppgifter-kandidater prioriteres og kjoeres raskere",
        "description": (
            "Build 1179 gjoer nordisk biloppslag raskere for svensk backlog. Fibaro10 sorterer naa svensk-format "
            "kandidater foran dansk-format kandidater, og oppslagsappen bruker provider-spesifikke pauser: 20 "
            "sekunder for svenske Biluppgifter-oppslag og 60 sekunder for danske Tjekbil-oppslag. Rate-limit og "
            "Cloudflare stopper fortsatt koeringen og setter global backoff."
        ),
        "applications": [
            "Fibaro10 backend (main.py): prioriterer svensk-format kandidater i car-info-kandidatlisten.",
            "Nordisk biloppslag (car_info_lookup/app/main.py): legger provider-spesifikke backlog-pauser og oeker maks kandidater per syklus.",
            "Konfigurasjon (.env.qnap.example, docker-compose.qnap.yml): setter nye standarder for svensk/dansk backlog-tempo.",
            "Dokumentasjon (docs/car-info-oppslag.md, car_info_lookup/README.md): dokumenterer raskere svensk backlog og dansk moderasjon.",
            "Buildlogg (build_log.py): registrerer build 1179.",
        ],
        "request": "Jeg onsker at vi blir ferdige med svenske backlogg snart, tror ikke vi trenger aa vaere saa forsiktige som naar vi hadde car.info.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Svenske kandidater behandles foer danske kandidater.",
            "Svenske Biluppgifter-kall venter 20 sekunder mellom hvert kall.",
            "Danske Tjekbil-kall venter 60 sekunder mellom hvert kall.",
            "Backlog-syklus kan ta opptil 1000 kandidater og trenger derfor ikke stoppe etter 12.",
        ],
    },
    {
        "version": "1",
        "build": "1178",
        "date": "15.06.2026",
        "headline": "Danske kjoretoy via Tjekbil",
        "title": "Nordisk fallback slar opp svenske og danske skilt etter SVV",
        "description": (
            "Build 1178 utvider fallback for kjoretoy som SVV ikke finner. Svenske skilt bruker fortsatt "
            "Biluppgifter.se, mens danske skilt bruker Tjekbil sitt DMR-API. Fibaro10 kjoerer SVV forst, "
            "trigger deretter nordisk fallback ved permanent uten-treff, og setter omrade til Sverige eller "
            "Danmark bare naar ekstern kilde bekrefter samme registreringsnummer med kjoretoydata."
        ),
        "applications": [
            "Fibaro10 backend (main.py): utvider kandidatfilter, SVV-uten-treff-trigger, lagring og kjoretoyvisning til svensk/dansk fallback.",
            "Nordisk biloppslag (car_info_lookup/app/main.py): velger Biluppgifter for svenske skilt og Tjekbil for danske skilt.",
            "Nordisk biloppslag (car_info_lookup/app/parsing.py): legger Tjekbil JSON-parser med biltype, forstegangsregistrering, VIN, drivstoff, effekt og kontrollfrist.",
            "Konfigurasjon (.env.qnap.example, docker-compose.qnap.yml): dokumenterer og sender videre TJEKBIL_URL_TEMPLATE.",
            "Tester (tests/test_car_info_lookup.py): dekker svensk format, dansk format og Tjekbil-parseren.",
            "Dokumentasjon (docs/car-info-oppslag.md, car_info_lookup/README.md): beskriver nordisk fallback og norsk/dansk format-overlapp.",
            "Buildlogg (build_log.py): registrerer build 1178.",
        ],
        "request": (
            "Sjekk danske biler paa samme maate via https://www.tjekbil.dk/. Kjor forst norske VVG/SVV, "
            "saa svenske og saa danske. Testnummer DY71543."
        ),
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Tjekbil API brukes bare for skilt som matcher dansk format etter SVV-uten-treff.",
            "Danske treff lagres i samme kjoretoyfelt som andre fallback-data og kan sette omrade Danmark.",
            "Health for oppslagsappen viser nordisk service og Tjekbil URL-template.",
        ],
    },
    {
        "version": "1",
        "build": "1177",
        "date": "15.06.2026",
        "headline": "Gammel svensk lookup-state ryddes",
        "title": "Biluppgifter-oppslag starter uten gammel provider-backoff",
        "description": (
            "Build 1177 rydder gammel oppslagsstate automatisk ved oppstart hvis state-filen fortsatt inneholder "
            "referanser til tidligere svensk kilde. Dette hindrer at en gammel rate-limit/backoff blokkerer nye "
            "Biluppgifter-oppslag etter deploy."
        ),
        "applications": [
            "Svensk biloppslag (car_info_lookup/app/main.py): nullstiller gammel last_error, last_url, last_result og backoff ved provider-opprydding.",
            "Buildlogg (build_log.py): registrerer build 1177.",
        ],
        "request": "Glem car info.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Health/state viser ikke lenger gammel ekstern kilde etter container-restart.",
            "Gammel backoff kan ikke stoppe Biluppgifter-kjoering.",
        ],
    },
    {
        "version": "1",
        "build": "1176",
        "date": "15.06.2026",
        "headline": "Biluppgifter blir eneste svenske bilkilde",
        "title": "Svenske kjoretoyoppslag bruker Biluppgifter.se",
        "description": (
            "Build 1176 fjerner car.info som aktiv kilde og parser. Biluppgifter.se er eneste runtime-kilde "
            "for svenske biler. Kilden gir HTML med modell, aar, farge, forstegangsregistrering, siste eierbytte, "
            "trafikkstatus, besiktning og tekniske felt naar siden svarer. Interne car_info-navn i database/API "
            "beholdes bare som kompatibilitetslag."
        ),
        "applications": [
            "Svensk biloppslag (car_info_lookup/app/main.py): bruker Biluppgifter.se som eneste provider.",
            "Svensk biloppslag (car_info_lookup/app/parsing.py): fjerner gammel parser og leser Biluppgifter label/verdi-felter.",
            "Fibaro10 backend (main.py): viser svensk kilde generisk og legger siste eierbytte fra Biluppgifter.",
            "Konfigurasjon (.env.qnap.example, docker-compose.qnap.yml): fjerner provider-valg og dokumenterer Biluppgifter-URL.",
            "Tester (test_car_info_lookup.py): dekker Biluppgifter-parseren med WDB22E-lignende HTML.",
            "Dokumentasjon (docs/car-info-oppslag.md, car_info_lookup/README.md): oppdateres til Biluppgifter-only.",
            "Buildlogg (build_log.py): registrerer build 1176.",
        ],
        "request": "Hva med aa legge om til https://biluppgifter.se/fordon/wdb22e/ med et testnummer? Glem car info.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Biluppgifter.se brukes som eneste URL for nye svenske oppslag.",
            "Parseren henter modell, aar, farge, forst registrert, siste eierbytte, status, kontrollfrist og tekniske felt.",
            "Gammel provider-backoff nullstilles automatisk fordi provider er endret til Biluppgifter.",
        ],
    },
    {
        "version": "1",
        "build": "1175",
        "date": "15.06.2026",
        "headline": "Car.info trigges rett etter SVV-uten-treff",
        "title": "Svenske skilt som SVV ikke finner slas opp direkte hos car.info",
        "description": (
            "Build 1175 gjoer car.info-oppslag mer responsivt for sjeldne svenske biler. Naar SVV/Vegvesen "
            "gir permanent uten-treff paa et skilt som matcher svensk format, trigger Fibaro10 et direkte "
            "oppslag paa akkurat dette skiltet. Backlog-jobben blir liggende som rolig fallback og respekterer "
            "fortsatt car.info backoff."
        ),
        "applications": [
            "Fibaro10 backend (main.py): samler svenske SVV-uten-treff og trigger car.info direkte etter commit.",
            "Car.info-oppslag (car_info_lookup/app/main.py): legger tokenbeskyttet /api/run-plate/{plate}.",
            "Konfigurasjon (.env.qnap.example): dokumenterer auto-trigger for SVV-uten-treff.",
            "Dokumentasjon (docs/car-info-oppslag.md, car_info_lookup/README.md): beskriver direkteoppslag og backlog-fallback.",
            "Buildlogg (build_log.py): registrerer build 1175.",
        ],
        "request": "Det er veldig sjelden med svenske biler, men jeg onsker aa hente dem saa raskt som mulig etter at VVG/SVV har kjoert og ikke funnet.",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "SVV-uten-treff paa svensk-formatert plate gir umiddelbar car.info-trigger.",
            "Direkteoppslaget bruker eksakt skilt, ikke bare neste kandidat i backlog.",
            "Hvis car.info er i backoff eller opptatt, logges dette og vanlig backlog tar over senere.",
        ],
    },
    {
        "version": "1",
        "build": "1174",
        "date": "15.06.2026",
        "headline": "Car.info-oppslag kjoeres roligere",
        "title": "Svenske biloppslag settes ned til ca. ett kall hvert femte minutt",
        "description": (
            "Build 1174 justerer car_info_lookup etter at 60 sekunder mellom oppslag traff car.info sin "
            "rate-limit/coffee break. Ny standard er 300 sekunder mellom faktiske car.info-kall, maks 12 "
            "kandidater per backlog-syklus og fortsatt 240 minutters global pause ved rate-limit."
        ),
        "applications": [
            "Car.info-oppslag (car_info_lookup/app/main.py): setter roligere standarder for request- og backlog-pause.",
            "Docker/QNAP (docker-compose.qnap.yml, .env.qnap.example): dokumenterer og eksponerer de nye rate-verdiene.",
            "Dokumentasjon (docs/car-info-oppslag.md, car_info_lookup/README.md): beskriver 300 sekunders pause og manuell backlog-stoerrelse.",
            "Buildlogg (build_log.py): registrerer build 1174.",
        ],
        "request": "Hvor sjelden maa vi kjoere om vi skal faa svar tror du?",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Observerte at QNAP fikk 429/coffee break etter 7 oppslag med 60 sekunders pause.",
            "Setter anbefalt tempo til ett faktisk oppslag hvert 5. minutt.",
            "Beholder automatisk 4 timers backoff naar car.info ber oss vente.",
        ],
    },
    {
        "version": "1",
        "build": "1173",
        "date": "15.06.2026",
        "headline": "Car.info vises i vanlige kjoretoyfelt",
        "title": "Svenske car.info-data brukes som fallback i Kjoretoy, farge og klasse",
        "description": (
            "Build 1173 rydder visningen av svenske kjoretoydata. Car.info-bilnavn ligger ikke lenger som eget felt, "
            "men brukes som fallback i standardfeltet Kjoretoy naar SVV ikke har data. Aarsmodell, farge, klasse, "
            "registreringsstatus og kontrollfrist bruker samme fallback-prinsipp."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger felles visningshjelpere for SVV/car.info-fallback.",
            "Fibaro10 backend (main.py): fjerner separat Car.info bil-felt fra kjoretoydetaljen.",
            "Buildlogg (build_log.py): registrerer build 1173.",
        ],
        "request": "Hvorfor ligger info om kjoretoy i eget felt car.info bil? Jeg vil ha det i Kjoretoy sammen med de andre.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Kjoretoyfeltet viser SVV-data foerst og car.info som fallback.",
            "Tabell- og detaljtitler bruker samme fallback.",
            "Farge, kjoretoyklasse, registreringsstatus og kontrollfrist kan ogsaa fylles fra car.info naar SVV mangler.",
        ],
    },
    {
        "version": "1",
        "build": "1172",
        "date": "14.06.2026",
        "headline": "Car.info-backlog gaar gjennom hele koeen",
        "title": "Svenske bilkandidater behandles som en vedvarende backlog-jobb med rate-limit-respekt",
        "description": (
            "Build 1172 gjoer car_info_lookup fra enkel intervalljobb til en backlog-prosess. Den tar kandidat etter kandidat "
            "til koeen er tom eller car.info svarer med rate-limit, og fortsetter automatisk etter global pause."
        ),
        "applications": [
            "Car.info-oppslag (car_info_lookup/app/main.py): legger backlog-syklus, kandidatstatus og /api/run-backlog.",
            "Konfigurasjon (.env.qnap.example): setter QNAP-default til backlog-modus, 15 minutters intervall, en bil av gangen og pause mellom kall.",
            "Dokumentasjon (docs/car-info-oppslag.md, car_info_lookup/README.md): beskriver full backlog-kjoering og rate-limit.",
            "Buildlogg (build_log.py): registrerer build 1172.",
        ],
        "request": "Gjoer det helt ferdig og kjoer gjennom alle bilene som ligger uten opplysninger naa.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Backlog-modus fortsetter automatisk gjennom alle kandidater over tid.",
            "Jobben stopper trygt ved car.info coffee break og fortsetter etter backoff.",
            "Health viser kandidatantall, backlog-status og siste resultat.",
            "Manuell backlog-syklus kan trigges via /api/run-backlog.",
        ],
    },
    {
        "version": "1",
        "build": "1171",
        "date": "14.06.2026",
        "headline": "Flere car.info-bilfelt lagres",
        "title": "Car.info-parseren tar med flere relevante svenske kjøretøyopplysninger",
        "description": (
            "Build 1171 utvider car.info-normaliseringen med flere relevante bilfelt. I tillegg fjernes aapenbare "
            "placeholderverdier som Logga in og Les mer, slik at detaljvisningen viser nyttige data fremfor skjemastoy."
        ),
        "applications": [
            "Car.info-oppslag (car_info_lookup/app/parsing.py): normaliserer klassifisering, generasjon, drivlinje, forbruk, CO2, tankvolum og seter.",
            "Fibaro10 backend (main.py): viser de ekstra car.info-feltene paa kjoeretoeydetaljen.",
            "Dokumentasjon (docs/car-info-oppslag.md): oppdaterer listen over lagrede felt.",
            "Tester (test_car_info_lookup.py): dekker de nye feltene og stoyfiltrering.",
            "Buildlogg (build_log.py): registrerer build 1171.",
        ],
        "request": (
            "Ta med foerstegangsregistrering, biltype, farge og andre relevante opplysninger som car.info viser."
        ),
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Flere tekniske bilfelt lagres i car_info_data.fields.",
            "Kjoeretoeydetaljen viser de nye feltene naar de finnes.",
            "Placeholderverdier fra car.info filtreres bort fra normaliserte fakta.",
        ],
    },
    {
        "version": "1",
        "build": "1170",
        "date": "14.06.2026",
        "headline": "Car.info-token slipper gjennom global auth",
        "title": "Global innlogging slipper intern car.info-app gjennom til de isolerte oppslagsrutene",
        "description": (
            "Build 1170 retter opp at global innloggingsmiddleware stoppet car_info_lookup med 401 foer "
            "endepunktenes token-sjekk ble naadd. Tokenen godtas naa kun for kandidatlisten og resultatpostingen."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger smal middleware-passering for CAR_INFO_APP_TOKEN paa car.info-rutene.",
            "Buildlogg (build_log.py): registrerer build 1170.",
        ],
        "request": (
            "Start car.info-skrapingen paa QNAP og soerg for at den faktisk kan hente kandidater uten masterpassord."
        ),
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Intern car.info-token blir validert foer vanlig bruker/passord-krav.",
            "Unntaket er avgrenset til car.info-kandidatlisten og car.info-resultatpostingen.",
        ],
    },
    {
        "version": "1",
        "build": "1169",
        "date": "14.06.2026",
        "headline": "Intern token for car.info-oppslag",
        "title": "Car.info-appen kan bruke egen intern token mot Fibaro10 uten masterpassord",
        "description": (
            "Build 1169 strammer inn auth mellom car_info_lookup og Fibaro10. QNAP har bare hashbasert mastertilgang, "
            "saa bakgrunnsappen bruker naa CAR_INFO_APP_TOKEN mot de to isolerte car.info-endepunktene i stedet for "
            "plaintext brukernavn og passord."
        ),
        "applications": [
            "Fibaro10 backend (main.py): godtar x-car-info-token kun for kandidatlisten og resultatpostingen til car.info.",
            "Car.info-oppslag (car_info_lookup): sender CAR_INFO_APP_TOKEN mot Fibaro10 naar bruker/passord ikke finnes.",
            "Konfigurasjon (.env.qnap.example): dokumenterer CAR_INFO_APP_TOKEN.",
            "Dokumentasjon (docs/car-info-oppslag.md, car_info_lookup/README.md): beskriver intern token og lagrede bilfelt.",
            "Buildlogg (build_log.py): registrerer build 1169.",
        ],
        "request": (
            "Gjoer car.info-skrapingen ferdig og start den paa QNAP, men uten aa bruke eller rekonstruere masterpassord. "
            "Ta med foerstegangsregistrering, biltype, farge og andre relevante opplysninger fra car.info."
        ),
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Bakgrunnsappen kan hente kandidater og poste resultat med intern token.",
            "Token-unntaket er avgrenset til car.info-dataflyten.",
            "Dokumentasjonen viser hvilke normaliserte felt som lagres fra car.info.",
        ],
    },
    {
        "version": "1",
        "build": "1168",
        "date": "14.06.2026",
        "headline": "Trygg car.info-app for svenske biler",
        "title": "Svenske biler som SVV ikke finner kan bekreftes sakte via car.info",
        "description": (
            "Build 1168 legger car.info-oppslag i en egen QNAP-app. Appen henter bare kandidater der SVV er forsokt "
            "uten at Fibaro10 har faatt kjoretoy-nokkeldata, filtrerer hardt paa svensk skiltformat og kjører som en "
            "sakte nattjobb med global pause ved car.info rate-limit. Bekreftede svenske biler settes til omrade Sverige."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger car.info-felter paa kjoretoy, kandidat-API, resultat-API og manuell trigger.",
            "Car.info-oppslag (car_info_lookup): ny separat FastAPI-app med svensk skiltfilter, HTML-parser, rate-limit-backoff og scheduler.",
            "Docker/QNAP (docker-compose.qnap.yml, scripts/deploy-qnap.ps1): bygger, starter og bevarer data for car_info_lookup.",
            "Dokumentasjon (docs/car-info-oppslag.md): beskriver sikkerhetsregler, flyt og lagrede felt.",
            "Tester (test_car_info_lookup.py): laaser svensk skiltformat og grunnleggende car.info-parser.",
            "Buildlogg (build_log.py): registrerer build 1168.",
        ],
        "request": (
            "Lag en automatisk, trygg loesning som henter car.info-data for svenske biler som SVV ikke finner, "
            "bekrefter at det faktisk er svenske biler og setter omraade Sverige. Ta med forstegangsregistrering, biltype, farge og andre relevante felt."
        ),
        "work_duration": "ca. 60 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Ny separat car_info_lookup-app skraper ikke bredt, men henter en svensk kandidat per intervall.",
            "Svensk skiltfilter stopper norske og ukjente formater for car.info-kall.",
            "Fibaro10 lagrer car.info-status, URL, feil og strukturert JSON paa kjoretoy.",
            "Bekreftet svensk bil setter omrade til Sverige naar omrade er blankt eller ikke funnet.",
            "Kjoretoydetalj viser car.info-status og relevante bilfelt.",
        ],
    },
    {
        "version": "1",
        "build": "1167",
        "date": "14.06.2026",
        "headline": "Solingsoppgjor snur fortegn fra kreditnota",
        "title": "Altera-kreditnotaer vises som normale forretningstall",
        "description": (
            "Altera sender solingsoppgjoret som kreditnota. Build 1167 normaliserer derfor fortegnene i soling/oppgjor: "
            "solomsetning, produktsalg, sum, mva og utbetaling vises positivt, mens transaksjonskostnad og serviceavtale vises som fratrekk."
        ),
        "applications": [
            "Fibaro10 backend (main.py): bumper settlement-parser til versjon 5 og snur fortegn for Altera-kreditnotaer.",
            "Tester (test_settlement_parser.py): oppdaterer soling-oppgjor-testen til aa forvente positive inntekter og negative fratrekk.",
            "Buildlogg (build_log.py): registrerer build 1167.",
        ],
        "request": "du maa snu fortegnene paa soling/oppgjoer da det er kredittnota",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Solomsetning og produktsalg vises positivt.",
            "Transaksjonskostnad og serviceavtale vises negativt som fratrekk.",
            "Sum eks. mva, mva og belop NOK vises positivt.",
            "Eksisterende importerte oppgjor blir tolket paa nytt fordi parser-versjonen er oppdatert.",
        ],
    },
    {
        "version": "1",
        "build": "1166",
        "date": "14.06.2026",
        "headline": "Solingsoppgjor kan lastes inn og kontrolleres",
        "title": "Altera-kreditnotaer for soling er lagt inn etter samme mal som parkering",
        "description": (
            "Soling har faatt egen oppgjorsside med manuell opplasting av Altera-kreditnotaer. "
            "Den nye parseren er rettet mot tekstbaserte Visma/Altera-PDF-er og leser kreditnotanummer, dokumentdato, periode, "
            "solomsetning, produktsalg, transaksjonskostnad, serviceavtale, markedsforing, sum eks. mva, mva og belop NOK. "
            "Detaljsiden viser avleste felt til venstre og originalen stort til hoyre, med kontroll av skjemaets egne summer."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger provider for soling/Altera og egen parser for tekstbaserte kreditnota-PDF-er.",
            "Fibaro10 backend (main.py): legger API for soling/oppgjor, detaljvisning, originalvedlegg og manuell filopplasting.",
            "Desktop V2 soling (SunSettlementsPage.tsx): ny side for flerfil-opplasting, liste, tolkningsstatus og belopssammendrag.",
            "Desktop V2 oppgjor (SettlementDetailPage.tsx): samme dokumentvisning kan brukes av parkering og soling.",
            "Desktop V2 navigasjon (App.tsx, moduleViews.ts, navigation.ts): legger Soling > Oppgjor og detaljruter.",
            "Desktop V2 API/CSS (api.ts, styles.css): legger upload-hjelper, soling-detaljfetch og kompakt oppgjorslayout.",
            "Tester (test_settlement_parser.py): laaser tolkingen av Visma/Altera-kreditnota med sumkontroll.",
            "Buildlogg (build_log.py): registrerer build 1166.",
        ],
        "request": (
            "vi skal lage tilsvarende for soling, men der mangler vi aa hente ut litt tall fra sun2 ogsaa men forst kan du lage istand etter samme mal. "
            "Bruk den bedre Altera/Visma PDF-en som grunnlag, ikke bruk tid paa aa stotte begge PDF-varianter naa."
        ),
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Soling har faatt menyvalg Oppgjor i nytt grensesnitt.",
            "Altera-kreditnotaer kan lastes opp manuelt fra Soling > Oppgjor, og flere PDF-er kan velges samtidig.",
            "Tekstbaserte kreditnota-PDF-er tolkes til strukturerte felt og periodiseres etter dokumentdato.",
            "Detaljsiden viser original-PDF sammen med avleste felt og intern sumkontroll.",
            "Bildebaserte PDF-er lagres fortsatt som original, men krever OCR/manuell kontroll senere.",
        ],
    },
    {
        "version": "1",
        "build": "1165",
        "date": "14.06.2026",
        "headline": "Oppgjorsdetalj kontrollerer bare skjemaets egne summer",
        "title": "Kildekontroll fjernet fra vedleggvisningen",
        "description": (
            "Detaljsiden for parkeringsoppgjor blandet intern kildekontroll inn i selve vedleggkontrollen. "
            "Denne builden lar detaljsiden kun vise avleste felt og kontrollere at beregnede summer fra disse stemmer med avleste sumfelt."
        ),
        "applications": [
            "Desktop V2 oppgjor (SettlementDetailPage.tsx): fjerner kildekontroll mot Fibaro10 fra detaljsiden.",
            "Desktop V2 oppgjor (SettlementDetailPage.tsx): viser avleste belop rent, og viser beregnet/verdiavvik bare paa sumkontrollradene.",
            "Desktop V2 CSS (styles.css): fjerner ubrukt styling for kildekontrollkort i detaljvisningen.",
            "Buildlogg (build_log.py): registrerer build 1165.",
        ],
        "request": "vi trenger ikke kildekontroll paa detalj siden. vi trenger bare aa sjekke at om vi regner ut de avleste feltetene saa stemmer det med de avleste sum feltene",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Kildekontrollseksjonen er fjernet fra detaljsiden for oppgjor.",
            "Belopskortene viser naa kun verdien som er lest fra skjemaet.",
            "Sumkontrollen viser avlest sum, beregnet sum fra de avleste feltene og avvik.",
            "Belopskort farges ikke lenger av kildeavvik som ikke vises paa detaljsiden.",
        ],
    },
    {
        "version": "1",
        "build": "1164",
        "date": "14.06.2026",
        "headline": "Oppgjorslisten viser prosentavvik og kompakt tolking",
        "title": "Avvik i oppgjorskontrollen vises i prosent og tolking som statusikon",
        "description": (
            "Oppgjorslisten brukte unodvendig mye plass paa kronedifferanser og tekst/progress for tolking. "
            "Denne builden gjor forstesiden strammere ved aa vise kildeavvik i prosent og tolkningsstatus som ett tydelig ikon."
        ),
        "applications": [
            "Desktop V2 parkering (ParkingSettlementsPage.tsx): beregner prosentavvik mot skjemabelopet for Flowbird/mynt-kort og EasyPark.",
            "Desktop V2 parkering (ParkingSettlementsPage.tsx): erstatter tekststatus og progressbar med gronn/oransje/rod tolkningsindikator med tooltip.",
            "Desktop V2 CSS (styles.css): smalner tolkningskolonnen og styler statusikonene.",
            "Buildlogg (build_log.py): registrerer build 1164.",
        ],
        "request": "avviket paa forste siden/tabellen kan vaere i % ikke i kr saa sparer vi plass. Tolket kan vaere bare en gronn hake, evt orange om det er mindre sannsynlig tolket rett, og rod om det er noe helt galt",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Flowbird/mynt-kort og EasyPark viser naa prosentavvik i tabellen.",
            "Storste avvik i raden vises ogsaa som prosent.",
            "Tolket-kolonnen viser ett ikon: gronn ved trygg tolking, oransje ved usikker tolking og rod ved feil/manglende tolking.",
            "Tooltip paa ikonet viser status og tolkningssikkerhet.",
        ],
    },
    {
        "version": "1",
        "build": "1163",
        "date": "14.06.2026",
        "headline": "Oppgjorsdetalj prioriterer originalskjema",
        "title": "Vedleggvisningen viser innleste verdier til venstre og PDF stort til hoyre",
        "description": (
            "Detaljsiden for parkeringsoppgjor hadde for mye rapport- og kontrollflate over originalen. "
            "Denne builden gjor siden til en dokumentvisning der innleste verdier ligger kompakt til venstre, mens PDF/originalskjemaet faar hovedplassen."
        ),
        "applications": [
            "Desktop V2 oppgjor (SettlementDetailPage.tsx): erstatter rapportkort, verdict, feltlister og rawmetadata med venstre verdipanel og stor originalvisning.",
            "Desktop V2 CSS (styles.css): legger dokumentlayout, kompakte verdi-kort, kildekontrollkort og stor PDF-frame.",
            "Buildlogg (build_log.py): registrerer build 1163.",
        ],
        "request": "naar du klikker deg inn paa vedlegget saa holder det med at de feltene som du leser inn er til venstre og at pdf en faar resten av plassen",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Detaljsiden viser naa kun en kompakt header, venstre panel med innleste verdier og originalskjemaet.",
            "Aktuelle belop, kildekontroll og summer ligger i en smal venstre kolonne.",
            "PDF/originalvedlegg bruker resten av bredden og stor viewport-hoyde.",
            "Tekniske feltlister og raadata er fjernet fra primaervisningen.",
        ],
    },
    {
        "version": "1",
        "build": "1162",
        "date": "14.06.2026",
        "headline": "Oppgjorslisten viser kontrollene direkte",
        "title": "Parkeringsoppgjor gaar rett til liste med to kildekontroller",
        "description": (
            "Oppgjorssiden hadde for mye plass brukt paa toppkort og sammendrag. "
            "Denne builden fjerner de store toppfeltene og lar selve oppgjorslisten vise Flowbird/mynt-kort og EasyPark som ryddige kontrollkolonner."
        ),
        "applications": [
            "Desktop V2 parkering (ParkingSettlementsPage.tsx): fjerner stort siste-oppgjor-kort, importkort, sammendragsfliser og separat kontrollkort.",
            "Desktop V2 parkering (ParkingSettlementsPage.tsx): bygger oppgjorslisten som en kontrolltabell med skjema, Fibaro10 og avvik for Flowbird og EasyPark.",
            "Desktop V2 CSS (styles.css): legger tabellhode, kompakte kontrollceller og bedre responsiv oppforsel for oppgjorslisten.",
            "Buildlogg (build_log.py): registrerer build 1162.",
        ],
        "request": "du klarer aa lage dette skjemaet mye bedre, i tabellen paa foerste siden saa kan vi vise alle kontrollene ryddig",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Oppgjorssiden starter naa direkte med listen over oppgjor.",
            "Hver rad viser Flowbird/mynt-kort med skjema, Fibaro10 og avvik.",
            "Hver rad viser EasyPark med skjema, Fibaro10 og avvik.",
            "Til utbetaling beholdes som orienterende belop, mens kildeavvikene er hovedkontrollen.",
        ],
    },
    {
        "version": "1",
        "build": "1161",
        "date": "14.06.2026",
        "headline": "Parkeringsoppgjor kontrollerer riktige kilder",
        "title": "EasyPark og Flowbird/Park Nordic kontrolleres hver for seg",
        "description": (
            "Oppgjorskontrollen blandet tidligere interne parkeringstall i en total sammenligning. "
            "Denne builden skiller kildeverdiene slik at EasyPark-linjen kontrolleres mot source_system=EasyPark, "
            "og brutto mynt/kort kontrolleres mot source_system=flowbird-parknordic."
        ),
        "applications": [
            "Fibaro10 backend (main.py): summerer parkeringer per source_system for oppgjorsperioden.",
            "Fibaro10 backend (main.py): legger kildebaserte avvik for Flowbird og EasyPark i oppgjorsdetalj og oversikt.",
            "Desktop V2 API (api.ts): utvider oppgjorsfelt med kildeetikett og kildedetalj.",
            "Desktop V2 oppgjor (SettlementDetailPage.tsx): viser Fibaro10-kildeverdi og avvik direkte paa relevante skjemalinjer.",
            "Desktop V2 parkering (ParkingSettlementsPage.tsx): viser Flowbird og EasyPark som separate kontrollverdier.",
            "Desktop V2 CSS (styles.css): gir kildekontroll-linjer bedre kolonneplass og responsiv oppforsel.",
            "Tester (test_settlement_parser.py): laaser at Flowbird og EasyPark kontrolleres mot riktige source_system-verdier.",
            "Buildlogg (build_log.py): registrerer build 1161.",
        ],
        "request": "kilde: EasyPark og kilde: flowbird-parknordic",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Brutto mynt/kortautomat sammenlignes naa med intern sum eks. mva fra source_system=flowbird-parknordic.",
            "EasyPark-linjen sammenlignes naa med intern sum eks. mva fra source_system=EasyPark.",
            "Oppgjorsoversikten viser storste kildeavvik og detaljraden viser begge kildene separat.",
            "Den gamle total-parkering-mot-EasyPark-logikken er fjernet fra primarvisningen.",
        ],
    },
    {
        "version": "1",
        "build": "1160",
        "date": "14.06.2026",
        "headline": "Oppgjør fikk enkelt verdiformular",
        "title": "Parkeringsoppgjør viser fire aktuelle beløp og kontrollsummer",
        "description": (
            "Park Nordic-skjemaet inneholder mange tall, men bare fire beløp er operative for videre kontroll. "
            "Denne builden lager et eget enkelt formular for disse verdiene og bruker summeringslinjene som teknisk kontroll på innlesingen."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger Oppgjørsformular-seksjon med fire operative beløp og kontrollsummer.",
            "Fibaro10 backend (main.py): retter parserrekkefølge for Langtidsparkering og Netto innbetalte kontrollavgifter.",
            "Fibaro10 backend (main.py): bumper Park Nordic-parseren til versjon 3 slik eksisterende oppgjør reparses.",
            "Desktop V2 API (api.ts): utvider oppgjørsfelt med gruppe, forventet verdi, avvik og status.",
            "Desktop V2 oppgjørsdetalj (SettlementDetailPage.tsx): viser nytt enkelt formular over detaljfeltene.",
            "Desktop V2 CSS (styles.css): styler formularen som kompakt regnskapskontroll.",
            "Tester (test_settlement_parser.py): oppdaterer forventet mapping for kontrollavgifter/langtidsparkering.",
            "Buildlogg (build_log.py): registrerer build 1160.",
        ],
        "request": "det er egentlig kun de 4 beløpene som jeg har markert med en pil som er aktuelle, i tillegg til evt summene som det er rød strek uner",
        "work_duration": "ca. 40 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Formularet viser Brutto mynt/kortautomat, EasyPark, Fratrekk tømming/telling/kort og Netto innbetalte kontrollavgifter.",
            "Kontrollsummer viser Nettoinntekter mynt/kortautomat, Grunnlag omsetning eks. mva og Til utbetaling med lest verdi, beregnet verdi og avvik.",
            "Parseren mapper nå 0-linjen som Langtidsparkering og 25 740-linjen som Netto innbetalte kontrollavgifter.",
            "Detaljsiden beholder originalskjema og full teknisk feltliste, men løfter det enkle formularet opp som primær arbeidsflate.",
        ],
    },
    {
        "version": "1",
        "build": "1159",
        "date": "14.06.2026",
        "headline": "Parkeringsoppgjør ble en kontrollflate",
        "title": "Oppgjør viser siste skjema, avvik og feltkontroll tydelig",
        "description": (
            "Oppgjørssiden var fortsatt for generisk og teknisk. Denne revisjonen gjør Parkering/Oppgjør til en egen kontrollflate "
            "med tydelig siste oppgjør, klikkbare rapportlinjer, avviksstatus og en detaljrapport som viser Fibaro10, skjema, tolkede felter og originalfil samlet."
        ),
        "applications": [
            "Desktop V2 parkering (ParkingSettlementsPage.tsx): ny egen oppgjørsside i stedet for generisk modulvisning.",
            "Desktop V2 routing (App.tsx): /parkering/oppgjor går nå til den nye oppgjørskontrollen.",
            "Desktop V2 oppgjørsdetalj (SettlementDetailPage.tsx): bygger om detaljen til rapportlayout med kontrollkort og feltlister.",
            "Desktop V2 CSS (styles.css): legger spesifikke oppgjørsstiler for rapport, kontroll, avvik og responsiv layout.",
            "Buildlogg (build_log.py): registrerer build 1159.",
        ],
        "request": "du må da kunne klare å designe dette mye mye bedre?",
        "work_duration": "ca. 60 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppgjørslisten er byttet fra generisk tabell til klikkbare kontrollrader med periode, fil, status, tolkesikkerhet, beløp og avvik.",
            "Toppen viser siste oppgjør som et rapportkort med til utbetaling, skjema EasyPark, Fibaro10 og avvik i samme visuelle gruppe.",
            "Detaljsiden har fått et eget kontrollresultat som tydelig sier om oppgjøret ser konsistent ut eller krever manuell sjekk.",
            "Detaljrapporten viser originalskjema og feltmapping side ved side på desktop, med bedre beløpshierarki og riktig prosentvis tolkesikkerhet.",
        ],
    },
    {
        "version": "1",
        "build": "1158",
        "date": "14.06.2026",
        "headline": "Parkeringsoppgjør tolker Park Nordic-skjema",
        "title": "Oppgjør viser skjematall, parserregler og avvik mot Fibaro10",
        "description": (
            "Parkeringsoppgjør var for mye en originalfil-visning. Nå leses Park Nordic-PDF-er maskinelt, "
            "nøkkelfelter trekkes ut, og detaljsiden viser både kilde/regler, tolkesikkerhet og kontroll mot interne EasyPark-tall."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger parser for Park Nordic PDF/tekst/regneark og reparsing av eksisterende oppgjør ved visning.",
            "Fibaro10 backend (main.py): import fra Gmail lagrer skjemafelter og parsermetadata direkte på nye oppgjør.",
            "Fibaro10 backend (main.py): oppgjørslisten viser EasyPark-beløp, estimert inkl. mva, til utbetaling og kontrollavvik.",
            "Desktop V2 oppgjørsdetalj (SettlementDetailPage.tsx): bygger om siden til kontrollfelter ved siden av originalskjema.",
            "Desktop V2 tabeller/CSS (ModulePage.tsx/styles.css): legger tydelige kolonneetiketter, statusfarger og tolkesikkerhet.",
            "Tester (test_settlement_parser.py): dekker representativ Park Nordic-tekst og uetiketterte summeringsrader.",
            "Backend-avhengigheter (requirements.txt): legger til pypdf og openpyxl for PDF/regneark-lesing.",
            "Buildlogg (build_log.py): registrerer build 1158.",
        ],
        "request": "det mangler en god del rundt tolking av skjema og jeg synes heller ikke dette er sælig oversiktlig",
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Park Nordic-PDF-er tolkes til strukturerte felter som EasyPark, fratrekk, grunnlag, andel, mva og til utbetaling.",
            "Eksisterende oppgjør uten parsed-data reparses automatisk når oppgjørslisten eller detaljsiden åpnes.",
            "Detaljsiden viser nøkkeltall, kilde/regler og tolkesikkerhet før tekniske e-postmetadata.",
            "Kontroll mot Fibaro10 viser avvik mellom interne EasyPark-tall og EasyPark-linjen i skjemaet estimert inkl. mva.",
        ],
    },
    {
        "version": "1",
        "build": "1157",
        "date": "14.06.2026",
        "headline": "Parkeringsoppgjør flyttet til Parkering",
        "title": "Park Nordic-oppgjør ligger under Parkering",
        "description": (
            "Parkeringsoppgjør hører funksjonelt til Parkering, siden Soling senere skal få sin egen oppgjørsside. "
            "Meny, ruter, lenker og importaction er derfor flyttet fra Omsetning til Parkering."
        ),
        "applications": [
            "Fibaro10 backend (main.py): eksponerer parkeringsoppgjør gjennom parkeringmodulen og bruker parkering-action for Gmail-import.",
            "Desktop V2 meny (moduleViews.ts): fjerner Oppgjør fra Omsetning og legger Oppgjør under Parkering.",
            "Desktop V2 routing (App.tsx/navigation.ts): flytter detaljruten til /parkering/oppgjor/<id>.",
            "Desktop V2 oppgjørsdetalj (SettlementDetailPage.tsx): tilbakeknappen peker til Parkering/Oppgjør.",
            "Buildlogg (build_log.py): registrerer build 1157.",
        ],
        "request": "jeg synes oppgjør skal flyttes til parkering. det kommer også en oppgjør sak under soling.",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppgjør er fjernet fra Omsetning-menyen.",
            "Parkering-menyen har fått eget Oppgjør-valg.",
            "Oppgjørslisten og detaljsiden bruker nå /parkering/oppgjor.",
            "Gmail-importhandlingen bruker nå /api/actions/parkering/fetch-settlements.",
        ],
    },
    {
        "version": "1",
        "build": "1156",
        "date": "14.06.2026",
        "headline": "Oppgjør med originalskjema og feltkontroll",
        "title": "Oppgjørsdetalj viser originalfil, tolkede felter og intern kontroll",
        "description": (
            "Omsetning/Oppgjør får klikkbare oppgjørsrader. Hvert oppgjør åpner en detaljside med originalvedlegget "
            "fra Gmail, tolkede databasefelter, kilde/regler for hvert felt og intern kontroll mot Fibaro10 sine EasyPark-tall."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger JSON-detalj for oppgjør og sikkert endepunkt for originalvedlegg.",
            "Fibaro10 backend (main.py): gjør oppgjørsrader klikkbare med path til detaljside.",
            "Desktop V2 API-kontrakt (api.ts): legger typer og fetch for oppgjørsdetalj.",
            "Desktop V2 routing (App.tsx/navigation.ts): legger rute for /omsetning/oppgjor/<id>.",
            "Desktop V2 oppgjør (SettlementDetailPage.tsx): viser originalskjema, feltkartlegging og rå importmetadata.",
            "Desktop V2 tabeller/CSS (ModulePage.tsx/styles.css): gjør oppgjørsfelter klikkbare og styler detaljsiden.",
            "Buildlogg (build_log.py): registrerer build 1156.",
        ],
        "request": "jeg vil ha mulighet til å klikke på et oppgjør å se orginal skjema. samtidig vil jeg vise hvilke felter du har puttet informasonnen i slik at jeg kan ha kontroll",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppgjørslisten lenker nå til detaljside via periode, filnavn eller emne.",
            "Detaljsiden viser originalvedlegg inline når filtypen støtter det, ellers åpne/last ned-knapper.",
            "Alle tolkede felter vises med databasefelt, verdi og kilde/regel.",
            "Kontroll mot interne EasyPark-tall viser antall, omsetning og snitt for tolket periode.",
            "Hvis skjemaet ikke er maskinlest ennå, vises dette eksplisitt i stedet for å skjule manglende parsing.",
        ],
    },
    {
        "version": "1",
        "build": "1155",
        "date": "14.06.2026",
        "headline": "Per-bil rydding av ikke funnet",
        "title": "Kjøretøydetalj kan nullstille `ikke funnet` for én bil",
        "description": (
            "Parkering/kjøretøy får en målrettet handling på detaljsiden som bare vises når den aktuelle bilen "
            "har navn eller område satt til `ikke funnet`. Handlingen nullstiller disse feltene slik at bilen kan behandles på nytt."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger per-kjøretøy API for å fjerne `ikke funnet` fra navn og område.",
            "Fibaro10 backend (main.py): eksponerer handlingen på kjøretøydetalj bare når bilen faktisk har `ikke funnet`.",
            "Desktop V2 API-kontrakt (api.ts): legger actions på kjøretøydetaljresponsen.",
            "Desktop V2 kjøretøydetalj (ParkingVehicleDetailPage.tsx): viser handlingsknapp med bekreftelse og reload.",
            "Buildlogg (build_log.py): registrerer build 1155.",
        ],
        "request": "lag mulighet for å fjerne \"ikke funnet\" på en og en bil",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Ny knapp `Fjern 'ikke funnet'` på kjøretøydetalj når navn eller område er satt til `ikke funnet`.",
            "Handlingen fjerner bare eksakt `ikke funnet`, ikke andre manuelt satte verdier.",
            "Områdekilde og områdeoppdatert nullstilles sammen med område når område ryddes.",
        ],
    },
    {
        "version": "1",
        "build": "1154",
        "date": "14.06.2026",
        "headline": "Autodetekterer Gmail-arkivmappe",
        "title": "Park Nordic-import finner Gmail All Mail uavhengig av språk",
        "description": (
            "Gmail-kontoen kan ha lokalisert navn på arkivmappen, for eksempel `[Gmail]/All e-post`. "
            "Oppgjørsimporten finner nå mappen via IMAP-flagget `\\All` og bruker `INBOX` pluss denne mappen som standard."
        ),
        "applications": [
            "Fibaro10 backend (main.py): autodetekterer Gmail sin `\\All`-mappe når `SETTLEMENT_GMAIL_MAILBOXES` ikke er satt.",
            "Fibaro10 backend (main.py): dedupliserer fortsatt vedlegg på SHA-256 når samme e-post finnes i flere mapper.",
            "Dokumentasjon (docs/utviklingsoppsett.md): oppdaterer mappeoppsettet for Park Nordic Gmail-import.",
            "Buildlogg (build_log.py): registrerer build 1154.",
        ],
        "request": "du kan hente parkering i gmail. kommer fra fredrik@parknordic.no",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Standard mappevalg er nå `INBOX` og autodetektert Gmail-arkivmappe.",
            "Hardkodet engelsk `[Gmail]/All Mail` er fjernet fra standardoppsettet.",
            "`SETTLEMENT_GMAIL_MAILBOXES` kan fortsatt settes manuelt ved behov.",
        ],
    },
    {
        "version": "1",
        "build": "1153",
        "date": "14.06.2026",
        "headline": "Gmail-mappevalg for oppgjør",
        "title": "Park Nordic-import tåler Gmail-mapper med mellomrom",
        "description": (
            "Gmail IMAP kan feile på mapper som `[Gmail]/All Mail` hvis mappenavnet ikke siteres riktig. "
            "Importen prøver nå sitert variant først for mappenavn med mellomrom eller skråstrek og hopper kontrollert videre hvis en mappe ikke kan åpnes."
        ),
        "applications": [
            "Fibaro10 backend (main.py): gjør Gmail mailbox-select robust for `[Gmail]/All Mail` og tilsvarende IMAP-mappenavn.",
            "Buildlogg (build_log.py): registrerer build 1153.",
        ],
        "request": "du kan hente parkering i gmail. kommer fra fredrik@parknordic.no",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppgjørsimporten stopper ikke lenger hvis en Gmail-mappe krever sitert navn.",
            "Mapper som fortsatt ikke kan åpnes legges i `mailbox_errors` i importresultatet.",
        ],
    },
    {
        "version": "1",
        "build": "1152",
        "date": "14.06.2026",
        "headline": "Park Nordic oppgjør fra Gmail",
        "title": "Omsetning får import og kontrollside for parkeringsoppgjør",
        "description": (
            "Omsetning utvides med en egen oppgjørsside som kan hente månedlige Park Nordic-vedlegg fra Gmail. "
            "Importen lagrer originalvedlegg, periodetolkning og e-postmetadata, og viser interne EasyPark-tall for samme periode."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger tabellen `settlement_imports` for uendrede oppgjørsvedlegg og metadata.",
            "Fibaro10 backend (main.py): legger Gmail IMAP-import fra `fredrik@parknordic.no` med deduplisering på SHA-256.",
            "Fibaro10 backend (main.py): legger `/api/actions/omsetning/fetch-parking-settlements` med settings-tilgang.",
            "Fibaro10 backend (main.py): eksponerer `/omsetning/oppgjor` med importstatus og kontroll mot interne parkeringstall.",
            "Desktop V2 navigasjon (moduleViews.ts): legger Oppgjør under Omsetning.",
            "Desktop V2 tabeller (ModulePage.tsx): legger kolonneetiketter for oppgjør og kontrolltabell.",
            "Dokumentasjon (docs/utviklingsoppsett.md): dokumenterer Gmail-variablene for oppgjørsimport.",
            "Buildlogg (build_log.py): registrerer build 1152.",
        ],
        "request": "du kan hente parkering i gmail. kommer fra fredrik@parknordic.no",
        "work_duration": "ca. 40 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "`/omsetning/oppgjor` viser importerte Park Nordic-oppgjør.",
            "Knappen `Hent Park Nordic fra Gmail` henter nye vedlegg fra Gmail og hopper over duplikater.",
            "Vedlegg lagres uendret sammen med avsender, e-postdato, emne, filnavn, størrelse og SHA-256.",
            "Perioder tolkes fra emne/filnavn, med antatt forrige måned hvis e-posten kommer tidlig i måneden.",
            "Kontrolltabellen viser interne parkeringsantall og beløp for samme periode som oppgjøret.",
        ],
    },
    {
        "version": "1",
        "build": "1151",
        "date": "14.06.2026",
        "headline": "Sammenhengsanalyse i Admin",
        "title": "V2 får analyseflate for sammenheng mellom aktivitet, vær og energi",
        "description": (
            "Admin får en analyseflate som samler daglige data fra soling, parkering, Yr og energilogging. "
            "Siden beregner enkle korrelasjoner som kan peke på faktorer som ser ut til å påvirke aktivitet og omsetning."
        ),
        "applications": [
            "Fibaro10 backend (main.py): aggregerer siste 90 dager fra SUN2, EasyPark, Yr og energilogging.",
            "Fibaro10 backend (main.py): beregner Pearson-korrelasjoner mellom aktivitet/omsetning og faktorer som vær, ukedag og strøm.",
            "Fibaro10 backend (main.py): eksponerer `/admin/analyse` med kort, graf, korrelasjonstabell og dagsgrunnlag.",
            "Desktop V2 navigasjon (moduleViews.ts): legger Analyse inn under Admin.",
            "Desktop V2 tabeller (ModulePage.tsx): legger etiketter for analysekolonner.",
            "Buildlogg (build_log.py): registrerer build 1151.",
        ],
        "request": "du må gjennomføre alle punktene du foreslo",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "`/admin/analyse` viser sterkeste observerte faktor for soling, parkering og total omsetning.",
            "Korrelasjonstabellen viser retning, styrke og antall dager i grunnlaget.",
            "Dagsgrunnlaget viser soling, parkering, omsetning, værdata og energidata per dag.",
            "Grafen kan skifte mellom antall, omsetning og vær for siste 45 dager.",
            "Resultatene beskrives eksplisitt som indikasjoner, ikke årsaksbevis.",
        ],
    },
    {
        "version": "1",
        "build": "1150",
        "date": "14.06.2026",
        "headline": "Datakvalitet i Admin",
        "title": "V2 får egen datakvalitetsside med dekning, ferskhet og avvik fra mål",
        "description": (
            "Admin får en egen datakvalitetsside som beregner status direkte fra produksjonsdata. "
            "Siden viser om sentrale datasett er komplette nok for drift og analyse, og peker videre til riktig ryddeside."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger beregninger for datakvalitet på importstatus, parkering, soling, energi, ventilasjon, Yr og lys.",
            "Fibaro10 backend (main.py): eksponerer `/admin/datakvalitet` via V2 modul-API med kort, avvikstabell og handlinger.",
            "Desktop V2 navigasjon (moduleViews.ts): legger Datakvalitet inn under Admin.",
            "Desktop V2 tabeller (ModulePage.tsx): legger etiketter for målepunkt, mål, dekning og mangler.",
            "Buildlogg (build_log.py): registrerer build 1150.",
        ],
        "request": "du må gjennomføre alle punktene du foreslo",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "`/admin/datakvalitet` viser vektet datakvalitetsscore.",
            "Parkering måles på eiernavn, område og reg.nr-dekning.",
            "Soling måles på bilde-dekning siste 14 dager og romgrunnlag.",
            "Energi måles på realtime ferskhet og forventet 30-sekunders sampledekning.",
            "Ventilasjon, Yr og lys måles på ferskhet.",
        ],
    },
    {
        "version": "1",
        "build": "1149",
        "date": "14.06.2026",
        "headline": "Oppgaver blir handlingsbare",
        "title": "Admin-oppgaver får stabile nøkler og operative handlinger",
        "description": (
            "Oppgavesiden utvides fra ren avviksliste til en mer operativ arbeidsflate. "
            "Hver oppgavetype får en stabil teknisk nøkkel, og siden får handlingsknapper for de vanligste tiltakene."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger stabil task_key på alle beregnede adminoppgaver.",
            "Fibaro10 backend (main.py): legger actions på `/admin/oppgaver` for EasyPark, SVV, solbilder og områdeopprydding.",
            "Buildlogg (build_log.py): registrerer build 1149.",
        ],
        "request": "du må gjennomføre alle punktene du foreslo",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppgaver kan nå kobles til faste nøkler som `parking:vehicle-area-not-found` og `energy:realtime-stale`.",
            "Admin/Oppgaver har knapper for å oppdatere EasyPark, kjøre SVV-sync, koble solbilder og fjerne område ikke funnet.",
            "Handlingene bruker eksisterende tilgangskontroll og eksisterende V2 action-system.",
        ],
    },
    {
        "version": "1",
        "build": "1148",
        "date": "14.06.2026",
        "headline": "Felles oppgaveliste i V2",
        "title": "Admin får samlet oppfølging av avvik og vedlikeholdsoppgaver",
        "description": (
            "V2 får en egen admin-side for oppgaver som samler konkrete avvik fra flere deler av systemet. "
            "Målet er å gjøre drift mer handlingsorientert: datakilder som er trege eller feiler, kjøretøydata "
            "som mangler navn eller område, solinger uten bilde og energilogging som stopper opp vises ett sted."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger inn beregning av adminoppgaver basert på importstatus, parkering, soling og energi.",
            "Fibaro10 backend (main.py): eksponerer `/admin/oppgaver` via eksisterende V2 modul-API med kort og tabeller.",
            "Desktop V2 navigasjon (moduleViews.ts): legger Oppgaver inn som første admin-underside.",
            "Desktop V2 tabeller (ModulePage.tsx): legger norske etiketter og alvorlighetsmerking for oppgavetabellen.",
            "Buildlogg (build_log.py): registrerer build 1148.",
        ],
        "request": "prøv å implemtere på en best mulig måte",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "`/admin/oppgaver` viser nå en prioritert liste over oppgaver på tvers av systemet.",
            "Datakilder med advarsel eller feil løftes frem med alvorlighetsgrad og direkte lenke til datakildesiden.",
            "Parkering viser egne oppgaver for blanke navn, navn ikke funnet, blanke områder og område ikke funnet.",
            "Soling varsler om soltimer siste 14 dager som mangler Axis-bilde.",
            "Energi varsler hvis realtime loggingen stopper opp eller siste effektdifferanse er over 1000 W.",
        ],
    },
    {
        "version": "1",
        "build": "1147",
        "date": "14.06.2026",
        "headline": "Solsengforbruk løftet til V2",
        "title": "Energi får V2-side for kalkulert forbruk per solseng",
        "description": (
            "Den gamle funksjonen for å beregne solsengenes strømforbruk er løftet inn i det nye grensesnittet. "
            "Beregningen bruker fortsatt SUN2-timer, HC3 differanseforbruk og ventilasjonslogg, men presenteres nå "
            "som en egen V2-side med datoperiode, nøkkelkort, metodeforklaring, effektgraf og tabeller."
        ),
        "applications": [
            "Fibaro10 backend (main.py): samler solsengforbruksberegningen i en gjenbrukbar analyse-loader for klassisk visning og V2 API.",
            "Fibaro10 backend (main.py): korrigerer kWh-beregningen til faktisk sampleintervall slik at 30-sekunderslogging ikke dobles.",
            "Desktop V2 API-typer (api.ts): legger til energySunbeds-kontrakt med rom, observasjoner og sammendrag.",
            "Desktop V2 energi (EnergySunbedsPage.tsx og ModulePage.tsx): legger inn dedikert side for forbruk per solseng.",
            "Desktop V2 stilark (styles.css): legger kompakt design for metodekort, effektgraf og solsengtabeller.",
            "Buildlogg (build_log.py): registrerer build 1147.",
        ],
        "request": "i den gamle fibaro10 så hadde jeg et system for å kalkulere solsengenes fobruk. den funksjonaliteten må løftes over",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "`/energi/forbruk-per-seng` viser nå V2-side med samme kalkulasjon som gammel løsning.",
            "Datofiltre for fra/til styrer beregningsperioden, med samme 120-dagers maksgrense.",
            "Kalkulasjonen korrigerer for takvifte og bruker baseline uten aktive solsenger.",
            "Målt kWh beregnes nå med faktisk sampleintervall i stedet for fast 60 sekunder.",
            "Klassisk visning er også tilgjengelig på `/classic/energi/forbruk-per-seng`.",
        ],
    },
    {
        "version": "1",
        "build": "1146",
        "date": "14.06.2026",
        "headline": "Forrige uke-kurve i omsetningssammenligning",
        "title": "Omsetning sammenligning viser også tilsvarende tidspunkt samme dag forrige uke",
        "description": (
            "Detaljdiagrammet for omsetningssammenligning får en ekstra referansekurve for samme dag forrige uke. "
            "Kurven bruker samme kildebaserte datakutt som resten av statussammenligningen, slik at soling og "
            "parkering sammenlignes mot tilsvarende tidspunkt."
        ),
        "applications": [
            "Fibaro10 backend (main.py): utvider /api/status/comparison med referenceComparisons for samme dag forrige uke.",
            "Desktop V2 API-typer (api.ts): legger til referansesammenligning i kontrakten.",
            "Desktop V2 omsetning (StatusComparisonPage.tsx): tegner ekstra stiplet referansekurve i akkumulert utvikling.",
            "Desktop V2 stilark (styles.css): legger til legend-markør for referansekurven.",
            "Buildlogg (build_log.py): registrerer build 1146.",
        ],
        "request": "på omsetning sammenligning så vil jeg gjerne også ha en kurve som sammenligner med tilsvarende tidspunkt samme dag forrige uke",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Når dagsvisning sammenlignes med i går, vises nå også kurven for samme dag forrige uke.",
            "Hvis samme dag forrige uke allerede er valgt som hovedsammenligning, dupliseres ikke kurven.",
            "Referansekurven bruker egne sol- og parkeringslaner med samme relative tidsakse.",
            "Beløpsvisning får referansekurve på sum, soling og parkering; antallsvisning får referansekurve på soling og parkering.",
        ],
    },
    {
        "version": "1",
        "build": "1145",
        "date": "14.06.2026",
        "headline": "Lavere kort i hele grensesnittet",
        "title": "Kortene i V2 komprimeres ytterligere etter visuell gjennomgang",
        "description": (
            "Kortene var fortsatt for høye. Det siste visuelle CSS-laget setter derfor en tydelig lavere skala for "
            "modul-kort, generelle metric-kort, statusperiodekort, supportkort og summary-kort."
        ),
        "applications": [
            "Desktop V2 visuell profil (visual-refresh.css): legger inn siste kompakte kortlag som overstyrer tidligere tema.",
            "Buildlogg (build_log.py): registrerer build 1145.",
        ],
        "request": "jeg synes fortsatt kortene er for høye",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Modul-kort er redusert fra 104px til 82px.",
            "Generelle metric-kort er redusert fra 122px til 96px.",
            "Hovedtall på modul-kort er redusert til 16px.",
            "Summary-, statusperiode- og supportkort får lavere padding og mindre typografi.",
            "Kompaktlaget ligger sist i CSS slik at det faktisk slår gjennom over hele V2.",
        ],
    },
    {
        "version": "1",
        "build": "1144",
        "date": "14.06.2026",
        "headline": "Kompaktere kort i hele V2",
        "title": "Nøkkel-, status- og oppsummeringskort får mindre høyde og roligere typografi",
        "description": (
            "Kortene i V2 er strammet inn globalt med lavere høyder, mindre tall, mindre padding og tettere avstand. "
            "Målet er bedre oversikt og mindre visuelt volum på alle sider."
        ),
        "applications": [
            "Desktop V2 grunnstil (styles.css): reduserer metric-card, module-metric, summary-card, status-period-card og status-support-item.",
            "Desktop V2 visuell profil (visual-refresh.css): justerer siste lastede kortoverstyringer slik at kompakt stil faktisk slår gjennom.",
            "Buildlogg (build_log.py): registrerer build 1144.",
        ],
        "request": "jeg synes kortene alltid er for store på alle sidene, kan du justere ned både fonten og størrelsen på sånne kort ganske grundig",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Generelle metric-kort er redusert i høyde fra 154px til 122px.",
            "Modul-kort er redusert til 104px og bruker mindre hovedtall.",
            "Summary- og statusperiodekort har lavere padding, mindre beløp og tettere rader.",
            "Statusforsidens støtte-/nøkkelkort er gjort mer kompakte.",
            "Detaljtekst på metric-kort linjekuttes til maks to kompakte linjer.",
        ],
    },
    {
        "version": "1",
        "build": "1143",
        "date": "14.06.2026",
        "headline": "Kompakte nøkkelkort på soling dagslinje",
        "title": "Soling dagslinje får mer presise kort for soltid, omsetning og rombruk",
        "description": (
            "Kortene på soling dagslinje er strammet inn visuelt og viser flere operative nøkkeltall uten å bruke like "
            "mye plass."
        ),
        "applications": [
            "Fibaro10 backend (main.py): beregner snitt soltid pr time, snitt omsetning pr soling og rom med høyest inntjening.",
            "Desktop V2 API-typer (api.ts): utvider soling dagslinje med topRevenueRoom.",
            "Desktop V2 stilark (styles.css): gjør modul-kortene lavere og demper fontstørrelsen.",
            "Buildlogg (build_log.py): registrerer build 1143.",
        ],
        "request": (
            "På samme sted så har vi et kort for Total soltid, døp om dette til soltid og legg også inn snitt pr time. "
            "på kortet omsetning så vil jeg også ha inn snitt pr soling. på mest brukt vil jeg også ha inn hvem som har "
            "størst inntjening. alle kortene er for store, gjør de mindre ikke så kjempe store fonter."
        ),
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "`Total soletid` heter nå `Soltid`.",
            "Soltid-kortet viser total minutter og snitt minutter pr time.",
            "Omsetning-kortet viser snitt kroner pr soling.",
            "Mest brukt-kortet viser også rommet med høyest inntjening.",
            "Modul-kortene har lavere høyde og mindre talltypografi.",
        ],
    },
    {
        "version": "1",
        "build": "1142",
        "date": "14.06.2026",
        "headline": "Egen energimåling på soling dagslinje",
        "title": "Soling dagslinje viser både Elvia og intern energimåling",
        "description": (
            "Energikortet og energilinjen på soling dagslinje tar nå med Fibaro10 sin interne kWh-beregning i tillegg "
            "til Elvia-timesforbruket for valgt dag."
        ),
        "applications": [
            "Fibaro10 backend (main.py): summerer EnergyFibaroSample.inntak_delta_kwh per time for valgt soling-dag.",
            "Desktop V2 soling (SunTimelinePanel.tsx): viser Elvia og egen måling i energinotat, totalfelt og timegraf.",
            "Desktop V2 API-typer (api.ts): utvider SunTimeline med interne energifelt.",
            "Desktop V2 stilark (styles.css): skiller Elvia og egen måling visuelt i energilinjen.",
            "Buildlogg (build_log.py): registrerer build 1142.",
        ],
        "request": "på dagslinje soling så har vi et kort som viser energi, i tillegg til elvia tallet burde vi også ha vårt eget",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Strømforbruk-kortet beholder Elvia som hovedtall når Elvia-data finnes.",
            "Detaljlinjen viser nå også egen kWh og antall interne samples.",
            "Energilinjen viser Elvia og egen måling side om side per time.",
            "Tooltip per time viser begge kildene.",
        ],
    },
    {
        "version": "1",
        "build": "1141",
        "date": "14.06.2026",
        "headline": "Ryddeknapp for parkeringsområde",
        "title": "Parkering får knapp for å nullstille område satt til ikke funnet",
        "description": (
            "V2-parkering viser nå en handling når kjøretøy har område satt til `ikke funnet`. Handlingen setter "
            "disse områdene tilbake til blankt, slik at de kan behandles på nytt i vanlig områdeoppslag."
        ),
        "applications": [
            "Fibaro10 backend (main.py): gjenbruker ryddehelper for `omrade = ikke funnet` og legger til JSON action-endpoint.",
            "Desktop V2 parkering (main.py module payload): viser `Fjern område 'ikke funnet'` som handling på relevante parkeringsvisninger.",
            "Buildlogg (build_log.py): registrerer build 1141.",
        ],
        "request": "en knapp for å fjerne område ikke funnet",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Knappen vises når det finnes kjøretøy med område `ikke funnet`.",
            "Handling krever innstillings-/mastertilgang.",
            "Berørte kjøretøy får område, områdekilde og områdeoppdatert satt til blankt.",
            "V2 får JSON-svar og automatisk reload etter handling.",
            "Klassisk rydde-endpoint bruker samme backend-helper.",
        ],
    },
    {
        "version": "1",
        "build": "1140",
        "date": "14.06.2026",
        "headline": "Rydder primærflagg på soltimebilder",
        "title": "Eldre soltimer med bilder får valgt ett hovedbilde automatisk",
        "description": (
            "Noen eldre soltimer hadde lagrede Axis-bilder uten at ett av dem var merket som hovedbilde. "
            "Migreringen velger -15-bildet der det finnes, ellers bildet som ligger nærmest -15 sekunder."
        ),
        "applications": [
            "Database (migrations/versions/20260614_0745_sun2_image_primary_backfill.sql): setter primærbilde på soltimer som mangler primærflagg.",
            "Buildlogg (build_log.py): registrerer build 1140.",
        ],
        "request": "hva med knapp for å sette hovedbilde, en ting er når du er inne i arkivet, men også når du er i grensesnittet.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Fant 39 eldre soltimer med bilder, men uten primærbilde.",
            "Legger inn migrering som velger ett hovedbilde per berørt soltime.",
            "Prioriterer offset -15, ellers nærmeste tilgjengelige offset til -15.",
            "Endrer ikke soltimer som allerede har et primærbilde.",
        ],
    },
    {
        "version": "1",
        "build": "1139",
        "date": "14.06.2026",
        "headline": "Hovedbilde fra soltimekort",
        "title": "Lagrede soltimebilder kan settes som hovedbilde direkte i grensesnittet",
        "description": (
            "De fem lagrede bildene på en soltime kan nå brukes direkte til å velge hovedbilde. Dette endrer bare "
            "hvilket eksisterende bilde som er primært, uten å kopiere bildet på nytt eller endre fem-bildersserien."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger til API for å markere et lagret soltimebilde som primærbilde.",
            "Desktop V2 (api.ts og ModulePage.tsx): legger `Sett som hovedbilde` direkte i inline-bildevisningen.",
            "Dokumentasjon (docs/axis-camera-snapshots.md): beskriver forskjellen mellom å sette lagret bilde som hovedbilde og å hente nytt arkivbilde.",
            "Buildlogg (build_log.py): registrerer build 1139.",
        ],
        "request": "hva med knapp for å sette hovedbilde, en ting er når du er inne i arkivet, men også når du er i grensesnittet.",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Ny knapp vises sammen med Forrige/Neste på de fem lagrede soltimebildene.",
            "Knappen er deaktivert når bildet allerede er hovedbilde.",
            "Valget krever samme innstillings-/mastertilgang som manuelt bildebytte.",
            "Eksisterende bildeserie beholdes uendret; bare is_primary flyttes til valgt bilde.",
        ],
    },
    {
        "version": "1",
        "build": "1138",
        "date": "14.06.2026",
        "headline": "Tidligere Axis-lagring",
        "title": "Axis starter snapshot-lagring før åpning slik at første soltime får bilde",
        "description": (
            "Siste soltime manglet bilde fordi timen startet 06:59, mens Axis-lagring startet 07:00. SUN2-bildeserien "
            "henter bilder før starttidspunktet, så første kunde ved åpning trenger snapshot-buffer før åpning."
        ),
        "applications": [
            "Axis snapshot-app (axis_camera_snapshots/app/main.py): endrer standard lagringsstart fra 07:00 til 06:45.",
            "Docker/QNAP (docker-compose.qnap.yml og .env.qnap.example): bruker 06:45-23:00 som anbefalt lagringsvindu.",
            "Dokumentasjon (docs/axis-camera-snapshots.md): forklarer hvorfor lagring må starte før åpningstid.",
            "QNAP drift: live config for axis_camera_snapshots oppdateres til capture_start_time 06:45.",
            "Buildlogg (build_log.py): registrerer build 1138.",
        ],
        "request": "er det noe feil med bild løsningen nå, siste soling fikk ingen bilde",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Bekreftet at selve bildeløsningen og containerne er friske.",
            "Fant at siste soltime startet 06:59 og derfor trengte bilder fra ca. 06:59:05-06:59:25.",
            "Fant at første Axis-bilde ble lagret 07:00:04, altså for sent for automatisk match.",
            "Flytter fremtidig lagringsstart til 06:45 for å dekke første kunde og mindre tidsavvik.",
            "Dagens manglende soltime blir ikke automatisk fylt, fordi de første tilgjengelige bildene etter 07:00 var tomme.",
        ],
    },
    {
        "version": "1",
        "build": "1137",
        "date": "13.06.2026",
        "headline": "Inline-blaing i soltimebilder",
        "title": "De fem lagrede soltimebildene kan blas direkte i soltimekortet",
        "description": (
            "Soltimekortet viser nå den lagrede fem-bildersserien direkte. Forrige/neste bytter mellom de fem bildene "
            "uten å åpne bildearkivet. Bildearkivet brukes bare når man vil bla i alle Axis-bilder og eventuelt bytte hovedbilde."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger session_images inn i soltime-radene slik at frontend får hele fem-bildersserien direkte.",
            "Desktop V2 (ModulePage.tsx): gjør soltimebildet til en inline-blaer med Forrige/Neste og egen Bildearkiv-knapp.",
            "Desktop V2 CSS (styles.css): rydder bort gammel bildeknapp og legger kompakt stil for inline-bilde, metadata og kontroller.",
            "Dokumentasjon (docs/axis-camera-snapshots.md): beskriver at standardserien blas direkte og at arkivet er for alle Axis-bilder.",
            "Buildlogg (build_log.py): registrerer build 1137.",
        ],
        "request": "jeg synes de 5 skal ligge inne slik at man ikke må åpne bildearkivet for de, men bare bla i bildet slik det er - om man åpner bildearkivet skal man kunne bla i alle",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Soltimekortet får alle fem lagrede bilder direkte fra API-et.",
            "Forrige/Neste blar bare i de fem bildene som hører til soltimen.",
            "Bildearkiv åpner hele Axis-arkivet rundt valgt bilde.",
            "Bruk dette bildet i arkivet kan fortsatt bytte hovedbildet på posten.",
            "Ingen databaseendring er nødvendig i denne builden.",
        ],
    },
    {
        "version": "1",
        "build": "1136",
        "date": "13.06.2026",
        "headline": "Fem bilder per soltime",
        "title": "Soltimebilder lagres som serie fra 25 til 5 sekunder før start",
        "description": (
            "Axis-koblingen lagrer nå fem bilder per SUN2-soltime. Hovedbildet er fortsatt 15 sekunder før beregnet start, "
            "men posten får i tillegg to bilder før og to bilder etter dette punktet."
        ),
        "applications": [
            "Fibaro10 backend (main.py): endrer soltimebildekoblingen til å lagre offset-serien -25, -20, -15, -10 og -5 sekunder.",
            "Database (migrations/versions/20260613_2315_sun2_session_image_series.sql): fjerner unik ett-bildebegrensning og legger offset_seconds/is_primary.",
            "Desktop V2 (ModulePage.tsx og api.ts): viser lagret bildeserie med forrige/neste-knapper og beholder arkivvalg for manuelt hovedbilde.",
            "Dokumentasjon (.env.qnap.example og docs/axis-camera-snapshots.md): beskriver 15 sekunder som hovedoffset og fem lagrede bilder.",
            "Tester (tests/test_sun2_axis_snapshots.py): dekker ny fem-bilders target-serie.",
            "Buildlogg (build_log.py): registrerer build 1136.",
        ],
        "request": "og ta med totalt 5 bilder altså to før 15 og to etter 15, dvs -25, -20, -15, -10, -5. alle legges inn i soltimen med knapper for å bla frem og tilbake",
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Ny automatisk kobling fyller fem bilder per soltime når de finnes i Axis-arkivet.",
            "Eksisterende soltimebilder migreres til offset -5, siden de ble koblet med gammel 5-sekundersregel.",
            "Backfill legger inn nytt hovedbilde på offset -15 og fyller de andre manglende offsetene.",
            "Listen viser antall lagrede bilder på soltimekortet.",
            "Bilde-modal åpner lagrede bilder først og lar deg bla gjennom serien.",
            "Arkivmodus kan fortsatt brukes for å velge et nytt hovedbilde manuelt.",
        ],
    },
    {
        "version": "1",
        "build": "1135",
        "date": "13.06.2026",
        "headline": "Bildevelger for soltimer",
        "title": "Soltimer kan bla i Axis-arkivet og bytte lagret bilde manuelt",
        "description": (
            "Enkeltimevisningen for soling har fatt en bildebrowser. Nar et soltimebilde apnes kan man bla eldre og "
            "nyere i Axis-arkivet, kontrollere bildet mot beregnet bildetid og lagre valgt arkivbilde pa posten."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger til trygt snapshot-ID-oppslag, arkivbildevisning, bildebrowser-API og POST for a bytte soltimebilde.",
            "Desktop V2 (ModulePage.tsx): legger bildebrowser-modal med eldre/nyere navigasjon og Bruk dette bildet-knapp.",
            "Desktop V2 CSS (styles.css): gir bildebrowseren stort bilde, kompakte metadata og tydelige tom-/lastetilstander.",
            "Tester (tests/test_sun2_axis_snapshots.py): dekker snapshot-ID og filoppslag i Axis dagmapper.",
            "Dokumentasjon (docs/axis-camera-snapshots.md): beskriver manuell bildebytteflyt.",
            "Buildlogg (build_log.py): registrerer build 1135.",
        ],
        "request": "kan vi legge inn mulighet for a bla frem og tilbake i bildene nar man er inne pa en soltime og har apnet et bilde, da vil jeg kanpper som kan bla i bildearkivet opp og ned og en ok knapp for a skifte ut det bildet som er lagret pa posten",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Klikk pa soltimebildet apner bildearkivet.",
            "Bildearkivet kan bla eldre og nyere rundt valgt eller beregnet bildetid.",
            "Bruk dette bildet erstatter bildet lagret pa soltimeposten.",
            "Endring krever innstillings-/mastertilgang fordi den skriver til databasen.",
            "Filstier eksponeres ikke til frontend; bare tidsbaserte snapshot-ID-er brukes.",
        ],
    },
    {
        "version": "1",
        "build": "1134",
        "date": "13.06.2026",
        "headline": "Datovalg for parkeringsområder",
        "title": "Parkering/område kan vises for hele historikken, én dato eller et tidsrom",
        "description": (
            "Områdevisningen for parkering har fått datofilter. Uten datoer vises hele historikken som før. Hvis bare "
            "første dato fylles ut, vises én valgt dato. Hvis både fra- og til-dato fylles ut, beregnes områdefordelingen "
            "fra faktiske parkeringsøkter i perioden."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger til periodeberegning for parkeringsområder basert på parking_sessions.",
            "Fibaro10 V2-modul (main.py): legger datofiltre, periodekort og periodebevisste område-/mangler-tabeller på Parkering/område.",
            "Klassisk parkering/område (main.py og templates/parking_areas.html): bruker samme periodegrunnlag og får datofilter.",
            "Desktop V2 (ModulePage.tsx): legger tydelige kolonneetiketter for andeler i områdevisningen.",
            "Buildlogg (build_log.py): registrerer build 1134.",
        ],
        "request": "på parkering/område ønsker jeg å ha inn en dato velger slik at jeg kan velge en dato eller et tidsrom i tillegg til å velge hele",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Blanke datofelt betyr hele historikken.",
            "Bare fra-dato betyr én valgt dato.",
            "Fra- og til-dato betyr tidsrom, inklusive til-dato.",
            "Mangler område-tabellen følger valgt periode.",
            "Områdetabellen viser andel av biler og andel av parkeringer i valgt grunnlag.",
        ],
    },
    {
        "version": "1",
        "build": "1133",
        "date": "13.06.2026",
        "headline": "Retter SUN2-bildevalg",
        "title": "Axis-bilder for SUN2 bruker minuttpresisjon riktig",
        "description": (
            "SUN2 Owner leverer enkelttimer med minuttpresisjon, uten sekunder. Fibaro10 valgte tidligere bilde fem "
            "sekunder før starten av minuttet, noe som kunne gi tomt bilde før kunden kom inn. Bildekoblingen tolker "
            "nå minuttpresise SUN2-rader som midt i minuttet og velger bildet fem sekunder før dette."
        ),
        "applications": [
            "Fibaro10 backend (main.py): legger inn SUN2_AXIS_SNAPSHOT_MINUTE_ASSUMED_SECOND og beregner egen Axis-target for SUN2-rader.",
            "Fibaro10 bildekoblings-API (main.py): støtter replace=true slik at eksisterende feilvalgte bilder kan rekobles.",
            "Klassisk soltimevisning (templates/sun2_sessions.html): oppdaterer tekst for valgt Axis-bilde.",
            "Dokumentasjon (docs/axis-camera-snapshots.md og .env.qnap.example): beskriver minuttpresisjon, offset og rekobling.",
            "Tester (tests/test_sun2_axis_snapshots.py): dekker minuttpresise og sekundpresise SUN2-tider.",
            "Buildlogg (build_log.py): registrerer build 1133.",
        ],
        "request": "jeg ser at timen 17:46 har et bilde fra 17:45:54 men der er det ingen personer,, det skal jo ikke forekomme",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Beholder SUN2-starttidene uendret for statistikk og dagslinjer.",
            "Tolker minuttpresise SUN2-rader som sekund 30 ved bildevalg.",
            "Velger fortsatt bilde fem sekunder før beregnet bildetid.",
            "Gjør det mulig å rekoble eksisterende bilder med replace=true.",
        ],
    },
    {
        "version": "1",
        "build": "1132",
        "date": "13.06.2026",
        "headline": "Axis lagrer bare i åpningstid",
        "title": "Axis snapshot får lagringsvindu 07:00-23:00 for å begrense diskbruk",
        "description": (
            "Axis snapshot-appen kan nå styres med et eget lagringsvindu. Automatisk capture kjører bare mellom "
            "start- og sluttid, med 07:00-23:00 som standard for å følge åpningstiden. Manuell testknapp kan fortsatt "
            "hente et bilde utenfor vinduet."
        ),
        "applications": [
            "Axis snapshot-app (axis_camera_snapshots/app/main.py): legger til capture_start_time/capture_end_time, tidsvalidering, status og webskjema.",
            "Docker/QNAP (docker-compose.qnap.yml): legger inn AXIS_CAPTURE_START_TIME og AXIS_CAPTURE_END_TIME med 07:00-23:00 som standard.",
            "Dokumentasjon (docs/axis-camera-snapshots.md): beskriver nytt lagringsvindu og manuell test utenfor vinduet.",
            "Buildlogg (build_log.py): registrerer build 1132.",
        ],
        "request": "for å begrense plassen en del så kan vi jo sette tidspunkter i axis appen slik at den sparer bilder bare i åpningstiden",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Setter standard automatisk lagringsvindu til 07:00-23:00.",
            "Stopper automatisk snapshot utenfor lagringsvinduet uten å logge dette som feil.",
            "Viser om appen lagrer akkurat nå og hvilket vindu som gjelder på Axis-siden.",
            "Eksponerer lagringsvinduet i /health og /api/status.",
        ],
    },
    {
        "version": "1",
        "build": "1131",
        "date": "13.06.2026",
        "headline": "Axis-bilder hvert femte sekund",
        "title": "Axis snapshot tar bilder oftere og Fibaro10 kobler bildet fem sekunder før solstart",
        "description": (
            "Axis snapshot-appen har fått fem sekunder som standard intervall. Fibaro10 sin automatiske kobling av "
            "bilder til SUN2-soltimer sikter nå på bildet nærmest fem sekunder før start, med strammere toleranse "
            "for å unngå at et for gammelt bilde velges hvis et snapshot mangler."
        ),
        "applications": [
            "Axis snapshot-app (axis_camera_snapshots/app/main.py): standard intervall og webskjema er endret fra 10 til 5 sekunder.",
            "Docker/QNAP (docker-compose.qnap.yml): AXIS_INTERVAL_SECONDS har 5 sekunder som ny standard.",
            "Fibaro10 backend (main.py): SUN2-bildekobling bruker 5 sekunders offset og 8 sekunders standardtoleranse.",
            "Klassisk soltimevisning (templates/sun2_sessions.html): tekst for valgt Axis-bilde er oppdatert.",
            "Dokumentasjon (docs/axis-camera-snapshots.md): driftseksempel og koblingsregel er oppdatert.",
            "Buildlogg (build_log.py): registrerer build 1131.",
        ],
        "request": "vi tar nå bilder med axis snapshot hvert 10 sekund, jeg tror vi må øke dette til hvert 5 og ta det bilde som er 5 sekunder før soling inn i fibaro10",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Endrer standard snapshot-intervall fra 10 til 5 sekunder.",
            "Endrer SUN2-bildekobling fra start minus 10 sekunder til start minus 5 sekunder.",
            "Strammer standardtoleransen fra 15 til 8 sekunder.",
            "Oppdaterer visning og dokumentasjon slik at de beskriver ny regel.",
        ],
    },
    {
        "version": "1",
        "build": "1130",
        "date": "11.06.2026",
        "headline": "Retter EasyPark-tid i importstatus",
        "title": "EasyPark-oppdatering overskriver ikke lenger ekte importtid",
        "description": (
            "Manuell EasyPark-oppdatering i V2 registrerte en ekstra suksessrad etter den faktiske CSV-importen. "
            "Denne wrapper-raden kunne bli vist som nyeste import og gi misvisende tidspunkt/melding i loggen. "
            "Nå er det bare den faktiske importen som oppdaterer suksessstatus, mens feil fra downloaderen fortsatt logges."
        ),
        "applications": [
            "Backend importstatus (main.py): fjerner ekstra suksesslogging fra /api/actions/parkering/refresh.",
            "Klassisk datakildeside (main.py): skjuler gamle vellykkede EasyPark-downloader-wrapper-rader i kjøringshistorikken.",
            "Backend tidshåndtering (main.py): normaliserer tidspunkt før age-beregning og sender importstatus som lokal ISO-tid.",
            "Backend health/import-API (main.py): bruker eksplisitt Oslo-tid i status- og health-payloads.",
            "Buildlogg (build_log.py): registrerer build 1130.",
        ],
        "request": "det ser ut til at det er et feil i fibaro10 på klokkeslett, når jeg oppdaterer easypark så får jeg et tidspunkt som er ca 10 min frem i tid i loggen",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Lar den faktiske EasyPark CSV-importen eie sist kjørt, antall og meldingen i importstatus.",
            "Skjuler historiske vellykkede EasyPark-downloader-wrapper-rader fra datakildeloggen, men beholder eventuelle feil.",
            "Logger fortsatt feil hvis EasyPark-downloaderen feiler.",
            "Gjør last_success_at, last_run_at, last_failed_at og next_expected_at eksplisitte med Europe/Oslo-offset i importstatus-API.",
            "Normaliserer tidsverdier før minutter-siden-beregning.",
        ],
    },
    {
        "version": "1",
        "build": "1129",
        "date": "11.06.2026",
        "headline": "Dagvelger og heldøgnsgrafer for lys og energi",
        "title": "Lys/dagslogg og Energi/status viser valgt helt døgn uten zoom-slider",
        "description": (
            "Lys/dagslogg og Energi/status bruker nå dagvelger direkte i grafkortet. Grafene bruker fast tidsakse fra "
            "00:00 til 24:00 for valgt dato, slik at hele døgnet vises uten den automatiske skyvebaren under grafen."
        ),
        "applications": [
            "Backend V2-modul (main.py): lar lys og energi bruke day-parameter, heldøgns tidsakse og dagsnavigasjon.",
            "Desktop V2 API-typer (api.ts): utvider chart-kontrakten med tidsakse, zoomstyring og dagvelgerdata.",
            "Desktop V2 grafkomponent (ModuleVisuals.tsx): viser Forrige dag, I dag, Neste dag og datofelt i grafkortet.",
            "Desktop V2 modulside (ModulePage.tsx): kobler grafens dagvelger til URL-parameteren day.",
            "Desktop V2 CSS (styles.css og visual-refresh.css): strammer opp den nye kontrollraden.",
            "Buildlogg (build_log.py): registrerer build 1129.",
        ],
        "request": "på lys/dagslogg og energi/status så vil jeg ikke ha denne skyvebaren under jeg vil ha det likt som på soling omsetning osv med dagvelger men at det er en hel dag som vises",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Fjerner automatisk zoom-slider for lys- og energidagsgrafene.",
            "Legger dagvelger med forrige dag, i dag, neste dag og datofelt direkte i grafkortet.",
            "Setter tidsaksen til hele valgt døgn fra 00:00 til 24:00.",
            "Lar Energi/status vise valgt dags realtime effekt og akkumulert forbruk.",
            "Lar Lys/dagslogg vise valgt dags lux og lysstatus uten fra/til-filterkort.",
        ],
    },
    {
        "version": "1",
        "build": "1128",
        "date": "11.06.2026",
        "headline": "Legger metrikkvalg på soling oversikt",
        "title": "Soling/oversikt kan nå bytte mellom omsetning og antall i ukesgrafen",
        "description": (
            "Ukesutviklingsgrafen på Soling/oversikt bruker nå samme metrikkløsning som parkering og omsetning. "
            "Omsetning er standardvisning, antall kan velges i grafkortet, og inneværende år samt året før er fortsatt "
            "standard synlige sammenligningsår."
        ),
        "applications": [
            "Backend V2-modul (main.py): utvider solingens ukesgraf med metrics for omsetning og antall.",
            "Soling/statistikk (main.py): fjerner duplisert separat antall-ukesgraf fordi samme graf nå kan bytte metrikk.",
            "Buildlogg (build_log.py): registrerer build 1128.",
        ],
        "request": "soling/oversikt så ønsker jeg at u kan velge mellom omsetning og antall",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Legger metrics revenue/count på solingens ukesutviklingsgraf.",
            "Setter Omsetning som standardmetrikk.",
            "Beholder standard synlige år som inneværende år og året før.",
            "Rydder bort separat antallgraf på statistikk der den ble overflødig.",
        ],
    },
    {
        "version": "1",
        "build": "1127",
        "date": "11.06.2026",
        "headline": "Samordner lys- og energigrafer",
        "title": "Lys/dagslogg og Energi/status bruker nå samme grafmønster som øvrige V2-sider",
        "description": (
            "Grafene for lys og energi er lagt nærmere mønsteret som brukes på soling, parkering og omsetning. Energi "
            "har nå ett grafkort med valg mellom realtime effekt og akkumulert forbruk. Lys har ett grafkort med valg "
            "mellom lux og lysstatus. Samme generiske V2-grafkomponent brukes, inkludert legend og segmentert metrikkskifte."
        ),
        "applications": [
            "Backend V2-modul (main.py): lager metrics for Energi/status og Lys/dagslogg.",
            "Backend lux-dagslogg (main.py): inkluderer lysstatus per sample i chartdata.",
            "Desktop V2 API-typer (api.ts): støtter trappelinjer i generiske chart-serier.",
            "Desktop V2 grafkomponent (ModuleVisuals.tsx): bruker step/smooth fra seriepayload.",
            "Buildlogg (build_log.py): registrerer build 1127.",
        ],
        "request": "på lys/dagslogg og energi/status grafene har du brukt en litt annen løsning. kan vi gjøre dette likt som de andre",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Energi/status viser ett grafkort med metrikker: Effekt og Forbruk.",
            "Forbruksgrafen beregnes fra delta-kWh i realtime-samples.",
            "Lys/dagslogg viser ett grafkort med metrikker: Lux og Lysstatus.",
            "Lysstatus tegnes som trappelinjer slik at av/på blir lesbart.",
            "Utvider felles chart-komponent i V2 i stedet for å lage spesialløsning.",
        ],
    },
    {
        "version": "1",
        "build": "1126",
        "date": "11.06.2026",
        "headline": "Setter standardår for soling oversikt",
        "title": "Soling/oversikt åpner nå med inneværende år og året før som synlige sammenligningsår",
        "description": (
            "Ukesutviklingsgrafen for soling bruker nå samme standard som parkering og omsetning. Ved åpning vises "
            "bare inneværende år og året før, mens eldre år fortsatt kan slås på manuelt i forklaringen."
        ),
        "applications": [
            "Backend V2-modul (main.py): legger defaultVisibleSeries på solingens ukesutviklingsgraf.",
            "Buildlogg (build_log.py): registrerer build 1126.",
        ],
        "request": "soling/oversikt ønsker jeg også skal starte med kun året i år og året før som sammenligningsgrunnlag",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Henter inneværende år fra lokal Oslo-tid.",
            "Setter standard synlige serier til inneværende år og året før.",
            "Lar eldre år fortsatt ligge i grafen og kunne aktiveres manuelt.",
        ],
    },
    {
        "version": "1",
        "build": "1125",
        "date": "11.06.2026",
        "headline": "Gjenoppretter brukt masterinnlogging",
        "title": "Masteropprydding beholder nå masteren som faktisk er i bruk",
        "description": (
            "Databasebackupen viste at den brukte masterraden hadde en eldre hash enn verdien i MASTER_ACCESS_KEY_HASH. "
            "Masterhashen er gjenopprettet i databasen, og oppstartslogikken er endret slik at aktiv master med høyest "
            "faktisk bruk beholdes og ikke overskrives av miljøvariabelen ved restart."
        ),
        "applications": [
            "Produksjonsdatabase: gjenoppretter hash for masterraden som hadde reell brukshistorikk.",
            "Backend oppstart (main.py): bevarer eksisterende aktiv master-hash og fjerner bare duplikatrader.",
            "Buildlogg (build_log.py): registrerer build 1125.",
        ],
        "request": "master brukeren funker ikke",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Hentet slettet masterhash fra databasebackup 20260611-031500.",
            "Gjenopprettet masterraden i live database.",
            "Endret deduplisering til å velge aktiv master med høyest uses_count.",
            "Sluttet å overskrive eksisterende masterhash med MASTER_ACCESS_KEY_HASH når en aktiv master allerede finnes.",
        ],
    },
    {
        "version": "1",
        "build": "1124",
        "date": "11.06.2026",
        "headline": "Retter masteropprydding",
        "title": "Masteropprydding prioriterer gyldig master-hash og slår sammen bruksteller",
        "description": (
            "Første oppryddingsforsøk valgte raden med høyest bruksteller, men den gyldige master-hashen lå på den "
            "andre duplikatraden. Oppstartslogikken prioriterer nå raden med gyldig master-hash, sletter øvrige "
            "masterduplikater først, og flytter historisk bruksteller over på den beholdte raden."
        ),
        "applications": [
            "Backend oppstart (main.py): velger masterrad etter gyldig hash før duplikater slettes.",
            "Buildlogg (build_log.py): registrerer build 1124.",
        ],
        "request": "hvorfor er master brukeren to ganger i lista?",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Prioriterer masterraden med gjeldende MASTER_ACCESS_KEY_HASH.",
            "Sletter duplikatrader før eventuell normalisering som kan treffe unik key_hash-indeks.",
            "Slår sammen uses_count fra masterduplikater.",
            "Retter oppstart etter feilet 1123-deploy.",
        ],
    },
    {
        "version": "1",
        "build": "1123",
        "date": "11.06.2026",
        "headline": "Rydder duplikat masterbruker",
        "title": "Oppstarten beholder bare én masterbruker i tilgangslisten",
        "description": (
            "Databasen hadde to aktive masterrader med samme navn og samme nøkkelprefix. Oppstartslogikken er strammet "
            "inn slik at den beholder den masterraden som faktisk er brukt, normaliserer den, og fjerner øvrige "
            "masterduplikater."
        ),
        "applications": [
            "Backend oppstart (main.py): dedupliserer masterbruker ved oppstart.",
            "Buildlogg (build_log.py): registrerer build 1123.",
        ],
        "request": "hvorfor er master brukeren to ganger i lista?",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Fant to aktive masterrader i access_keys.",
            "Beholder raden med faktisk brukshistorikk.",
            "Fjerner ubrukte masterduplikater ved oppstart.",
            "Sikrer at masterraden alltid normaliseres til navn master, rolle master og prefix sun2_master.",
        ],
    },
    {
        "version": "1",
        "build": "1122",
        "date": "11.06.2026",
        "headline": "Fullfører brukeradministrasjon i V2",
        "title": "Admin/brukere kan nå opprette og vedlikeholde vanlige brukere i nytt grensesnitt",
        "description": (
            "Brukeradministrasjonen er flyttet frem i V2 slik at brukerlisten er første tabell, Ny-knappen er synlig, "
            "og vanlige brukere kan få endret rolle, aktiv-status og passord. Masterbrukeren vises som låst for å unngå "
            "at driftstilgangen endres fra tabellen."
        ),
        "applications": [
            "Backend admin API (main.py): legger passordreset til brukeroppdatering og sperrer duplikate brukernavn.",
            "Admin V2-modul (main.py): viser brukertabellen først og bruker egne kort for brukeradministrasjon.",
            "Desktop V2 tabeller (ModulePage.tsx): skjuler redigering av masterbrukeren og viser den som låst.",
            "Buildlogg (build_log.py): registrerer build 1122.",
        ],
        "request": "brukeradministrasjon er ikk emulig i det nye grensesnittet",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Gjør Brukere til første tabell på Admin > Brukere.",
            "Lar Ny-knappen opprette brukere direkte i V2.",
            "Legger inn passordfelt for å sette nytt passord på eksisterende vanlig bruker.",
            "Sperrer opprettelse av duplikate brukernavn og reserverer brukernavnet master.",
            "Viser masterbrukeren som låst i brukerlisten i stedet for å tilby redigering.",
        ],
    },
    {
        "version": "1",
        "build": "1121",
        "date": "11.06.2026",
        "headline": "Viser ikke funnet som eget kjøretøytall",
        "title": "Parkering/kjøretøy beholder hovedtall for mangler og viser ikke funnet separat",
        "description": (
            "Kjøretøysiden beholder hovedtallet for manglende navn og område som summen av blanke felt og verdien "
            "'ikke funnet'. Samtidig vises 'ikke funnet' som egne tall i tillegg, slik at man kan skille mellom "
            "reelt tomme felt og oppslag som allerede har gitt negativt resultat."
        ),
        "applications": [
            "Backend V2-modul (main.py): legger separate blank/ikke funnet-tellinger til kjøretøykortene.",
            "Parkeringsoppslag (main.py): verktøybeskrivelser viser hvor mange som er ikke funnet.",
            "Buildlogg (build_log.py): registrerer build 1121.",
        ],
        "request": "det er greit at hovedtallet er slik som nå både mangler og ikke funnet, men jeg vil gjerne at ikke funnet tas med som et eget tall i tillegg",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Deler mangler-logikken i blanke felt og 'ikke funnet' for navn.",
            "Deler mangler-logikken i blanke felt og 'ikke funnet' for område.",
            "Lar hovedkortene fortsatt vise samlet mangler-count.",
            "Legger egne kort for 'Ikke funnet navn' og 'Ikke funnet område'.",
            "Legger fordelingstekst på hovedkortene: blanke / ikke funnet.",
        ],
    },
    {
        "version": "1",
        "build": "1120",
        "date": "11.06.2026",
        "headline": "Retter manglende navn på kjøretøy",
        "title": "Parkering/kjøretøy teller nå manglende navn og område fra hele tabellen",
        "description": (
            "Kjøretøysiden viste for lavt antall manglende navn fordi V2-kortet telte bare de 250 sist observerte "
            "kjøretøyene. Live kontroll viste 36 740 kjøretøy totalt, 9 675 blanke navn og 1 878 med verdien "
            "'ikke funnet'. Backend teller nå blanke felt og 'ikke funnet' som manglende, og V2 bruker fulltabell-counts "
            "for både navn og område."
        ),
        "applications": [
            "Backend V2-modul (main.py): bruker fulltabell-counts for manglende navn og område på parkering/kjøretøy.",
            "Parkeringsoppslag (main.py): oppslagstabeller og verktøytellinger bruker samme mangler-definisjon som API-et.",
            "Buildlogg (build_log.py): registrerer build 1120.",
        ],
        "request": "parkering/kjøretøy, at bare 58 mangler navn må være helt feil",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Fant at tallet 58 var manglende navn blant siste 250 kjøretøy, ikke hele datagrunnlaget.",
            "Endrer mangler-definisjon slik at blankt felt og 'ikke funnet' teller som manglende.",
            "Endrer V2-kortene til å vise total mangler-count fra hele kjøretøytabellen.",
            "Endrer Parkering > Oppslag slik at verktøytelling og listene bruker samme fulltabell-logikk.",
            "Forventet live-tall etter deploy er om lag 11 553 manglende navn og 11 047 manglende områder med dagens data.",
        ],
    },
    {
        "version": "1",
        "build": "1119",
        "date": "10.06.2026",
        "headline": "Flytter gamle innganger til Desktop V2",
        "title": "Gamle konto-, AI- og modul-URLer peker naa inn i nytt rammeverk",
        "description": (
            "Gjennomgangen av gamle HTML-innganger er strammet opp slik at brukerflyten holder seg i Desktop V2. "
            "Profilmenyen peker ikke lenger til /konto, gamle konto- og AI-visninger videresendes til Admin, "
            "lysinnstillinger lastes i V2, og gamle modulaliaser i React-rutingen sender brukeren til riktig ny side."
        ),
        "applications": [
            "Backend-ruter (main.py): gamle GET-visninger for konto, AI, energi testside og lysinnstillinger peker til V2.",
            "Desktop V2 appskall (App.tsx): profilmeny og legacy-aliaser rutes internt til nye modulsider.",
            "Buildlogg (build_log.py): registrerer build 1119.",
        ],
        "request": "sorg for at alt er over i nytt rammeverk",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjoring",
        "changes": [
            "Endrer profilmenyen fra gammel /konto/oversikt til V2 Admin > Brukere.",
            "Videresender gamle /konto/*-sider til tilsvarende Admin-sider.",
            "Videresender gamle /ai/*-sider til Admin > AI.",
            "Lar /lys/innstillinger laste Desktop V2 i stedet for gammel template.",
            "Legger React-redirects for gamle status-, parkering-, energi-, lys-, ventilasjon- og renhold-aliaser.",
            "Beholder API- og POST-ruter som fortsatt trengs for drift og lagring.",
        ],
    },
    {
        "version": "1",
        "build": "1118",
        "date": "10.06.2026",
        "headline": "Retter QNAP-deploy for rene miljøeksempler",
        "title": "Deploy bevarer ikke lenger .env.example som hemmelig miljøfil",
        "description": (
            "Kontroll av funksjonalitet og drift viste at QNAP-worktree ble stående dirty fordi deployscriptet tok "
            "backup og restore av easypark_downloader/.env.example via det brede mønsteret .env.*. Det gjorde at "
            "tracked eksempelkonfig kunne overskrives etter git reset. Deployscriptet hopper nå eksplisitt over "
            ".env.example ved backup og restore, slik at QNAP kan holde ren git-status samtidig som reelle .env-filer "
            "fortsatt bevares."
        ),
        "applications": [
            "Deployscript (scripts/deploy-qnap.ps1): ekskluderer .env.example og */.env.example fra miljøfil-backup og restore.",
            "Buildlogg (build_log.py): registrerer build 1118.",
        ],
        "request": "kontroller hele løsningen i forhold til funksjonalitet og hastighet",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Fant at QNAP hadde modifisert easypark_downloader/.env.example etter deploy.",
            "Årsaken var at deployscriptet behandlet .env.example som en lokal hemmelig miljøfil.",
            "La inn eksplisitt skip av .env.example i begge backup-/restore-løkkene.",
            "Bevarer fortsatt faktiske .env-filer og dataområder under deploy.",
        ],
    },
    {
        "version": "1",
        "build": "1117",
        "date": "10.06.2026",
        "headline": "Rydder og effektiviserer CSS-laget",
        "title": "Visuell overstyring flyttes ut av hoved-CSS og komprimeres med felles selektorer",
        "description": (
            "CSS-laget etter den visuelle oppgraderingen er ryddet. Den store 1116-overstyringen er flyttet ut av "
            "styles.css og inn i et eget visual-refresh-lag som lastes etter base-CSS. Selektorer som gjorde samme "
            "jobb på mange komponenter er samlet med :is(), og gamle base-duplikater som nå bare ble overstyrt er "
            "fjernet. Resultatet er tydeligere ansvarsdeling mellom struktur-CSS og visuell chrome, samtidig som "
            "frontend-bundlen blir noe mindre."
        ),
        "applications": [
            "Desktop V2 importrekkefølge (main.tsx): laster visual-refresh.css etter styles.css.",
            "Desktop V2 base-CSS (styles.css): fjerner den store nederste overstyringsblokken og trygge dupliserte chrome-regler.",
            "Desktop V2 visuelt lag (styles/visual-refresh.css): samler 1116-uttrykket i et eget, komprimert CSS-lag.",
            "Buildlogg (build_log.py): registrerer build 1117.",
        ],
        "request": "effektiviser og rydd opp i css",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Flytter visuelle overstyringer ut av styles.css.",
            "Legger nytt visual-refresh.css som eget ansvarlig lag for appens moderne uttrykk.",
            "Komprimerer repeterte selector-lister med :is().",
            "Fjerner dupliserte kort-, tabell- og grafregler fra base-CSS der visual-laget nå er autoritativt.",
            "Reduserer CSS-bundlen fra omtrent 51,6 kB til omtrent 50,7 kB i produksjonsbuild.",
        ],
    },
    {
        "version": "1",
        "build": "1116",
        "date": "10.06.2026",
        "headline": "Visuell hovedoppgradering av Desktop V2",
        "title": "Appen får lettere flater, tydeligere kort, bedre tabeller og mer ryddige grafer",
        "description": (
            "Desktop V2 er visuelt strammet opp som en samlet revisjon. Oppgraderingen samler farger, radius, skygger "
            "og komponentuttrykk i felles tokens, gjør venstremeny og toppfaner mer presise, gir kort og statusflater "
            "tydeligere hierarki, og rydder tabeller og grafer slik at applikasjonen fremstår mer profesjonell og "
            "konsekvent på tvers av status, moduler, omsetning, ventilasjon og admin."
        ),
        "applications": [
            "Desktop V2 design tokens (designTokens.ts og tokens.css): oppdaterer farger, radius, skygger og Ant Design-komponenttema.",
            "Desktop V2 appskall (layout.css): forbedrer venstremeny, logoområde, toppbar, profilknapp og modulfaner.",
            "Desktop V2 felles CSS (styles.css): oppgraderer kort, statusperioder, støttefliser, tabeller, skjemaelementer, hover/fokus og informasjonsflater.",
            "Desktop V2 grafer (ModuleVisuals.tsx, RevenueMonthPage.tsx, StatusComparisonPage.tsx og VentilationPage.tsx): gir tooltip, legend, akser og grid mer ryddig og felles uttrykk.",
            "Buildlogg (build_log.py): registrerer build 1116.",
        ],
        "request": "da en grundig visuell oppgradering",
        "work_duration": "ca. 55 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Løfter grunnpaletten til et lysere og mer kontrollert dashboard-uttrykk.",
            "Gir venstremeny, aktiv modul og profilknapp mer presis visuell respons.",
            "Standardiserer kort med felles radius, skygge, accentlinjer og roligere typografi.",
            "Rydder statusforsiden med klarere periodekort, datakildeindikator, støttefliser og lister.",
            "Forbedrer tabeller med tydeligere hoder, hover og avstand.",
            "Forbedrer grafene med bedre tooltip, legend, akseavstand, grid og søyle-/linjefokus.",
            "Kjører visuell mock-render i browser for status og modulside før deploy.",
        ],
    },
    {
        "version": "1",
        "build": "1115",
        "date": "10.06.2026",
        "headline": "Synliggjør datakvalitet på statusforsiden",
        "title": "Statuslinjen viser nå datakilder OK/treg/feil med klikk til detaljer",
        "description": (
            "Statusforsiden får en kompakt datakildeindikator i toppstatusen. Den viser hvor mange datakilder som er "
            "OK av totalt antall, markerer varsel/feil med egen farge og lenker direkte til Admin > Datakilder. "
            "Dermed blir kvaliteten på datagrunnlaget synlig før man tolker dagens tall."
        ),
        "applications": [
            "Desktop V2 status (OverviewPage.tsx): beregner datakildestatus og viser en klikkbar indikator i statuslinjen.",
            "Desktop V2 CSS (styles.css): legger inn kompakt OK/varsel/feil-styling for datakildeindikatoren.",
            "Buildlogg (build_log.py): registrerer build 1115.",
        ],
        "request": "fortsett og gjør alt du har foreslått uten å stoppe",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Legger datakildeindikator ved siden av sist oppdatert på statusforsiden.",
            "Viser antall OK-datakilder av totalt antall.",
            "Markerer varsel og feil med gul eller rød status.",
            "Lenker indikatoren direkte til Admin > Datakilder for detaljert feilsøk.",
        ],
    },
    {
        "version": "1",
        "build": "1114",
        "date": "10.06.2026",
        "headline": "Gjør domenefarger og forklaringslenker mer presise",
        "title": "Aktiv modul får riktig farge og sentrale kort peker eksplisitt til grunnlaget",
        "description": (
            "Neste helhetssteg strammer sammenheng mellom område, farge og forklaring. Aktiv modul setter nå "
            "aksentfarge for venstremeny og toppfaner, slik at Parkering, Soling, Energi, Omsetning, Ventilasjon "
            "og Lys følger samme fargelogikk overalt. Backend sender også eksplisitte href-er for de viktigste "
            "kortene, og frontend skjuler lenker som bare ville sendt brukeren tilbake til samme side."
        ),
        "applications": [
            "Desktop V2 appskall (App.tsx, layout.css og tokens.css): aktiv modul styrer aksentfarge i meny og toppfaner.",
            "Desktop V2 kortlogikk (ModuleVisuals.tsx og domainModel.ts): fjerner selvlenker og beholder bare nyttige forklaringsklikk.",
            "fibaro10 backend (main.py): legger eksplisitte href-er på sentrale kort for soling, parkering, omsetning, energi, ventilasjon, lys, renhold og admin.",
            "Buildlogg (build_log.py): registrerer build 1114.",
        ],
        "request": "fortsett og gjør alt du har foreslått uten å stoppe",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Setter modulspesifikk aksentfarge for hovedmeny og toppfaner.",
            "Parkering bruker blå, soling gul/oransje, energi grønn, omsetning rød, ventilasjon blågrønn og lys gul.",
            "Legger eksplisitte forklaringslenker på de mest brukte modul-kortene.",
            "Hindrer at kort markeres klikkbare når lenken bare peker til samme side.",
            "Beholder frontendens fallback-lenker som sikkerhet der backend ikke har eksplisitt href ennå.",
        ],
    },
    {
        "version": "1",
        "build": "1113",
        "date": "10.06.2026",
        "headline": "Strammer helhet, domener og forklarende klikk",
        "title": "Navigasjon, fargebruk og modul-kort får felles logikk",
        "description": (
            "Desktop V2 er ryddet videre mot en mer konsekvent helhet. Status er registrert som intern toppside uten "
            "å komme tilbake i hovedmenyen, Omsetning har fått sammenligning som logisk underside, og modul-kortene "
            "bruker samme domenelabel, hover og klikkmønster som statuskortene. Kort uten eksplisitt backend-lenke "
            "peker nå til mest relevante forklaringsside ut fra modul, tone og korttittel."
        ),
        "applications": [
            "Desktop V2 navigasjon (moduleViews.ts og App.tsx): rydder status som intern side, flytter sammenligning under Omsetning og sorterer underfaner mer logisk.",
            "Desktop V2 domenemodell (domainModel.ts): samler domene-labels og standardlenker for kortforklaringer.",
            "Desktop V2 metrikkort (MetricCard.tsx og ModuleVisuals.tsx): bruker felles domenelabel, tag, hover og klikkadferd.",
            "Desktop V2 moduler (ModulePage.tsx): sender modul og aktiv underside inn i kortkomponenten for riktig standardlenke.",
            "Desktop V2 status (OverviewPage.tsx og StatusComparisonPage.tsx): sender sammenligningsklikk til Omsetning/Sammenligning.",
            "Desktop V2 CSS (styles.css): gjør metrikkortene visuelt mer konsekvente på tvers av domener.",
            "fibaro10 backend (main.py): gjør api_card klar for eksplisitte href-lenker uten å endre eksisterende kall.",
            "Buildlogg (build_log.py): registrerer build 1113.",
        ],
        "request": "gjør alt sammen slik du foreslår",
        "work_duration": "ca. 35 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Registrerer Status som intern toppside slik logo-routing og aktiv modul-logikk blir ryddig.",
            "Legger Omsetning/Sammenligning inn som egen logisk underside for forklarende tidslinjer.",
            "Sorter underfanene for Parkering og Soling etter daglig bruk, analyse og register.",
            "Samler domenelabel og standardlenker for parkering, soling, energi, ventilasjon, lys, renhold, admin og omsetning.",
            "Gjør modul-kort klikkbare til relevant forklaringsside når backend ikke sender eksplisitt href.",
            "Gir alle metrikkort felles domenetag, hover og pilindikator når de kan åpnes.",
        ],
    },
    {
        "version": "1",
        "build": "1112",
        "date": "10.06.2026",
        "headline": "Forenkler topp og terskelfarger i parkeringsdagslinje",
        "title": "Dagslinjen starter på datovelger og beleggstolper får 25-skala",
        "description": (
            "Parkeringsdagslinjen viser nå bare relevant innhold fra datovelgeren og nedover. Beleggstolpene har fast "
            "skala opp til 25 biler, der normaldelen er blå, delen over 20 biler markeres oransje og delen over 23 "
            "biler markeres rødt. Fargene ligger dermed kun i øvre del av stolpen når tersklene passeres."
        ),
        "applications": [
            "fibaro10 backend (main.py): eksponerer fast occupancyScaleMax=25 i parkingTimeline-payloaden.",
            "Desktop V2 API-kontrakt (api.ts): legger occupancyScaleMax inn i parkeringstidslinjetypen.",
            "Desktop V2 modulside (ModulePage.tsx): skjuler modulknapper og toppkort for parkeringsdagslinjen.",
            "Desktop V2 parkering (ParkingTimelinePanel.tsx): tegner belegg som stablede terskelsegmenter.",
            "Desktop V2 CSS (styles.css): erstatter helfarget beleggstolpe med blå/oransje/rød segmentstolpe.",
            "Buildlogg (build_log.py): registrerer build 1112.",
        ],
        "request": (
            "de to øverste radene på siden er unødvendig ta bort alt over dato velger. den raden som viser stolper "
            "for belegg bør ha fast skala opptil 25 biler og bør være oransje når det går over 20 og rød når det "
            "går over 23 / altså øverste delen på stolpen"
        ),
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Fjerner handlinger og nøkkelkort over datovelgeren på Parkering/Dagslinje.",
            "Setter beleggskurven til fast 0-25-skala i stedet for å skalere mot 23 plasser.",
            "Tegner blå stolpedel for 0-20 biler, oransje toppdel for 21-23 biler og rød toppdel over 23 biler.",
            "Oppdaterer tooltipen for belegg med at skalaen er 25 og kapasiteten er 23.",
        ],
    },
    {
        "version": "1",
        "build": "1111",
        "date": "10.06.2026",
        "headline": "Rydder parkeringsdagslinje til ren kapasitetsvisning",
        "title": "Bilnummer fjernes fra tidsblokkene og 11+12 vises som 23 spor",
        "description": (
            "Parkeringsdagslinjen er strammet inn visuelt. Siden viser nå én samlet kapasitetsmodell med 23 spor "
            "i stedet for to virtuelle rekker. Synlige bilnummer i blokkene er fjernet, og blokkene fungerer som "
            "rene tidsmarkører med detaljer ved hover/klikk."
        ),
        "applications": [
            "fibaro10 backend (main.py): endrer parkeringsdagslinjen til én samlet 23-sporsmodell og rydder tooltipinnhold.",
            "Desktop V2 parkering (ParkingTimelinePanel.tsx): fjerner synlige bilnummer og 11+12-skille fra visningen.",
            "Desktop V2 CSS (styles.css): gjør parkeringsblokkene lavere og renere uten tekstinnhold.",
            "Buildlogg (build_log.py): registrerer build 1111.",
        ],
        "request": "bil nummerne gjør det rotete og ingen nytte. jeg synes også det bør ryddes litt i hvordan det fylles , og ingen hensikt i å skille det i to rader når du setter det opp slik",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Samler parkeringsdagslinjen til én kapasitetsgruppe med 23 spor.",
            "Fjerner synlig reg.nr-tekst fra alle parkeringsblokker.",
            "Fjerner reg.nr fra tooltipens hovedtekst, men beholder klikk til filtrert parkeringsliste.",
            "Endrer sporfordeling til å gjenbruke det sist frigitte ledige sporet for roligere fylling.",
            "Fjerner den kunstige kjørefelt-/11+12-markeringen fra UI-et.",
        ],
    },
    {
        "version": "1",
        "build": "1110",
        "date": "10.06.2026",
        "headline": "Retter toppbelegg i parkeringsdagslinje",
        "title": "Beleggskurven teller samtidige parkeringer per 15-minutters midtpunkt",
        "description": (
            "Etter produksjonsverifikasjon av build 1109 ble det funnet at beleggskurven telte alle parkeringer som "
            "berørte et 15-minutters intervall. Det kunne gi for høy toppverdi selv når plassfordelingen ikke hadde "
            "overflow. Beregningen teller nå parkeringer som faktisk er aktive på midtpunktet i hver bøtte."
        ),
        "applications": [
            "fibaro10 backend (main.py): korrigerer occupancy-beregningen for parkeringsdagslinjen.",
            "Buildlogg (build_log.py): registrerer build 1110 som verifiseringsretting etter build 1109.",
        ],
        "request": "lag en visuell fremstilling kreativt for 23 dvs 11+12 parkeringsplasser tilsvarende dagslinje på soling. har du en god ide? kjør på overrask meg. skal ligge som egen side under parkering.",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Teller samtidige parkeringer ved midtpunktet i hvert 15-minutters intervall.",
            "Hindrer at toppbelegg blir kunstig høyere enn faktisk samtidighet.",
            "Beholder 23-plassfordelingen og resten av parkeringsdagslinjen uendret.",
        ],
    },
    {
        "version": "1",
        "build": "1109",
        "date": "10.06.2026",
        "headline": "Lager parkeringsdagslinje med 23 plasser",
        "title": "Parkering får visuell dagslinje fordelt på 11 + 12 virtuelle plasser",
        "description": (
            "Det er lagt inn en egen side under Parkering som viser døgnet som 23 parkeringsplasser fordelt på "
            "to rekker. Siden bruker faktiske EasyPark-økter, fordeler dem deterministisk på første ledige plass "
            "og viser samtidig beleggskurve, toppbelegg, omsetning og beleggstid."
        ),
        "applications": [
            "fibaro10 backend (main.py): bygger parkingTimeline-payload med 23 plasser, beleggskurve og dagsoppsummering.",
            "Desktop V2 API-kontrakt (api.ts): legger til typer for parkeringsdagslinje.",
            "Desktop V2 parkering (ParkingTimelinePanel.tsx): ny visuell side for 11 + 12 parkeringsplasser.",
            "Desktop V2 modulside og meny (ModulePage.tsx, moduleViews.ts): kobler /parkering/dagslinje inn i navigasjon og datohåndtering.",
            "Desktop V2 CSS (styles.css): kompakt tidslinjedesign med blå parkeringsprofil og 23 plasser.",
            "Buildlogg (build_log.py): registrerer build 1109.",
        ],
        "request": "lag en visuell fremstilling kreativt for 23 dvs 11+12 parkeringsplasser tilsvarende dagslinje på soling. har du en god ide? kjør på overrask meg. skal ligge som egen side under parkering.",
        "work_duration": "ca. 45 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Legger til Parkering/Dagslinje som eget menypunkt.",
            "Fordeler parkeringer på 23 virtuelle plasser etter første-ledige-prinsipp.",
            "Viser rekke A med 11 plasser og rekke B med 12 plasser.",
            "Tegner klikkbare parkeringsblokker med reg.nr, tid, varighet og beløp i tooltip.",
            "Viser beleggskurve per 15 minutter og nøkkeltall for toppbelegg, beleggstid og utnyttelse.",
        ],
    },
    {
        "version": "1",
        "build": "1108",
        "date": "10.06.2026",
        "headline": "Sender viftestatus i ventilasjon dagsamples",
        "title": "Avfuktermarkering får faktisk fan_avfukter-data fra backend",
        "description": (
            "Backend sender nå viftestatusfeltene med i day.samples for ventilasjon/dagslogg. Forrige build la "
            "frontenden klar til å tegne avfukterperioder fra fan_avfukter, men API-payloaden manglet selve "
            "fan_avfukter-verdiene i samples-listen."
        ),
        "applications": [
            "fibaro10 backend (main.py): inkluderer fan_vip, fan_2etg, fan_tak og fan_avfukter i ventilasjonens day.samples.",
            "Desktop V2 ventilasjon (VentilationPage.tsx): harmoniserer tooltiptekst for aktive intervaller.",
            "Buildlogg (build_log.py): registrerer build 1108 som datakorrigering for avfuktermarkering.",
        ],
        "request": "det funker ikke",
        "work_duration": "ca. 10 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Legger viftestatusfeltene inn i sample-payloaden som frontenden bruker.",
            "Sikrer at fan_avfukter faktisk er tilgjengelig på ventilasjon/dagslogg.",
            "Lar samples med bare viftestatus fortsatt være gyldige for tidslinjen.",
            "Beholder tidligere eventbasert fallback.",
            "Endrer intervalltooltip til 'aktiv' for både event- og samplebaserte perioder.",
        ],
    },
    {
        "version": "1",
        "build": "1107",
        "date": "10.06.2026",
        "headline": "Markerer avfukterperioder fra dagsmålinger",
        "title": "Avfukter får samme på-markering som viftelinjene",
        "description": (
            "Ventilasjon/dagslogg bruker nå også sampleverdiene for fan_avfukter når aktive intervaller tegnes. "
            "Dermed vises avfukteren som på mellom målepunktene selv om det mangler egne start/stopp-hendelser."
        ),
        "applications": [
            "Desktop V2 API-kontrakt (api.ts): eksponerer sample_attr på ventilasjonsvifter.",
            "Desktop V2 ventilasjon (VentilationPage.tsx): lager aktive intervaller fra dagsmålingenes boolske viftestatus.",
            "Buildlogg (build_log.py): registrerer build 1107 som eget avfuktersteg.",
        ],
        "request": "du må gjøre det sammme med avfukeren",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Bruker sample_attr fra backend for å finne riktig statusfelt per vifte.",
            "Tegner aktive intervaller fra fan_avfukter i dagsmålingene.",
            "Faller tilbake til hendelsesbaserte intervaller når sampledata mangler.",
            "Beholder start/stopp-punktene som før.",
            "Gjør dette generelt for alle ventilasjonslinjer, med avfukter som viktigste effekt.",
        ],
    },
    {
        "version": "1",
        "build": "1106",
        "date": "10.06.2026",
        "headline": "Markerer på-perioder i ventilasjon dagslogg",
        "title": "Viftelinjene viser nå aktive intervaller mellom start og stopp",
        "description": (
            "På ventilasjon/dagslogg markeres nå perioden mellom PÅ- og AV-punktene i viftelinjene. Dette gjør det "
            "lettere å se når hver vifte faktisk har stått på, uten å måtte lese enkeltpunktene manuelt."
        ),
        "applications": [
            "Desktop V2 ventilasjon (VentilationPage.tsx): beregner på-intervaller fra fanEvents og tegner dem i tidslinjen.",
            "Desktop V2 CSS (styles.css): legger visuell stil for aktive vifteintervaller bak start/stopp-punktene.",
            "Buildlogg (build_log.py): registrerer build 1106 som eget ventilasjonsforbedringssteg.",
        ],
        "request": "dagslogg ventilasjon der vil jeg ha markert mellom punktene slik at man ser den står på enkelt",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Beregner intervaller fra PÅ til neste AV per vifte.",
            "Lar åpne PÅ-intervaller gå til nå-markøren for i dag eller døgnslutt for historiske dager.",
            "Tegner fargede, diskrete segmenter bak hendelsespunktene.",
            "Beholder start/stopp-punktene og tooltipene.",
            "Bruker samme tidsakseposisjon som eksisterende viftehendelser.",
        ],
    },
    {
        "version": "1",
        "build": "1105",
        "date": "10.06.2026",
        "headline": "Rydder kompakt ventilasjonssample visuelt",
        "title": "Gjør toppfeltet på ventilasjon dagslogg tettere og mer lesbart",
        "description": (
            "Den kompakte samplevisningen på ventilasjon/dagslogg er ryddet visuelt. Sampletid, måleverdier, vær "
            "og viftestatus har fått tydeligere soner, jevnere kolonner og mindre unødvendig luft."
        ),
        "applications": [
            "Desktop V2 ventilasjon (VentilationPage.tsx): justerer kompakt snapshot-markup og tooltiptekst.",
            "Desktop V2 CSS (styles.css): strammer inn layout, chip-design, måleverdiggrid og viftestatuslinje.",
            "Buildlogg (build_log.py): registrerer build 1105 som eget visuelt oppryddingssteg.",
        ],
        "request": "kan du rydde opp i dette visuelt",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Gjør sampletid og modus til en egen kompakt informasjonsblokk.",
            "Legger måleverdiene i faste grid-kolonner i stedet for ujevn flexflyt.",
            "Gir værfeltet en tydeligere høyresone.",
            "Strammer inn viftestatusrad og tag-størrelser.",
            "Beholder eksisterende data og funksjonell oppførsel.",
        ],
    },
    {
        "version": "1",
        "build": "1104",
        "date": "10.06.2026",
        "headline": "Typefester API-kontrakter mellom backend og frontend",
        "title": "Gjør buildlogg- og health-payloads eksplisitte på begge sider",
        "description": (
            "Backend har fått egne TypedDict-kontrakter for buildlogg og health, og funksjonene som bygger disse "
            "payloadene returnerer nå konkrete kontrakttyper. Frontendens API-lag har tilsvarende TypeScript-typer "
            "for health, og dokumentasjonen beskriver hvor kontraktene skal holdes synkronisert."
        ),
        "applications": [
            "API-kontrakter (api_types.py): TypedDict-definisjoner for buildlogg, buildtabell og health.",
            "Backend kontraktbyggere (api_contracts.py, observability.py, build_log.py): returnerer eksplisitte payloadtyper.",
            "Desktop V2 API-lag (desktop_v2/src/api.ts): legger HealthResponse og fetchHealth til frontendkontrakten.",
            "Dokumentasjon (docs/api-kontrakter.md): beskriver eierfiler og synkroniseringsregel.",
            "Tester (tests/test_api_types.py): låser sentrale kontraktfelt.",
            "Buildlogg (build_log.py): registrerer build 1104 som typekontrakt-trinn.",
        ],
        "request": "altså jeg vil at du skal gjøre alle trinnene etterhverandre ett nytt build for hver. jeg vil at du skal gjøre det uten å stoppe",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppretter api_types.py som backendens typekontrakt for sentrale payloads.",
            "Typefester buildlogg og health-kontrakter i backend.",
            "Legger HealthResponse og fetchHealth i frontendens API-lag.",
            "Dokumenterer kontraktplassering og vedlikeholdsregel.",
            "Legger unit-tester for kontraktfeltene.",
        ],
    },
    {
        "version": "1",
        "build": "1103",
        "date": "10.06.2026",
        "headline": "Herder HTTP-svar med sikkerhetsheadere",
        "title": "Samler browser-sikkerhet i egen modul og legger den på alle svar",
        "description": (
            "Applikasjonen setter nå en samlet standardpakke med sikkerhetsheadere på HTTP-svar. Dette begrenser "
            "MIME-sniffing, framing, referrer-lekkasje og uønskede browser capabilities. HSTS er bevisst valgfritt "
            "via miljøvariabel siden løsningen også kjøres på interne HTTP-adresser."
        ),
        "applications": [
            "Sikkerhetsmodul (security.py): eier header-policy og HSTS opt-in.",
            "fibaro10 backend (main.py): legger sikkerhetsheadere på alle HTTP-svar via middleware.",
            "Kvalitetssjekk (scripts/check-local.ps1): kompilerer security.py sammen med resten av backend.",
            "Tester (tests/test_security.py): verifiserer standardheadere, HSTS opt-in og at eksisterende headere ikke overskrives.",
            "Buildlogg (build_log.py): registrerer build 1103 som eget sikkerhetstrinn.",
        ],
        "request": "altså jeg vil at du skal gjøre alle trinnene etterhverandre ett nytt build for hver. jeg vil at du skal gjøre det uten å stoppe",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppretter security.py med felles sikkerhetsheader-policy.",
            "Legger HTTP-middleware som bruker policyen på alle svar.",
            "Holder Strict-Transport-Security av som standard for intern HTTP-drift.",
            "Legger SECURITY_HSTS_ENABLED og SECURITY_HSTS_MAX_AGE_SECONDS som miljøstyring.",
            "Legger enhetstester for policyen.",
        ],
    },
    {
        "version": "1",
        "build": "1102",
        "date": "10.06.2026",
        "headline": "Legger til backup- og restore-verifisering",
        "title": "Kan teste QNAP-backup med midlertidig PostgreSQL-restore",
        "description": (
            "Det er lagt til et ikke-destruktivt verifiseringsscript for QNAP-backup. Scriptet kjører backup, "
            "sjekker backupmappen og SQL-dumpen, og kan lese dumpen inn i en midlertidig PostgreSQL-database før "
            "testdatabasen slettes igjen. Produksjonsdata overskrives ikke."
        ),
        "applications": [
            "Backup-verifisering (scripts/verify-qnap-backup.ps1): kjører backup og valgfri restore dry-run på QNAP.",
            "QNAP backup (scripts/qnap-backup.sh): gjenbrukes som faktisk backupkilde.",
            "Dokumentasjon (docs/utviklingsoppsett.md): beskriver restore-test og SkipSqlRestore.",
            "Buildlogg (build_log.py): registrerer build 1102 som eget backup/restore-trinn.",
        ],
        "request": "altså jeg vil at du skal gjøre alle trinnene etterhverandre ett nytt build for hver. jeg vil at du skal gjøre det uten å stoppe",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppretter scripts/verify-qnap-backup.ps1.",
            "Verifiserer at backupmappen og SQL-dump finnes.",
            "Legger støtte for midlertidig PostgreSQL restore-test og automatisk cleanup.",
            "Dokumenterer restore-testen i utviklingsoppsettet.",
            "Beholder -SkipSqlRestore for rask filkontroll uten database-restore.",
        ],
    },
    {
        "version": "1",
        "build": "1101",
        "date": "10.06.2026",
        "headline": "Etablerer frontend design-tokens",
        "title": "Samler domene-, semantikk- og Ant Design-farger i ett grunnlag",
        "description": (
            "Desktop V2 har fått et tydeligere designgrunnlag. Farger og Ant Design-theme er samlet i "
            "designTokens.ts, CSS root-variabler er flyttet til tokens.css, og tone-klasser bruker nå et felles "
            "--tone-color-token. Dette gir mer konsekvent fargebruk uten å redesigne skjermbildene."
        ),
        "applications": [
            "Desktop V2 tokens (designTokens.ts): semantiske farger, domenefarger, labels og Ant Design-theme.",
            "Desktop V2 CSS (styles/tokens.css): eier root-variabler og tone-token.",
            "Desktop V2 appstart (main.tsx): bruker felles antdTheme.",
            "Kompatibilitet (domainColors.ts): re-eksporterer domainColors slik eksisterende grafer fortsetter å fungere.",
            "CSS (styles.css/layout.css): fjerner dupliserte root-farger og bruker --tone-color på tone-klasser.",
        ],
        "request": "altså jeg vil at du skal gjøre alle trinnene etterhverandre ett nytt build for hver. jeg vil at du skal gjøre det uten å stoppe",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppretter designTokens.ts for frontendens farge- og theme-grunnlag.",
            "Oppretter styles/tokens.css for CSS-variabler.",
            "Flytter Ant Design-theme ut av main.tsx.",
            "Beholder domainColors API for eksisterende grafkode.",
            "Samler tone-klasser rundt --tone-color.",
        ],
    },
    {
        "version": "1",
        "build": "1100",
        "date": "10.06.2026",
        "headline": "Forbedrer health og observability",
        "title": "Health viser build, commit, database og valgfrie datakildedetaljer",
        "description": (
            "/health er utvidet fra en statisk lagringsliste til et tydeligere driftsendepunkt. Det viser "
            "appversjon, build, commit, starttidspunkt og databasekontroll. Med details=true kan det også vise "
            "importjobbstatus uten at Docker healthcheck trenger å gjøre tunge oppslag."
        ),
        "applications": [
            "Observability (observability.py): ren health-kontrakt og sentral lagringsliste.",
            "fibaro10 backend (main.py): /health kontrollerer database og kan returnere datakildestatus med details=true.",
            "Docker (Dockerfile, docker-compose.qnap.yml): APP_COMMIT kan sendes inn som build-arg.",
            "Deploy (scripts/deploy-qnap.ps1): sender aktiv git-commit inn i Docker-builden.",
            "Tester (tests/test_observability.py): dekker health-payload og storage-tabeller.",
        ],
        "request": "altså jeg vil at du skal gjøre alle trinnene etterhverandre ett nytt build for hver. jeg vil at du skal gjøre det uten å stoppe",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppretter observability.py med health_payload og STORAGE_TABLES.",
            "Utvider /health med build, commit, starttidspunkt og SELECT 1 databasekontroll.",
            "Legger details=true for importjobbstatus uten å gjøre standard healthcheck tyngre.",
            "Sender APP_COMMIT inn ved Docker-build på QNAP.",
            "Legger observability-tester og kompilering i kvalitetssjekken.",
        ],
    },
    {
        "version": "1",
        "build": "1099",
        "date": "10.06.2026",
        "headline": "Legger til Playwright UI-smoke-test",
        "title": "Tester bygget desktopapp med mockede API-data før deploy",
        "description": (
            "Desktop V2 har fått en Playwright-basert smoke-test som starter en lokal mockserver mot ferdigbygget "
            "dist, åpner buildloggen og en generisk modulside, og verifiserer at appskall, lazy-loaded ruter, "
            "kort, grafseksjon og tabellinnhold rendrer uten browser-feil."
        ),
        "applications": [
            "Desktop V2 smoke-test (desktop_v2/scripts/smoke-ui.mjs): ny Playwright-test med lokal mockserver.",
            "Frontend pakke (desktop_v2/package.json/package-lock.json): legger til Playwright og scriptet npm run smoke:ui.",
            "Pre-deploy (scripts/check-local.ps1): kjører UI smoke etter frontend build.",
            "GitHub CI (.github/workflows/ci.yml): installerer Chromium før kvalitetssjekk.",
            "Lokal setup (scripts/setup-local-dev.ps1): installerer frontend-avhengigheter og Playwright Chromium på ny maskin.",
        ],
        "request": "altså jeg vil at du skal gjøre alle trinnene etterhverandre ett nytt build for hver. jeg vil at du skal gjøre det uten å stoppe",
        "work_duration": "ca. 30 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Legger til Playwright som dev-avhengighet i desktop_v2.",
            "Oppretter smoke-ui.mjs som tester /admin/build og /soling/oversikt mot mockede API-svar.",
            "Kobler npm run smoke:ui inn i scripts/check-local.ps1.",
            "Oppdaterer GitHub CI til å installere Playwright Chromium.",
            "Oppdaterer lokal setup slik nye maskiner får nødvendig browser-runtime.",
        ],
    },
    {
        "version": "1",
        "build": "1098",
        "date": "10.06.2026",
        "headline": "Legger til kontrollert migrasjonsrunner",
        "title": "Kan liste, tørrkjøre og kjøre SQL-migrasjoner med schema_migrations-sporing",
        "description": (
            "Migrasjonsstrukturen er utvidet med en runner som oppdager SQL-filer, holder oversikt i "
            "schema_migrations og kan kjøres manuelt med --list eller --dry-run før reell kjøring. "
            "Runneren er ikke koblet automatisk inn i deploy ennå, slik at databaseendringer forblir et kontrollert steg."
        ),
        "applications": [
            "Migrasjonsrunner (migration_runner.py): oppdager, filtrerer og kjører SQL-migrasjoner.",
            "CLI (scripts/run-migrations.py): kommando for list, dry-run og kjøring mot DATABASE_URL.",
            "Migrasjonsgenerator (scripts/new-migration.ps1): lager SQL-filer som passer runnerens transaksjonshåndtering.",
            "Dokumentasjon (migrations/README.md): viser hvordan migrasjoner opprettes og kjøres.",
            "Tester (tests/test_migration_runner.py): dekker filoppdagelse, sortering og pending-logikk.",
        ],
        "request": "altså jeg vil at du skal gjøre alle trinnene etterhverandre ett nytt build for hver. jeg vil at du skal gjøre det uten å stoppe",
        "work_duration": "ca. 25 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppretter migration_runner.py med schema_migrations-sporing.",
            "Oppretter scripts/run-migrations.py for manuell kjøring.",
            "Dokumenterer list/dry-run/run i migrations/README.md.",
            "Justerer ny migrasjonsmal slik at runneren eier transaksjonen.",
            "Legger til tester for migrasjonsoppdagelse og pending-migrasjoner.",
        ],
    },
    {
        "version": "1",
        "build": "1097",
        "date": "10.06.2026",
        "headline": "Innfører GitHub CI for kvalitetssjekk",
        "title": "Kjører Python-, test- og frontendkontroller automatisk på GitHub",
        "description": (
            "Repositoryet har fått en GitHub Actions workflow som installerer Python- og Node-avhengigheter og "
            "kjører samme lokale kvalitetssjekk som brukes før QNAP-deploy. Dette gir tidligere varsling ved "
            "feil på push og pull requests."
        ),
        "applications": [
            "GitHub Actions (.github/workflows/ci.yml): ny CI-workflow for main og pull requests.",
            "Python dev-avhengigheter (requirements-dev.txt): legger til httpx for FastAPI TestClient i CI.",
            "Pre-deploy (scripts/check-local.ps1): gjenbrukes som felles kvalitetssjekk lokalt og i GitHub CI.",
            "Buildlogg (build_log.py): registrerer build 1097 som eget CI-trinn.",
        ],
        "request": "altså jeg vil at du skal gjøre alle trinnene etterhverandre ett nytt build for hver. jeg vil at du skal gjøre det uten å stoppe",
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppretter .github/workflows/ci.yml.",
            "Setter opp Python 3.12 og Node 24 i CI.",
            "Installerer runtime- og dev-avhengigheter før test.",
            "Kjører scripts/check-local.ps1 som felles kvalitetssjekk.",
            "Legger requirements-dev.txt med httpx for FastAPI-integrasjonstest.",
        ],
    },
    {
        "version": "1",
        "build": "1096",
        "date": "10.06.2026",
        "headline": "Legger grunnlag for API- og integrasjonstester",
        "title": "Tester buildlogg-API som kontrakt og FastAPI-rute",
        "description": (
            "Buildlogg-endepunktene har fått en egen ren API-kontraktsmodul som kan testes uten database og "
            "uten FastAPI installert lokalt. Testpakken validerer responsformen alltid, og inneholder i tillegg "
            "en FastAPI TestClient-test som aktiveres automatisk i miljøer der dev-avhengighetene finnes."
        ),
        "applications": [
            "API-kontrakter (api_contracts.py): ny modul for admin/build payloads brukt av både main.py og tester.",
            "fibaro10 backend (main.py): admin/build-endepunktene bruker kontraktsmodulen.",
            "Tester (tests/test_api_contracts.py): kontraktstester og valgfri FastAPI-integrasjonstest.",
            "Pre-deploy (scripts/check-local.ps1): Python-kompilering dekker nye moduler.",
        ],
        "request": "altså jeg vil at du skal gjøre alle trinnene etterhverandre ett nytt build for hver. jeg vil at du skal gjøre det uten å stoppe",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppretter api_contracts.py for testbar API-responsbygging.",
            "Flytter buildlogg-responsene for /api/admin/builds over på kontraktsfunksjoner.",
            "Legger kontraktstester som kjører uten ekstern database.",
            "Legger valgfri FastAPI TestClient-integrasjonstest for miljøer med dev-avhengigheter.",
            "Utvider lokal kvalitetssjekk til å kompilere nye Python-moduler.",
        ],
    },
    {
        "version": "1",
        "build": "1095",
        "date": "10.06.2026",
        "headline": "Deler ut første domenelogikk fra main.py",
        "title": "Flytter tidformattering og Roborock-hjelpere til egne moduler",
        "description": (
            "Første videre oppdeling av main.py er gjort med lav risiko. Rene formatteringsfunksjoner er flyttet "
            "til time_formatting.py, og Roborock-labeling, tidsplanvisning og JSON-formattering er flyttet til "
            "roborock_domain.py. Eksisterende template-filtre og kall beholdes via import i main.py."
        ),
        "applications": [
            "fibaro10 backend (main.py): mindre hovedfil og import av rene hjelpefunksjoner fra domene-/utilitymoduler.",
            "Tidformattering (time_formatting.py): eier lokal/source dato- og tidsformattering.",
            "Roborock-domene (roborock_domain.py): eier Roborock-labels, schedule-tekst og visningshjelpere.",
            "Tester/build (scripts/check-local.ps1): eksisterende kvalitetssjekk validerer flyttingen.",
        ],
        "request": "altså jeg vil at du skal gjøre alle trinnene etterhverandre ett nytt build for hver. jeg vil at du skal gjøre det uten å stoppe",
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Oppretter time_formatting.py for lokal og source-basert dato-/tidsvisning.",
            "Oppretter roborock_domain.py for Roborock-koder, signaltekst, schedule-tekst og formatfiltre.",
            "Kobler main.py til de nye modulene uten å endre template-filterkontrakter.",
            "Lar databaseklasser og API-ruter stå urørt i dette første domenekuttet.",
        ],
    },
    {
        "version": "1",
        "build": "1094",
        "date": "10.06.2026",
        "headline": "Gjennomfører strukturert teknisk kvalitetsløft",
        "title": "Deler kode, tester, deploysjekk og driftskontroller i ryddigere struktur",
        "description": (
            "Den prioriterte forbedringsrekken er gjennomført i rekkefølge. Buildloggen er flyttet ut av "
            "main.py, ModulePage og CSS er delt opp, frontend-sider lastes nå lazy, typebruken er strammet inn, "
            "det er lagt til tester, Docker-healthchecks, bedre logging, migrasjonsstruktur og en fast lokal "
            "kvalitetssjekk som kjøres før QNAP-deploy."
        ),
        "applications": [
            "fibaro10 backend (main.py): mindre hovedfil, import av buildloggmodul etter miljølasting og mer logging ved viktige feil.",
            "fibaro10 buildlogg (build_log.py): egen modul for appversjon, buildnummer, buildhistorikk og normalisering.",
            "Desktop V2 appskall (App.tsx): sidene lastes lazy med felles Suspense-fallback.",
            "Desktop V2 modulsider (ModulePage.tsx): grafikk, filtre og solingstidslinje er flyttet til egne komponenter.",
            "Desktop V2 API-klient (api.ts): felles JsonRecord og ModuleRow-typer for generiske dataflater.",
            "Desktop V2 styling (styles.css, styles/layout.css, styles/build.css): layout og buildlogg-CSS er skilt ut fra hovedstilarket.",
            "Desktop V2 buildkonfig (vite.config.ts): mer presis vendor-chunking for antd og charts.",
            "Docker/QNAP (docker-compose.qnap.yml): healthchecks for fibaro10 og online_dashboard.",
            "Scripts (check-local.ps1, deploy-qnap.ps1, new-migration.ps1): fast lokal kvalitetssjekk før deploy og enkel migrasjonsgenerator.",
            "Tester (tests/test_build_log.py): grunnleggende tester for buildlogg-kontrakten.",
        ],
        "request": "oki gjør alt i denne rekkefølgen",
        "work_duration": "ca. 75 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Flytter BUILD_LOG, APP_BUILD og APP_VERSION ut av main.py og inn i build_log.py.",
            "Flytter ModuleMetric, ModuleChartPanel, ModuleFilterBar og SunTimelinePanel ut av ModulePage.tsx.",
            "Splitter global layout- og buildlogg-CSS ut fra styles.css.",
            "Lazy-loader hovedsidene i desktopappen for bedre oppstart og tydeligere chunking.",
            "Legger til npm-script for typecheck/check og unittest-dekning for buildlogg.",
            "Innfører felles JsonRecord og ModuleRow-typer i frontendens generiske dataflyt.",
            "Legger Docker-healthchecks på /health for fibaro10 og online_dashboard.",
            "Legger inn felles logger og logging av sentrale feil i NTFY, Elvia, AI-søk og EasyPark-import.",
            "Etablerer migrations/versions med README og generator for nye migrasjonsfiler.",
            "Lager scripts/check-local.ps1 og kobler den inn som standard pre-deploy-steg i deploy-qnap.ps1.",
        ],
    },
    {
        "version": "1",
        "build": "1093",
        "date": "10.06.2026",
        "headline": "Teknisk opprydding i appskall og buildlogg",
        "title": "Rydder og optimaliserer kode etter siste funksjonsendringer",
        "description": (
            "Det er gjort en avgrenset vedlikeholdsrunde i desktop V2 og backend. "
            "Appskallet henter nå innlogget bruker én gang og deler data videre til profil og buildfooter. "
            "CSS er trimmet for ubrukte regler, og buildlogg-normalisering i backend er strammet inn."
        ),
        "applications": [
            "Desktop V2 appskall (App.tsx): felles hovedmenydefinisjon og én delt henting av bruker/builddata.",
            "Desktop V2 stilark (styles.css): fjerner ubrukte selektorer og feilreferanse i media-query.",
            "fibaro10 backend (main.py): enklere buildlogg-radbygging og nytt buildinnslag.",
        ],
        "request": (
            "Nå er det igjen tid for at du rydder i kode, både css og annen kode må forbedres, trimmes og "
            "optimaliseres jevnlig"
        ),
        "work_duration": "ca. 20 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Samler brukerhenting i App.tsx slik at profilmeny og buildnummer bruker samme AuthUser-data.",
            "Bygger hovedmeny og valgt meny fra samme moduldefinisjon for mindre repetisjon.",
            "Fjerner ubrukte CSS-regler for app-header-empty og status-support-grid.",
            "Forenkler api_build_log_row slik at den gjenbruker normalized_build_log_entry konsekvent.",
        ],
    },
    {
        "version": "1",
        "build": "1092",
        "date": "10.06.2026",
        "headline": "Buildlogg med klikkbar leveransehistorikk",
        "title": "Gjør buildloggen til et komplett leveransearkiv",
        "description": (
            "Buildloggen i desktop V2 er gjort om fra en generisk tabell til en egen arbeidsflate. "
            "Oversikten viser nå bare dato, build og en kort leveranseoverskrift, mens hver build kan åpnes "
            "for en egen detaljside med full bestilling, endringer, berørte applikasjoner og målefelt for "
            "tidsbruk og kreditter."
        ),
        "applications": [
            "Desktop V2 navigasjon (App.tsx): buildnummer synlig nederst i venstremenyen og nye ruter for buildliste/detalj.",
            "Desktop V2 API-klient (api.ts): egne typer og kall for buildloggoversikt og enkeltbuild.",
            "Desktop V2 buildlogg (BuildLogPage.tsx og BuildDetailPage.tsx): ny tabellvisning og detaljskjerm.",
            "Desktop V2 stilark (styles.css): visuell styling av buildfooter, liste, detaljkort og promptfelt.",
            "fibaro10 backend (main.py): normalisert buildlogg-API, nytt kortfelt for tabelloverskrift og build 1092.",
        ],
        "request": (
            "det er litt mer å gjøre på build logg, jeg vil ha et eget kort felt som passer i en tabell som du lager "
            "en veldig god overskrift. jeg vil også ha et build nummer synlig nederst på venstre menyen. når du går "
            "inn i denne lista skal du få en tabell med dato, build, overskrift. så skal du kunne trykke på det "
            "enkelte og få en pen skjerm med all info om denne builden. jeg vil også ha tid du brukte på å lage den "
            "og hvor mange kreditter det brukte?"
        ),
        "work_duration": "ca. 15 min",
        "credits_used": "Ikke tilgjengelig fra lokal Codex-kjøring",
        "changes": [
            "Legger til kortfeltet headline for en ryddig leveranseoverskrift i buildtabellen.",
            "Lager Admin > Build som egen side med tabellkolonnene dato, build og leveranseoverskrift.",
            "Lager detaljside per build med beskrivelse, endringer, applikasjoner, bestilling, tidsbruk og kreditter.",
            "Viser aktivt buildnummer nederst i venstremenyen.",
            "Eksponerer buildloggen via egne interne API-endepunkter for desktop V2.",
        ],
    },
    {
        "version": "1",
        "build": "1091",
        "date": "10.06.2026",
        "headline": "Status via logo og drift under Admin",
        "title": "Rydder status ut av hovedmenyen",
        "description": (
            "Status er gjort til en egen startside som nås via logoen i desktop V2, uten egen hovedmeny eller "
            "statusfaner i topplinjen. Drift/datakilder er flyttet til Admin slik at hovedmenyen får tydeligere "
            "fagområder."
        ),
        "applications": [
            "Desktop V2 navigasjon (App.tsx): status fjernet fra hovedmenyen, logo gjort klikkbar, og drift rutes til Admin.",
            "Desktop V2 moduldefinisjoner (moduleViews.ts og navigation.ts): status tatt ut av fanestrukturen og drift lagt under Admin.",
            "Desktop V2 stilark (styles.css): logoen oppfører seg som en tydelig intern lenke.",
            "fibaro10 backend (main.py): buildlogg og statuskortlenke til drift/datakilder oppdatert.",
        ],
        "request": (
            "status siden synes jeg ikke skal ha et eget menyvalg, her skal vi gjøre logo knapp trykkbar og at den "
            "går til status siden. status siden skal heller ikke ha noe topp meny osv.. drift siden bør få en annen "
            "plass uunder admin eller noe"
        ),
        "changes": [
            "Fjerner Status som eget valg i venstremenyen.",
            "Gjør Fibaro10-logoen klikkbar og peker den til Status > Oversikt.",
            "Flytter Drift til Admin > Drift og lar gammel /status/drift redirecte dit.",
            "Skjuler statusfanene ved å ta status ut av den generelle modulnavigasjonen.",
        ],
    },
    {
        "version": "1",
        "build": "1090",
        "date": "10.06.2026",
        "title": "Flytter omsetning til eget hovedpunkt",
        "description": (
            "Omsetning er skilt ut fra Status til en egen hovedmodul i desktop V2. "
            "Den gamle månedsvisningen er flyttet til Månedsoversikt, og ny standardforside viser samlet "
            "omsetning med samme type ukesutvikling som parkering og soling."
        ),
        "applications": [
            "Desktop V2 navigasjon (App.tsx og moduleViews.ts): nytt hovedpunkt, nye ruter og flyttet månedsvisning.",
            "Desktop V2 modulvisning (ModulePage.tsx): norske kolonnenavn for samlet omsetning.",
            "fibaro10 backend (main.py): ny omsetningsmodul i modul-API-et, samlet ukesutviklingsgraf og oppdaterte statuslenker.",
        ],
        "request": (
            "jeg ønsker et eget hovedpunkt omsetning, hit vil jeg flytte  status/omsetning siden og kalle den "
            "månedsoversikt . i tillegg vil jeg ha en default side som er lik som på pakering og soling altså "
            "sum omsetning ukesutvikling"
        ),
        "changes": [
            "Legger Omsetning inn som eget hovedpunkt i desktopmenyen.",
            "Flytter månedsdiagrammet fra Status > Omsetning til Omsetning > Månedsoversikt.",
            "Legger Omsetning > Oversikt med sumkort, samlet ukesutvikling, topplister for dager og måneder.",
        ],
    },
    {
        "version": "1",
        "build": "1089",
        "date": "10.06.2026",
        "title": "Utvider buildlogg med bestilling og berørte applikasjoner",
        "description": (
            "Buildloggen er utvidet fra en enkel endringsliste til en mer komplett leveranselogg. "
            "Nye buildinnslag kan nå beskrive hva som ble gjort, hvilke deler av løsningen som ble endret, "
            "og hvilken konkret bestilling som lå til grunn for endringen."
        ),
        "applications": [
            "fibaro10 backend (main.py): buildloggstruktur, buildnummer og admin-tabeller.",
            "Klassisk konto/build (templates/build_log.html): detaljert visning av beskrivelse, applikasjoner og bestilling.",
            "Desktop V2 admin: buildloggdata sendes med de nye feltene i modul-API-et.",
        ],
        "request": (
            "jeg ønsker å få en litt bedre build logg, jeg vil ha litt mer beskrivelse av hva som er gjort "
            "og hvilke applikasjoner som måtte endres, så vil jeg ha et eget felt som du også logger hele "
            "bestillingen eller promten om du vil"
        ),
        "changes": [
            "Legger til feltene description, applications og request i buildloggen.",
            "Oppdaterer /konto/build slik at nye buildinnslag viser full beskrivelse, berørte applikasjoner og original bestilling.",
            "Utvider Admin > Buildlogg-tabellene med de nye feltene som søkbar oversikt.",
        ],
    },
    {
        "version": "1",
        "build": "1088",
        "date": "10.06.2026",
        "title": "Legger temperatur- og fuktmodus i ventilasjon dagslogg",
        "changes": [
            "Legger egen fokusvelger for temperatur og fuktighet i ventilasjon dagslogg.",
            "Starter temperaturgrafen med kun Loft aktiv og fuktgrafen med kun Fukt kjeller aktiv.",
            "Legger alle loggede fuktighetsmaalere inn som valgbare serier i dagsloggen.",
        ],
    },
    {
        "version": "1",
        "build": "1087",
        "date": "10.06.2026",
        "title": "Rydder domenefarger i desktop V2",
        "changes": [
            "Samler desktop-paletten rundt faste domenefarger for omsetning, parkering, soling og energi.",
            "Retter omsetnings- og statussammenligningsgrafer slik at soling er oransje og parkering er bl\u00e5.",
            "Gjor energikort og energigrafer gr\u00f8nne, og flytter solingsdagslinjen til oransje-varianter.",
        ],
    },
    {
        "version": "1",
        "build": "1086",
        "date": "10.06.2026",
        "title": "Robustgjor ankerdato i statussammenligning",
        "changes": [
            "Gjor ankerdato-tolkingen robust for interne kall og vanlig HTTP-bruk.",
            "Beholder periodeblaing og sammenligningslogikk fra build 1085.",
        ],
    },
    {
        "version": "1",
        "build": "1085",
        "date": "10.06.2026",
        "title": "Legger bla-knapper i statussammenligning",
        "changes": [
            "Legger forrige- og neste-knapper paa detaljsiden for statussammenligning.",
            "Utvider status-sammenlignings-API med ankerdato for dag, uke og m\u00e5ned.",
            "Bruker full historisk periode, men beholder importtidspunkt som kutt for innev\u00e6rende periode.",
        ],
    },
    {
        "version": "1",
        "build": "1084",
        "date": "10.06.2026",
        "title": "Legger belopsgrafer i statussammenligning",
        "changes": [
            "Legger bryter mellom antall og belop paa detaljsiden for statussammenligning.",
            "Viser akkumulert sumgraf for soling og parkering naar belop er valgt.",
            "Beholder separate akkumulerte grafer for soling og parkering i begge moduser.",
        ],
    },
    {
        "version": "1",
        "build": "1083",
        "date": "10.06.2026",
        "title": "Bytter statussammenligning til kumulative grafer",
        "changes": [
            "Erstatter hendelses-tidslinjen med kumulative linjegrafer for solinger og parkeringer.",
            "Viser valgt periode og sammenligningsperiode som egne linjer paa samme relative tidsakse.",
            "Beholder sammendrag og differanse over grafene.",
        ],
    },
    {
        "version": "1",
        "build": "1082",
        "date": "10.06.2026",
        "title": "Legger detaljvisning for statussammenligninger",
        "changes": [
            "Gjor sammenligningsradene paa Status > Oversikt klikkbare.",
            "Legger API og V2-side for tidslinje med solinger og parkeringer per sammenligning.",
            "Normaliserer naa- og historisk periode til samme relative tidsakse.",
        ],
    },
    {
        "version": "1",
        "build": "1081",
        "date": "10.06.2026",
        "title": "Rydder designet paa statusoversikt",
        "changes": [
            "Bygger om omsetningskortene med tydeligere total, kilde-tidspunkt og sammenligningsrader.",
            "Legger differanse og prosentvis avvik direkte paa hver sammenligning.",
            "Gjor driftkort og bunnpaneler mer kompakte og lettere aa skanne.",
        ],
    },
    {
        "version": "1",
        "build": "1080",
        "date": "10.06.2026",
        "title": "Utvider status med to perioder tilbake",
        "changes": [
            "Legger sammenligning mot to uker siden paa ukekortet.",
            "Legger sammenligning mot to maaneder siden paa maanedskortet.",
            "Bruker samme kilde-spesifikke datakutt for soling og parkering i de ekstra sammenligningene.",
        ],
    },
    {
        "version": "1",
        "build": "1079",
        "date": "10.06.2026",
        "title": "Legger ukesammenligning paa dagens status",
        "changes": [
            "Legger ekstra sammenligning paa I dag-kortet mot samme dag forrige uke.",
            "Bruker fortsatt datatidspunkt per kilde for soling og parkering i den nye sammenligningen.",
            "Skiller sammenligningene visuelt slik at i gaar og forrige uke leses hver for seg.",
        ],
    },
    {
        "version": "1",
        "build": "1078",
        "date": "10.06.2026",
        "title": "Presiserer datatidspunkt for statusomsetning",
        "changes": [
            "Lar statusperioder bruke siste oppdateringstidspunkt per kilde i stedet for klokkeslettet akkurat naa.",
            "Beregner tidligere dag, uke og maaned mot samme relative datatidspunkt for soling og parkering hver for seg.",
            "Viser tydelig datagrunnlag og sammenligningstidspunkt i omsetningskortene paa Status > Oversikt.",
        ],
    },
    {
        "version": "1",
        "build": "1077",
        "date": "10.06.2026",
        "title": "Komprimerer toppen paa ventilasjon dagslogg",
        "changes": [
            "Bytter de store ventilasjonskortene over diagrammet med en kompakt statuslinje paa Ventilasjon > Dagslogg.",
            "Beholder full ventilasjonsoversikt paa de andre ventilasjonsundersidene.",
            "Viser temperatur, fukt, vaer og viftestatus mer tett slik at diagrammet kommer hoyere paa siden.",
        ],
    },
    {
        "version": "1",
        "build": "1076",
        "date": "10.06.2026",
        "title": "Justerer hendelsesrader i ventilasjonsgraf",
        "changes": [
            "Retter horisontal justering mellom vertikale viftelinjer og punktene under Ventilasjon > Dagslogg.",
            "Lar hendelsesradene bruke samme venstre akseplass og hoyre marg som ECharts-plottet.",
        ],
    },
    {
        "version": "1",
        "build": "1075",
        "date": "09.06.2026",
        "title": "Rydder viftehendelser i dagslogg",
        "changes": [
            "Legger Ventilasjon > Dagslogg over paa minuttskala slik at vertikale viftelinjer matcher punktene under diagrammet.",
            "Gjor alle vertikale viftelinjer stiplet og uten etiketter i selve diagrammet.",
            "Legger tydeligere start/stopp-markering og mouseover paa viftehendelsene under diagrammet.",
        ],
    },
    {
        "version": "1",
        "build": "1074",
        "date": "09.06.2026",
        "title": "Legger profilmeny i V2",
        "changes": [
            "Legger inn API-endepunkt for innlogget bruker og rolle.",
            "Flytter brukerprofil og utlogging inn i en moderne toppmeny i V2.",
            "Beholder eksisterende cookie-basert innlogging og logout-flyt.",
        ],
    },
    {
        "version": "1",
        "build": "1073",
        "date": "09.06.2026",
        "title": "Justerer ventilasjonsverktøylenke",
        "changes": [
            "Lar Ventilasjon > Innstillinger peke tilbake til V2-redigeringen som faktisk lagrer via config API.",
            "Beholder /classic/ kun for gamle verktøyflater som fortsatt trenger klassisk HTML eller filnedlasting.",
        ],
    },
    {
        "version": "1",
        "build": "1072",
        "date": "09.06.2026",
        "title": "Gjør klassiske verktøylenker tydelige",
        "changes": [
            "Legger klassiske oppslag, eksportfiler og renholdsdetaljer på /classic/ slik at V2-catchall ikke fanger dem.",
            "Oppdaterer V2-verktøytabeller til å peke på de eksplisitte classic-lenkene.",
            "Beholder V2-rutene rene uten bakoverkompatibilitetsomveier i hovedmenyen.",
        ],
    },
    {
        "version": "1",
        "build": "1071",
        "date": "09.06.2026",
        "title": "Rydder Elvia-importkort i audit",
        "changes": [
            "Forbedrer tekstbryting for lange Elvia-filnavn i importkortene.",
            "Lar importmeldinger bryte linjer i stedet for å presse kortbredden.",
            "Legger designjusteringen inn som del av systemgjennomgangen.",
        ],
    },
    {
        "version": "1",
        "build": "1070",
        "date": "09.06.2026",
        "title": "Retter solingprognose i audit",
        "changes": [
            "Retter en feil der solingprognosen brukte intradag-tempo før variabelen var definert.",
            "Gjenoppretter V2-visningen Soling > Prognose slik at den returnerer prognosekort, graf og lagrede prognoser.",
            "Legger feilen inn i buildloggen som del av systemgjennomgangen.",
        ],
    },
    {
        "version": "1",
        "build": "1069",
        "date": "09.06.2026",
        "title": "Utvider tooltip på omsetningsgraf",
        "changes": [
            "Viser sum for dagen i hover over Status > Omsetning.",
            "Legger antall solinger og parkeringer inn sammen med beløpene i graf-tooltipen.",
            "Holder totalsummen uten antall slik at tooltipen skiller mellom aktivitet og omsetning.",
        ],
    },
    {
        "version": "1",
        "build": "1068",
        "date": "09.06.2026",
        "title": "Rydder dagslogg for ventilasjon",
        "changes": [
            "Fjerner ekstra checkbox-filter over temperaturdiagrammet på Ventilasjon > Dagslogg.",
            "Lar ECharts-legend inne i diagrammet styre synlige temperaturserier.",
            "Legger vifte av/på-hendelser som vertikale markørlinjer i dagsdiagrammet.",
        ],
    },
    {
        "version": "1",
        "build": "1067",
        "date": "09.06.2026",
        "title": "Gjeninnfører Elvia-import i V2",
        "changes": [
            "Legger filopplasting og importstatus inn på Energi > Elvia i den nye desktopflaten.",
            "Viser Elvia-summer, toppdager, toppmåneder og siste importer som egne arbeidsflater.",
            "Eksponerer JSON-opplasting for Elvia med samme bakgrunnsimport som klassisk side.",
        ],
    },
    {
        "version": "1",
        "build": "1066",
        "date": "09.06.2026",
        "title": "Rydder ventilasjonssiden",
        "changes": [
            "Gir Ventilasjon en dedikert desktopvisning med egne kort, dagsgraf og viftehendelser.",
            "Skiller dagslogg, temp-logg, Yr-logg, hendelser og innstillinger tydeligere i API og grensesnitt.",
            "Flytter ventilasjonsinnstillinger til JSON-lagring i den nye appen.",
        ],
    },
    {
        "version": "1",
        "build": "1065",
        "date": "09.06.2026",
        "title": "Fjerner v2 fra app-URL",
        "changes": [
            "Flytter den nye desktopflaten til rene hovedruter som /status, /parkering og /soling.",
            "Flytter frontend-API fra versjonert prefix til /api og oppdaterer alle interne handlinger og lenker.",
            "Fjerner legacy-redirecten som sendte gamle UI-ruter til separat desktop-prefix.",
        ],
    },
    {
        "version": "1",
        "build": "1064",
        "date": "09.06.2026",
        "title": "Samler statusmenyen i V2",
        "changes": [
            "Samler Oversikt, Omsetning og Drift under hovedpunktet Status.",
            "Gir Status samme faste undersidemeny i topplinjen som de andre hovedområdene.",
            "Setter ny standardinngang til Status > Oversikt i V2.",
        ],
    },
    {
        "version": "1",
        "build": "1063",
        "date": "09.06.2026",
        "title": "Strammer inn V2-toppmeny",
        "changes": [
            "Flytter modulfaner til fast topplinje slik at undersidemenyen ikke skroller bort.",
            "Fjerner stor moduloverskrift og intro fra V2-modulsidene.",
            "Gjør valgt hovedmeny tydeligere i venstremenyen.",
        ],
    },
    {
        "version": "1",
        "build": "1062",
        "date": "09.06.2026",
        "title": "Bygger ut V2 soling-undersider",
        "changes": [
            "Legger native V2-visninger for soling oversikt, detaljer, dagslinje, enkeltimer, senger, medlemmer og prognose.",
            "Beholder ukesutvikling/statistikk, men gir hver underside egne kort, grafer og tabeller.",
            "Legger V2-handling for å lagre solingprognose.",
        ],
    },
    {
        "version": "1",
        "build": "1061",
        "date": "09.06.2026",
        "title": "Setter historisk V1 på egen port",
        "changes": [
            "Fjerner V1-lenker og iframe fra desktop v2.",
            "Lar historisk V1 kjøres som egen QNAP-container på port 8111 fra commit 487044d.",
            "Legger read-only deploy-script for V1-historikk i repoet slik at oppsettet kan gjenskapes.",
        ],
    },
    {
        "version": "1",
        "build": "1060",
        "date": "09.06.2026",
        "title": "Legger V1 ved siden av V2",
        "changes": [
            "Legger inn stabil /v1-inngang til gammelt brukergrensesnitt.",
            "Legger V1-knapp i desktop v2-headeren for manuell sammenligning i ny fane.",
            "Merker Klassisk-fanen tydelig som V1 for gjennomgang av manglende funksjoner.",
        ],
    },
    {
        "version": "1",
        "build": "1059",
        "date": "09.06.2026",
        "title": "Gjeninnfører grafer og redigering i v2",
        "changes": [
            "Legger native ECharts-grafer inn i v2 for energi, ventilasjon og lys dagslogg.",
            "Legger v2-redigering for energikurser, energilaster og brukere/tilgang.",
            "Legger inn Klassisk-flate i v2 slik at alle gamle sider og forms kan brukes mens native migrering fullføres.",
        ],
    },
    {
        "version": "1",
        "build": "1058",
        "date": "09.06.2026",
        "title": "Eksponerer manglende v2-verktøy",
        "changes": [
            "Legger inn v2-faner for parkeringoppslag, energiverktøy, styringsinnstillinger, renholdsroboter og adminverktøy.",
            "Viser gjeldende lys- og ventilasjonsregler, grenseverdier og endringshistorikk direkte i desktop v2.",
            "Samler gamle driftsflater som trygge lenker i v2 uten å eksponere hemmelige tilgangsverdier.",
        ],
    },
    {
        "version": "1",
        "build": "1057",
        "date": "08.06.2026",
        "title": "Forbedrer v2 tabellarbeid",
        "changes": [
            "Legger inn sortering i modul-tabeller og omsetningstabellen.",
            "Bruker mer stabile radnøkler i modul-tabeller.",
            "Høyrejusterer numeriske kolonner for bedre skanning.",
        ],
    },
    {
        "version": "1",
        "build": "1056",
        "date": "08.06.2026",
        "title": "Strammer v2 navigasjon og tomtilstander",
        "changes": [
            "Bruker intern SPA-navigasjon for v2-kort og siste-hendelser.",
            "Legger inn bedre tomtilstander i oversikt, drift og omsetning.",
            "Hindrer dobbel start av modulhandlinger mens en jobb kjører.",
        ],
    },
    {
        "version": "1",
        "build": "1055",
        "date": "08.06.2026",
        "title": "Finpusser v2 arbeidsflate",
        "changes": [
            "Normaliserer ugyldige v2-faner og viser pene modulnavn i sidehodet.",
            "Legger inn radtelling, treffstatus og bedre tomvisning i modul-tabeller.",
            "Forbedrer handlingsdialoger og API-feilmeldinger i desktop v2.",
        ],
    },
    {
        "version": "1",
        "build": "1054",
        "date": "08.06.2026",
        "title": "Rydder v2-meny og arbeidsflate",
        "changes": [
            "Forenkler venstremenyen til hovedområder og flytter undersider til lokale faner.",
            "Legger inn søk i v2-tabeller og tydeligere modulhandlinger.",
            "Legger inn v2-handlinger for EasyPark-oppdatering og SVV-sync.",
        ],
    },
    {
        "version": "1",
        "build": "1053",
        "date": "08.06.2026",
        "title": "Utvider v2 med undersider",
        "changes": [
            "Legger inn v2-undermenyer for parkering, soling, energi, ventilasjon, lys, renhold og admin.",
            "Gir flere gamle undersider egne v2-datavisninger i stedet for samme generiske modulside.",
            "Oppdaterer gamle UI-redirects slik at de peker til tilsvarende v2-underside.",
        ],
    },
    {
        "version": "1",
        "build": "1052",
        "date": "08.06.2026",
        "title": "Gjor desktop v2 til primaer UI",
        "changes": [
            "Legger v2-sider for parkering, soling, energi, ventilasjon, lys, renhold og admin.",
            "Eksponerer felles moduldata under /api/modules/{module}.",
            "Flytter rotadressen til desktopflaten og fjerner gamle UI-lenker fra menyen.",
        ],
    },
    {
        "version": "1",
        "build": "1051",
        "date": "08.06.2026",
        "title": "Starter separat desktop v2",
        "changes": [
            "Legger inn en egen React/Ant Design/ECharts-revisjon.",
            "Eksponerer nye JSON-endepunkter under /api for oversikt og maanedlig omsetning.",
            "Beholder dagens Jinja-grensesnitt uendret slik at begge revisjoner kan utvikles videre parallelt.",
        ],
    },
    {
        "version": "1",
        "build": "1050",
        "date": "08.06.2026",
        "title": "Maanedsgraf for omsetning",
        "changes": [
            "Legger inn egen Status/Omsetning-side med stablet soylediagram for en hel maaned.",
            "Viser soling og parkering per dag med maanedssummer og navigasjon mellom maaneder.",
            "Bruker hovedappens databasegrunnlag og ikke mobilappens online-dashboardkode.",
        ],
    },
    {
        "version": "1",
        "build": "1049",
        "date": "08.06.2026",
        "title": "Rydder nokkeltallside",
        "changes": [
            "Gjor Status/Nokkeltall mer kompakt med lavere fontstorrelse og tettere kort.",
            "Rydder seksjoner, spacing og kortdesign slik at PC-siden blir lettere a skanne.",
            "Beholder alle mobilunderside-tallene pa samme side.",
        ],
    },
    {
        "version": "1",
        "build": "1048",
        "date": "08.06.2026",
        "title": "Utvider nokkeltall med mobilundersider",
        "changes": [
            "Legger flere sammenligningstall fra mobilappens undersider inn pa Status/Nokkeltall.",
            "Viser samme tidspunkt forrige uke, samme dag forrige uke, to uker siden, forrige uke og forrige maned for soling og parkering.",
            "Legger inn flere energi-, temperatur- og fuktverdier uten teknisk kobling til online-dashboardet.",
        ],
    },
    {
        "version": "1",
        "build": "1047",
        "date": "08.06.2026",
        "title": "Tester PC-side for mobilkort",
        "changes": [
            "Legger inn en intern status/nokkeltall-side som samler kortene fra mobilvisningen for PC.",
            "Knytter hvert nokkeltallskort videre til riktig intern detaljside.",
            "Holder PC-visningen pa hovedappens databasegrunnlag i stedet for a avhenge av online-dashboardet.",
        ],
    },
    {
        "version": "1",
        "build": "1046",
        "date": "08.06.2026",
        "title": "Korrigerer solsenganalyse for takvifte",
        "changes": [
            "Trekker fra estimert 320 W for umalt takavtrekk når ventilasjonsloggen viser at takvifta gar.",
            "Bruker korrigert differanse i baseline og solsengestimat uten aa endre ra energilogg.",
            "Viser antall takviftekorrigerte samples pa forbruk-per-seng-siden.",
        ],
    },
    {
        "version": "1",
        "build": "1045",
        "date": "08.06.2026",
        "title": "Slutter aa logge HC3-differanse",
        "changes": [
            "Fjerner HC3 sin differanse-QA fra aktiv energilogg.",
            "Bruker kun Fibaro10 sin beregnede differanse fra realtime W.",
            "Rydder energioversikten for gammel differanse-kontrollverdi.",
        ],
    },
    {
        "version": "1",
        "build": "1044",
        "date": "08.06.2026",
        "title": "Lagrer energi i 30-sekunders bucket",
        "changes": [
            "Endrer energilagring fra minutt-bucket til 30-sekunders bucket.",
            "Hindrer at andre energisample i samme minutt overskriver den forrige.",
        ],
    },
    {
        "version": "1",
        "build": "1043",
        "date": "08.06.2026",
        "title": "Logger energi hvert 30 sekund",
        "changes": [
            "Endrer HC3 energilogg-scenen fra 60 til 30 sekunder.",
            "Gir mer presis kWh-beregning fra realtime W uten stor ekstra datamengde.",
        ],
    },
    {
        "version": "1",
        "build": "1042",
        "date": "08.06.2026",
        "title": "Beregner forbruk fra realtime",
        "changes": [
            "Beregner kWh-delta fra realtime W-verdier i stedet for akkumulerte HC3-maalerverdier.",
            "Lar akkumulerte HC3-verdier bli logget som kontrollverdier, men ikke styre dagsforbruket.",
            "Unngaar at reset i akkumulerte maalere paavirker beregnet forbruk.",
        ],
    },
    {
        "version": "1",
        "build": "1041",
        "date": "08.06.2026",
        "title": "Oppdaterer HC3 energioppsamling",
        "changes": [
            "Tilpasser beregnet energidifferanse etter at avfukter inngaar i Annet-oppsamlingen.",
            "Beholder avfukter som separat logget felt, men trekker den ikke dobbelt i differanseberegningen.",
        ],
    },
    {
        "version": "1",
        "build": "1040",
        "date": "08.06.2026",
        "title": "Lagrer komplett Yr-datagrunnlag",
        "changes": [
            "Logger flere strukturerte analysefelt fra komplett MET/Yr-varsel.",
            "Lagrer full MET/Yr-respons med HTTP-headere som raw JSON for senere analyser.",
            "Oppdaterer eksisterende Yr-rad med komplett datagrunnlag naar samme varsel allerede finnes.",
        ],
    },
    {
        "version": "1",
        "build": "1039",
        "date": "08.06.2026",
        "title": "Henter komplett Yr-varsel",
        "changes": [
            "Bytter Yr/MET-henting fra compact til complete for å få vindkast og nedbørsannsynlighet.",
            "Lar de nye analysefeltene fylles når MET leverer dem.",
        ],
    },
    {
        "version": "1",
        "build": "1038",
        "date": "08.06.2026",
        "title": "Utvider Yr-logging",
        "changes": [
            "Logger vindkast fra Yr/MET når feltet leveres.",
            "Logger nedbørsannsynlighet neste 1 og 6 timer når feltet leveres.",
            "Oppdaterer eksisterende Yr-rad med nye felter når samme varsel allerede er lagret.",
        ],
    },
    {
        "version": "1",
        "build": "1037",
        "date": "08.06.2026",
        "title": "Strammer mobilvisning",
        "changes": [
            "Gjør viftestatus mer kompakt på mobil i temp-loggen.",
            "Reduserer høyden på hvert målekort uten å fjerne statusinformasjon.",
        ],
    },
    {
        "version": "1",
        "build": "1036",
        "date": "08.06.2026",
        "title": "Rydder temp-loggdesign",
        "changes": [
            "Gjør temp-loggen mer kompakt med roligere kort og tydeligere seksjoner.",
            "Gir Inne-seksjonen mer plass på desktop og bedre flyt på mobil.",
            "Forenkler header, viftestatus og målefelt visuelt.",
        ],
    },
    {
        "version": "1",
        "build": "1035",
        "date": "08.06.2026",
        "title": "Forenkler temp-oversikt",
        "changes": [
            "Fjerner Styring fra Ute-seksjonen i temp-loggen.",
            "Fjerner estimert solsengverdi fra Inne-seksjonen.",
        ],
    },
    {
        "version": "1",
        "build": "1034",
        "date": "08.06.2026",
        "title": "Tydeliggjør uteverdier",
        "changes": [
            "Endrer Ute-seksjonen i temp-loggen til Styring, Netatmo og Yr.",
            "Flytter Netatmo-fukt til Netatmo-raden.",
        ],
    },
    {
        "version": "1",
        "build": "1033",
        "date": "08.06.2026",
        "title": "Forenkler temp logg",
        "changes": [
            "Fjerner Diff og Kilde fra temp-loggens visning.",
            "Beholder temperatur og fukt i Ventilasjon-gruppen.",
        ],
    },
    {
        "version": "1",
        "build": "1032",
        "date": "08.06.2026",
        "title": "Justerer temp logg-grupper",
        "changes": [
            "Samler loft og innluft i en egen Ventilasjon-gruppe.",
            "Legger uteverdier og Yr i en egen Ute-gruppe.",
            "Legger kjellerverdier i en egen Kjeller-gruppe.",
        ],
    },
    {
        "version": "1",
        "build": "1031",
        "date": "08.06.2026",
        "title": "Rydder temp logg",
        "changes": [
            "Deler temp loggen inn i gruppene Inne, Ute og loft, og Teknisk.",
            "Viser temperatur og fukt samlet per sone for raskere lesing.",
            "Beholder viftestatus, modus og regelhjelp øverst i hver måling.",
        ],
    },
    {
        "version": "1",
        "build": "1030",
        "date": "08.06.2026",
        "title": "Logger fukt i ventilasjon",
        "changes": [
            "Logger fukt for 1.etg, 2.etg, VIP, ute, Yr, loft, luftinntak og kjeller.",
            "Viser fuktverdier i ventilasjonsloggene og online-dashboardet.",
            "Oppdaterer HC3 ventilasjonsrunner scene 363 med fuktsensorene.",
        ],
    },
    {
        "version": "1",
        "build": "1029",
        "date": "08.06.2026",
        "title": "Legger inn kjeller og avfukter",
        "changes": [
            "Logger temperatur og fukt fra kjeller i ventilasjonsloggen.",
            "Legger avfukter inn som styrbar klimaenhet.",
            "Logger avfukterens effekt og kWh i HC3 energiloggen.",
        ],
    },
    {
        "version": "1",
        "build": "1028",
        "date": "06.06.2026",
        "title": "Retter HC3 målerlogging",
        "changes": [
            "Gjør rådata fra HC3 måleravlesninger JSON-sikre slik at timestamp ikke stopper lagring.",
        ],
    },
    {
        "version": "1",
        "build": "1027",
        "date": "05.06.2026",
        "title": "Teller pågående parkeringer",
        "changes": [
            "Viser antall pågående parkeringer direkte i overskriften på Parkering/Oversikt.",
        ],
    },
    {
        "version": "1",
        "build": "1026",
        "date": "31.05.2026",
        "title": "Dato i kjøretøytabell",
        "changes": [
            "Endrer Parkering/Kjøretøy slik at først sett og sist sett viser både dato og klokkeslett.",
            "Legger inn eget kort datoformat for historikkfelt som ikke bare skal vise klokkeslett.",
        ],
    },
    {
        "version": "1",
        "build": "1025",
        "date": "31.05.2026",
        "title": "Deler temperaturkort",
        "changes": [
            "Splitter temperaturfeltet i online-dashboardet i to kort: Inne og Ute.",
            "Inne-kortet viser snittet stort med 1.etg, 2.etg og VIP som underverdier.",
            "Ute-kortet viser beregnet utetemperatur stort med Ute, Innluft og Yr som underverdier.",
        ],
    },
    {
        "version": "1",
        "build": "1024",
        "date": "31.05.2026",
        "title": "Retter klikkbare mobilkort",
        "changes": [
            "Retter klikkbare kort i online-dashboardet slik at seksjonene Lys og Ventilasjon ikke fragmenteres som inline-elementer.",
            "Fjerner de hvite restflatene som kunne vises rett over Lys, rett under Ventilasjon og nederst på mobilforsiden.",
            "Beholder den kompakte mobile forsiden og rydder CSS-regelen slik at kortlenker oppfører seg likt.",
        ],
    },
    {
        "version": "1",
        "build": "1023",
        "date": "31.05.2026",
        "title": "Mobil overflow-fiks",
        "changes": [
            "Retter online-dashboardet slik at temperaturkort, lyskort og ventilasjonskort ikke kan presse siden bredere enn mobilskjermen.",
            "Gjør temperaturkortet mer kompakt på smal skjerm og lar ekstra temperaturverdier bryte til to kolonner.",
            "Legger inn tydelige overflow-vakter i mobil-CSS-en uten å endre den enkle forsidemodellen.",
        ],
    },
    {
        "version": "1",
        "build": "1022",
        "date": "31.05.2026",
        "title": "Enklere mobilforside",
        "changes": [
            "Forenkler forsiden i online-dashboardet slik at soling og parkering viser i dag/i går kompakt med skråstrek.",
            "Flytter detaljer som beløp, siste hendelser, uke og måned til undersidene.",
            "Reduserer høyden på hovedkortene for et raskere mobiloverblikk.",
        ],
    },
    {
        "version": "1",
        "build": "1021",
        "date": "31.05.2026",
        "title": "Mobilapp med detaljsider",
        "changes": [
            "Gjør logoen i online-dashboardet til fast vei tilbake til forsiden.",
            "Legger inn ett-nivå detaljsider for soling, parkering, energi, temperatur, lys og ventilasjon.",
            "Gjør aktuelle kort klikkbare og legger en tilgangsstyrt EasyPark-oppdatering på parkeringsdetaljen.",
        ],
    },
    {
        "version": "1",
        "build": "1020",
        "date": "31.05.2026",
        "title": "Rikere mobilapp",
        "changes": [
            "Utvider online-dashboardet med åpningstid, strøm akkurat nå og forbruk hittil i dag.",
            "Legger inn sammenligning mot i går for soling og parkering, samt siste registrerte soling og parkering.",
            "Legger inn kompakte uke- og månedstall for soling og parkering i den offentlige mobilvisningen.",
        ],
    },
    {
        "version": "1",
        "build": "1019",
        "date": "31.05.2026",
        "title": "Ryddigere energioversikter",
        "changes": [
            "Rydder opp i grensesnittet for Energi > Kurser og Energi > Laster.",
            "Gjør handlingsknapper, filter, PDF-uttak og registrering mer samlet og mindre støyende.",
            "Legger registrering av ny last i et sammenleggbart panel slik at oversikten er lettere å bruke til daglig.",
        ],
    },
    {
        "version": "1",
        "build": "1018",
        "date": "31.05.2026",
        "title": "PDF-eksport for energi",
        "changes": [
            "Legger inn PDF-uttak for kursliste og lastregister under Energi.",
            "PDF-ene lages direkte i appen uten ekstra avhengigheter og deles automatisk over flere sider.",
        ],
    },
    {
        "version": "1",
        "build": "1017",
        "date": "31.05.2026",
        "title": "Redigerbar kursliste",
        "changes": [
            "Legger inn edit-modus pa Energi > Kurser slik at kursbeskrivelse, vern, kabel, JFB, status og notat kan endres direkte i grensesnittet.",
            "Lagring skjer per kursrad slik at tavledokumentasjonen kan holdes levende uten ny Excel-import.",
        ],
    },
    {
        "version": "1",
        "build": "1016",
        "date": "31.05.2026",
        "title": "Energi kurs og laster",
        "changes": [
            "Legger inn egne datatabeller for elektriske kurser og praktiske laster under Energi.",
            "Seeder kursliste 37 som tavledokumentasjon uten a overskrive senere endringer.",
            "Legger inn sider for kursliste og lastregister med kobling mot kurs, Fibaro-id, Z-Wave-id og forventet effekt.",
        ],
    },
    {
        "version": "1",
        "build": "1015",
        "date": "31.05.2026",
        "title": "Bedre prognosemodell",
        "changes": [
            "Retter dagsprognoser slik at soling ikke straffes for manglende natt- og for-apning-data.",
            "Endrer maneds- og arsprognose slik at dagens tempo sammenlignes med forventet aktivitet hittil, ikke hele dagen.",
            "Fjerner dobbel nedjustering av resterende del av innevarende dag i prognosegrunnlaget.",
        ],
    },
    {
        "version": "1",
        "build": "1014",
        "date": "30.05.2026",
        "title": "CSS-gjennomgang",
        "changes": [
            "Rydder ansvarsdelingen mellom app.css, Lilletorget designsystem og fast venstremeny.",
            "Reduserer app.css til tokens, baseoppsett og få sidespesifikke regler slik at komponenter ikke defineres dobbelt.",
            "Oppdaterer CSS-cache for å sikre at QNAP-løsningen laster den ryddede stilstrukturen.",
        ],
    },
    {
        "version": "1",
        "build": "1013",
        "date": "30.05.2026",
        "title": "Retter norske tegn",
        "changes": [
            "Retter feil kodede norske tegn i parkeringsprognose og dashboardkort.",
            "Retter ukedagsnavn og års-/månedsoverskrifter som kunne vises som mojibake.",
            "Retter tegn i små SUN2-statusapper slik at På og går vises riktig.",
        ],
    },
    {
        "version": "1",
        "build": "1012",
        "date": "30.05.2026",
        "title": "Oppdatert dokumentasjon",
        "changes": [
            "Skriver sluttbrukermanualen på nytt med ryddig kapittelinndeling, korrekt norsk tegnsett og oppdatert forklaring av alle hovedområder.",
            "Skriver teknisk manual på nytt med QNAP-produksjon, intern hovedapp, offentlig online-dashboard, containere, porter, dataflyt, API, database, sikkerhet og feilsøking.",
            "Dokumenterer skillet mellom full intern Fibaro10-app og separat offentlig nøkkeltall-app for mobil.",
            "Legger inn tydeligere driftsrutiner for parkering, soling, lys, ventilasjon, energi, renhold og datakilder.",
        ],
    },
    {
        "version": "1",
        "build": "1011",
        "date": "30.05.2026",
        "title": "Kontrollert fargeløft",
        "changes": [
            "Legger inn et samlet fargelag i designsystemet med svake aksentflater per hovedområde.",
            "Gir kort, paneler, tabellhoder og statusmerker mer visuell retning uten å endre layout.",
            "Beholder grønn/rød statuslogikk for på/av og ok/feil slik at driftssignaler fortsatt er tydelige.",
            "Oppdaterer CSS-cache slik at QNAP-løsningen laster det nye uttrykket med en gang.",
        ],
    },
    {
        "version": "1",
        "build": "1010",
        "date": "30.05.2026",
        "title": "Design- og CSS-opprydding",
        "changes": [
            "Rydder app.css ned til rene grunnvariabler, temafarger og felles komponentregler.",
            "Gjør owner-nav.css til eneste kilde for fast venstremeny og gjør menyen mer kompakt.",
            "Fjerner gamle overlappende mobil- og layoutregler fra app.css som kunne gi ulik bredde mellom sider.",
            "Oppdaterer CSS-cache slik at QNAP-løsningen laster det nye designlaget umiddelbart.",
            "Beholder buildloggen som fast historikk for synlige endringer i løsningen.",
        ],
    },
    {
        "version": "1",
        "build": "1009",
        "date": "30.05.2026",
        "title": "SVV og statusstatistikk",
        "changes": [
            "Gjør SVV-berikelsen mer robust ved midlertidige feil fra Statens vegvesen.",
            "Stopper SVV-batchen etter første 429/500/502/503/504 slik at mange biler ikke feilmerkes når tjenesten er nede.",
            "Viser tydelig statusmelding når kjøretøy venter på ny SVV-prøve etter midlertidig feil.",
            "Endrer Status/Statistikk slik at grafen bare viser samlet beløp for soling og parkering.",
            "Legger inn valg mellom ukevis beløp og akkumulert årskurve på Status/Statistikk.",
        ],
    },
    {
        "version": "1",
        "build": "1008",
        "date": "29.05.2026",
        "title": "CSS-opprydding",
        "changes": [
            "Fjerner gamle overlappende designlag fra app.css slik at Lilletorget-systemet styrer farger, kort, knapper og typografi.",
            "Flytter nødvendige kompatibilitetsregler for parkering, filtre og klikkbare merker til felles designsystem.",
            "Oppdaterer CSS-cache slik at QNAP-løsningen laster den ryddede stilen uten gammel nettlesercache.",
        ],
    },
    {
        "version": "1",
        "build": "1007",
        "date": "29.05.2026",
        "title": "Teknisk driftsside",
        "changes": [
            "Bygger om teknisk side til en samlet driftsoversikt for hovedapp, online-dashboard, QNAP, HC3 og lokale loggerapper.",
            "Legger inn vedlikeholdslenker til de viktigste sidene for status, parkering, soling, lys, ventilasjon, energi, renhold og AI.",
            "Dokumenterer containere, porter, dataflyt, driftsrutiner, API-endepunkter, feilsøking og hva som bør beholdes eller kan arkiveres.",
        ],
    },
    {
        "version": "1",
        "build": "1006",
        "date": "29.05.2026",
        "title": "Lik sidestart",
        "changes": [
            "Gjør toppfelt på dashboard, soling, lys, ventilasjon og konto til samme høyde, plassering og typestørrelse.",
            "Legger inn manglende sidetopper på logg- og innstillingssider slik at de starter likt.",
            "Oppdaterer CSS-cache for å sikre at den ryddede toppstilen brukes i QNAP-løsningen.",
        ],
    },
    {
        "version": "1",
        "build": "1005",
        "date": "29.05.2026",
        "title": "Presise sidetopper",
        "changes": [
            "Strammer sidetoppene til fast plassering, fast tittelst\u00f8rrelse og lik venstrejustering.",
            "Skiller direkte h1-sidetopper fra toppfelt med handlinger, slik at de f\u00e5r samme visuelle geometri.",
            "Oppdaterer CSS-cache slik at den nye toppstilen lastes p\u00e5 alle sider.",
        ],
    },
    {
        "version": "1",
        "build": "1004",
        "date": "29.05.2026",
        "title": "Felles sidetopper",
        "changes": [
            "Innf\u00f8rer et felles system for overskrifter, hjelpetekster og topphandlinger p\u00e5 sidene.",
            "Legger til manglende sidetopper p\u00e5 status-dagslinje, lyslogg og ventilasjonslogg.",
            "Rydder fontst\u00f8rrelser og avstand i toppfelt slik at sidene starter mer likt.",
        ],
    },
    {
        "version": "1",
        "build": "1003",
        "date": "29.05.2026",
        "title": "Retter tegnsett i buildlogg",
        "changes": [
            "Rydder buildloggen slik at norske tegn vises riktig.",
            "Ingen funksjonell endring i prognoser eller \u00f8vrige sider.",
        ],
    },
    {
        "version": "1",
        "build": "1002",
        "date": "29.05.2026",
        "title": "Lagrede prognoser",
        "changes": [
            "Legger til knapp for \u00e5 lagre prognose p\u00e5 b\u00e5de Soling/Prognose og Parkering/Prognose.",
            "Hver lagring tar vare p\u00e5 dag-, m\u00e5neds- og \u00e5rsprognosen slik den s\u00e5 ut akkurat da.",
            "Prognosesidene viser en tabell med lagrede prognoser og faktisk utvikling s\u00e5 langt.",
            "Avvik vises for antall og kroner slik at vi kan se hvor godt modellen treffer over tid.",
        ],
    },
    {
        "version": "1",
        "build": "1001",
        "date": "29.05.2026",
        "title": "Parkering prognose",
        "changes": [
            "Legger til egen prognoseside for parkering under Parkering.",
            "Prognosen beregner forventet antall parkeringer, inntekt og varighet for dag, måned og år.",
            "Modellen bruker historikk, ukedag, sesong, helligdager og tempo hittil i perioden.",
            "Parkering-menyen har fått nytt valg for prognose.",
        ],
    },
    {
        "version": "1",
        "build": "1000",
        "date": "29.05.2026",
        "title": "Første nummererte build",
        "changes": [
            "Innfører fast versjonsnummer og buildnummer i menyen.",
            "Buildnummeret er klikkbart og åpner denne buildloggen.",
            "Mobilappen logger nå innlogging, refresh og avviste innlogginger som brukeraktivitet.",
            "Parkering/Område viser både andel unike biler og andel parkeringer, uten grafisk stolpefelt.",
            "Dette er startpunktet for videre bygglogg: fremtidige endringer legges inn her med nytt buildnummer.",
        ],
    }
]


def normalized_build_log_entry(row: Dict[str, Any]) -> BuildLogEntryPayload:
    applications = row.get("applications") or []
    if not isinstance(applications, list):
        applications = [str(applications)] if applications else []
    changes = row.get("changes") or []
    if not isinstance(changes, list):
        changes = [str(changes)] if changes else []
    build = str(row.get("build", ""))
    description = row.get("description") or " ".join(str(item) for item in changes)
    return {
        "version": str(row.get("version", APP_VERSION)),
        "build": build,
        "date": str(row.get("date", "")),
        "headline": str(row.get("headline") or row.get("title") or f"Build {build}"),
        "title": str(row.get("title") or row.get("headline") or f"Build {build}"),
        "description": str(description or ""),
        "applications": [str(item) for item in applications],
        "changes": [str(item) for item in changes],
        "request": str(row.get("request") or ""),
        "workDuration": str(row.get("work_duration") or row.get("workDuration") or "Ikke registrert"),
        "creditsUsed": str(row.get("credits_used") or row.get("creditsUsed") or "Ikke registrert"),
        "path": f"/admin/build/{build}",
        "isCurrent": build == str(APP_BUILD),
    }


def build_log_list_row(row: Dict[str, Any]) -> BuildLogListRowPayload:
    build = str(row.get("build", ""))
    return {
        "build": build,
        "date": str(row.get("date", "")),
        "headline": str(row.get("headline") or row.get("title") or f"Build {build}"),
        "path": f"/admin/build/{build}",
        "isCurrent": build == str(APP_BUILD),
    }


def api_build_log_row(row: Dict[str, Any]) -> BuildLogTableRowPayload:
    normalized = normalized_build_log_entry(row)
    applications_text = "; ".join(normalized["applications"])
    return {
        "build": normalized["build"],
        "date": normalized["date"],
        "headline": normalized["headline"],
        "title": normalized["title"],
        "description": normalized["description"],
        "applications": applications_text,
        "request": normalized["request"],
        "work_duration": normalized["workDuration"],
        "credits_used": normalized["creditsUsed"],
        "path": normalized["path"],
    }


def build_log_entry_by_build(build: str) -> Optional[Dict[str, Any]]:
    build_value = str(build)
    for row in BUILD_LOG:
        if str(row.get("build", "")) == build_value:
            return row
    return None
