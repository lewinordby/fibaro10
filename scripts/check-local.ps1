$ErrorActionPreference = "Stop"

function Run($exe, [string[]]$arguments, [string]$WorkingDirectory = "") {
    $original = (Get-Location).Path
    if ($WorkingDirectory) {
        Set-Location $WorkingDirectory
    }
    try {
        & $exe @arguments
        if ($LASTEXITCODE -ne 0) {
            throw "$exe failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Set-Location $original
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$desktopDir = Join-Path $repoRoot "desktop_v2"
$owntracksFrontendDir = Join-Path $repoRoot "owntracks_service/frontend"
$revenueFrontendDir = Join-Path $repoRoot "revenue_app/frontend"
$parkingFrontendDir = Join-Path $repoRoot "parking_app/frontend"
$shellFrontendDir = Join-Path $repoRoot "shell_app/frontend"
$domainApps = @("sun_app", "energy_app", "operations_app", "maintenance_app", "system_app", "link_app")
$npm = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }

Write-Host "Python syntax check"
Run "python" @("-m", "py_compile", "main.py", "build_log.py", "api_contracts.py", "api_types.py", "energy_helpers.py", "migration_runner.py", "observability.py", "security.py", "roborock_domain.py", "sun2_helpers.py", "time_formatting.py", "value_parsing.py", "system_inventory.py", "microapp_backend/runtime.py", "car_info_lookup/app/main.py", "car_info_lookup/app/parsing.py", "parking_sun_linker/app/main.py", "maintenance_mobile/app/main.py", "fibaro10ipad/app/main.py", "owntracks_service/app/main.py", "revenue_app/app/main.py", "parking_app/app/main.py", "shell_app/app/main.py", "sun_app/app/main.py", "energy_app/app/main.py", "operations_app/app/main.py", "maintenance_app/app/main.py", "system_app/app/main.py", "link_app/app/main.py", "v1_reference/app/main.py", "scripts/run-migrations.py", "scripts/backfill_sunroom_alarm_history.py", "scripts/configure_energy_course_6.py", "scripts/upsert_hc3_single_door_logger_scenes.py") $repoRoot

Write-Host "Python unit tests"
Run "python" @("-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py") $repoRoot
Run "python" @("-m", "unittest", "revenue_app.tests.test_main") $repoRoot
Run "python" @("-m", "unittest", "shell_app.tests.test_main") $repoRoot
Run "python" @("-m", "pytest", "tests/test_domain_microapps.py", "tests/test_system_inventory.py", "-q") $repoRoot

Write-Host "Frontend typecheck and build"
Run $npm @("run", "check") $desktopDir

Write-Host "OwnTracks frontend typecheck and build"
Run $npm @("run", "check") $owntracksFrontendDir

Write-Host "Revenue app frontend typecheck and build"
Run $npm @("run", "build") $revenueFrontendDir

Write-Host "Parking app frontend typecheck and build"
Run $npm @("run", "build") $parkingFrontendDir

Write-Host "Shell app frontend typecheck and build"
Run $npm @("run", "build") $shellFrontendDir

foreach ($app in $domainApps) {
    Write-Host "$app frontend typecheck and build"
    Run $npm @("run", "build") (Join-Path $repoRoot "$app/frontend")
}

Write-Host "Frontend CSS parse"
Run $npm @("run", "parse:css") $desktopDir

Write-Host "Frontend CSS audit"
Run $npm @("run", "audit:css") $desktopDir

Write-Host "Frontend bundle audit"
Run $npm @("run", "audit:bundle") $desktopDir

Write-Host "Frontend route audit"
Run $npm @("run", "audit:routes") $desktopDir

Write-Host "Frontend UI smoke"
Run $npm @("run", "smoke:ui") $desktopDir

Write-Host "Git whitespace check"
Run "git" @("diff", "--check") $repoRoot

Write-Host "Local quality check OK"
