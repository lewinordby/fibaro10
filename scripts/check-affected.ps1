param(
    [string[]]$Services = @(),
    [string[]]$ChangedFiles = @(),
    [switch]$EasyPark,
    [switch]$Roborock,
    [switch]$Dreame
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
. (Join-Path $PSScriptRoot "script-runtime.ps1")

function Run($exe, [string[]]$arguments, [string]$workingDirectory = $repoRoot) {
    Push-Location $workingDirectory
    try {
        & $exe @arguments
        if ($LASTEXITCODE -ne 0) { throw "$exe failed with exit code $LASTEXITCODE" }
    }
    finally {
        Pop-Location
    }
}

$pythonFiles = @($ChangedFiles | Where-Object { $_ -match '\.py$' -and (Test-Path (Join-Path $repoRoot $_)) })
if ($pythonFiles.Count -gt 0) {
    Write-Host "Python syntax: $($pythonFiles.Count) endrede filer"
    Run "python" (@("-m", "py_compile") + $pythonFiles)
}

Invoke-ProjectScript "test-deploy-plan.ps1"
Run "python" @("-m", "pytest", "tests/test_deploy_safety.py", "-q")

if ("fibaro10" -in $Services) {
    Write-Host "Kjernetester"
    Run "python" @("-m", "pytest", "tests", "-q")
}

if (@("revenue_app", "parking_app", "sun_app", "energy_app", "operations_app", "maintenance_app", "system_app", "link_app") | Where-Object { $_ -in $Services }) {
    Run "python" @("-m", "pytest", "tests/test_domain_microapps.py", "-q")
}

if ("operations_app" -in $Services) {
    Run "python" @("-m", "pytest", "tests/test_domain_microapps.py", "tests/test_roborock_door_automation.py", "tests/test_roborock_control.py", "tests/test_roborock_schedules.py", "-q")
}
if ($EasyPark) {
    Run "python" @("-m", "pytest", "tests/test_easypark_downloader.py", "tests/test_import_jobs.py", "-q")
}
if ($Roborock) {
    Run "python" @("-m", "pytest", "tests/test_roborock_control.py", "tests/test_roborock_logger_resilience.py", "tests/test_roborock_profiles.py", "tests/test_roborock_schedules.py", "tests/test_roborock_telemetry.py", "tests/test_roborock_timestamps.py", "tests/test_roborock_water.py", "tests/test_roborock_water_interlock.py", "tests/test_roborock_zones.py", "-q")
}
if ($Dreame) {
    Run "python" @("-m", "pytest", "tests/test_cleaning_robot_domain.py", "tests/test_dreame_logger.py", "-q")
}

if ("revenue_app" -in $Services) { Run "python" @("-m", "pytest", "revenue_app/tests", "-q") }
if ("parking_app" -in $Services) { Run "python" @("-m", "pytest", "parking_app/tests", "-q") }
foreach ($mobile in @("maintenance_mobile", "alarm_mobile")) {
    if ($mobile -in $Services) { Run "python" @("-m", "pytest", "$mobile/tests", "-q") }
}
if ("unifi_protect_events" -in $Services) { Run "python" @("-m", "pytest", "tests", "-q") (Join-Path $repoRoot "unifi_protect_events") }
if ("visual_anomaly_service" -in $Services) { Run "python" @("-m", "pytest", "tests", "-q") (Join-Path $repoRoot "visual_anomaly_service") }
if ("sun2_session_scraper" -in $Services) { Run "python" @("-m", "pytest", "tests/test_sun2_live_sync_policy.py", "tests/test_sun2_helpers.py", "-q") }
if ("car_info_lookup" -in $Services) { Run "python" @("-m", "pytest", "tests/test_car_info_lookup.py", "-q") }
if ("axis_camera_snapshots" -in $Services) { Run "python" @("-m", "pytest", "tests/test_axis_snapshot_retention.py", "tests/test_sun2_axis_snapshots.py", "-q") }
if ("parking_sun_linker" -in $Services) { Run "python" @("-m", "pytest", "tests/test_parking_sun_linker.py", "tests/test_parking_sun_link_logic.py", "-q") }
if ("owntracks_service" -in $Services) { Run "python" @("-m", "pytest", "tests/test_owntracks_service.py", "-q") }

Run "git" @("diff", "--check")
Write-Host "Avgrenset kvalitetskontroll OK: $($Services -join ', ')"
