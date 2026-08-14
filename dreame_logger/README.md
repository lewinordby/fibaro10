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

## Teknisk avhengighet

Docker-bygget henter commit `3720223e11353aba622f8da34c9041586865aa48` (`v2.0.0b25`) av den MIT-lisensierte
`Tasshack/dreame-vacuum`-integrasjonen. Versjonen støtter Dreamehome og Aqua10-familien. Kartbehandling er slått
av for lavere minnebruk. Integrasjonens valgfrie analyseanrop erstattes med en lokal, deaktivert adresse under
bygging; robotidentitet sendes derfor ikke til tredjepartsanalyse fra denne tjenesten.
