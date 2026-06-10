import os
from typing import Any, Dict, Optional

from api_types import BuildLogEntryPayload, BuildLogTableRowPayload


APP_VERSION = os.getenv("APP_VERSION", "1")
APP_BUILD = os.getenv("APP_BUILD", "1118")
BUILD_LOG = [
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
            "Retter en feil der solingprognosen brukte intradag-tempo fÃ¸r variabelen var definert.",
            "Gjenoppretter V2-visningen Soling > Prognose slik at den returnerer prognosekort, graf og lagrede prognoser.",
            "Legger feilen inn i buildloggen som del av systemgjennomgangen.",
        ],
    },
    {
        "version": "1",
        "build": "1069",
        "date": "09.06.2026",
        "title": "Utvider tooltip pÃ¥ omsetningsgraf",
        "changes": [
            "Viser sum for dagen i hover over Status > Omsetning.",
            "Legger antall solinger og parkeringer inn sammen med belÃ¸pene i graf-tooltipen.",
            "Holder totalsummen uten antall slik at tooltipen skiller mellom aktivitet og omsetning.",
        ],
    },
    {
        "version": "1",
        "build": "1068",
        "date": "09.06.2026",
        "title": "Rydder dagslogg for ventilasjon",
        "changes": [
            "Fjerner ekstra checkbox-filter over temperaturdiagrammet pÃ¥ Ventilasjon > Dagslogg.",
            "Lar ECharts-legend inne i diagrammet styre synlige temperaturserier.",
            "Legger vifte av/pÃ¥-hendelser som vertikale markÃ¸rlinjer i dagsdiagrammet.",
        ],
    },
    {
        "version": "1",
        "build": "1067",
        "date": "09.06.2026",
        "title": "GjeninnfÃ¸rer Elvia-import i V2",
        "changes": [
            "Legger filopplasting og importstatus inn pÃ¥ Energi > Elvia i den nye desktopflaten.",
            "Viser Elvia-summer, toppdager, toppmÃ¥neder og siste importer som egne arbeidsflater.",
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
