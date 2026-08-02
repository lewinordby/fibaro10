# UniFi Protect → Protect Ledger → Fibaro10

## Lokal arkitektur

All innhenting skjer fra QNAP direkte mot `https://192.168.1.1`. Protect Ledger
bruker det offisielle lokale REST- og WebSocket-grensesnittet. PostgreSQL,
stillbilder, Alarm Manager-webhooks og Fibaro10-integrasjonen forblir på
lokalnettet.

## Fibaro10-endepunkter

Fibaro10-serveren videresender følgende kall til Protect Ledger med tjenestetoken:

- `GET /api/unifi-protect/status`
- `GET /api/unifi-protect/cameras`
- `GET /api/unifi-protect/capabilities`
- `GET /api/unifi-protect/stats`
- `GET /api/unifi-protect/events?limit=100&cursor=...`
- `GET /api/unifi-protect/recognitions?kind=license_plate&is_known=false`
- `GET /api/unifi-protect/recognitions/{recognition_id}`
- `GET /api/unifi-protect/recognitions/{recognition_id}/snapshot`
- `GET /api/unifi-protect/events/{source_event_id}/snapshot`
- `GET /api/unifi-protect/bollards`
- `GET /api/unifi-protect/bollards/cameras/{camera_id}/{baseline|latest|overlay|ai}`
- `GET /api/unifi-protect/bollards/cameras/{camera_id}/{baseline|latest|overlay}/crop`
- `GET /api/unifi-protect/bollards/assets/{asset_key}/{baseline|latest|overlay|ai}`
- `GET /api/unifi-protect/bollards/regions/{region_id}/baseline`
- `GET /api/unifi-protect/bollards/incidents/{incident_id}/images/{camera_id}/{kind}`

Disse rutene bruker Fibaro10s eksisterende innlogging. Frontend-kode skal derfor
bruke proxyen og aldri få tilgang til `UNIFI_PROTECT_READ_API_TOKEN`.
Ruten uten `/crop` leverer det urørte helbildet for kompatibilitet. Ruten med
`/crop` leverer kameraets faste pikselutsnitt og brukes av de nye grensesnittene.

## Direkte API

Interne tjenester kan lese `http://unifi_protect_events:8130/api/v1/*` med:

```http
Authorization: Bearer <UNIFI_PROTECT_READ_API_TOKEN>
```

Lister returnerer `items`, `has_more` og `next_cursor`. Send `next_cursor` tilbake
som `cursor` for neste side. Hendelser kan filtreres på `event_type`, `camera_id`,
`detection_type`, `from`, `to` og `has_snapshot`. Gjenkjenninger kan filtreres på
`kind`, `value`, `camera_id`, `is_known`, `from` og `to`.

SSE-strømmen `/api/v1/stream` bruker hendelsesnavnene `event` og `recognition`.
Klienter skal gjøre vanlig reconnect og deretter hente siste side for å dekke et
eventuelt mellomrom.

`GET /api/v1/stats` gir Fibaro10 ett samlet kall for drift, kameraer,
hendelsestall, gjenkjenningstall og status på Alarm Manager-signalene.
`GET /api/v1/recognitions/{id}` inkluderer rå trigger, rå webhook, korrelert
hendelse og bildets kamera, tidspunkt, tidsavvik og status. Det dedikerte
`GET /api/v1/recognitions/{id}/snapshot` returnerer bare bildet som ble hentet
for den konkrete gjenkjenningen; eldre hendelsesbilder brukes aldri som fallback.

## Alarm Manager

Mottaker:

```text
POST http://192.168.20.218:8130/api/v1/webhooks/unifi-alarm
```

Gatewayadressen i `UNIFI_PROTECT_WEBHOOK_ALLOWED_IPS` kan sende POST direkte.
Andre avsendere autentiserer med et separat `UNIFI_PROTECT_WEBHOOK_TOKEN` som
Bearer-token, `X-API-Key` eller `?token=...`. Opprett separate regler
for kjente og ukjente skilt for å lagre alle registreringer. Opprett tilsvarende
regler for ansikter. Test hver regel i UniFi og kontroller siden
`/integrations`; den innebygde sjekklisten blir grønn etter hvert som hver av de
fire signalvariantene faktisk er mottatt. Rå webhook beholdes for feilsøking og
fremtidig parsertilpasning. UniFis offentlige Protect-API tilbyr ikke oppretting
av Alarm Manager-regler, så dette engangsvalget gjøres i Protect-grensesnittet.

## Pullertovervåking

Administrasjon ligger på `http://192.168.20.218:8130/bollards`. Modulen er låst
til `G6 Butikk Nord`, `G6 Butikk Front` og `G6 Solstudio Front`. Alle bilder
hentes direkte fra lokal Protect-gateway og lagres i samme lokale snapshot-rot
som resten av Ledger.

Hvert kamera har ett fast helbilde som godkjent referanse. Hvert femte minutt
henter Ledger et nytt lokalt bilde og sammenligner faste, interne soner rundt
pullertene i de samme pikselposisjonene som i referansen. Bildet flyttes,
skaleres, roteres eller perspektivjusteres aldri. Endret kameraoppløsning gir en
feil i stedet for automatisk normalisering. Grensesnittet får et ferdig utsnitt
fra ett absolutt 4K-pikselrektangel per kamera. Referanse og siste bilde bruker
alltid identisk rektangel og vises uten fargefilter; slideren endrer bare
gjennomsiktigheten mellom lagene.

Trappa ved Solstudio er et selvstendig kontrollobjekt på kameraet
`G6 Solstudio Front`. Pullertene bruker sitt kompakte utsnitt, mens trappa bruker
det faste kildepikselutsnittet `x=2200`, `y=400`, `bredde=1640`, `høyde=1760`.
Originalbildet beskjæres straks med disse absolutte koordinatene. Det ferdige
utsnittet lagres som referanse eller siste bilde og er den samme filen som vises
og analyseres. Referanse og løpende bilder hentes med samme Protect-opptaksmodus.
Analysen bruker alle pikslene i det ferdige utsnittet; bildet flyttes, skaleres,
roteres eller perspektivkorrigeres aldri. Trappa har egen lagret status, egen
sammenligning, eget overlegg og egen hendelsestype. En vedvarende strukturell
endring oppretter et separat varsel om mulig endring eller skade på trappa.
Analysepolygonet følger selve metallkonstruksjonen; asfalt, veimerking og
refleksjoner i døra inngår ikke i skadevurderingen.

Store endringer fra parkerte biler, personer, tildekking eller kraftig lysendring
klassifiseres som `obscured` og utløser ikke pullertalarm. En lokal strukturell
endring må fortsatt finnes ved neste femminutterskontroll og støttes av minst to
kameraer før hendelsen bekreftes. Ved bekreftet hendelse lagres referanse og nytt
bilde fra hvert bekreftende kamera. Bil-/skiltobservasjoner i nærheten knyttes til
den lokale konteksten. Pushvarselet bruker en egen pullertkanal og inneholder bare
kort alarmtekst; bilder og registreringsnummer sendes ikke ut.

Trappekontrollen er uavhengig av pullertkontrollen og trenger derfor ikke støtte
fra et annet kamera. Den samme varighetsgrensen brukes, slik at kortvarige
personer eller gjenstander ikke varsles som skade.

### Lokal AI-kontroll

`visual_anomaly_service` kjører lokalt på QNAP uten ekstern bildeoverføring. Den
har fire separate profiler: tre for pullertflatene og én for trappa. Tjenesten
leser Protect-arkivet som read-only, mens modeller og metadata lagres på SSD i
`VISUAL_AI_HOST_DATA_DIR`.

Hvert originalbilde beskjæres først med de samme absolutte 4K-koordinatene som
den klassiske kontrollen. Relevante objektsoner kopieres deretter til et fast
analyseatlas. Kildebildet blir aldri justert, flyttet, perspektivkorrigert eller
brukt med et annet utsnitt. PatchCore-minnebanken er posisjonsbundet: en detalj
kan bare sammenlignes med historiske detaljer fra samme atlasposisjon.

Pullertprofilene bruker egne soner inne i hvert ferdig beskårne visningsbilde.
Dette er bevisst adskilt fra OpenCV-sonene, som er angitt relativt til hele
4K-kilden. Før feature-ekstraksjon gjøres analyseatlaset lokalt grått og
kontrastnormalisert for å dempe utslag fra sol, skygge og kameraets hvitbalanse.
Ingen av disse interne analyseoperasjonene endrer referansebildet eller bildet
som vises i Fibaro10.

Modellen bruker ResNet18 som lokal feature extractor og er trent uten eksterne
skadeetiketter. Hver profil lagrer treningsantall, kalibreringsgrunnlag, terskel,
modellversjon og inferenstid. AI-varmekartet viser hvor avviksscoren oppstår.
Inntil 240 historiske bilder fordeles over hele tidslinjen; omtrent 80 prosent
brukes i minnebanken og resten til uavhengig kalibrering av terskelen.
En separat kantgeometri-score sammenligner samtidig strukturen med det nærmeste
normale historiske bildet. Høyeste terskelforhold fra de to metodene bestemmer
AI-statusen, og begge bidrar til varmekartet.

Når en AI-profil er ferdig trent, krever en ny alarm at både den klassiske
OpenCV-kontrollen og AI-kontrollen finner et avvik. Et rent lys-, skygge- eller
pikselutslag blir fortsatt synlig som klassisk kontrollresultat, men oppretter
ikke alarm når AI-en vurderer strukturen som normal. Dersom AI-tjenesten trener,
stopper eller feiler, faller varslingen automatisk tilbake til klassisk kontroll.
Fibaro10 viser begge vurderingene og den samlede hybridstatusen.

I Fibaro10 vises kontrollområdene i to eksplisitte grupper: `Pullerter` og
`Trapp`. `Trapp ved Solstudio` skal derfor alltid være synlig som et eget valg
når Protect Ledger rapporterer at det faste trappeobjektet er kalibrert.

Det tokenbeskyttede endepunktet `GET /api/v1/bollards` leverer innstillinger,
kameraer, faste referanser, siste sammenligning, overlay, aktiv status, historikk, kontekst og lenker til
bevisbilder. Fibaro10-proxyen skriver lenkene om slik at klienten aldri trenger
Protect Ledger-tokenet.

## Drift

- `/health` krever bare database og viser kødybde, arbeidere og WebSocket-status.
- `/ready` krever både database og aktiv WebSocket.
- Hendelsesbilder og prioriterte gjenkjenningsbilder har separate, begrensede køer.
- Hendelser dedupliseres med Protect event-ID; webhooks dedupliseres med SHA-256.
- Oppbevaringsjobben sletter gamle eventrader, gjenkjenninger, webhooks og
  tilhørende JPEG-filer i samme oppbevaringsvindu.
