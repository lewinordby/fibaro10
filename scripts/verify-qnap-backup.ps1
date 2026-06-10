param(
    [string]$QnapAlias = "qnap-fibaro10",
    [string]$RemoteDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$BackupRoot = "/share/CACHEDEV1_DATA/Public/containerdata/backups/fibaro10",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker",
    [string]$PostgresContainer = "postgres-1",
    [string]$PostgresUser = "app",
    [string]$PostgresDb = "fibaro10_local",
    [switch]$SkipSqlRestore
)

$ErrorActionPreference = "Stop"

$skipRestoreValue = if ($SkipSqlRestore) { "1" } else { "0" }

$remote = @"
set -e
. /opt/etc/profile 2>/dev/null || true
cd "$RemoteDir"
backup_dir=`$(BACKUP_ROOT="$BackupRoot" POSTGRES_CONTAINER="$PostgresContainer" POSTGRES_USER="$PostgresUser" POSTGRES_DB="$PostgresDb" sh scripts/qnap-backup.sh </dev/null)
test -d "`$backup_dir"
echo "Backup: `$backup_dir"

if [ ! -f "`$backup_dir/.env" ]; then
    echo "WARN: .env was not present in backup"
fi

sql_file="`$backup_dir/$PostgresDb.sql"
if "$Docker" inspect "$PostgresContainer" >/dev/null 2>&1; then
    test -s "`$sql_file"
    echo "SQL dump: `$sql_file"
    if [ "$skipRestoreValue" != "1" ]; then
        stamp=`$(date +%Y%m%d%H%M%S)
        restore_db="fibaro10_restore_check_`$stamp"
        "$Docker" exec "$PostgresContainer" dropdb -U "$PostgresUser" --if-exists "`$restore_db" >/dev/null 2>&1 || true
        "$Docker" exec "$PostgresContainer" createdb -U "$PostgresUser" "`$restore_db"
        restore_status=0
        "$Docker" exec -i "$PostgresContainer" psql -U "$PostgresUser" -d "`$restore_db" -v ON_ERROR_STOP=1 < "`$sql_file" >/dev/null || restore_status=`$?
        "$Docker" exec "$PostgresContainer" dropdb -U "$PostgresUser" --if-exists "`$restore_db" >/dev/null 2>&1 || true
        if [ "`$restore_status" -ne 0 ]; then
            exit "`$restore_status"
        fi
        echo "Restore dry-run: OK (`$restore_db)"
    else
        echo "Restore dry-run: SKIPPED"
    fi
else
    echo "WARN: Postgres container $PostgresContainer not found; SQL restore test skipped"
fi
"@

$remote = $remote -replace "`r`n", "`n" -replace "`r", "`n"

$stamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$remoteScriptPath = "/tmp/fibaro10-verify-backup-$stamp.sh"
$localScriptPath = Join-Path $env:TEMP "fibaro10-verify-backup-$stamp.sh"

try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($localScriptPath, $remote, $utf8NoBom)
    scp -q -o BatchMode=yes -o ConnectTimeout=8 $localScriptPath "${QnapAlias}:$remoteScriptPath"
    if ($LASTEXITCODE -ne 0) {
        throw "Backup verification upload failed with exit code $LASTEXITCODE"
    }
}
finally {
    if (Test-Path -LiteralPath $localScriptPath) {
        Remove-Item -LiteralPath $localScriptPath -Force
    }
}

ssh -o BatchMode=yes -o ConnectTimeout=8 $QnapAlias "sh $remoteScriptPath; rc=`$?; rm -f $remoteScriptPath; exit `$rc"
if ($LASTEXITCODE -ne 0) {
    throw "Backup verification failed with exit code $LASTEXITCODE"
}
