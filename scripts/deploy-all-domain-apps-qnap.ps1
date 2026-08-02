param(
    [string]$QnapHost = "admin@192.168.20.218",
    [string]$IdentityFile = "$env:USERPROFILE\.ssh\id_ed25519_qnap_fibaro10",
    [string]$RemoteDir = "/share/CACHEDEV1_DATA/Public/containerdata/fibaro10",
    [string]$Docker = "/share/CACHEDEV1_DATA/.qpkg/container-station/usr/bin/.libs/docker"
)

$ErrorActionPreference = "Stop"
$apps = @("revenue_app", "parking_app", "sun_app", "energy_app", "operations_app", "maintenance_app", "system_app", "link_app")
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$npm = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }

foreach ($app in $apps) {
    Write-Host "Kontrollerer $app ..."
    Push-Location (Join-Path $repoRoot "$app\frontend")
    try {
        & $npm run build
        if ($LASTEXITCODE -ne 0) { throw "$app frontend build feilet" }
        & $npm audit --audit-level=moderate
        if ($LASTEXITCODE -ne 0) { throw "$app dependency audit feilet" }
    }
    finally { Pop-Location }
}

Push-Location $repoRoot
try {
    python -m pytest tests/test_domain_microapps.py -q
    if ($LASTEXITCODE -ne 0) { throw "Mikroapp-kontrakttestene feilet" }

    foreach ($app in $apps) {
        & (Join-Path $PSScriptRoot "deploy-domain-app-qnap.ps1") `
            -App $app `
            -QnapHost $QnapHost `
            -IdentityFile $IdentityFile `
            -RemoteDir $RemoteDir `
            -Docker $Docker `
            -SkipLocalChecks
        if ($LASTEXITCODE -ne 0) { throw "$app deploy feilet" }
    }
}
finally { Pop-Location }

Write-Host "Alle fagappene er bygget, kontrollert og oppdatert."
