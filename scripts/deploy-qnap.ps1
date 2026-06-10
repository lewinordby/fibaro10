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
    [switch]$SkipLocalCheck
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
for file in .env .env.* easypark_downloader/.env easypark_downloader/.env.*; do
    case "`$file" in .env.example|*/.env.example) continue ;; esac
    [ -f "`$file" ] || continue
    target="`$backup_dir/`$file"
    mkdir -p "`$(dirname "`$target")"
    cp -p "`$file" "`$target"
done
[ -d easypark_downloader/data ] && mkdir -p "`$backup_dir/easypark_downloader" && cp -a easypark_downloader/data "`$backup_dir/easypark_downloader/data"
git fetch origin "$Branch"
git reset --hard "origin/$Branch"
git clean -fdx -e .env -e '.env.*' -e easypark_downloader/.env -e 'easypark_downloader/.env.*' -e easypark_downloader/data/
for file in .env .env.* easypark_downloader/.env easypark_downloader/.env.*; do
    case "`$file" in .env.example|*/.env.example) continue ;; esac
    source="`$backup_dir/`$file"
    [ -f "`$source" ] || continue
    mkdir -p "`$(dirname "`$file")"
    cp -p "`$source" "`$file"
done
[ -d "`$backup_dir/easypark_downloader/data" ] && [ ! -d easypark_downloader/data ] && mkdir -p easypark_downloader && cp -a "`$backup_dir/easypark_downloader/data" easypark_downloader/data
export APP_COMMIT=`$(git rev-parse --short HEAD)
"$Docker" compose -f docker-compose.qnap.yml up -d --build fibaro10 online_dashboard
"$Docker" compose -f docker-compose.qnap.yml ps
echo "Backup: `$backup_dir"
"@

Run "ssh" @("-i", $IdentityFile, $QnapHost, (NormalizeRemote $remote))

Run "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "health-check.ps1"))
if (-not $SkipSmoke) {
    Run "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "smoke-check.ps1"))
}
