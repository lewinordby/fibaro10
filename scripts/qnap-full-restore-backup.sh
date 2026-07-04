#!/bin/sh
set -eu

REMOTE_DIR="${REMOTE_DIR:-/share/CACHEDEV1_DATA/Public/containerdata/fibaro10}"
BACKUP_ROOT="${BACKUP_ROOT:-/share/CACHEDEV3_DATA/fibaro10_archive/full_restore_backup}"
BACKUP_DIR="${BACKUP_DIR:-$BACKUP_ROOT/latest}"
ARCHIVE_ROOT="${ARCHIVE_ROOT:-/share/CACHEDEV3_DATA/fibaro10_archive}"
DOCKER="${DOCKER:-/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-postgres-1}"
POSTGRES_USER="${POSTGRES_USER:-app}"
POSTGRES_DB="${POSTGRES_DB:-fibaro10_local}"
LOCK_DIR="${LOCK_DIR:-/tmp/fibaro10-full-restore-backup.lock}"

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "Full restore backup is already running: $LOCK_DIR" >&2
    exit 0
fi
trap 'rm -rf "$LOCK_DIR"' EXIT INT TERM

source /opt/etc/profile 2>/dev/null || true

stamp="$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR" "$BACKUP_ROOT/logs"
log_file="$BACKUP_ROOT/logs/$stamp.log"
status_file="$BACKUP_DIR/BACKUP_STATUS.txt"

log() {
    printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "$log_file"
}

env_value() {
    file="$1"
    key="$2"
    [ -f "$file" ] || return 0
    line="$(grep -m 1 "^${key}=" "$file" || true)"
    [ -n "$line" ] || return 0
    printf '%s' "${line#*=}"
}

copy_file_if_exists() {
    source_file="$1"
    target_file="$2"
    [ -f "$source_file" ] || return 0
    mkdir -p "$(dirname "$target_file")"
    cp -p "$source_file" "$target_file"
}

sync_dir_if_exists() {
    source_dir="$1"
    target_dir="$2"
    [ -n "$source_dir" ] || return 0
    [ -d "$source_dir" ] || return 0
    mkdir -p "$(dirname "$target_dir")"
    rsync -a --delete "$source_dir/" "$target_dir/"
}

sync_path_if_exists() {
    source_path="$1"
    target_path="$2"
    [ -n "$source_path" ] || return 0
    [ -e "$source_path" ] || return 0
    if [ -d "$source_path" ]; then
        sync_dir_if_exists "$source_path" "$target_path"
    else
        copy_file_if_exists "$source_path" "$target_path"
    fi
}

remove_backup_subdir() {
    target_dir="$1"
    case "$target_dir" in
        "$BACKUP_ROOT"/*) ;;
        *)
            echo "Refusing to remove path outside backup root: $target_dir" >&2
            exit 1
            ;;
    esac
    [ -e "$target_dir" ] || return 0
    rm -rf "$target_dir"
}

host_path_backup_target() {
    source_path="$1"
    clean_path="$(printf '%s' "$source_path" | sed 's#^/##')"
    printf '%s/runtime/host-paths/%s' "$BACKUP_DIR" "$clean_path"
}

backup_docker_mounts() {
    [ -x "$DOCKER" ] || return 0

    mount_inventory="$BACKUP_DIR/system/docker-mounts.tsv"
    mount_review="$BACKUP_DIR/system/docker-mounts-review.txt"
    : > "$mount_inventory"
    : > "$mount_review"

    "$DOCKER" ps -a --format '{{.Names}}' 2>/dev/null | while read -r container; do
        [ -n "$container" ] || continue
        "$DOCKER" inspect --format '{{range .Mounts}}{{.Type}}|{{.Source}}|{{.Destination}}{{println}}{{end}}' "$container" 2>/dev/null | while IFS='|' read -r mount_type source_path dest_path; do
            [ -n "$source_path" ] || continue
            decision="review"

            case "$source_path" in
                "$BACKUP_ROOT"|"$BACKUP_ROOT"/*)
                    decision="skip:backup-root"
                    ;;
                "$REMOTE_DIR"|"$REMOTE_DIR"/*)
                    decision="covered:repo-working-tree"
                    ;;
                /share/Public/pgdata|/share/Public/pgdata/*|*/postgres/pgdata|*/postgres/pgdata/*)
                    decision="covered:postgres-dump"
                    ;;
                */axis_camera_snapshots/snapshots|*/axis_camera_snapshots/snapshots/*)
                    decision="excluded:raw-axis-snapshot-buffer"
                    ;;
                /etc/*|/var/run/docker.sock)
                    decision="skip:system-bind"
                    ;;
                /share/CACHEDEV*_DATA/*|/share/Public/*|/share/homes/*)
                    decision="copied:host-path"
                    sync_path_if_exists "$source_path" "$(host_path_backup_target "$source_path")"
                    ;;
                */docker/volumes/*|*/container-station*/volumes/*)
                    decision="copied:docker-volume"
                    sync_path_if_exists "$source_path" "$(host_path_backup_target "$source_path")"
                    ;;
            esac

            printf '%s\t%s\t%s\t%s\t%s\n' "$container" "$mount_type" "$source_path" "$dest_path" "$decision" >> "$mount_inventory"
            case "$decision" in
                review)
                    printf '%s\t%s\t%s\t%s\n' "$container" "$mount_type" "$source_path" "$dest_path" >> "$mount_review"
                    ;;
            esac
        done
    done
}

write_section() {
    title="$1"
    shift
    {
        echo
        echo "## $title"
        "$@"
    } >> "$BACKUP_DIR/system/manifest.md" 2>&1 || true
}

cd "$REMOTE_DIR"

EASYPARK_HOST_DATA_DIR="${EASYPARK_HOST_DATA_DIR:-$(env_value easypark_downloader/.env EASYPARK_HOST_DATA_DIR)}"
AXIS_HOST_DATA_DIR="${AXIS_HOST_DATA_DIR:-$(env_value .env AXIS_HOST_DATA_DIR)}"
OWNTRACKS_HOST_DATA_DIR="${OWNTRACKS_HOST_DATA_DIR:-$(env_value .env OWNTRACKS_HOST_DATA_DIR)}"
CAR_INFO_HOST_DATA_DIR="${CAR_INFO_HOST_DATA_DIR:-$(env_value .env CAR_INFO_HOST_DATA_DIR)}"
SUN2_SESSION_SCRAPER_HOST_DATA_DIR="${SUN2_SESSION_SCRAPER_HOST_DATA_DIR:-$(env_value .env SUN2_SESSION_SCRAPER_HOST_DATA_DIR)}"
FIBARO10_CADDY_DATA_DIR="${FIBARO10_CADDY_DATA_DIR:-$(env_value .env FIBARO10_CADDY_DATA_DIR)}"
FIBARO10_CADDY_CONFIG_DIR="${FIBARO10_CADDY_CONFIG_DIR:-$(env_value .env FIBARO10_CADDY_CONFIG_DIR)}"

log "Starting full restore backup to $BACKUP_DIR"
printf 'started=%s\nstatus=running\n' "$stamp" > "$status_file"

mkdir -p \
    "$BACKUP_DIR/secrets" \
    "$BACKUP_DIR/repo" \
    "$BACKUP_DIR/postgres" \
    "$BACKUP_DIR/runtime" \
    "$BACKUP_DIR/archive" \
    "$BACKUP_DIR/system"

log "Removing raw Axis snapshot archive from restore backup scope"
remove_backup_subdir "$BACKUP_DIR/archive/axis_camera_snapshots"

log "Copying secrets and config files"
for file in \
    .env .env.* \
    easypark_downloader/.env easypark_downloader/.env.* \
    car_info_lookup/.env car_info_lookup/.env.* \
    sun2_session_scraper/.env sun2_session_scraper/.env.* \
    axis_camera_snapshots/data/config.json \
    axis_camera_snapshots/data/state.json \
    Caddyfile docker-compose.qnap.yml easypark_downloader/docker-compose.yml \
    .dockerignore .gitignore .gitattributes; do
    case "$file" in .env.example|.env.qnap.example|*/.env.example) continue ;; esac
    copy_file_if_exists "$file" "$BACKUP_DIR/secrets/$file"
done

copy_file_if_exists /etc/config/crontab "$BACKUP_DIR/system/etc-config/crontab"
copy_file_if_exists /etc/config/qpkg.conf "$BACKUP_DIR/system/etc-config/qpkg.conf"
copy_file_if_exists /etc/config/uLinux.conf "$BACKUP_DIR/system/etc-config/uLinux.conf"
copy_file_if_exists /etc/hosts "$BACKUP_DIR/system/etc/hosts"
copy_file_if_exists /etc/resolv.conf "$BACKUP_DIR/system/etc/resolv.conf"
sync_dir_if_exists /etc/ssh "$BACKUP_DIR/system/etc-ssh"
sync_dir_if_exists /root/.ssh "$BACKUP_DIR/system/root-ssh"
sync_dir_if_exists /share/homes/admin/.ssh "$BACKUP_DIR/system/admin-ssh"

log "Creating git bundle and source snapshot"
if command -v git >/dev/null 2>&1; then
    git rev-parse HEAD > "$BACKUP_DIR/repo/commit.txt" 2>/dev/null || true
    git status --short > "$BACKUP_DIR/repo/status.txt" 2>/dev/null || true
    git remote -v > "$BACKUP_DIR/repo/remotes.txt" 2>/dev/null || true
    git bundle create "$BACKUP_DIR/repo/fibaro10.bundle" --all >/dev/null 2>&1 || true
fi
rsync -a --delete \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude 'desktop_v2/node_modules' \
    --exclude 'owntracks_service/frontend/node_modules' \
    "$REMOTE_DIR/" "$BACKUP_DIR/repo/working-tree/"

log "Dumping PostgreSQL"
if "$DOCKER" inspect "$POSTGRES_CONTAINER" >/dev/null 2>&1; then
    "$DOCKER" exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$BACKUP_DIR/postgres/${POSTGRES_DB}.sql"
    "$DOCKER" exec "$POSTGRES_CONTAINER" pg_dump -U "$POSTGRES_USER" -Fc "$POSTGRES_DB" > "$BACKUP_DIR/postgres/${POSTGRES_DB}.dump"
    "$DOCKER" exec "$POSTGRES_CONTAINER" pg_dumpall -U "$POSTGRES_USER" --globals-only > "$BACKUP_DIR/postgres/globals.sql" || true
fi

log "Copying runtime data from SSD volume"
sync_dir_if_exists "${EASYPARK_HOST_DATA_DIR:-easypark_downloader/data}" "$BACKUP_DIR/runtime/easypark_downloader/data"
sync_dir_if_exists "${AXIS_HOST_DATA_DIR:-axis_camera_snapshots/data}" "$BACKUP_DIR/runtime/axis_camera_snapshots/data"
sync_dir_if_exists "${OWNTRACKS_HOST_DATA_DIR:-owntracks_service/data}" "$BACKUP_DIR/runtime/owntracks_service/data"
sync_dir_if_exists "${CAR_INFO_HOST_DATA_DIR:-car_info_lookup/data}" "$BACKUP_DIR/runtime/car_info_lookup/data"
sync_dir_if_exists "${SUN2_SESSION_SCRAPER_HOST_DATA_DIR:-sun2_session_scraper/data}" "$BACKUP_DIR/runtime/sun2_session_scraper/data"
sync_dir_if_exists "${FIBARO10_CADDY_DATA_DIR:-}" "$BACKUP_DIR/runtime/caddy/data"
sync_dir_if_exists "${FIBARO10_CADDY_CONFIG_DIR:-}" "$BACKUP_DIR/runtime/caddy/config"

log "Discovering and copying Docker host mounts"
backup_docker_mounts

log "Copying backup archive data from Vol3"
sync_dir_if_exists "$ARCHIVE_ROOT/fibaro10_deploy_backups" "$BACKUP_DIR/archive/fibaro10_deploy_backups"
sync_dir_if_exists "$ARCHIVE_ROOT/fibaro10_backups" "$BACKUP_DIR/archive/fibaro10_backups"

log "Writing Docker and system manifests"
{
    echo "# Fibaro10 Full Restore Backup"
    echo
    echo "- Generated: $(date)"
    echo "- Hostname: $(hostname)"
    echo "- Source repo: $REMOTE_DIR"
    echo "- Backup dir: $BACKUP_DIR"
    echo "- Postgres container: $POSTGRES_CONTAINER"
    echo "- Postgres db: $POSTGRES_DB"
    echo
} > "$BACKUP_DIR/system/manifest.md"

write_section "Disk" df -h
write_section "Mounts" mount
write_section "Crontab" crontab -l
write_section "Docker ps" "$DOCKER" ps
write_section "Docker images" "$DOCKER" images
write_section "Docker networks" "$DOCKER" network ls
write_section "Docker system df" "$DOCKER" system df

for container in postgres-1 easypark_downloader fibaro10 owntracks_service axis_camera_snapshots car_info_lookup sun2_session_scraper parking_sun_linker fibaro10_proxy online_dashboard maintenance_mobile; do
    "$DOCKER" inspect "$container" > "$BACKUP_DIR/system/docker-inspect-$container.json" 2>/dev/null || true
done
("$DOCKER" network inspect fibaro10_default > "$BACKUP_DIR/system/docker-network-fibaro10_default.json" 2>/dev/null) || true

cat > "$BACKUP_DIR/RESTORE-INSTRUCTIONS.md" <<'EOF'
# Restore av Fibaro10 paa ny QNAP

Denne katalogen er laget for aa kunne sette opp Fibaro10 paa nytt uten aa hente manglende hemmeligheter fra andre steder.
Den inneholder med vilje `.env`-filer, passord, tokens, app-profiler, database-dump, Caddy-data og runtime-data.

## 1. Anbefalt volumstruktur

Opprett helst samme logiske struktur:

- Vol1 / `CACHEDEV1_DATA`: Container Station og repo.
- Vol2 / `CACHEDEV2_DATA`: SSD RAID1 for runtime-data.
- Vol3 / `CACHEDEV3_DATA`: arkiv og backups. Raa Axis snapshot-buffer kopieres ikke; soltimebilder ligger i PostgreSQL-dumpen.

Hvis volum-idene blir annerledes paa ny QNAP maa stiene i `.env` justeres for:

- `EASYPARK_HOST_DATA_DIR`
- `OWNTRACKS_HOST_DATA_DIR`
- `AXIS_HOST_DATA_DIR`
- `AXIS_HOST_SNAPSHOT_DIR`
- `CAR_INFO_HOST_DATA_DIR`
- `SUN2_SESSION_SCRAPER_HOST_DATA_DIR`
- `FIBARO10_CADDY_DATA_DIR`
- `FIBARO10_CADDY_CONFIG_DIR`

## 2. Legg tilbake repo

Alternativ A, fra GitHub:

```sh
mkdir -p /share/CACHEDEV1_DATA/Public/containerdata
cd /share/CACHEDEV1_DATA/Public/containerdata
git clone https://github.com/lewinordby/fibaro10.git
cd fibaro10
```

Alternativ B, fra bundle i backupen:

```sh
mkdir -p /share/CACHEDEV1_DATA/Public/containerdata/fibaro10
cd /share/CACHEDEV1_DATA/Public/containerdata/fibaro10
git clone /sti/til/full_restore_backup/latest/repo/fibaro10.bundle .
```

Hvis Git ikke er tilgjengelig kan `repo/working-tree/` kopieres direkte til repo-stien.

## 3. Legg tilbake hemmeligheter og konfig

Kopier innhold fra:

```text
secrets/
```

til samme relative plassering under repoet:

```text
/share/CACHEDEV1_DATA/Public/containerdata/fibaro10
```

Eksempler:

```sh
cp -a secrets/.env /share/CACHEDEV1_DATA/Public/containerdata/fibaro10/.env
cp -a secrets/easypark_downloader/.env /share/CACHEDEV1_DATA/Public/containerdata/fibaro10/easypark_downloader/.env
cp -a secrets/sun2_session_scraper/.env /share/CACHEDEV1_DATA/Public/containerdata/fibaro10/sun2_session_scraper/.env
```

## 4. Legg tilbake runtime-data

Opprett runtime-root paa SSD-volumet og kopier tilbake:

```sh
mkdir -p /share/CACHEDEV2_DATA/fibaro10_runtime
cp -a runtime/easypark_downloader /share/CACHEDEV2_DATA/fibaro10_runtime/
cp -a runtime/owntracks_service /share/CACHEDEV2_DATA/fibaro10_runtime/
cp -a runtime/axis_camera_snapshots /share/CACHEDEV2_DATA/fibaro10_runtime/
cp -a runtime/car_info_lookup /share/CACHEDEV2_DATA/fibaro10_runtime/
cp -a runtime/sun2_session_scraper /share/CACHEDEV2_DATA/fibaro10_runtime/
cp -a runtime/caddy /share/CACHEDEV2_DATA/fibaro10_runtime/
```

`runtime/axis_camera_snapshots` inneholder metadata/konfig for Axis-jobben. Selve raa snapshot-bufferen er med vilje ikke med i denne backupen.

## 5. Legg tilbake arkivdata

```sh
mkdir -p /share/CACHEDEV3_DATA/fibaro10_archive
cp -a archive/fibaro10_deploy_backups /share/CACHEDEV3_DATA/fibaro10_archive/
cp -a archive/fibaro10_backups /share/CACHEDEV3_DATA/fibaro10_archive/
```

Axis-bilder som er knyttet til soltimer ligger i Fibaro10-databasen, i tabellen `sun2_tanning_session_images`, og blir gjenopprettet gjennom PostgreSQL-dumpen. Det historiske Axis snapshot-arkivet tas ikke med.

## Fremtidige tjenester og nye datakataloger

Backupjobben lager et Docker mount-inventar i:

```text
system/docker-mounts.tsv
```

Alle Docker host mounts under `/share/CACHEDEV*_DATA`, `/share/Public` og `/share/homes` kopieres automatisk til:

```text
runtime/host-paths/
```

Dette gjoer at nye containeriserte apper normalt blir med uten at scriptet maa endres manuelt.

Hvis en fremtidig container bruker en ukjent datasti, blir den listet i:

```text
system/docker-mounts-review.txt
```

Denne filen skal vaere tom. Hvis den ikke er tom, maa restore-backupen oppdateres eller ny datasti flyttes inn under en standard runtime/archive-katalog.

## 6. Start PostgreSQL og restore database

Opprett datamappe paa SSD:

```sh
mkdir -p /share/CACHEDEV2_DATA/fibaro10_runtime/postgres/pgdata
ln -sfn /share/CACHEDEV2_DATA/fibaro10_runtime/postgres/pgdata /share/Public/pgdata
```

Start PostgreSQL-container tilsvarende gammel installasjon, eller opprett den via Container Station/Docker:

```sh
docker run -d --name postgres-1 \
  --restart unless-stopped \
  -p 5432:5432 \
  -e POSTGRES_USER=app \
  -e POSTGRES_PASSWORD=<se .env/DATABASE_URL> \
  -e POSTGRES_DB=fibaro10_local \
  -v /share/Public/pgdata:/var/lib/postgresql/data \
  postgres:17
```

Restore database:

```sh
cat postgres/fibaro10_local.sql | docker exec -i postgres-1 psql -U app -d fibaro10_local
```

Hvis databasen allerede finnes og skal overskrives, dropp/opprett databasen foerst eller bruk `pg_restore` med `postgres/fibaro10_local.dump`.

## 7. Start appene

Fra repoet:

```sh
cd /share/CACHEDEV1_DATA/Public/containerdata/fibaro10
export APP_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo restored)
/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker compose -f docker-compose.qnap.yml up -d --build
cd easypark_downloader
/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker compose up -d --build
```

## 8. Legg tilbake cron

Se:

```text
system/etc-config/crontab
```

Minimum for ny backup:

```sh
20 3 * * * cd /share/CACHEDEV1_DATA/Public/containerdata/fibaro10 && sh scripts/qnap-backup.sh >> /share/CACHEDEV3_DATA/fibaro10_archive/fibaro10_backups/qnap-backup.log 2>&1
10 4 * * * cd /share/CACHEDEV1_DATA/Public/containerdata/fibaro10 && sh scripts/qnap-full-restore-backup.sh >> /share/CACHEDEV3_DATA/fibaro10_archive/full_restore_backup/full-restore-backup.log 2>&1
```

## 9. Kontroll

```sh
docker ps
curl http://127.0.0.1:8110/health
curl http://127.0.0.1:8125/health
curl http://127.0.0.1:8128/health
```

Fra utviklings-PC kan du ogsaa kjoere:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\health-check.ps1
cd desktop_v2
npm.cmd run smoke:live
```
EOF

cat > "$BACKUP_DIR/CODEX-RESTORE-PROMPT.txt" <<'EOF'
Du jobber paa en ny QNAP/ny installasjon og skal gjenopprette Fibaro10 fra denne full restore backup-katalogen.

Maal:
- Sett opp Fibaro10, online dashboard, vedlikeholdsapp, OwnTracks, EasyPark downloader, Axis snapshot-service, nordisk biloppslag, SUN2 scraper og koblingsmotor.
- Bruk alle hemmeligheter, passord, tokens, .env-filer, Caddy-data, runtime-data og database-dump fra backupen. Axis-bilder som er knyttet til soltimer ligger i database-dumpen.
- Ikke utelat noe. Ikke regenerer hemmeligheter hvis de finnes i backupen.
- Ikke skriv hemmeligheter i chatten; bruk filene direkte.
- Dokumenter eventuelle lokale stiendringer hvis ny QNAP bruker andre volum-id-er enn CACHEDEV1_DATA, CACHEDEV2_DATA og CACHEDEV3_DATA.

Backupkatalogens innhold:
- RESTORE-INSTRUCTIONS.md: detaljert restore-oppskrift.
- secrets/: alle .env-filer og konfigfiler med hemmeligheter.
- repo/fibaro10.bundle: Git bundle med repo/historikk.
- repo/working-tree/: arbeidskopi av repoet.
- postgres/: PostgreSQL SQL-dump, custom dump og globals.
- runtime/: SSD runtime-data for EasyPark, OwnTracks, Axis metadata/konfig, biloppslag, SUN2 scraper og Caddy.
- runtime/host-paths/: automatisk oppdagede Docker host mounts for nye tjenester.
- archive/: deploy-backups og Fibaro10 backups. Raa Axis snapshot-buffer er ikke med.
- system/: Docker inspect, crontab, QNAP-konfig og systemmanifest.
- system/docker-mounts.tsv: inventar over alle Docker mounts og backupbeslutning.
- system/docker-mounts-review.txt: skal vaere tom; inneholder nye/ukjente datakilder som maa vurderes.

Arbeidsrekkefolge:
1. Les RESTORE-INSTRUCTIONS.md i denne katalogen.
2. Identifiser backupens absolutte sti paa den nye maskinen.
3. Finn tilgjengelige QNAP-volumer med df -h og /share/CACHEDEV*_DATA.
4. Lag eller velg tilsvarende roller:
   - repo/Container Station: Vol1 eller hovedvolum
   - runtime/database: SSD RAID1-volum
   - arkiv/backups: stort arkivvolum
5. Hvis volum-id-er avviker, oppdater stier i .env-filene foer oppstart.
6. Gjenopprett repo fra repo/fibaro10.bundle eller repo/working-tree/.
7. Kopier secrets/ tilbake til repoet.
8. Kopier runtime/ til SSD runtime-root.
9. Kopier archive/ til arkivroot. Ikke forvent historisk Axis snapshot-buffer; soltimebilder kommer fra PostgreSQL.
10. Opprett/start postgres-1 og restore postgres/fibaro10_local.sql eller postgres/fibaro10_local.dump.
11. Start alle Docker Compose-tjenester.
12. Legg tilbake cron-jobber for qnap-backup.sh og qnap-full-restore-backup.sh.
13. Kjor health-check og live smoke-test.
14. Bekreft at alle containere er oppe og at domenene peker riktig via Caddy.

Viktige prinsipper:
- Behandle backupen som autoritativ kilde.
- Ikke slett original backup.
- Ikke endre databasetabeller manuelt med mindre restore krever det.
- Hvis noe feiler, stopp og les system/docker-inspect-*.json og system/manifest.md for gammel containerkonfig.
- Etter vellykket restore: kjor en ny full restore backup paa den nye QNAP-en.
EOF

find "$BACKUP_DIR" -type f -print | sort > "$BACKUP_DIR/MANIFEST.files"
du -sh "$BACKUP_DIR" > "$BACKUP_DIR/SIZE.txt" 2>/dev/null || true
final_status="ok"
if [ -s "$BACKUP_DIR/system/docker-mounts-review.txt" ]; then
    final_status="warning"
    log "Full restore backup completed with mount review warnings"
else
    log "Full restore backup completed"
fi
printf 'started=%s\nfinished=%s\nstatus=%s\n' "$stamp" "$(date +%Y%m%d-%H%M%S)" "$final_status" > "$status_file"
echo "$BACKUP_DIR"
