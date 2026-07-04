param(
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$Git = "",
    [string]$Branch = "main",
    [string]$RemoteDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker",
    [switch]$SkipPush,
    [switch]$AllowDirty,
    [switch]$SkipSmoke,
    [switch]$SkipLocalCheck,
    [int]$BackupRetentionCount = 20
)

$ErrorActionPreference = "Stop"

function Run($exe, [string[]]$arguments) {
    & $exe @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$exe failed with exit code $LASTEXITCODE"
    }
}

function NormalizeRemote([string]$script) {
    $script -replace "`r`n", "`n" -replace "`r", "`n"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
if (-not $Git) {
    $defaultGit = "C:\Program Files\Git\cmd\git.exe"
    $Git = if (Test-Path $defaultGit) { $defaultGit } else { "git" }
}

if (-not (Test-Path -LiteralPath $IdentityFile)) {
    throw "Missing SSH identity file: $IdentityFile. Run scripts\setup-local-dev.ps1 first."
}

if (-not $SkipLocalCheck) {
    Run "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "check-local.ps1"))
}

Run $Git @("fetch", "origin", $Branch)
$currentBranch = (& $Git branch --show-current).Trim()
if ($currentBranch -ne $Branch) {
    throw "Deploy expects branch $Branch, but current branch is $currentBranch."
}

$status = (& $Git status --porcelain)
if ($status -and -not $AllowDirty) {
    Write-Host $status
    throw "Working tree is not clean. Commit or stash changes, or pass -AllowDirty."
}

if (-not $SkipPush) {
    Run $Git @("push", "origin", $Branch)
}

$preflight = @"
set -e
source /opt/etc/profile 2>/dev/null || true
command -v git >/dev/null
test -d "$RemoteDir"
test -x "$Docker"
cd "$RemoteDir"
git rev-parse --is-inside-work-tree >/dev/null
"@

Run "ssh" @("-i", $IdentityFile, "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", $QnapHost, (NormalizeRemote $preflight))

$remote = @"
set -e
source /opt/etc/profile 2>/dev/null || true
cd "$RemoteDir"
backup_root="$RemoteDir/../fibaro10_deploy_backups"
stamp=`$(date +%Y%m%d-%H%M%S)
backup_dir="`$backup_root/`$stamp"
mkdir -p "`$backup_dir"
if [ "$BackupRetentionCount" -gt 0 ]; then
    backup_count=`$(find "`$backup_root" -mindepth 1 -maxdepth 1 -type d -name '20[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]' | wc -l)
    delete_count=`$((backup_count - $BackupRetentionCount))
    if [ "`$delete_count" -gt 0 ]; then
        find "`$backup_root" -mindepth 1 -maxdepth 1 -type d -name '20[0-9][0-9][0-9][0-9][0-9][0-9]-[0-9][0-9][0-9][0-9][0-9][0-9]' \
            | sort \
            | head -n "`$delete_count" \
            | while IFS= read -r old_backup; do rm -rf -- "`$old_backup"; done
    fi
fi
for file in .env .env.* easypark_downloader/.env easypark_downloader/.env.* car_info_lookup/.env car_info_lookup/.env.* sun2_session_scraper/.env sun2_session_scraper/.env.* axis_camera_snapshots/data/config.json axis_camera_snapshots/data/state.json; do
    case "`$file" in .env.example|.env.qnap.example|*/.env.example) continue ;; esac
    [ -f "`$file" ] || continue
    target="`$backup_dir/`$file"
    mkdir -p "`$(dirname "`$target")"
    cp -p "`$file" "`$target"
done
[ -d easypark_downloader/data ] && mkdir -p "`$backup_dir/easypark_downloader" && cp -a easypark_downloader/data "`$backup_dir/easypark_downloader/data"
[ -d car_info_lookup/data ] && mkdir -p "`$backup_dir/car_info_lookup" && cp -a car_info_lookup/data "`$backup_dir/car_info_lookup/data"
[ -d sun2_session_scraper/data ] && mkdir -p "`$backup_dir/sun2_session_scraper" && cp -a sun2_session_scraper/data "`$backup_dir/sun2_session_scraper/data"
[ -d axis_camera_snapshots/data ] && mkdir -p "`$backup_dir/axis_camera_snapshots" && cp -a axis_camera_snapshots/data "`$backup_dir/axis_camera_snapshots/data"
[ -d owntracks_service/data ] && mkdir -p "`$backup_dir/owntracks_service" && cp -a owntracks_service/data "`$backup_dir/owntracks_service/data"
legacy_sun2_dir="$RemoteDir/../sun2_session_scraper"
[ -f "`$legacy_sun2_dir/.env" ] && mkdir -p "`$backup_dir/sun2_session_scraper" && cp -p "`$legacy_sun2_dir/.env" "`$backup_dir/sun2_session_scraper/.env"
[ -d "`$legacy_sun2_dir/data" ] && mkdir -p "`$backup_dir/sun2_session_scraper" && cp -a "`$legacy_sun2_dir/data" "`$backup_dir/sun2_session_scraper/data"
git fetch origin "$Branch"
git reset --hard "origin/$Branch"
git clean -fdx -e .env -e '.env.*' -e easypark_downloader/.env -e 'easypark_downloader/.env.*' -e easypark_downloader/data/ -e car_info_lookup/.env -e 'car_info_lookup/.env.*' -e car_info_lookup/data/ -e sun2_session_scraper/.env -e 'sun2_session_scraper/.env.*' -e sun2_session_scraper/data/ -e axis_camera_snapshots/data/ -e axis_camera_snapshots/snapshots/ -e owntracks_service/data/
for file in .env .env.* easypark_downloader/.env easypark_downloader/.env.* car_info_lookup/.env car_info_lookup/.env.* sun2_session_scraper/.env sun2_session_scraper/.env.* axis_camera_snapshots/data/config.json axis_camera_snapshots/data/state.json; do
    case "`$file" in .env.example|.env.qnap.example|*/.env.example) continue ;; esac
    source="`$backup_dir/`$file"
    [ -f "`$source" ] || continue
    mkdir -p "`$(dirname "`$file")"
    cp -p "`$source" "`$file"
done
[ -d "`$backup_dir/easypark_downloader/data" ] && [ ! -d easypark_downloader/data ] && mkdir -p easypark_downloader && cp -a "`$backup_dir/easypark_downloader/data" easypark_downloader/data
[ -d "`$backup_dir/car_info_lookup/data" ] && [ ! -d car_info_lookup/data ] && mkdir -p car_info_lookup && cp -a "`$backup_dir/car_info_lookup/data" car_info_lookup/data
[ -d "`$backup_dir/sun2_session_scraper/data" ] && [ ! -d sun2_session_scraper/data ] && mkdir -p sun2_session_scraper && cp -a "`$backup_dir/sun2_session_scraper/data" sun2_session_scraper/data
[ -d "`$backup_dir/axis_camera_snapshots/data" ] && [ ! -d axis_camera_snapshots/data ] && mkdir -p axis_camera_snapshots && cp -a "`$backup_dir/axis_camera_snapshots/data" axis_camera_snapshots/data
[ -d "`$backup_dir/owntracks_service/data" ] && [ ! -d owntracks_service/data ] && mkdir -p owntracks_service && cp -a "`$backup_dir/owntracks_service/data" owntracks_service/data
mkdir -p axis_camera_snapshots/data axis_camera_snapshots/snapshots car_info_lookup/data
mkdir -p sun2_session_scraper/data
mkdir -p easypark_downloader/data
mkdir -p owntracks_service/data
[ -d "`$legacy_sun2_dir" ] && (cd "`$legacy_sun2_dir" && "$Docker" compose down || true)
export APP_COMMIT=`$(git rev-parse --short HEAD)
"$Docker" rm -f owntracks_mqtt >/dev/null 2>&1 || true
"$Docker" compose -f docker-compose.qnap.yml up -d --build --force-recreate owntracks_service fibaro10_proxy
"$Docker" compose -f docker-compose.qnap.yml up -d --build fibaro10 online_dashboard maintenance_mobile axis_camera_snapshots car_info_lookup sun2_session_scraper parking_sun_linker
(cd easypark_downloader && "$Docker" compose up -d --build)
"$Docker" exec fibaro10_proxy caddy validate --config /etc/caddy/Caddyfile || { "$Docker" logs --tail=80 fibaro10_proxy; exit 1; }
"$Docker" compose -f docker-compose.qnap.yml ps
(cd easypark_downloader && "$Docker" compose ps)
echo "Backup: `$backup_dir"
"@

Run "ssh" @("-i", $IdentityFile, $QnapHost, (NormalizeRemote $remote))

Run "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "health-check.ps1"))
if (-not $SkipSmoke) {
    Run "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "smoke-check.ps1"))
    $desktopDir = Join-Path $repoRoot "desktop_v2"
    $npm = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }
    $originalDir = (Get-Location).Path
    try {
        Set-Location $desktopDir
        Run $npm @("run", "smoke:live")
    }
    finally {
        Set-Location $originalDir
    }
}
