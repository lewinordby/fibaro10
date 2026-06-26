import os
from typing import Any, Dict, Optional

from api_types import BuildLogEntryPayload, BuildLogTableRowPayload


APP_VERSION = os.getenv("APP_VERSION", "1")
APP_BUILD = os.getenv("APP_BUILD", "1249")
BUILD_LOG = [
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
