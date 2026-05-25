# Dokumentasjonsoversikt

Oppdatert 25.05.2026.

Dette repoet dokumenterer både hovedappen `Fibaro10 / Lilletorget drift` og de lokale loggerne som fyller databasen.

## Levende dokumentasjon i appen

| Side | Bruk |
| --- | --- |
| Konto -> Manual | Sluttbrukerveiledning for daglig bruk, menyer, varsler og feilsøking. |
| Konto -> Teknisk | Teknisk oversikt over dataflyt, roller, endepunkter og feilsøking. |
| Status -> Datakilder | Operativ status for alle datakilder og importjobber. |

## Dokumenter i repoet

| Fil | Innhold |
| --- | --- |
| `docs/sun2-enkeltimer.md` | Hvordan SUN2 enkelttimer skrapes og importeres løpende. |
| `docs/roborock-logger.md` | Drift av lokal Roborock_logger på QNAP/Docker. |
| `docs/roborock-datakilder.md` | Hvilke Roborock-data som kan hentes fra cloud og lokal LAN. |
| `docs/roborock.md` | Historisk testnotat for Roborock-integrasjonen. |
| `docs/gjennomgang_2026-05-23.md` | Tidligere gjennomgang, nå oppdatert med dagens status. |

## Viktige prinsipper

- Appen viser alltid data fra egen database, ikke direkte fra tredjeparts-API-er i brukergrensesnittet.
- HC3 poster lys, ventilasjon og energi direkte til Fibaro10.
- QNAP/Docker brukes for lokale loggere som Roborock og SUN2-skraping.
- Elvia er manuell månedlig import fordi eksporten krever BankID.
- Status -> Datakilder er fasit for om en datakilde faktisk går.
- SUN2/Elvia-tidspunkter behandles som kildens lokale tid, mens Yr/HC3 vises i Europe/Oslo.
