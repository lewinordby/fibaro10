# Dreame_logger

Separat innlesings- og kontrolltjeneste for Dreame-robotene. Tjenesten kjører på QNAP port `8094`, leser
Dreamehome og sender normalisert status, telemetri, historikk og planer til Fibaro10.

## Aqua10

1. Legg roboten til i Dreamehome og sett navnet til `Aqua10`.
2. Kopier `.env.example` til `.env` og legg inn Dreamehome-kontoen.
3. Opprett Docker-volumet én gang: `docker volume create dreame_logger_dreame_logger_data`.
4. Kjør `docker compose -f docker-compose.qnap.yml up -d --build`.
5. Åpne `http://192.168.20.218:8094` og kjør første synkronisering.

Tjenesten er isolert fra Roborock-loggeren. En feil eller ny build her påvirker derfor ikke de eksisterende
robotene. Dersom Fibaro10 er utilgjengelig, legges ferdige batcher i lokal kø og sendes senere.
Eksempelfilen er versjonsstyrt, mens den virkelige `.env`-filen bevares lokalt på QNAP ved hver utrulling og
tas med i nattbackupen.

## Vannhendelser og påfylling (build 4)

Vanlig synkronisering av status, jobber og planer går fortsatt hvert femte minutt.
Endringer i rentvannstank, skittentvannstank, vannvarsel og robotens tank registreres
i tillegg direkte fra Dreame-integrasjonens property-listeners. Det krever ikke
hyppigere skraping. En tank kan tas ut og settes tilbake mellom to vanlige innlesinger.

Hver observasjon lagres umiddelbart i `/data/telemetry-outbox`, med mottakstidspunkt
og årsak i rådataenes `collection`. Køen sendes i rekkefølge, normalt innen to sekunder.
Ved API-feil beholdes observasjonene på disk og forsøkes igjen etter 30 sekunder.
De overlever omstart. Påfyllingsloggen bruker fortsatt faktisk tankstatus: uttak og
tilbake til OK er en indikasjon på påfylling, ikke en måling av antall liter.
En tapt forbindelse til Dreame kan fortsatt medføre manglende mellomliggende hendelser.
Vannsperren for planlagte jobber kontrolleres som før ved vanlig synkronisering.

Feilen 6. september 2026: tankuttak 16:14:17 og tilbake 16:16:34 ble mottatt i Dreame,
men falt mellom databasesamplene 16:11:41 og 16:16:41. Logger med disse hendelsene
kan repareres med `scripts/recover-dreame-refill-events.py`. Scriptet kjører kontroll
uten endringer først; `--apply` lagrer bare dokumenterte hendelser, med original
logglinje som kilde. Det endrer ikke måleverdier eller robotens nåværende status.

## Teknisk avhengighet

Docker-bygget henter commit `3720223e11353aba622f8da34c9041586865aa48` (`v2.0.0b25`) av den MIT-lisensierte
`Tasshack/dreame-vacuum`-integrasjonen. Versjonen støtter Dreamehome og Aqua10-familien. Kartbehandling er slått
av for lavere minnebruk. Integrasjonens valgfrie analyseanrop erstattes med en lokal, deaktivert adresse under
bygging; robotidentitet sendes derfor ikke til tredjepartsanalyse fra denne tjenesten.
