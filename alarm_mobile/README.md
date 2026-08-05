# Alarm mobile

Mobilflate for operative varsler ved Lilletorget.

- Døralarmer og kontroll av solrom
- Pullerter og trapp med egen kontrollside per bildeutsnitt
- Alarmhistorikk og status for overvåkingen
- Direkte lenker fra ntfy til riktig alarm eller hendelse

Appen bruker samme brukerbase som Fibaro10, men har egen innloggingsøkt og eget domene.

## Kontrollbilder

Pullertsiden viser en lett liste med siste bilde, status og bildetid for hvert kontrollfelt:

- G6 Butikk Nord
- G6 Butikk Front
- G6 Solstudio Front
- Trapp ved Solstudio

Et trykk åpner en egen side for feltet. Der kan referanse og siste bilde sammenlignes med
gjennomsiktighet, siste bilde, forskjellsbilde eller referanse alene. Siden viser tidsstempler,
endringsscore, relaterte hendelser og knapper for å bla direkte til forrige eller neste kontrollfelt.
Direktelenken bruker `?section=pullerter&monitor=<monitor-id>` og bevares gjennom innlogging.
