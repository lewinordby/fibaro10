from __future__ import annotations

import os
from typing import Any


PROTECT_LEDGER_VERSION = os.getenv("PROTECT_LEDGER_VERSION", "1")
PROTECT_LEDGER_BUILD = os.getenv("PROTECT_LEDGER_BUILD", "23")
PROTECT_LEDGER_COMMIT = os.getenv("PROTECT_LEDGER_COMMIT", "unknown")


PROTECT_LEDGER_BUILD_LOG: list[dict[str, Any]] = [
    {
        "version": "1",
        "build": "23",
        "date": "25.08.2026",
        "headline": "Nordiske registertreff får effektiv perioderapport",
        "title": "Bekreftede registreringsnumre grupperes til daglige kjøretøyopphold",
        "description": (
            "Protect Ledger kan nå hente registerbekreftede kjøretøy fra Norge, Sverige og Danmark "
            "for en hel uke eller måned i ett databasekall. Bare opphold med mer enn ti minutter "
            "mellom første og siste dedupliserte kameraobservasjon tas med."
        ),
        "request": (
            "Finn biler som er observert i mer enn ti minutter og er bekreftet i kjøretøyregister "
            "for Norge, Sverige eller Danmark, slik at Fibaro10 kan kontrollere manglende betaling."
        ),
        "changes": [
            "Legger til /api/v1/registered-vehicles/stays.",
            "Krever is_valid=true og landkode NO, SE eller DK.",
            "Dedupliserer kamerahendelser og grupperer per registreringsnummer og lokal kalenderdag.",
        ],
        "applications": [
            "Protect Ledger: nytt internt lese-API og SQL-aggregat.",
            "Fibaro10 build 1813: avstemming mot parkeringsbetaling.",
        ],
    },
    {
        "version": "1",
        "build": "20",
        "date": "07.08.2026",
        "headline": "Korrigert selektiv utrulling med flere berorte tjenester",
        "title": "Protect Ledger 19 leveres sammen med deployrettingen",
        "description": (
            "Forste utrullingsforsok bygget ingen containere fordi shell-betingelsen ikke handterte to "
            "tjenestenavn. Build 20 inneholder samme ytelsesforbedring som build 19 og markerer den "
            "korrigerte, verifiserte produksjonsutrullingen."
        ),
        "request": "gjør dette i den rekkefølgen",
        "changes": [
            "Beholder lett dagsammendrag og avgrenset detaljhenting fra build 19.",
            "Utrulles med en eksplisitt boolsk tjenestetest som takler flere containere.",
        ],
        "applications": [
            "Protect Ledger: produksjonsleveranse av den nye skiltjournalen.",
            "Fibaro10 build 1663: korrigert selektiv deploy.",
        ],
    },
    {
        "version": "1",
        "build": "19",
        "date": "07.08.2026",
        "headline": "Rask dagsoversikt med komplett detaljarkiv ved behov",
        "title": "Skiltjournalen skiller lett listegrunnlag fra full deteksjonshistorikk",
        "description": (
            "Protect Ledger kan na levere et lite dagsammendrag med første og siste bilde, alle tidspunkter "
            "og komplett kvalitetsgrunnlag. Hele deteksjonslisten kan samtidig avgrenses til ett skilt og "
            "hentes først nar brukeren ber om detaljene."
        ),
        "request": "gjør dette i den rekkefølgen",
        "changes": [
            "Legger til include_detections for lett eller komplett dagsrespons.",
            "Legger til plate-filter for rask detaljhenting av ett registreringsnummer.",
            "Bevarer full OCR-variantkontroll med et separat, lett tids- og kameragrunnlag.",
            "Tester bade sammendragsmodus og avgrenset detaljsporring.",
        ],
        "applications": [
            "Protect Ledger: dagsaggregat og internt lese-API.",
            "Fibaro10 build 1662: rask observerte-biler-side.",
        ],
    },
    {
        "version": "1",
        "build": "18",
        "date": "07.08.2026",
        "headline": "Oppdatert og sikker Python-plattform",
        "title": "Protect Ledger bruker samme reviderte webplattform som resten av løsningen",
        "description": (
            "Aiohttp er oppdatert til siste korrigerte versjon, og tjenestens komplette "
            "avhengighetstre er kontrollert automatisk mot kjente sårbarheter."
        ),
        "request": "sett igang og gjør alt i den rekkefølgen du foreslår",
        "changes": [
            "Oppdaterer aiohttp fra 3.14.2 til 3.14.3.",
            "Inkluderer Protect Ledger i den felles pip-audit-kontrollen.",
            "Bevarer eksisterende bildeanalyse og hendelseslogikk uendret.",
        ],
        "applications": [
            "Protect Ledger: oppdatert HTTP-klient/serveravhengighet.",
            "Fibaro10 build 1654: felles Python-sikkerhetsrevisjon.",
        ],
    },
    {
        "version": "1",
        "build": "17",
        "date": "01.08.2026",
        "headline": "Isolert lokal AI-analyse",
        "title": "Pullerter og trapp får uavhengig PatchCore- og strukturkontroll med varmekart",
        "description": (
            "Protect Ledger sender bare de faste kontrollutsnittene til en lokal CPU-tjeneste på QNAP. "
            "AI-score, terskel og varmekart lagres per kontrollflate. Når modellen er klar, må den "
            "bekrefte et klassisk utslag før alarm; ved AI-feil faller systemet tilbake til OpenCV."
        ),
        "request": "Kontroller både pullertene og trappa med en lokal AI-modell.",
        "changes": [
            "Kobler tre pullertprofiler og en egen trappeprofil til riktig fast kildeutsnitt.",
            "Bruker samlet score fra posisjonsbundet feature-analyse og lokal kantgeometri.",
            "Lagrer AI-status, score, terskel, varmekart, modellversjon og inferenstid.",
            "Rapporterer normal, AI-vurdering, klassisk vurdering eller samstemt avvik som hybridstatus.",
            "Krever samstemt klassisk og lokal AI-vurdering for alarm når modellen er klar.",
            "Beholder eksisterende bildeanalyse og varsling fullt operativ ved alle AI-feil.",
        ],
        "applications": [
            "Protect Ledger: AI-klient, databasespor og bilde-API.",
            "Visual Anomaly Service: lokale modeller og varmekart.",
            "Fibaro10 build 1614: operativ visning av AI-resultatene.",
        ],
    },
    {
        "version": "1",
        "build": "16",
        "date": "01.08.2026",
        "headline": "Direkte sammenligning av faste utsnitt",
        "title": "Trappebildet beskjæres, lagres og sammenlignes uten geometrisk behandling",
        "description": (
            "Referanse og løpende bilde bruker samme Protect-opptaksmodus. Det absolutte "
            "kildepikselrektangelet lagres som selve kontrollbildet, og analysen arbeider direkte "
            "på alle pikslene i dette utsnittet uten arbeidsnedskalering eller bildejustering."
        ),
        "request": "Beskjær originalbildet med faste punkter og sammenlign bare resultatet.",
        "changes": [
            "Materialiserer trappereferansen som et eget beskåret JPEG-bilde.",
            "Lagrer hvert nytt trappebilde med identiske absolutte koordinater.",
            "Fjerner nedskalering fra trappeanalysen og avviser avvikende bildestørrelse.",
            "Bruker highQuality=true for både referanse og alle løpende kontroller.",
            "Lagrer også beskåret bildebevis dersom trappealarmen utløses.",
        ],
        "applications": [
            "Protect Ledger: kildepikselbasert trappeanalyse og bilde-API.",
            "Fibaro10 build 1612: tydelig egen Trapp-gruppe.",
        ],
    },
    {
        "version": "1",
        "build": "15",
        "date": "01.08.2026",
        "headline": "Selvstendig overvåking av trappa",
        "title": "Trapp og pullerter analyseres som separate kontrollobjekter",
        "description": (
            "Trappa ved Solstudio har fått eget fast kildepikselutsnitt, egen vedvarende status og "
            "eget skadesvarsel. Pullertutsnittet forblir kompakt og de to analysene påvirker ikke hverandre."
        ),
        "request": "Trappa er like viktig å varsle på; skill den ut som eget varsel og eget utsnitt.",
        "changes": [
            "Oppretter en egen fast strukturmonitor for Trapp ved Solstudio.",
            "Bruker utsnittet x=2200, y=400, bredde=1640 og høyde=1760 uten geometrisk behandling.",
            "Sammenligner hele trappestrukturen mot referansen og krever vedvarende endring før alarm.",
            "Maskerer asfalt og dørrefleksjoner utenfor trappa fra selve skadeanalysen.",
            "Lagrer trappeavvik som egen hendelse med egen varseltekst.",
        ],
        "applications": [
            "Protect Ledger: separat analyse, status og bilde-API for trappa.",
            "Fibaro10 build 1611: eget kontrollområde for trappa.",
            "Vedlikehold mobil build 1465: viser trappa med eget utsnitt og status.",
        ],
    },
    {
        "version": "1",
        "build": "14",
        "date": "01.08.2026",
        "headline": "Fast utsnitt av uendrede kildepiksler",
        "title": "Kamerabildene beskjæres på serveren uten geometrisk korreksjon",
        "description": (
            "Build 14 bruker ett absolutt 4K-pikselrektangel per pullertkamera. Referanse, siste bilde "
            "og analysebilde får samme utsnitt uten zoom, rotasjon, flytting eller perspektivkorrigering. "
            "En endret kameraoppløsning avvises i stedet for å bli normalisert."
        ),
        "request": "Bildene skal bare beskjæres likt hver gang og ellers være uendret; bare innholdet skal tolkes.",
        "changes": [
            "Definerer faste, absolutte pikselrektangler for alle tre kameraene.",
            "Leverer ferdig beskårne JPEG-bilder til alle grensesnitt gjennom begge API-navnerom.",
            "Fjerner klientenes relative zoom og fargefilter på referansebildet.",
            "Legger på X-Image-Geometry og X-Crop-Rect for enkel teknisk kontroll.",
        ],
        "applications": [
            "Protect Ledger: sentral og testet pikselbeskjæring.",
            "Fibaro10 build 1610: bruker den beskårne bildestrømmen direkte.",
            "Vedlikehold mobil build 1464: samme bildefremstilling på Varsler.",
        ],
    },
    {
        "version": "1",
        "build": "13",
        "date": "01.08.2026",
        "headline": "Slider med entydige bildeendepunkter",
        "title": "Opptakstid og tydelig farge skiller referansen fra siste bilde",
        "description": (
            "Build 13 viser full dato og klokkeslett ved begge ender av transparensslideren. "
            "Referansebildet har en tydeligere kjølig blågrå behandling, mens siste bilde fortsatt "
            "vises i originale farger og identiske faste pikselposisjoner."
        ),
        "request": "Gjør fargeforskjellen tydeligere og vis rolle, dato og klokkeslett ved slideren.",
        "changes": [
            "Legger full opptakstid under Referanse til venstre og Siste bilde til høyre.",
            "Forsterker bare referansens blågrå fargebehandling.",
            "Beholder siste bilde ubehandlet og geometrien helt fast.",
        ],
        "applications": [
            "Protect Ledger: entydig slider med opptakstider.",
            "Fibaro10 build 1609: samme sammenligning i Pullerter.",
            "Vedlikehold mobil build 1463: samme sammenligning på Varsler.",
        ],
    },
    {
        "version": "1",
        "build": "12",
        "date": "01.08.2026",
        "headline": "Tydelig transparent kameraoverlegg",
        "title": "Transparens er tilbake uten å gi slipp på fast geometri og referansemerking",
        "description": (
            "Build 12 gjeninnfører den foretrukne transparente sammenligningen. Referansen er fortsatt "
            "blågrå og begge bilder bruker identiske, faste pikselposisjoner. Skyveren er tydelig merket "
            "fra referanse ved 0 prosent til siste bilde ved 100 prosent."
        ),
        "request": "Behold transparent sammenligning, men ta vare på de øvrige forbedringene.",
        "changes": [
            "Gjeninnfører kontrollert transparens mellom referanse og siste bilde.",
            "Beholder fast kamerageometri uten flytting eller perspektivjustering.",
            "Beholder blågrå referanse, tidsstempler og tydelig 0–100-prosentmerking.",
        ],
        "applications": [
            "Protect Ledger: transparent overlegg med fast geometri.",
            "Fibaro10 build 1608: samme sammenligning i Pullerter.",
            "Vedlikehold mobil build 1462: samme sammenligning på Varsler.",
        ],
    },
    {
        "version": "1",
        "build": "11",
        "date": "01.08.2026",
        "headline": "Fast før/etter-skyver uten visuell forskyvning",
        "title": "Referanse og siste bilde skilles tydelig uten kryssblanding",
        "description": (
            "Build 11 erstatter det gjennomsiktige bildeoverlegget med en ekte før/etter-skyver. "
            "Referansen står fast til venstre med blågrå fargebehandling, mens siste bilde står fast "
            "til høyre i originalfarger. Bare den tydelige skillelinjen flyttes."
        ),
        "request": "Gjør referansen tydeligere og fjern inntrykket av at kamerabildet flytter seg.",
        "changes": [
            "Fjerner gjennomsiktighetsblanding mellom referanse og siste bilde.",
            "Legger inn fast pikselbasert før/etter-skyver med tydelig håndtak.",
            "Viser blågrå referanse, siste bilde i originalfarger og tidsstempel på begge.",
            "Oppdaterer forklaringene slik at fast kamerageometri er tydelig dokumentert.",
        ],
        "applications": [
            "Protect Ledger: før/etter-skyver og tydelige bildemerker.",
            "Fibaro10 build 1607: samme sammenligningsmodell i Pullerter.",
            "Vedlikehold mobil build 1461: samme sammenligningsmodell på Varsler.",
        ],
    },
    {
        "version": "1",
        "build": "10",
        "date": "01.08.2026",
        "headline": "Fast kamerageometri i pullertkontrollen",
        "title": "Kamerabildene sammenlignes uten automatisk forskyvning",
        "description": (
            "Build 10 fjerner perspektivjusteringen som kunne flytte deler av et bilde selv om "
            "kameraet sto fast. Referanse, siste bilde, overlay og pullertsoner bruker nå de samme "
            "faste pikselposisjonene. Bare en eventuell endring i bildeoppløsning normaliseres."
        ),
        "request": "Kameraene står fast, de flytter seg ikke.",
        "changes": [
            "Fjerner ORB-basert homografi og perspektivtransformasjon fra pullertanalysen.",
            "Beholder nye kamerabilder uforflyttet i både analyse og siste-bilde-visning.",
            "Bruker samme faste koordinater for referanse, pullertsoner og overlay.",
            "Normaliserer bare oppløsningen dersom kameraets bildestørrelse faktisk er endret.",
            "Legger regresjonstester som avviser enhver automatisk geometrisk forskyvning.",
        ],
        "applications": [
            "Protect Ledger: fast pikselbasert pullertanalyse og bildelagring.",
            "Fibaro10 Pullerter: siste bilde og overlay vises uten kunstig perspektivforskyvning.",
        ],
    },
    {
        "version": "1",
        "build": "9",
        "date": "22.07.2026",
        "headline": "Pullertsoner tåler sol, skygge og trafikk",
        "title": "Automatisk varsling avgjøres av selve pullertene",
        "description": (
            "Build 9 beholder helbildene for justering, dokumentasjon og overlay, men flytter "
            "alarmbeslutningen til faste interne soner rundt metallstrukturene. Dermed kan ikke "
            "endret sollys, asfalt eller en bil utenfor pullertene sette alle kameraene i tildekket status."
        ),
        "request": "Vis referanse og siste bilde som overlay, og gjør automatisk varsling forståelig og pålitelig.",
        "changes": [
            "Tre kameraer justeres fortsatt geometrisk mot sine faste referansebilder hvert femte minutt.",
            "Selve flytteanalysen bruker skjulte, kameraspesifikke soner rundt de synlige pullertene.",
            "Treffgrensen er kontrollert mot både dagslys, direkte sol og simulerte fjernede pullerter.",
            "En enkelt tildekket sone gir ikke alarm; flere manglende soner klassifiseres som tildekking.",
            "Avvik må vedvare i fem minutter og bekreftes av minst to kameraer før ntfy-varsel sendes.",
            "Overlay-bildet beholder komplette lokale før- og etterbilder uten å tegne analysefeltene i brukerflaten.",
        ],
        "applications": [
            "unifi_protect_events/app/bollards.py: fast soneanalyse, flerkamerabekreftelse og lokal dokumentasjon.",
            "unifi_protect_events/tests/test_bollards.py: normaltilstand og simulert fysisk flytting.",
            "Vedlikehold mobil build 1460: referanse og siste bilde som standard-overlay.",
        ],
    },
    {
        "version": "1",
        "build": "8",
        "date": "21.07.2026",
        "headline": "Separat og personvernssikker pullertkanal",
        "title": "Mobilabonnementet for pullerter er skilt helt fra dørvarsler",
        "description": (
            "Build 8 oppretter en egen pullertkanal når ingen eksplisitt kanal er konfigurert. "
            "Alarmteksten inneholder bare pullertnavn og kontrollbeskjed. Lokale bilder, "
            "registreringsnummer og hendelseskontekst sendes aldri med pushvarselet."
        ),
        "request": "Gjør det mulig å abonnere på pullerter på samme måte som dører, men som et eget abonnement.",
        "changes": [
            "Fjerner reservekoblingen til NTFY_DOORS_TOPIC.",
            "Avleder en separat, vanskelig gjettbar pullertkanal fra lokal hovednøkkel.",
            "Fjerner registreringsnummer fra ekstern varseltekst.",
            "Beholder komplett hendelseskontekst og alle bilder lokalt.",
        ],
        "applications": [
            "unifi_protect_events/app/main.py: separat kanaloppsett.",
            "unifi_protect_events/app/bollards.py: personvernssikker alarmtekst.",
            "Fibaro10 build 1598: mobilstatus, abonnement og testvarsel.",
        ],
    },
    {
        "version": "1",
        "build": "7",
        "date": "21.07.2026",
        "headline": "Automatisk helbildesammenligning hvert femte minutt",
        "title": "Tre faste kamerareferanser sammenlignes uten manuelle markeringer",
        "description": (
            "Build 7 erstatter manuell kalibrering med ett fast referansebilde for hvert av de tre "
            "G6-kameraene. Hvert femte minutt hentes et nytt lokalt bilde, rettes inn mot referansen "
            "og sammenlignes. Grensesnittet viser referanse og nytt bilde som justerbar overlay, samt "
            "et beregnet forskjellsbilde der lokale strukturelle endringer markeres rødt."
        ),
        "request": "Sammenlign hele bildene, behold eksisterende bilder som referanse og hent nytt bilde hvert femte minutt.",
        "changes": [
            "Ingen områder, polygoner eller manuelle pullertmarkeringer er nødvendige.",
            "Faste helbilder fra G6 Butikk Nord, G6 Butikk Front og G6 Solstudio Front brukes som referanser.",
            "Nye bilder justeres geometrisk mot referansen før piksel- og kantforskjeller beregnes.",
            "Store endringer fra biler, mennesker eller lys klassifiseres som tildekking i stedet for pullertalarm.",
            "Lokal strukturell endring må vedvare og støttes av flere kameraer før varsel.",
            "Kun siste femminuttersbilde og overlay beholdes; hendelsesbilder lagres separat som bevis.",
        ],
        "applications": [
            "unifi_protect_events/app/bollards.py: helbildejustering, differanse og flerkamerabekreftelse.",
            "unifi_protect_events/app/static: før/etter-slider og rødt forskjellsbilde.",
            "migrations/versions/20260721_2230_add_bollard_full_frame_comparison.sql: kamerareferanser og sammenligningsstatus.",
            "Fibaro10 API: samme lokale endepunkt med kamerastatus, referanse, siste bilde og overlay.",
        ],
    },
    {
        "version": "1",
        "build": "6",
        "date": "21.07.2026",
        "headline": "Lokal overvåking av pullerter",
        "title": "Tre G6-kameraer oppdager vedvarende flytting med før- og etterbilder",
        "description": (
            "Build 6 legger til en egen Pullerter-modul for G6 Butikk Nord, G6 Butikk Front og "
            "G6 Solstudio Front. Brukeren markerer pullertene direkte i lokale kamerabilder, "
            "godkjenner referansene og kan deretter aktivere en ressursbegrenset bakgrunnsanalyse. "
            "Ved bekreftet avvik lagres riktig referanse, nytt kontrollbilde og nærliggende bil- og skiltdata."
        ),
        "request": "Overvåk pullertene foran solstudioet og varsle hvis en blir kjørt på og flyttet.",
        "changes": [
            "Stort kalibreringsgrensesnitt med zoom og formtilpasset overlay for de tre valgte G6-kameraene.",
            "Bare pikslene inne i pullertens polygonmaske brukes i den lokale OpenCV-sammenligningen.",
            "Kamerajustering og maskert bildesøk måler fysisk forskyvning uten at asfalt og biler dominerer.",
            "Vedvarende avvik kreves, og to kameravinkler brukes når samme pullert er markert flere steder.",
            "Referanse og kontrollbilde lagres lokalt per kamera sammen med komplett hendelseshistorikk.",
            "Tekstvarsel kan kobles til eksisterende lokale ntfy-kanal uten å sende bilder ut.",
            "Tokenbeskyttet API og Fibaro10-proxy eksponerer status, historikk og bevisbilder.",
        ],
        "applications": [
            "unifi_protect_events/app/bollards.py: analyse, kalibrering, hendelser og varsling.",
            "unifi_protect_events/app/static: egen responsiv Pullerter-side.",
            "migrations/versions/20260721_2200_add_unifi_bollard_monitoring.sql: databaseschema.",
            "Fibaro10 API: lokal lesetilgang til pullertstatus og bilder.",
        ],
    },
    {
        "version": "1",
        "build": "5",
        "date": "21.07.2026",
        "headline": "Deteksjonsbilde fra riktig kamera og tidspunkt",
        "title": "Hver gjenkjenning får nå sitt eget tidsstyrte kamerabilde",
        "description": (
            "Build 5 skiller gjenkjenningsbilder fra generelle hendelsesbilder. Når Alarm Manager "
            "sender et skilt eller ansikt, bruker Ledger kamera-ID-en i webhooken og tidsstyrer et "
            "høyoppløst lokalt snapshot mot OCR-tidspunktet. Bildets kamera, tidspunkt og avvik lagres "
            "som revisjonsdata og følger gjenkjenningen videre til Fibaro10."
        ),
        "request": "Jeg trenger bilde fra rett kamera på rett tidspunkt.",
        "changes": [
            "Egen prioritert bildekø for skilt- og ansiktsgjenkjenninger.",
            "Ett bilde per kamera og OCR-tidspunkt, koblet til alle samtidige OCR-forslag.",
            "Høyoppløst snapshot tidsstyres mot webhookens hendelsestid med begrenset venting.",
            "API-et eksponerer bildekamera, bildets tidspunkt, tidsavvik, status og kilde.",
            "Eldre livebilder fra generelle hendelser brukes ikke lenger som OCR-dokumentasjon.",
        ],
        "applications": [
            "unifi_protect_events/app/main.py: gjenkjenningskø, tidsstyrt kamerahenting og bilde-API.",
            "unifi_protect_events/app/integration.py: revisjonsmetadata i liste-, detalj- og dags-API.",
            "unifi_protect_events/app/static: korrekt bilde og tidsavvik i grensesnittet.",
            "migrations/versions/20260721_2030_add_unifi_recognition_snapshots.sql: bildeschema.",
            "Fibaro10 Biler: deteksjonsbilde per OCR-observasjon i stedet for hendelsesbilde.",
        ],
    },
    {
        "version": "1",
        "build": "4",
        "date": "21.07.2026",
        "headline": "Synlig buildnummer og egen buildlogg",
        "title": "Protect Ledger viser versjon og komplett endringshistorikk",
        "description": (
            "Build 4 gir Protect Ledger en egen, synlig versjonsidentitet. Gjeldende build vises i "
            "sidefeltet, helsesjekken og API-et, mens en ny Buildlogg-side samler hva som ble endret, "
            "hvorfor det ble gjort og hvilke deler av løsningen som ble berørt."
        ),
        "request": "Vi må ha inn buildnummer og logg i PL også.",
        "changes": [
            "Gjeldende versjon og build vises fast nederst i hovedmenyen.",
            "Ny hovedside viser søkbar buildhistorikk med endringer og berørte komponenter.",
            "Health, oversikt og det versjonerte API-et eksponerer samme buildinformasjon.",
            "PL-versjonen kan styres separat fra Fibaro10 med egne miljøvariabler.",
        ],
        "applications": [
            "unifi_protect_events/app/build_log.py: egen statisk og maskinlesbar buildhistorikk.",
            "unifi_protect_events/app/main.py: buildinfo i health og nye build-API-er.",
            "unifi_protect_events/app/templates/index.html: egen Buildlogg-side og buildlenke.",
            "unifi_protect_events/app/static/app.js: lasting, søk og presentasjon av historikken.",
            "docker-compose.qnap.yml: separat PL-versjon og buildnummer.",
        ],
    },
    {
        "version": "1",
        "build": "3",
        "date": "21.07.2026",
        "headline": "Nordisk skiltvalidering eies av Ledger",
        "title": "Bilskilt renses og kvalitetssikres før de leveres til Fibaro10",
        "description": (
            "Build 3 flyttet all behandling av registreringsnummer til Protect Ledger. Råobservasjoner "
            "beholdes, mens normaliserte skilt kontrolleres mot lokal historikk, Statens vegvesen og "
            "relevante svenske og danske oppslagskilder før de får en presentasjonsstatus."
        ),
        "request": "All behandling og rydding bør skje i Protect Ledger før presentasjon i Fibaro10.",
        "changes": [
            "Ny Biler-side med dato, søk, kvalitetsfilter og første/siste deteksjon.",
            "Valideringskjede med cache, retry og tydelig skille mellom feil og manglende treff.",
            "Mulige OCR-varianter merkes uten å slette eller slå sammen råobservasjoner.",
            "Fibaro10 henter ferdig kvalitetssikrede skilt og kobler bare parkering og betaling.",
        ],
        "applications": [
            "unifi_protect_events/app/plate_validation.py: valideringskø og kildeorkestrering.",
            "unifi_protect_events/app/integration.py: dagsoversikt og normaliserte API-svar.",
            "unifi_protect_events/app/static: komplett lokal Biler-side.",
            "migrations/versions/20260721_1700_add_unifi_plate_validations.sql: cache og revisjonsspor.",
        ],
    },
    {
        "version": "1",
        "build": "2",
        "date": "21.07.2026",
        "headline": "Alle skilt og kjente personer",
        "title": "Alarm Manager-webhooks lagrer verdier som WebSocket ikke inneholder",
        "description": (
            "Build 2 utvidet Ledger med lokale webhook-mottak for UniFi Protect Alarm Manager. Dette "
            "gjør det mulig å lagre både kjente og ukjente bilskilt samt kjente ansikter, med kobling "
            "til nærmeste hendelse og stillbilde når Protect sender nødvendig metadata."
        ),
        "request": "Lagre alle bilskilt og rapporter kjente personer.",
        "changes": [
            "Deduplisert lagring av komplette Alarm Manager-kall.",
            "Normaliserte gjenkjenninger for bilskilt, ansikt og person av interesse.",
            "Egen Gjenkjenning-side og tokenbeskyttede integrasjonsendepunkter.",
            "Live kontroll av hvilke kjent/ukjent-regler som faktisk har sendt data.",
        ],
        "applications": [
            "unifi_protect_events/app/integration.py: webhooktolking, lagring og korrelasjon.",
            "unifi_protect_events/app/main.py: webhook, gjenkjennings-API og SSE.",
            "unifi_protect_events/app/static: Gjenkjenning- og Integrasjoner-sider.",
            "migrations/versions/20260721_1500_add_unifi_recognitions_api.sql: webhook- og gjenkjenningstabeller.",
        ],
    },
    {
        "version": "1",
        "build": "1",
        "date": "21.07.2026",
        "headline": "Lokal UniFi Protect-hendelseslogg",
        "title": "Protect Ledger samler hendelser og stillbilder lokalt på QNAP",
        "description": (
            "Build 1 etablerte Protect Ledger som en selvstendig lokal tjeneste. Den lytter på UniFi "
            "Protects WebSocket, dedupliserer oppdateringer, lagrer rådata i PostgreSQL og henter ett "
            "stillbilde per valgt hendelse uten å bruke UniFi Cloud."
        ),
        "request": "Lag en god lokal løsning for UniFi-hendelser med valgfri lagring og eget grensesnitt.",
        "changes": [
            "Stabil WebSocket-innlesing med gjenoppkobling og avgrenset stillbildekø.",
            "Katalog over alle observerte og mulige hendelses- og deteksjonstyper.",
            "Konfigurerbar lagring per kamera, type og AI-/lyddeteksjon.",
            "Responsive sider for oversikt, hendelser, lagring og integrasjoner.",
            "Versjonert REST-API og SSE-strøm for lokale konsumenter.",
        ],
        "applications": [
            "unifi_protect_events/app/main.py: innsamler, health, API og applikasjonslivsløp.",
            "unifi_protect_events/app/admin.py: policy, katalog, søk og lagringsstatistikk.",
            "unifi_protect_events/app/static: selvstendig administrasjonsgrensesnitt.",
            "migrations/versions/20260721_1045_add_unifi_protect_events.sql: grunnschema.",
            "migrations/versions/20260721_1230_add_unifi_event_policy_ui.sql: policy og stillbilder.",
        ],
    },
]


def normalized_build_log_entry(row: dict[str, Any]) -> dict[str, Any]:
    build = str(row.get("build") or "")
    return {
        "version": str(row.get("version") or PROTECT_LEDGER_VERSION),
        "build": build,
        "date": str(row.get("date") or ""),
        "headline": str(row.get("headline") or row.get("title") or f"Build {build}"),
        "title": str(row.get("title") or row.get("headline") or f"Build {build}"),
        "description": str(row.get("description") or ""),
        "request": str(row.get("request") or ""),
        "changes": list(row.get("changes") or []),
        "applications": list(row.get("applications") or []),
    }


def protect_ledger_build_summary() -> dict[str, str]:
    return {
        "name": "Protect Ledger",
        "version": PROTECT_LEDGER_VERSION,
        "build": PROTECT_LEDGER_BUILD,
        "commit": PROTECT_LEDGER_COMMIT,
    }


def protect_ledger_build_log_payload(
    *, query: str = "", limit: int = 100
) -> dict[str, Any]:
    all_rows = [normalized_build_log_entry(row) for row in PROTECT_LEDGER_BUILD_LOG]
    rows = list(all_rows)
    needle = query.strip().casefold()
    if needle:
        rows = [
            row
            for row in rows
            if needle
            in " ".join(
                [
                    row["build"],
                    row["date"],
                    row["headline"],
                    row["title"],
                    row["description"],
                    row["request"],
                    *row["changes"],
                    *row["applications"],
                ]
            ).casefold()
        ]
    limited = rows[: max(1, min(limit, 500))]
    return {
        "current": protect_ledger_build_summary(),
        "current_build": PROTECT_LEDGER_BUILD,
        "latest": all_rows[0] if all_rows else None,
        "total_count": len(all_rows),
        "count": len(rows),
        "items": limited,
    }


def protect_ledger_build_detail(build: str) -> dict[str, Any] | None:
    requested = build.strip()
    for row in PROTECT_LEDGER_BUILD_LOG:
        if str(row.get("build") or "") == requested:
            return normalized_build_log_entry(row)
    return None
