param(
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$RemoteDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$frontendDir = Join-Path $repoRoot "revenue_app\frontend"
$archive = Join-Path $repoRoot "tmp\revenue-app-deploy.tgz"
$npm = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }
$build = (Get-Content -LiteralPath (Join-Path $repoRoot "revenue_app\BUILD") -Raw).Trim()

if (-not (Test-Path -LiteralPath $IdentityFile)) {
    throw "Mangler SSH-nøkkel: $IdentityFile"
}

Push-Location $frontendDir
try {
    & $npm run build
    if ($LASTEXITCODE -ne 0) { throw "Revenue frontend build feilet" }
    & $npm audit --audit-level=moderate
    if ($LASTEXITCODE -ne 0) { throw "Revenue frontend dependency audit feilet" }
}
finally {
    Pop-Location
}

Push-Location $repoRoot
try {
    python -m unittest revenue_app.tests.test_main
    if ($LASTEXITCODE -ne 0) { throw "Revenue backendtester feilet" }

    New-Item -ItemType Directory -Force -Path (Split-Path $archive) | Out-Null
    tar -czf $archive `
        --exclude='revenue_app/frontend/node_modules' `
        --exclude='revenue_app/frontend/dist' `
        --exclude='revenue_app/frontend/*.tsbuildinfo' `
        --exclude='revenue_app/**/__pycache__' `
        revenue_app packages/mosaic-theme docker-compose.qnap.yml .dockerignore scripts/deploy-revenue-app-qnap.ps1
    if ($LASTEXITCODE -ne 0) { throw "Kunne ikke lage deployarkiv" }

    scp -i $IdentityFile $archive "${QnapHost}:/tmp/revenue-app-deploy.tgz"
    if ($LASTEXITCODE -ne 0) { throw "Kunne ikke overføre deployarkiv" }

    $remote = @"
set -e
source /opt/etc/profile 2>/dev/null || true
cd "$RemoteDir"
tar -xzf /tmp/revenue-app-deploy.tgz
export APP_COMMIT=`$(git rev-parse --short HEAD 2>/dev/null || echo local)
export REVENUE_APP_BUILD="$build"
"$Docker" compose -f docker-compose.qnap.yml build revenue_app
"$Docker" compose -f docker-compose.qnap.yml up -d --no-deps revenue_app
for attempt in 1 2 3 4 5 6; do
  curl -fsS http://192.168.20.218:8151/ready && exit 0
  sleep 3
done
exit 1
"@
    ssh -i $IdentityFile -o BatchMode=yes $QnapHost ($remote -replace "`r`n", "`n")
    if ($LASTEXITCODE -ne 0) { throw "Revenue app deploy eller readiness-kontroll feilet" }
}
finally {
    Pop-Location
}

Write-Host "Revenue app er oppdatert uten å restarte Fibaro10."
