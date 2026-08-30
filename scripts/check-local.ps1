$ErrorActionPreference = "Stop"

function Run($exe, [string[]]$arguments, [string]$WorkingDirectory = "") {
    $original = (Get-Location).Path
    if ($WorkingDirectory) {
        Set-Location $WorkingDirectory
    }
    try {
        & $exe @arguments
        if ($env:OS -eq "Windows_NT" -and $exe -eq "npm.cmd" -and $LASTEXITCODE -eq -1073740791) {
            Write-Warning "Node avsluttet med sporadisk Windows/libuv-feil etter kjøring. Prøver samme kommando én gang til."
            Start-Sleep -Seconds 1
            & $exe @arguments
        }
        if ($LASTEXITCODE -ne 0) {
            throw "$exe failed with exit code $LASTEXITCODE"
        }
    }
    finally {
        Set-Location $original
    }
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$owntracksFrontendDir = Join-Path $repoRoot "owntracks_service/frontend"
$npm = if ($env:OS -eq "Windows_NT") { "npm.cmd" } else { "npm" }

Write-Host "Python syntax check"
$pythonFiles = @(& git -C $repoRoot ls-files "*.py" | Where-Object { Test-Path -LiteralPath (Join-Path $repoRoot $_) })
if ($LASTEXITCODE -ne 0 -or $pythonFiles.Count -eq 0) {
    throw "Could not enumerate tracked Python files."
}
Run "python" (@("-m", "py_compile") + $pythonFiles) $repoRoot
Run "python" @("-c", "from build_log import APP_BUILD; assert APP_BUILD == open('BUILD', encoding='utf-8').read().strip()") $repoRoot
Run "python" @("-m", "pip", "check") $repoRoot

Write-Host "Python dependency security audit"
Run "python" @("scripts/audit_python_dependencies.py") $repoRoot

Write-Host "Python unit tests"
Run "python" @("-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py") $repoRoot
Run "python" @("-m", "pytest", "tests/test_core_architecture.py", "tests/test_core_contracts.py", "tests/test_core_routers.py", "tests/test_operational_workspaces.py", "-q") $repoRoot
Run "python" @("-m", "pytest", "tests/test_summary_calculations.py", "tests/test_summary_runtime.py", "tests/test_overview_batch_queries.py", "tests/test_revenue_top_weeks.py", "tests/test_domain_top_weeks.py", "-q") $repoRoot
Run "python" @("-m", "unittest", "revenue_app.tests.test_main") $repoRoot
Run "python" @("-m", "unittest", "parking_app.tests.test_main") $repoRoot
Run "python" @("-m", "pytest", "tests/test_domain_microapps.py", "tests/test_system_inventory.py", "-q") $repoRoot
Run "python" @("-m", "pytest", "maintenance_mobile/tests", "-q") $repoRoot
Run "python" @("-m", "pytest", "alarm_mobile/tests", "-q") $repoRoot
Run "python" @("-m", "pytest", "tests", "-q") (Join-Path $repoRoot "unifi_protect_events")
Run "python" @("-m", "pytest", "tests/test_profiles.py", "-q") (Join-Path $repoRoot "visual_anomaly_service")

Write-Host "QNAP deploy plan tests"
Run "powershell" @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $PSScriptRoot "test-deploy-plan.ps1")) $repoRoot

Write-Host "Mobile JavaScript syntax"
Run "node" @("--check", "maintenance_mobile/app/static/maintenance-mobile.js") $repoRoot
Run "node" @("--check", "alarm_mobile/app/static/alarm-mobile.js") $repoRoot

Write-Host "OwnTracks frontend typecheck and build"
Run $npm @("run", "check") $owntracksFrontendDir
Run $npm @("audit", "--audit-level=moderate") $owntracksFrontendDir

Write-Host "Git whitespace check"
Run "git" @("diff", "--check") $repoRoot

Write-Host "Local quality check OK"
