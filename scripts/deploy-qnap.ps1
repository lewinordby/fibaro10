param(
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$Git = "",
    [string]$Branch = "main",
    [string]$RemoteDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$RemoteBackupRoot = "/share/CACHEDEV3_DATA/fibaro10_archive/fibaro10_deploy_backups",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker",
    [switch]$SkipPush,
    [switch]$AllowDirty,
    [switch]$SkipSmoke,
    [switch]$SkipLocalCheck,
    [string[]]$ForceServices = @(),
    [switch]$ForceEasyPark,
    [switch]$ForceRoborock,
    [switch]$ForceDreame,
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

. (Join-Path $PSScriptRoot "deploy-plan.ps1")

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot
if (-not $Git) {
    $defaultGit = "C:\Program Files\Git\cmd\git.exe"
    $Git = if (Test-Path $defaultGit) { $defaultGit } else { "git" }
}

if (-not (Test-Path -LiteralPath $IdentityFile)) {
    throw "Missing SSH identity file: $IdentityFile. Run scripts\setup-local-dev.ps1 first."
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

$targetCommit = (& $Git rev-parse HEAD).Trim()
$remoteCommitOutput = & ssh -i $IdentityFile -o BatchMode=yes $QnapHost "source /opt/etc/profile 2>/dev/null || true; cd '$RemoteDir' && git rev-parse HEAD"
$remoteCommitOk = $LASTEXITCODE -eq 0
$remoteCommit = if ($remoteCommitOk) { ([string]($remoteCommitOutput | Select-Object -Last 1)).Trim() } else { "" }
$forceFullDeploy = -not $remoteCommitOk -or -not $remoteCommit
$changedFiles = @()
if (-not $forceFullDeploy) {
    $changedFiles = @(& $Git diff --name-only $remoteCommit $targetCommit)
    if ($LASTEXITCODE -ne 0) { $forceFullDeploy = $true }
}
$deployPlan = Get-DeployPlan -ChangedFiles $changedFiles -ForceAll $forceFullDeploy
$validForceServices = @(
    "owntracks_service", "fibaro10", "revenue_app", "parking_app", "sun_app",
    "energy_app", "operations_app", "maintenance_app", "system_app", "link_app",
    "unifi_protect_events", "visual_anomaly_service", "online_dashboard",
    "maintenance_mobile", "alarm_mobile", "axis_camera_snapshots",
    "car_info_lookup", "sun2_backfill_downloader", "sun2_importer",
    "sun2_session_scraper", "parking_sun_linker", "fibaro10_proxy"
)
$unknownForceServices = @($ForceServices | Where-Object { $_ -notin $validForceServices })
if ($unknownForceServices.Count -gt 0) {
    throw "Unknown forced service(s): $([string]::Join(', ', $unknownForceServices))"
}
if ($ForceServices.Count -gt 0) {
    $deployPlan.Services = @($validForceServices | Where-Object { $_ -in @($deployPlan.Services + $ForceServices) })
}
if ($ForceEasyPark) { $deployPlan.EasyPark = $true }
if ($ForceRoborock) { $deployPlan.Roborock = $true }
if ($ForceDreame) { $deployPlan.Dreame = $true }
$coreDeployValue = if ("fibaro10" -in $deployPlan.Services) { "1" } else { "0" }
$standardServices = @($deployPlan.Services | Where-Object { $_ -ne "fibaro10" })
$composeServices = [string]::Join(" ", $standardServices)
$displayServices = [string]::Join(" ", $deployPlan.Services)
$hasComposeServicesValue = if ($standardServices.Count -gt 0) { "1" } else { "0" }
$deployAllValue = if ($deployPlan.All) { "1" } else { "0" }
$deployEasyParkValue = if ($deployPlan.EasyPark) { "1" } else { "0" }
$deployRoborockValue = if ($deployPlan.Roborock) { "1" } else { "0" }
$deployDreameValue = if ($deployPlan.Dreame) { "1" } else { "0" }
$restartProxyValue = if (@($changedFiles | Where-Object { ([string]$_).Replace("\", "/") -eq "Caddyfile" }).Count -gt 0) { "1" } else { "0" }
Write-Host "Deploy plan: services=[$displayServices], core=$coreDeployValue, EasyPark=$deployEasyParkValue, Roborock=$deployRoborockValue, Dreame=$deployDreameValue, full=$deployAllValue"
$broadValidation = $deployPlan.All -or $deployPlan.Services.Count -gt 4
if (-not $SkipLocalCheck) {
    if ($broadValidation) {
        Run "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "check-local.ps1"))
    } else {
        $checkArguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "check-affected.ps1"), "-Services") + @($deployPlan.Services) + @("-ChangedFiles") + @($changedFiles)
        if ($deployPlan.EasyPark) { $checkArguments += "-EasyPark" }
        if ($deployPlan.Roborock) { $checkArguments += "-Roborock" }
        if ($deployPlan.Dreame) { $checkArguments += "-Dreame" }
        Run "powershell" $checkArguments
    }
}
if (-not $SkipPush) {
    Run $Git @("push", "origin", $Branch)
}

$remote = @"
set -e
source /opt/etc/profile 2>/dev/null || true
cd "$RemoteDir"
backup_root="$RemoteBackupRoot"
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
for file in .env .env.* easypark_downloader/.env easypark_downloader/.env.* car_info_lookup/.env car_info_lookup/.env.* sun2_backfill_downloader/.env sun2_backfill_downloader/.env.* sun2_importer/.env sun2_importer/.env.* sun2_session_scraper/.env sun2_session_scraper/.env.* roborock_logger/.env roborock_logger/.env.* dreame_logger/.env dreame_logger/.env.* axis_camera_snapshots/data/config.json axis_camera_snapshots/data/state.json; do
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
git clean -fdx -e .env -e '.env.*' -e easypark_downloader/.env -e 'easypark_downloader/.env.*' -e easypark_downloader/data/ -e car_info_lookup/.env -e 'car_info_lookup/.env.*' -e car_info_lookup/data/ -e sun2_backfill_downloader/.env -e 'sun2_backfill_downloader/.env.*' -e sun2_importer/.env -e 'sun2_importer/.env.*' -e sun2_session_scraper/.env -e 'sun2_session_scraper/.env.*' -e sun2_session_scraper/data/ -e roborock_logger/.env -e 'roborock_logger/.env.*' -e dreame_logger/.env -e 'dreame_logger/.env.*' -e axis_camera_snapshots/data/ -e axis_camera_snapshots/snapshots/ -e owntracks_service/data/ -e owntracks_service/postgres_data/ -e unifi_protect_events/data/ -e visual_anomaly_service/data/
for file in .env .env.* easypark_downloader/.env easypark_downloader/.env.* car_info_lookup/.env car_info_lookup/.env.* sun2_backfill_downloader/.env sun2_backfill_downloader/.env.* sun2_importer/.env sun2_importer/.env.* sun2_session_scraper/.env sun2_session_scraper/.env.* roborock_logger/.env roborock_logger/.env.* dreame_logger/.env dreame_logger/.env.* axis_camera_snapshots/data/config.json axis_camera_snapshots/data/state.json; do
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
mkdir -p owntracks_service/postgres_data
mkdir -p visual_anomaly_service/data
env_value() {
    file="`$1"
    key="`$2"
    [ -f "`$file" ] || return 0
    line=`$(grep -m 1 "^`$key=" "`$file" 2>/dev/null || true)
    printf '%s' "`${line#*=}"
}
set_env_value() {
    file="`$1"
    key="`$2"
    value="`$3"
    temp="`$file.tmp"
    grep -v "^`$key=" "`$file" > "`$temp" 2>/dev/null || true
    printf '%s=%s\n' "`$key" "`$value" >> "`$temp"
    mv "`$temp" "`$file"
}
if [ ! -f dreame_logger/.env ]; then
    cp dreame_logger/.env.example dreame_logger/.env
fi
dreame_token=`$(env_value dreame_logger/.env DREAME_CONTROL_TOKEN)
if [ -z "`$dreame_token" ] || [ "`$dreame_token" = "replace-with-long-random-token" ]; then
    if command -v openssl >/dev/null 2>&1; then
        dreame_token=`$(openssl rand -hex 32)
    else
        dreame_token=`$(printf '%s' "`$(date +%s)-`${RANDOM:-0}-`${RANDOM:-0}" | sha256sum | cut -d' ' -f1)
    fi
    set_env_value dreame_logger/.env DREAME_CONTROL_TOKEN "`$dreame_token"
fi
for key in FIBARO10_API_USERNAME FIBARO10_API_PASSWORD; do
    current=`$(env_value dreame_logger/.env "`$key")
    case "`$current" in ''|replace-with-fibaro10-password|logger)
        inherited=`$(env_value roborock_logger/.env "`$key")
        [ -n "`$inherited" ] && set_env_value dreame_logger/.env "`$key" "`$inherited"
        ;;
    esac
done
set_env_value .env DREAME_CONTROL_TOKEN "`$dreame_token"
set_env_value .env DREAME_LOGGER_URL "http://dreame_logger:8094"
set_env_value .env DREAME_EXPECTED_ROBOT_NAME "Aqua10"
[ -d "`$legacy_sun2_dir" ] && (cd "`$legacy_sun2_dir" && "$Docker" compose down || true)
export APP_COMMIT=`$(git rev-parse --short HEAD)
export APP_BUILD=`$(cat BUILD)
export PROTECT_LEDGER_BUILD=`$(cat unifi_protect_events/BUILD)
export OWNTRACKS_APP_BUILD=`$(cat owntracks_service/BUILD)
export REVENUE_APP_BUILD=`$(cat revenue_app/BUILD)
export PARKING_APP_BUILD=`$(cat parking_app/BUILD)
export SUN_APP_BUILD=`$(cat sun_app/BUILD)
export ENERGY_APP_BUILD=`$(cat energy_app/BUILD)
export OPERATIONS_APP_BUILD=`$(cat operations_app/BUILD)
export MAINTENANCE_APP_BUILD=`$(cat maintenance_app/BUILD)
export MAINTENANCE_MOBILE_BUILD=`$(cat maintenance_mobile/BUILD)
export ALARM_MOBILE_BUILD=`$(cat alarm_mobile/BUILD)
export SYSTEM_APP_BUILD=`$(cat system_app/BUILD)
export LINK_APP_BUILD=`$(cat link_app/BUILD)
"$Docker" compose -f docker-compose.qnap.yml config --quiet
"$Docker" rm -f owntracks_mqtt >/dev/null 2>&1 || true
if [ "$coreDeployValue" = "1" ]; then
    sh scripts/deploy-core-qnap.sh "$Docker"
fi
if [ "$hasComposeServicesValue" = "1" ]; then
    echo "Building changed services: $composeServices"
    "$Docker" compose -f docker-compose.qnap.yml --profile unifi-protect up -d --build --no-deps $composeServices
else
    echo "No additional Compose services are affected by this revision."
fi
if [ "$restartProxyValue" = "1" ]; then
    echo "Issuing/renewing the active internal certificate before reloading Caddy"
    DOCKER_BIN="$Docker" sh scripts/renew-internal-https.sh
    echo "Refreshing the HTTPS proxy address in the LAN neighbor table"
    "$Docker" exec fibaro10_proxy arping -I eth1 -c 3 "`${FIBARO10_LAN_GATEWAY:-192.168.20.1}" >/dev/null 2>&1 || true
fi
ready=0
while [ "`$ready" -lt 60 ]; do
    curl -fsS --max-time 5 http://192.168.20.218:8110/health >/dev/null 2>&1 && break
    ready=`$((ready + 1))
    sleep 2
done
curl -fsS --max-time 5 http://192.168.20.218:8110/health >/dev/null
if [ "$deployEasyParkValue" = "1" ]; then
    (cd easypark_downloader && "$Docker" compose up -d --build)
fi
if [ "$deployRoborockValue" = "1" ]; then
    (cd roborock_logger && "$Docker" compose -f docker-compose.qnap.yml up -d --build)
fi
if [ "$deployDreameValue" = "1" ]; then
    "$Docker" volume inspect dreame_logger_dreame_logger_data >/dev/null 2>&1 || "$Docker" volume create dreame_logger_dreame_logger_data >/dev/null
    (cd dreame_logger && "$Docker" compose -f docker-compose.qnap.yml up -d --build)
fi
roborock_ready=0
while [ "`$roborock_ready" -lt 30 ]; do
    curl -fsS --max-time 5 http://192.168.20.218:8095/health >/dev/null 2>&1 && break
    roborock_ready=`$((roborock_ready + 1))
    sleep 2
done
curl -fsS --max-time 180 http://192.168.20.218:8095/sync-now >/dev/null
if [ "$deployDreameValue" = "1" ]; then
    dreame_ready=0
    while [ "`$dreame_ready" -lt 45 ]; do
        curl -fsS --max-time 5 http://192.168.20.218:8094/health >/dev/null 2>&1 && break
        dreame_ready=`$((dreame_ready + 1))
        sleep 2
    done
    curl -fsS --max-time 5 http://192.168.20.218:8094/health >/dev/null
fi
"$Docker" exec fibaro10_proxy caddy validate --config /etc/caddy/Caddyfile || { "$Docker" logs --tail=80 fibaro10_proxy; exit 1; }
"$Docker" exec fibaro10 caddy validate --config /etc/caddy/Caddyfile || { "$Docker" logs --tail=80 fibaro10; exit 1; }
for retired in shell_app fibaro10ipad fibaro10_v1 lilletorget_mantis_revenue lilletorget_ipad_home lilletorget_drift_ipad lilletorget_drift_ipad_ionic; do
    "$Docker" rm -f "`$retired" >/dev/null 2>&1 || true
done
"$Docker" compose -f docker-compose.qnap.yml ps
(cd easypark_downloader && "$Docker" compose ps)
[ ! -f dreame_logger/.env ] || (cd dreame_logger && "$Docker" compose -f docker-compose.qnap.yml ps)
echo "Backup: `$backup_dir"
"@

Run "ssh" @("-i", $IdentityFile, $QnapHost, (NormalizeRemote $remote))

if ($broadValidation) {
    Run "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "health-check.ps1"))
    if (-not $SkipSmoke) {
        Run "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "smoke-check.ps1"))
        Run "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "smoke-domain-apps.ps1"))
    }
} else {
    $smokeArguments = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "smoke-affected.ps1"))
    if ($deployPlan.Services.Count -gt 0) { $smokeArguments += @("-Services") + @($deployPlan.Services) }
    if ($deployPlan.EasyPark) { $smokeArguments += "-EasyPark" }
    if ($deployPlan.Roborock) { $smokeArguments += "-Roborock" }
    if ($deployPlan.Dreame) { $smokeArguments += "-Dreame" }
    if ($SkipSmoke) { $smokeArguments += "-SkipRoutes" }
    Run "powershell" $smokeArguments
}
