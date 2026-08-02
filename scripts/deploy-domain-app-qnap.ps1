param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("sun_app", "energy_app", "operations_app", "maintenance_app", "system_app", "link_app")]
    [string]$App,
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$RemoteDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker",
    [switch]$SkipLocalChecks
)

$ErrorActionPreference = "Stop"
$settings = @{
    sun_app = @{ Port = 8153; BuildEnv = "SUN_APP_BUILD" }
    energy_app = @{ Port = 8154; BuildEnv = "ENERGY_APP_BUILD" }
    operations_app = @{ Port = 8155; BuildEnv = "OPERATIONS_APP_BUILD" }
    maintenance_app = @{ Port = 8156; BuildEnv = "MAINTENANCE_APP_BUILD" }
    system_app = @{ Port = 8157; BuildEnv = "SYSTEM_APP_BUILD" }
    link_app = @{ Port = 8158; BuildEnv = "LINK_APP_BUILD" }
}
$selected = $settings[$App]
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$frontendDir = Join-Path $repoRoot "$App\frontend"
$archive = Join-Path $repoRoot "tmp\$App-deploy.tgz"
$remoteArchiveDir = "$RemoteDir/.deploy"
$remoteArchive = "$remoteArchiveDir/$App-deploy.tgz"
$npm = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }
$build = (Get-Content -LiteralPath (Join-Path $repoRoot "$App\BUILD") -Raw).Trim()

if (-not (Test-Path -LiteralPath $IdentityFile)) { throw "Mangler SSH-nøkkel: $IdentityFile" }

if (-not $SkipLocalChecks) {
    Push-Location $frontendDir
    try {
        & $npm run build
        if ($LASTEXITCODE -ne 0) { throw "$App frontend build feilet" }
        & $npm audit --audit-level=moderate
        if ($LASTEXITCODE -ne 0) { throw "$App dependency audit feilet" }
    }
    finally { Pop-Location }
}

Push-Location $repoRoot
try {
    if (-not $SkipLocalChecks) {
        python -m pytest tests/test_domain_microapps.py -q
        if ($LASTEXITCODE -ne 0) { throw "Mikroapp-kontrakttestene feilet" }
    }

    New-Item -ItemType Directory -Force -Path (Split-Path $archive) | Out-Null
    tar -czf $archive `
        --exclude="$App/frontend/node_modules" `
        --exclude="$App/frontend/dist" `
        --exclude="$App/frontend/*.tsbuildinfo" `
        --exclude="$App/**/__pycache__" `
        $App microapp_backend packages/mosaic-theme packages/microapp-ui docker-compose.qnap.yml .dockerignore
    if ($LASTEXITCODE -ne 0) { throw "Kunne ikke lage deployarkiv" }

    ssh -i $IdentityFile -o BatchMode=yes $QnapHost "mkdir -p '$remoteArchiveDir'"
    if ($LASTEXITCODE -ne 0) { throw "Kunne ikke klargjøre deploymappen på QNAP" }
    scp -i $IdentityFile $archive "${QnapHost}:$remoteArchive"
    if ($LASTEXITCODE -ne 0) { throw "Kunne ikke overføre deployarkiv" }

    $remote = @"
set -e
source /opt/etc/profile 2>/dev/null || true
cd "$RemoteDir"
tar -xzf "$remoteArchive"
export APP_COMMIT=`$(git rev-parse --short HEAD 2>/dev/null || echo local)
export $($selected.BuildEnv)="$build"
"$Docker" compose -f docker-compose.qnap.yml build "$App"
"$Docker" compose -f docker-compose.qnap.yml up -d --no-deps "$App"
for attempt in 1 2 3 4 5 6 7 8 9 10; do
  curl -fsS "http://192.168.20.218:$($selected.Port)/ready" && exit 0
  sleep 3
done
exit 1
"@
    ssh -i $IdentityFile -o BatchMode=yes $QnapHost ($remote -replace "`r`n", "`n")
    if ($LASTEXITCODE -ne 0) { throw "$App deploy eller readiness-kontroll feilet" }
}
finally { Pop-Location }

Write-Host "$App build $build er oppdatert uten å restarte Fibaro10 eller andre fagapper."
