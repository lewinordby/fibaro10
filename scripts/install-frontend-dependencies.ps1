$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$npm = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }
$frontends = @(
    "desktop_v2",
    "owntracks_service/frontend",
    "shell_app/frontend",
    "revenue_app/frontend",
    "parking_app/frontend",
    "sun_app/frontend",
    "energy_app/frontend",
    "operations_app/frontend",
    "maintenance_app/frontend",
    "system_app/frontend",
    "link_app/frontend"
)

foreach ($frontend in $frontends) {
    $directory = Join-Path $repoRoot $frontend
    Write-Host "Install frontend dependencies: $frontend"
    Push-Location $directory
    try {
        & $npm ci
        if ($LASTEXITCODE -ne 0) {
            throw "npm ci failed for $frontend with exit code $LASTEXITCODE"
        }
    }
    finally {
        Pop-Location
    }
}
