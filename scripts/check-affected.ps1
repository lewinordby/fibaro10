param(
    [string[]]$Services = @(),
    [string[]]$ChangedFiles = @(),
    [switch]$EasyPark,
    [switch]$Roborock,
    [switch]$Dreame
)

$ErrorActionPreference = "Stop"
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

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

Run "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "test-deploy-plan.ps1"))

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
if ($Roborock) {
    Run "python" @("-m", "pytest", "tests/test_roborock_control.py", "tests/test_roborock_logger_resilience.py", "tests/test_roborock_profiles.py", "tests/test_roborock_schedules.py", "tests/test_roborock_telemetry.py", "tests/test_roborock_timestamps.py", "tests/test_roborock_water.py", "tests/test_roborock_water_interlock.py", "tests/test_roborock_zones.py", "-q")
}
if ($Dreame) {
    Run "python" @("-m", "pytest", "tests/test_cleaning_robot_domain.py", "tests/test_dreame_logger.py", "-q")
}

Run "git" @("diff", "--check")
Write-Host "Avgrenset kvalitetskontroll OK: $($Services -join ', ')"
