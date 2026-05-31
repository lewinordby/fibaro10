# Utviklingsoppsett

## Arbeidsflyt

1. Jobb lokalt i `C:\Users\lewih\Documents\Codex\prosjekter\fibaro10`.
2. Commit endringer og push til GitHub.
3. Kjør deploy-scriptet:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\deploy-qnap.ps1
```

Scriptet pusher til GitHub, henter `origin/main` på QNAP, tar vare på runtimefiler, bygger Docker-image på nytt og kjører health checks.

## Produksjon

- QNAP: `192.168.20.218`
- Appmappe: `/share/CACHEDEV1_DATA/Public/containerdata/fibaro10`
- Intern app: `http://192.168.20.218:8110`
- Online dashboard: `https://online.lilletorget.net`
- Docker: `/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker`
- Git på QNAP leveres via Entware i `/opt/bin/git`.

## Backup

QNAP-backup-scriptet ligger i `scripts/qnap-backup.sh` og tar vare på `.env`, EasyPark runtime-data og PostgreSQL-dump når `postgres-1` er tilgjengelig:

```sh
sh /share/CACHEDEV1_DATA/Public/containerdata/fibaro10/scripts/qnap-backup.sh
```

Backuper lagres under `/share/CACHEDEV1_DATA/Public/containerdata/backups/fibaro10`, og de 20 nyeste beholdes.
