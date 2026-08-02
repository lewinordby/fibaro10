param(
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$RemoteDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$frontendDir = Join-Path $repoRoot "parking_app\frontend"
$archive = Join-Path $repoRoot "tmp\parking-app-deploy.tgz"
$npm = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }
$build = (Get-Content -LiteralPath (Join-Path $repoRoot "parking_app\BUILD") -Raw).Trim()

if (-not (Test-Path -LiteralPath $IdentityFile)) { throw "Mangler SSH-nøkkel: $IdentityFile" }

Push-Location $frontendDir
try {
    & $npm run build
    if ($LASTEXITCODE -ne 0) { throw "Parking frontend build feilet" }
    & $npm audit --audit-level=moderate
    if ($LASTEXITCODE -ne 0) { throw "Parking frontend dependency audit feilet" }
}
finally { Pop-Location }

Push-Location $repoRoot
try {
    python -m unittest parking_app.tests.test_main
    if ($LASTEXITCODE -ne 0) { throw "Parking backendtester feilet" }

    New-Item -ItemType Directory -Force -Path (Split-Path $archive) | Out-Null
    tar -czf $archive `
        --exclude='parking_app/frontend/node_modules' `
        --exclude='parking_app/frontend/dist' `
        --exclude='parking_app/frontend/*.tsbuildinfo' `
        --exclude='parking_app/**/__pycache__' `
        parking_app packages/mosaic-theme docker-compose.qnap.yml .dockerignore scripts/deploy-parking-app-qnap.ps1
    if ($LASTEXITCODE -ne 0) { throw "Kunne ikke lage deployarkiv" }

    scp -i $IdentityFile $archive "${QnapHost}:/tmp/parking-app-deploy.tgz"
    if ($LASTEXITCODE -ne 0) { throw "Kunne ikke overføre deployarkiv" }

    $remote = @"
set -e
source /opt/etc/profile 2>/dev/null || true
cd "$RemoteDir"
tar -xzf /tmp/parking-app-deploy.tgz
export APP_COMMIT=`$(git rev-parse --short HEAD 2>/dev/null || echo local)
export PARKING_APP_BUILD="$build"
"$Docker" compose -f docker-compose.qnap.yml build parking_app
"$Docker" compose -f docker-compose.qnap.yml up -d --no-deps parking_app
for attempt in 1 2 3 4 5 6 7 8; do
  curl -fsS http://192.168.20.218:8152/ready && exit 0
  sleep 3
done
exit 1
"@
    ssh -i $IdentityFile -o BatchMode=yes $QnapHost ($remote -replace "`r`n", "`n")
    if ($LASTEXITCODE -ne 0) { throw "Parking app deploy eller readiness-kontroll feilet" }
}
finally { Pop-Location }

Write-Host "Parking app er oppdatert uten å restarte Fibaro10 eller andre fagapper."
