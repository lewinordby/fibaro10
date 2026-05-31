param(
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$RemoteDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker",
    [switch]$SkipPush,
    [switch]$AllowDirty
)

$ErrorActionPreference = "Stop"

function Run($exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$exe failed with exit code $LASTEXITCODE"
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

Run "git" @("fetch", "origin", "main")
$status = (& git status --porcelain)
if ($status -and -not $AllowDirty) {
    Write-Host $status
    throw "Working tree is not clean. Commit or stash changes, or pass -AllowDirty."
}

if (-not $SkipPush) {
    Run "git" @("push", "origin", "main")
}

$remote = @"
set -e
source /opt/etc/profile 2>/dev/null || true
cd "$RemoteDir"
backup_root="$RemoteDir/../fibaro10_deploy_backups"
stamp=`$(date +%Y%m%d-%H%M%S)
backup_dir="`$backup_root/`$stamp"
mkdir -p "`$backup_dir"
for file in .env .env.* easypark_downloader/.env easypark_downloader/.env.*; do
    [ -f "`$file" ] || continue
    target="`$backup_dir/`$file"
    mkdir -p "`$(dirname "`$target")"
    cp -p "`$file" "`$target"
done
[ -d easypark_downloader/data ] && mkdir -p "`$backup_dir/easypark_downloader" && cp -a easypark_downloader/data "`$backup_dir/easypark_downloader/data"
git fetch origin main
git reset --hard origin/main
git clean -fd -e .env -e ".env.*" -e easypark_downloader/.env -e "easypark_downloader/.env.*" -e easypark_downloader/data
"$Docker" compose -f docker-compose.qnap.yml up -d --build fibaro10 online_dashboard
"$Docker" compose -f docker-compose.qnap.yml ps
echo "Backup: `$backup_dir"
"@

Run "ssh" @("-i", $IdentityFile, $QnapHost, $remote)

Run "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "health-check.ps1"))
