param(
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$RemoteDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker"
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$frontendDir = Join-Path $repoRoot "shell_app\frontend"
$archive = Join-Path $repoRoot "tmp\shell-app-deploy.tgz"
$remoteArchiveDir = "$RemoteDir/.deploy"
$remoteArchive = "$remoteArchiveDir/shell-app-deploy.tgz"
$npm = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }
$build = (Get-Content -LiteralPath (Join-Path $repoRoot "shell_app\BUILD") -Raw).Trim()

if (-not (Test-Path -LiteralPath $IdentityFile)) {
    throw "Mangler SSH-nøkkel: $IdentityFile"
}

Push-Location $frontendDir
try {
    & $npm run build
    if ($LASTEXITCODE -ne 0) { throw "Shell frontend build feilet" }
    & $npm audit --audit-level=moderate
    if ($LASTEXITCODE -ne 0) { throw "Shell frontend dependency audit feilet" }
}
finally {
    Pop-Location
}

Push-Location $repoRoot
try {
    python -m unittest shell_app.tests.test_main
    if ($LASTEXITCODE -ne 0) { throw "Shell backendtester feilet" }

    New-Item -ItemType Directory -Force -Path (Split-Path $archive) | Out-Null
    tar -czf $archive `
        --exclude='shell_app/frontend/node_modules' `
        --exclude='shell_app/frontend/dist' `
        --exclude='shell_app/frontend/*.tsbuildinfo' `
        --exclude='shell_app/**/__pycache__' `
        shell_app packages/mosaic-theme docker-compose.qnap.yml .dockerignore scripts/deploy-shell-app-qnap.ps1 `
        static/lilletorget-wordmark.png static/lilletorget-favicon.png
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
export SHELL_APP_BUILD="$build"
"$Docker" compose -f docker-compose.qnap.yml build shell_app
"$Docker" compose -f docker-compose.qnap.yml up -d --no-deps shell_app
for attempt in 1 2 3 4 5 6; do
  curl -fsS http://192.168.20.218:8150/ready && exit 0
  sleep 3
done
exit 1
"@
    ssh -i $IdentityFile -o BatchMode=yes $QnapHost ($remote -replace "`r`n", "`n")
    if ($LASTEXITCODE -ne 0) { throw "Shell deploy eller readiness-kontroll feilet" }
}
finally {
    Pop-Location
}

Write-Host "Lilletorget-skallet er oppdatert uten å restarte andre apper."
