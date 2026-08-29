$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$npm = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }
$frontends = @(
    "owntracks_service/frontend"
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
